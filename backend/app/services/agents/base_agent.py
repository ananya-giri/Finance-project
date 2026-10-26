import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("multi_agent")

class AgentContext:
    """
    FR-015: Shared execution context provided to every specialized AI agent.
    Carries target ticker, database session, input parameters, and shared blackboard memory.
    """
    def __init__(
        self,
        ticker: str,
        db: Session,
        parameters: Optional[Dict[str, Any]] = None,
        shared_memory: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None
    ):
        self.ticker = ticker.upper().strip()
        self.db = db
        self.parameters = parameters or {}
        self.shared_memory = shared_memory if shared_memory is not None else {}
        self.run_id = run_id or f"run_{int(time.time()*1000)}"

    def get_shared(self, key: str, default: Any = None) -> Any:
        return self.shared_memory.get(key, default)

    def set_shared(self, key: str, value: Any):
        self.shared_memory[key] = value


class AgentResult:
    """
    Standardized result payload returned by every specialized AI agent.
    """
    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        status: str = "COMPLETED",
        confidence_score: float = 0.85,
        execution_time_ms: int = 0,
        summary: str = "",
        data: Optional[Dict[str, Any]] = None,
        key_insights: Optional[List[str]] = None,
        error: Optional[str] = None
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.status = status
        self.confidence_score = confidence_score
        self.execution_time_ms = execution_time_ms
        self.summary = summary
        self.data = data or {}
        self.key_insights = key_insights or []
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status,
            "confidence_score": round(self.confidence_score, 4),
            "execution_time_ms": self.execution_time_ms,
            "summary": self.summary,
            "data": self.data,
            "key_insights": self.key_insights,
            "error": self.error
        }


class BaseAgent(ABC):
    """
    FR-015: Abstract Base Class for Specialized AI Agents.
    Defines metadata, capabilities, lifecycle, and standardized execution wrapper.
    """
    agent_id: str = "BASE_AGENT"
    name: str = "Base Agent"
    role: str = "Generic AI Agent"
    description: str = "Base interface for all specialized financial agents"
    version: str = "1.0.0"
    capabilities: List[str] = []
    fr_code: str = "FR-015"

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "version": self.version,
            "capabilities": self.capabilities,
            "fr_code": self.fr_code
        }

    def run(self, context: AgentContext) -> AgentResult:
        """
        Lifecycle execution wrapper with performance timing, error containment, and logging.
        """
        start_time = time.perf_counter()
        logger.info(f"[{self.agent_id}] Starting execution for ticker {context.ticker}...")
        try:
            result = self.execute(context)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            result.execution_time_ms = elapsed_ms
            logger.info(f"[{self.agent_id}] Completed in {elapsed_ms}ms with status {result.status}")
            return result
        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.exception(f"[{self.agent_id}] Execution error: {str(e)}")
            return AgentResult(
                agent_id=self.agent_id,
                agent_name=self.name,
                status="FAILED",
                confidence_score=0.0,
                execution_time_ms=elapsed_ms,
                summary=f"Agent encountered an execution failure: {str(e)}",
                error=str(e),
                data={"error_details": str(e)}
            )

    @abstractmethod
    def execute(self, context: AgentContext) -> AgentResult:
        """
        Agent-specific reasoning and quantitative processing logic.
        Must be implemented by subclasses.
        """
        pass


class AgentRegistry:
    """
    FR-015: Central Registry managing all specialized AI agents.
    Provides introspection, discovery, and dynamic execution.
    """
    _agents: Dict[str, BaseAgent] = {}

    @classmethod
    def register(cls, agent: BaseAgent):
        cls._agents[agent.agent_id] = agent
        logger.info(f"Registered Agent: {agent.agent_id} ({agent.name}) - {agent.fr_code}")

    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[BaseAgent]:
        return cls._agents.get(agent_id.upper().strip())

    @classmethod
    def list_agents(cls) -> List[Dict[str, Any]]:
        return [agent.get_metadata() for agent in cls._agents.values()]

    @classmethod
    def get_all(cls) -> Dict[str, BaseAgent]:
        return dict(cls._agents)
