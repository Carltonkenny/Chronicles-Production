from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime


class WorkOrder(BaseModel):
    agent_type: str = Field(..., description="Type of agent to execute")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data for the agent")
    timeout_ms: int = Field(default=30000, description="Timeout in milliseconds")
    story_hash: Optional[str] = Field(default=None, description="Story hash for lineage tracking")
    priority: int = Field(default=5, description="Priority (1-10, higher is more urgent)")


class WorkResult(BaseModel):
    success: bool = Field(..., description="Whether the work completed successfully")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Output data from the agent")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    wall_time_ms: float = Field(default=0.0, description="Wall clock time taken")
    tokens_used: int = Field(default=0, description="Tokens consumed")
    agent_lineage_id: Optional[str] = Field(default=None, description="Lineage entry ID")


class AgentLineage(BaseModel):
    id: str = Field(..., description="Unique lineage ID")
    story_hash: str = Field(..., description="Story hash this belongs to")
    agent_type: str = Field(..., description="Agent type")
    input_hash: str = Field(..., description="Hash of input data")
    output_hash: Optional[str] = Field(default=None, description="Hash of output data")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    wall_time_ms: float = Field(default=0.0)
    tokens_used: int = Field(default=0)
    success: bool = Field(default=False)
    error: Optional[str] = Field(default=None)
