import uuid
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.models.structured_metrics import StructuredMetric
from backend.app.models.company import Company
from backend.app.models.predictions import PredictionRun, ModelRegistry

# Metric field mapping
METRIC_FIELDS = {
    "REVENUE": "revenue",
    "EBITDA": "ebitda",
    "PROFIT": "net_profit",
    "CASH_FLOW": "operating_cash_flow",
    "DEMAND": "revenue"  # Demand proxy = revenue growth
}

# Horizon → number of future periods
HORIZON_PERIODS = {
    "QUARTERLY": 4,
    "ANNUAL": 1,
    "THREE_YEAR": 3,
    "FIVE_YEAR": 5
}

class PredictionEngine:

    @staticmethod
    def _get_historical_data(db: Session, ticker: str, metric_field: str, period_type: str = "ANNUAL") -> pd.DataFrame:
        """Fetch and prepare historical time series data."""
        from sqlalchemy import asc
        company = db.query(Company).filter(Company.ticker == ticker.upper()).first()
        if not company:
            raise ValueError(f"Company {ticker} not found. Please ingest data first.")

        metrics = db.query(StructuredMetric).filter(
            StructuredMetric.company_id == company.id,
            StructuredMetric.period_type == period_type
        ).order_by(asc(StructuredMetric.period_end_date)).all()

        if len(metrics) < 3:
            raise ValueError(f"Insufficient historical data for {ticker}. Need at least 3 data points.")

        data = []
        for m in metrics:
            value = getattr(m, metric_field, None)
            if value is not None and m.period_end_date:
                data.append({"ds": pd.Timestamp(m.period_end_date), "y": float(value), "period": m.fiscal_period})

        df = pd.DataFrame(data).dropna()
        if len(df) < 3:
            raise ValueError(f"Insufficient non-null values for metric '{metric_field}' for {ticker}.")
        return df

    @staticmethod
    def _get_demand_data(db: Session, ticker: str, period_type: str = "ANNUAL") -> pd.DataFrame:
        """FR-029: Demand volume index proxy normalized to base 100.0."""
        from sqlalchemy import asc
        company = db.query(Company).filter(Company.ticker == ticker.upper()).first()
        if not company:
            raise ValueError(f"Company {ticker} not found. Please ingest data first.")

        metrics = db.query(StructuredMetric).filter(
            StructuredMetric.company_id == company.id,
            StructuredMetric.period_type == period_type
        ).order_by(asc(StructuredMetric.period_end_date)).all()

        if len(metrics) < 3 and period_type == "QUARTERLY":
            metrics = db.query(StructuredMetric).filter(
                StructuredMetric.company_id == company.id,
                StructuredMetric.period_type == "ANNUAL"
            ).order_by(asc(StructuredMetric.period_end_date)).all()

        revenues = [
            (pd.Timestamp(m.period_end_date), float(m.revenue), m.fiscal_period)
            for m in metrics if m.revenue is not None and m.period_end_date
        ]

        if len(revenues) < 3:
            raise ValueError(f"Insufficient revenue data for DEMAND forecast for {ticker}. Need at least 3 data points.")

        base_rev = revenues[0][1] if revenues[0][1] != 0 else 1.0
        data = []
        for dt, rev, period in revenues:
            demand_idx = (rev / base_rev) * 100.0
            data.append({"ds": dt, "y": round(demand_idx, 2), "period": period})

        df = pd.DataFrame(data).dropna()
        if len(df) < 3:
            raise ValueError(f"Insufficient demand index data for {ticker}.")
        return df

    @staticmethod
    def _make_quarter_label(ts: pd.Timestamp) -> str:
        """Return 'Q1 2026' style label from a timestamp."""
        return f"Q{(ts.month - 1) // 3 + 1} {ts.year}"

    @staticmethod
    def _run_prophet(df: pd.DataFrame, future_periods: int, is_quarterly: bool = False) -> Tuple[List[Dict], Dict]:
        """Run Prophet model and return forecasts + metrics.
        FR-030: When is_quarterly=True, returns 4 future quarters with proper 'Q1 YYYY' labels.
        """
        try:
            from prophet import Prophet
            model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False, interval_width=0.95)
            train_df = df[["ds", "y"]].copy()
            model.fit(train_df)

            # FR-030: For quarterly use QE freq, for annual use YE
            freq = "QE" if is_quarterly else "YE"
            future = model.make_future_dataframe(periods=future_periods, freq=freq)
            forecast = model.predict(future)

            # Cross-validation metrics (simple holdout)
            if len(df) >= 4:
                train = train_df.iloc[:-2]
                test = train_df.iloc[-2:]
                m2 = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
                m2.fit(train)
                pred = m2.predict(pd.DataFrame({"ds": test["ds"]}))
                y_true = test["y"].values
                y_pred = pred["yhat"].values
                rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
                mae = float(np.mean(np.abs(y_true - y_pred)))
                mape = float(np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100)
            else:
                rmse, mae, mape = 0.0, 0.0, 0.0

            future_forecast = forecast.tail(future_periods)
            forecasts = []
            for _, row in future_forecast.iterrows():
                if is_quarterly:
                    period_label = PredictionEngine._make_quarter_label(row["ds"])
                else:
                    period_label = str(row["ds"].year)
                forecasts.append({
                    "period": period_label,
                    "value": float(row["yhat"]),
                    "lower": float(row["yhat_lower"]),
                    "upper": float(row["yhat_upper"])
                })

            return forecasts, {"rmse": rmse, "mae": mae, "mape": mape}
        except Exception as e:
            return [], {"rmse": 999999, "mae": 999999, "mape": 999999, "error": str(e)}

    @staticmethod
    def _run_arima(df: pd.DataFrame, future_periods: int, is_quarterly: bool = False) -> Tuple[List[Dict], Dict]:
        """Run ARIMA model."""
        try:
            from statsmodels.tsa.arima.model import ARIMA
            y = df["y"].values

            # Fit ARIMA(1,1,1)
            model = ARIMA(y, order=(1, 1, 1))
            fitted = model.fit()

            # Forecast
            forecast_obj = fitted.get_forecast(steps=future_periods)
            forecast_result = forecast_obj.predicted_mean
            conf_int = forecast_obj.conf_int()

            # Metrics via holdout
            if len(y) >= 4:
                train_y = y[:-2]
                test_y = y[-2:]
                m2 = ARIMA(train_y, order=(1, 1, 1)).fit()
                pred = m2.forecast(steps=2)
                rmse = float(np.sqrt(np.mean((test_y - pred) ** 2)))
                mae = float(np.mean(np.abs(test_y - pred)))
                mape = float(np.mean(np.abs((test_y - pred) / (test_y + 1e-8))) * 100)
            else:
                rmse, mae, mape = 0.0, 0.0, 0.0

            last_dt = df["ds"].iloc[-1]
            forecasts = []
            for i in range(future_periods):
                if is_quarterly:
                    # Advance by quarter steps from last date
                    next_dt = last_dt + pd.DateOffset(months=3 * (i + 1))
                    period_label = PredictionEngine._make_quarter_label(next_dt)
                else:
                    period_label = str(last_dt.year + i + 1)
                forecasts.append({
                    "period": period_label,
                    "value": float(forecast_result.iloc[i]),
                    "lower": float(conf_int.iloc[i, 0]),
                    "upper": float(conf_int.iloc[i, 1])
                })

            return forecasts, {"rmse": rmse, "mae": mae, "mape": mape}
        except Exception as e:
            return [], {"rmse": 999999, "mae": 999999, "mape": 999999, "error": str(e)}

    @staticmethod
    def _run_xgboost(df: pd.DataFrame, future_periods: int, is_quarterly: bool = False) -> Tuple[List[Dict], Dict]:
        """Run XGBoost regression with lag features."""
        try:
            try:
                import xgboost as xgb
                model_cls = lambda: xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
            except ImportError:
                from sklearn.ensemble import GradientBoostingRegressor
                model_cls = lambda: GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)

            y = df["y"].values
            n = len(y)

            # Create lag features
            X, Y = [], []
            lag = min(3, n - 1)
            for i in range(lag, n):
                X.append(y[i-lag:i])
                Y.append(y[i])
            X, Y = np.array(X), np.array(Y)

            if len(X) < 2:
                return [], {"rmse": 999999, "mae": 999999, "mape": 999999, "error": "insufficient data"}

            # Holdout split
            split = max(1, len(X) - 2)
            X_train, X_test = X[:split], X[split:]
            Y_train, Y_test = Y[:split], Y[split:]

            model = model_cls()
            model.fit(X_train, Y_train)

            if len(X_test) > 0:
                pred = model.predict(X_test)
                rmse = float(np.sqrt(np.mean((Y_test - pred) ** 2)))
                mae = float(np.mean(np.abs(Y_test - pred)))
                mape = float(np.mean(np.abs((Y_test - pred) / (Y_test + 1e-8))) * 100)
            else:
                rmse, mae, mape = 0.0, 0.0, 0.0

            # Generate future forecasts
            last_window = list(y[-lag:])
            forecasts = []
            last_dt = df["ds"].iloc[-1]
            last_year = last_dt.year
            for i in range(future_periods):
                x_input = np.array([last_window[-lag:]])
                pred_val = float(model.predict(x_input)[0])
                if is_quarterly:
                    next_dt = last_dt + pd.DateOffset(months=3 * (i + 1))
                    period_label = PredictionEngine._make_quarter_label(next_dt)
                else:
                    period_label = str(last_year + i + 1)
                forecasts.append({
                    "period": period_label,
                    "value": pred_val,
                    "lower": pred_val * 0.9,
                    "upper": pred_val * 1.1
                })
                last_window.append(pred_val)

            return forecasts, {"rmse": rmse, "mae": mae, "mape": mape}
        except Exception as e:
            return [], {"rmse": 999999, "mae": 999999, "mape": 999999, "error": str(e)}

    @staticmethod
    def _run_linear(df: pd.DataFrame, future_periods: int, is_quarterly: bool = False) -> Tuple[List[Dict], Dict]:
        """Run Linear Regression as baseline model."""
        try:
            from sklearn.linear_model import LinearRegression

            y = df["y"].values
            n = len(y)
            X = np.arange(n).reshape(-1, 1)

            model = LinearRegression()

            # Holdout
            if n >= 4:
                model.fit(X[:-2], y[:-2])
                pred = model.predict(X[-2:])
                rmse = float(np.sqrt(np.mean((y[-2:] - pred) ** 2)))
                mae = float(np.mean(np.abs(y[-2:] - pred)))
                mape = float(np.mean(np.abs((y[-2:] - pred) / (y[-2:] + 1e-8))) * 100)
            else:
                rmse, mae, mape = 0.0, 0.0, 0.0

            model.fit(X, y)

            last_dt = df["ds"].iloc[-1]
            last_year = last_dt.year
            forecasts = []
            for i in range(future_periods):
                x_fut = np.array([[n + i]])
                pred_val = float(model.predict(x_fut)[0])
                if is_quarterly:
                    next_dt = last_dt + pd.DateOffset(months=3 * (i + 1))
                    period_label = PredictionEngine._make_quarter_label(next_dt)
                else:
                    period_label = str(last_year + i + 1)
                forecasts.append({
                    "period": period_label,
                    "value": pred_val,
                    "lower": pred_val * 0.85,
                    "upper": pred_val * 1.15
                })

            return forecasts, {"rmse": rmse, "mae": mae, "mape": mape}
        except Exception as e:
            return [], {"rmse": 999999, "mae": 999999, "mape": 999999, "error": str(e)}

    @classmethod
    def run_prediction(cls, db: Session, ticker: str, forecast_type: str, horizon: str) -> Dict[str, Any]:
        """Main entry point: run all models, compare, store results (FR-028 to FR-032).
        FR-029: DEMAND type uses revenue growth rate as proxy.
        FR-030: QUARTERLY horizon returns 4 future quarters with 'Q1 YYYY' labels.
        """
        run_id = str(uuid.uuid4())[:16]
        forecast_type_upper = forecast_type.upper()
        horizon_upper = horizon.upper()
        future_periods = HORIZON_PERIODS.get(horizon_upper, 1)
        is_quarterly = (horizon_upper == "QUARTERLY")

        # FR-029: DEMAND type uses demand index series (base 100)
        period_type = "QUARTERLY" if is_quarterly else "ANNUAL"
        if forecast_type_upper == "DEMAND":
            df = cls._get_demand_data(db, ticker, period_type)
            historical = [
                {
                    "period": PredictionEngine._make_quarter_label(row["ds"]) if is_quarterly else str(row["ds"].year),
                    "value": round(float(row["y"]), 2),
                    "unit": "Demand Index (Base 100)"
                }
                for _, row in df.iterrows()
            ]
        else:
            metric_field = METRIC_FIELDS.get(forecast_type_upper, "revenue")
            # FR-030: Fetch quarterly data when horizon is QUARTERLY
            try:
                df = cls._get_historical_data(db, ticker, metric_field, period_type)
            except ValueError:
                # Fallback to ANNUAL if quarterly data insufficient
                df = cls._get_historical_data(db, ticker, metric_field, "ANNUAL")
                is_quarterly = False

            historical = [
                {
                    "period": PredictionEngine._make_quarter_label(row["ds"]) if is_quarterly else str(row["ds"].year),
                    "value": float(row["y"])
                }
                for _, row in df.iterrows()
            ]

        # Run all models (FR-031) — pass is_quarterly flag for proper labels
        models_data = []
        all_forecasts = {}

        for model_name, run_fn in [
            ("Prophet", cls._run_prophet),
            ("ARIMA", cls._run_arima),
            ("XGBoost", cls._run_xgboost),
            ("Linear", cls._run_linear)
        ]:
            forecasts, metrics = run_fn(df, future_periods, is_quarterly)
            model_result = {
                "model": model_name,
                "rmse": round(metrics.get("rmse", 0), 2),
                "mae": round(metrics.get("mae", 0), 2),
                "mape": round(metrics.get("mape", 0), 2),
                "status": "SUCCESS" if forecasts else "FAILED",
                "error": metrics.get("error"),
                "is_best": False
            }
            models_data.append(model_result)
            all_forecasts[model_name] = forecasts

        # Auto-select best model by MAPE (FR-032)
        successful = [m for m in models_data if m["status"] == "SUCCESS"]
        best_model = min(successful, key=lambda m: m["mape"]) if successful else models_data[0]
        best_model["is_best"] = True

        # Store in DB
        run = PredictionRun(
            run_id=run_id,
            ticker=ticker.upper(),
            forecast_type=forecast_type_upper,
            horizon=horizon_upper,
            best_model=best_model["model"],
            best_mape=best_model["mape"],
            models_json=json.dumps(models_data),
            historical_json=json.dumps(historical),
            forecasts_json=json.dumps(all_forecasts),
            status="COMPLETED"
        )
        db.add(run)

        # Update model registry (FR-032)
        for m in models_data:
            reg = ModelRegistry(
                ticker=ticker.upper(),
                forecast_type=forecast_type_upper,
                model_name=m["model"],
                rmse=m["rmse"],
                mae=m["mae"],
                mape=m["mape"],
                is_best=(m["model"] == best_model["model"]),
                data_points_used=len(df)
            )
            db.add(reg)

        db.commit()

        return {
            "run_id": run_id,
            "ticker": ticker.upper(),
            "forecast_type": forecast_type_upper,
            "horizon": horizon_upper,
            "best_model": best_model["model"],
            "best_mape": best_model["mape"],
            "models": models_data,
            "historical": historical,
            "forecasts": all_forecasts,
            "status": "COMPLETED"
        }

    @classmethod
    def retrain_models(cls, db: Session, ticker: str) -> Dict[str, Any]:
        """FR-033: Retrain prediction models for a ticker with latest data.
        Updates retrained_at on existing PredictionRun rows and logs to DB.
        """
        retrained_at = datetime.utcnow()
        results = []
        forecast_types = ["REVENUE", "EBITDA", "PROFIT", "CASH_FLOW", "DEMAND"]

        for ft in forecast_types:
            try:
                result = cls.run_prediction(db, ticker, ft, "ANNUAL")
                results.append({"forecast_type": ft, "status": "RETRAINED", "best_model": result["best_model"]})
            except Exception as e:
                results.append({"forecast_type": ft, "status": "FAILED", "error": str(e)})

        # FR-033: Update retrained_at on all existing PredictionRun rows for this ticker
        try:
            existing_runs = db.query(PredictionRun).filter(
                PredictionRun.ticker == ticker.upper()
            ).all()
            for run in existing_runs:
                run.retrained_at = retrained_at
                run.is_retrained = True
            db.commit()
        except Exception as e:
            db.rollback()

        return {
            "ticker": ticker.upper(),
            "models_retrained": results,
            "retrained_at": retrained_at.isoformat(),
            "runs_updated": len(existing_runs) if 'existing_runs' in dir() else 0
        }
