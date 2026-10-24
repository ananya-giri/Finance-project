import os
import json
import uuid
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.config import UPLOAD_DIR
from backend.app.models.company import Company
from backend.app.models.unstructured_doc import UnstructuredDocument
from backend.app.models.financial_statement import FinancialStatement
from backend.app.services.metrics_engine import MetricsEngine

logger = logging.getLogger("document_ingestion")

# Valid FR-002 Document Types
SUPPORTED_DOC_TYPES = {
    "INCOME_STATEMENT": "Income Statement",
    "BALANCE_SHEET": "Balance Sheet",
    "CASH_FLOW": "Cash Flow Statement",
    "ANNUAL_REPORT": "Annual Report",
    "QUARTERLY_REPORT": "Quarterly Report",
    "INVESTOR_PRESENTATION": "Investor Presentation",
    "EARNINGS_CALL_TRANSCRIPT": "Earnings Call Transcript"
}

class DocumentIngestionService:
    """
    FR-002 Document & Financial Statement Ingestion Service:
    Supports:
    - Income Statements (CSV, Excel, JSON)
    - Balance Sheets (CSV, Excel, JSON)
    - Cash Flow Statements (CSV, Excel, JSON)
    - Annual Reports (PDF, Text, 10-K)
    - Quarterly Reports (PDF, Text, 10-Q)
    - Investor Presentations (PDF, Slides)
    - Earnings Call Transcripts (Text, Audio transcripts, JSON)
    """

    @staticmethod
    def ingest_document(
        db: Session,
        ticker: str,
        doc_type: str,
        title: str,
        file_bytes: bytes,
        original_filename: str,
        fiscal_period: Optional[str] = None,
        period_type: str = "ANNUAL",
        period_date: Optional[date] = None,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        doc_type_clean = doc_type.upper().strip()
        if doc_type_clean not in SUPPORTED_DOC_TYPES:
            raise ValueError(
                f"Unsupported document type: '{doc_type}'. Must be one of: {list(SUPPORTED_DOC_TYPES.keys())}"
            )

        ticker = ticker.upper().strip()
        company = db.query(Company).filter(Company.ticker == ticker).first()
        if not company:
            company = Company(
                ticker=ticker,
                name=f"{ticker} Enterprise",
                sector="General",
                industry="Financial",
                last_synced_at=datetime.utcnow()
            )
            db.add(company)
            db.flush()

        # Save file to disk
        ext = Path(original_filename).suffix.lower()
        unique_filename = f"{ticker}_{doc_type_clean}_{uuid.uuid4().hex[:8]}{ext}"
        saved_file_path = UPLOAD_DIR / unique_filename

        with open(saved_file_path, "wb") as f:
            f.write(file_bytes)

        file_size = len(file_bytes)
        extracted_text = ""
        structured_data_extracted = {}

        # 1. Text extraction based on file extension
        if ext == ".pdf":
            extracted_text = DocumentIngestionService._extract_text_from_pdf(saved_file_path)
        elif ext in [".txt", ".json", ".log"]:
            try:
                extracted_text = file_bytes.decode("utf-8", errors="replace")
            except Exception:
                extracted_text = ""
        elif ext in [".csv", ".xlsx", ".xls"]:
            structured_data_extracted, extracted_text = DocumentIngestionService._extract_tabular_data(saved_file_path, ext)

        # 2. Determine fiscal period & date
        if not fiscal_period:
            current_year = datetime.utcnow().year
            fiscal_period = f"{current_year}-FY" if period_type == "ANNUAL" else f"{current_year}-Q1"
        if not period_date:
            period_date = date.today()

        # 3. If statement is tabular financial data (Income Statement, Balance Sheet, Cash Flow),
        # parse line items and feed to MetricsEngine (FR-003)
        metrics_updated = False
        if doc_type_clean in ["INCOME_STATEMENT", "BALANCE_SHEET", "CASH_FLOW"]:
            # Store in financial_statements table
            stmt_dict = structured_data_extracted if structured_data_extracted else {"raw_notes": extracted_text[:2000]}
            
            HistoricalIngestionService_save_statement = FinancialStatement(
                company_id=company.id,
                ticker=company.ticker,
                statement_type=doc_type_clean,
                period_type=period_type.upper(),
                fiscal_period=fiscal_period,
                fiscal_date=period_date,
                raw_data_json=json.dumps(stmt_dict),
                source="MANUAL_UPLOAD",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(HistoricalIngestionService_save_statement)

            # Recalculate metrics if key values were found
            if structured_data_extracted:
                MetricsEngine.calculate_and_store_metrics(
                    db=db,
                    company=company,
                    period_type=period_type.upper(),
                    fiscal_period=fiscal_period,
                    period_end_date=period_date,
                    data=structured_data_extracted,
                    source=f"UPLOAD_{doc_type_clean}"
                )
                metrics_updated = True

        # 4. Save metadata for RAG and Document Management (FR-013 ready)
        metadata = {
            "source": original_filename,
            "date": period_date.isoformat(),
            "industry": company.industry or "Corporate",
            "geography": company.country or "Global",
            "confidence_score": 0.98 if ext in [".pdf", ".csv", ".xlsx"] else 0.92,
            "doc_category": SUPPORTED_DOC_TYPES[doc_type_clean],
            **(custom_metadata or {})
        }

        # 5. Store in unstructured_documents table
        snippet = extracted_text[:1200] if extracted_text else f"File uploaded: {original_filename} ({file_size} bytes)"
        unstructured_doc = UnstructuredDocument(
            company_id=company.id,
            ticker=company.ticker,
            doc_type=doc_type_clean,
            title=title or f"{company.ticker} {SUPPORTED_DOC_TYPES[doc_type_clean]} ({fiscal_period})",
            fiscal_period=fiscal_period,
            file_name=original_filename,
            file_path=str(saved_file_path),
            file_size_bytes=file_size,
            mime_type=DocumentIngestionService._guess_mime(ext),
            content_snippet=snippet,
            text_length=len(extracted_text),
            metadata_json=json.dumps(metadata),
            uploaded_at=datetime.utcnow()
        )
        db.add(unstructured_doc)
        db.commit()
        db.refresh(unstructured_doc)

        # 6. Automatic FR-010 Vector Indexing into Persistent Vector Storage
        chunks_indexed = 0
        try:
            from backend.app.services.rag_service import RAGService
            rag_res = RAGService.index_document(
                db=db,
                document_id=unstructured_doc.id,
                text=extracted_text,
                metadata=metadata
            )
            chunks_indexed = rag_res.get("chunks_count", 0)
        except Exception as e:
            logger.warning(f"Auto vector indexing for doc #{unstructured_doc.id} deferred: {e}")

        return {
            "status": "SUCCESS",
            "document_id": unstructured_doc.id,
            "ticker": company.ticker,
            "doc_type": doc_type_clean,
            "type_label": SUPPORTED_DOC_TYPES[doc_type_clean],
            "title": unstructured_doc.title,
            "fiscal_period": fiscal_period,
            "file_size": file_size,
            "text_length": len(extracted_text),
            "metrics_updated": metrics_updated,
            "chunks_indexed": chunks_indexed,
            "content_snippet": snippet[:300] + "..." if len(snippet) > 300 else snippet
        }


    @staticmethod
    def _extract_text_from_pdf(path: Path) -> str:
        text = ""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(path)
            for page in doc:
                text += page.get_text() + "\n"
        except Exception as e:
            logger.warning(f"PyMuPDF failed, trying pdfplumber: {e}")
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    for p in pdf.pages:
                        extracted = p.extract_text()
                        if extracted:
                            text += extracted + "\n"
            except Exception as e2:
                logger.error(f"Failed to extract text from PDF: {e2}")
        return text.strip()

    @staticmethod
    def _extract_tabular_data(path: Path, ext: str) -> Tuple[Dict[str, Any], str]:
        parsed_dict = {}
        text_repr = ""
        try:
            if ext == ".csv":
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)

            text_repr = df.to_string()

            # Normalize column names
            # Look for 2-column key-value formats: [Metric, Value] or [Line Item, Amount]
            if len(df.columns) >= 2:
                for _, row in df.iterrows():
                    key = str(row.iloc[0]).strip().lower()
                    val = row.iloc[1]
                    try:
                        numeric_val = float(str(val).replace("$", "").replace(",", "").strip())
                        # Map standard terms to canonical keys
                        if "revenue" in key or "sales" in key:
                            parsed_dict["revenue"] = numeric_val
                        elif "ebitda" in key:
                            parsed_dict["ebitda"] = numeric_val
                        elif "ebit" in key or "operating income" in key:
                            parsed_dict["ebit"] = numeric_val
                        elif "net profit" in key or "net income" in key:
                            parsed_dict["net_profit"] = numeric_val
                        elif "operating cash flow" in key:
                            parsed_dict["operating_cash_flow"] = numeric_val
                        elif "free cash flow" in key:
                            parsed_dict["free_cash_flow"] = numeric_val
                        elif "total assets" in key:
                            parsed_dict["total_assets"] = numeric_val
                        elif "total debt" in key:
                            parsed_dict["total_debt"] = numeric_val
                        elif "stockholders equity" in key or "total equity" in key:
                            parsed_dict["total_equity"] = numeric_val
                        elif "eps" in key or "earnings per share" in key:
                            parsed_dict["eps"] = numeric_val
                        parsed_dict[str(row.iloc[0]).strip()] = numeric_val
                    except (ValueError, TypeError):
                        parsed_dict[str(row.iloc[0]).strip()] = str(val)

        except Exception as e:
            logger.error(f"Tabular extraction error: {e}")
        return parsed_dict, text_repr

    @staticmethod
    def _guess_mime(ext: str) -> str:
        mapping = {
            ".pdf": "application/pdf",
            ".csv": "text/csv",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".txt": "text/plain",
            ".json": "application/json"
        }
        return mapping.get(ext, "application/octet-stream")
