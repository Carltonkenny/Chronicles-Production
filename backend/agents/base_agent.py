import hashlib
import time
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

from config import CONFIG
from schemas import WorkOrder, WorkResult, AgentLineage
from logger_config import setup_logger

logger = setup_logger("BaseAgent")


class BaseAgent(ABC):
    agent_type: str = "base_agent"

    def __init__(self, timeout_ms: int = None):
        self.timeout_ms = timeout_ms or CONFIG.AGENT_TIMEOUT_S * 1000
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.wall_time_ms: float = 0.0
        self.tokens_used: int = 0

    async def execute(self, work_order: WorkOrder) -> WorkResult:
        self.started_at = datetime.utcnow()
        start_time = time.time()

        logger.info(
            f"[{self.agent_type}] Starting execution "
            f"(story_hash={work_order.story_hash}, priority={work_order.priority})"
        )

        try:
            cache_key = self._compute_cache_key(work_order)
            cached_result = await self._check_cache(cache_key)
            if cached_result:
                logger.info(f"[{self.agent_type}] Cache hit")
                return cached_result

            result = await asyncio.wait_for(
                self._execute_internal(work_order),
                timeout=self.timeout_ms / 1000.0
            )

            self.completed_at = datetime.utcnow()
            self.wall_time_ms = (time.time() - start_time) * 1000

            await self._write_lineage(work_order, result, success=True)

            if result.success:
                await self._save_to_cache(cache_key, result)

            logger.info(
                f"[{self.agent_type}] Completed in {self.wall_time_ms:.1f}ms "
                f"(success={result.success}, tokens={self.tokens_used})"
            )

            return result

        except asyncio.TimeoutError:
            self.completed_at = datetime.utcnow()
            self.wall_time_ms = (time.time() - start_time) * 1000

            error_msg = f"Agent timed out after {self.timeout_ms}ms"
            logger.error(f"[{self.agent_type}] {error_msg}")

            result = WorkResult(
                success=False,
                error_message=error_msg,
                wall_time_ms=self.wall_time_ms,
                tokens_used=self.tokens_used
            )

            await self._write_lineage(work_order, result, success=False)
            return result

        except Exception as e:
            self.completed_at = datetime.utcnow()
            self.wall_time_ms = (time.time() - start_time) * 1000

            error_msg = f"Agent execution failed: {str(e)}"
            logger.exception(f"[{self.agent_type}] {error_msg}")

            result = WorkResult(
                success=False,
                error_message=error_msg,
                wall_time_ms=self.wall_time_ms,
                tokens_used=self.tokens_used
            )

            await self._write_lineage(work_order, result, success=False)
            return result

    @abstractmethod
    async def _execute_internal(self, work_order: WorkOrder) -> WorkResult:
        pass

    def _compute_cache_key(self, work_order: WorkOrder) -> str:
        key = f"{self.agent_type}:{work_order.story_hash}:{hashlib.sha256(str(work_order.input_data).encode()).hexdigest()[:16]}"
        return hashlib.sha256(key.encode()).hexdigest()

    async def _check_cache(self, cache_key: str) -> Optional[WorkResult]:
        return None

    async def _save_to_cache(self, cache_key: str, result: WorkResult) -> None:
        pass

    async def _write_lineage(
        self,
        work_order: WorkOrder,
        result: WorkResult,
        success: bool
    ) -> None:
        lineage_id = hashlib.sha256(
            f"{self.agent_type}:{work_order.story_hash}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        lineage = AgentLineage(
            id=lineage_id,
            story_hash=work_order.story_hash or "unknown",
            agent_type=self.agent_type,
            input_hash=hashlib.sha256(str(work_order.input_data).encode()).hexdigest(),
            output_hash=hashlib.sha256(str(result.output_data).encode()).hexdigest() if result.success else None,
            started_at=self.started_at or datetime.utcnow(),
            completed_at=self.completed_at,
            wall_time_ms=self.wall_time_ms,
            tokens_used=self.tokens_used,
            success=success,
            error=result.error_message
        )

        logger.debug(f"Lineage entry created: {lineage_id}")
