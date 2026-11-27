from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, Any, List
from datetime import datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TaskCreate(BaseModel):
    title: str
    due_at: Optional[datetime] = None


class TaskOut(BaseModel):
    id: str
    title: str
    due_at: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class SearchHistoryOut(BaseModel):
    id: str
    query: str
    answer: Optional[str] = None
    sources: List[dict] = Field(default_factory=list)
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


VALID_TTS_VOICES = ("Kore", "Puck", "Charon", "Aoede", "Fenrir", "Leda", "Zephyr", "Orus")


class PreferencesUpdate(BaseModel):
    tts_voice: Optional[str] = None
    assistant_name: Optional[str] = None
    tone: Optional[str] = None  # "casual" | "formal"


class PreferencesOut(BaseModel):
    tts_voice: str
    assistant_name: str
    tone: str
    available_voices: List[str] = list(VALID_TTS_VOICES)

    model_config = ConfigDict(from_attributes=True)


class UsageStatsOut(BaseModel):
    total_sessions: int
    total_messages: int
    total_tool_calls: int
    tasks_created: int
    code_executions: int
    documents_uploaded: int
    searches_run: int


class WebhookCreate(BaseModel):
    name: str
    description: str
    url: str


class WebhookOut(BaseModel):
    id: str
    name: str
    description: str
    url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- Platform ---

class CustomAgentCreate(BaseModel):
    name: str
    description: str = ""
    persona: str
    tool_names: List[str] = Field(default_factory=list)
    enabled: bool = True

class CustomAgentOut(CustomAgentCreate):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PluginOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str
    version: str
    author: str
    icon: str
    category: str
    featured: bool
    tool_names: List[str] = Field(default_factory=list)
    installed: bool = False
    model_config = ConfigDict(from_attributes=True)

class AnalyticsOut(BaseModel):
    sessions: int
    messages: int
    tool_calls: int
    successful_tool_calls: int
    failed_tool_calls: int
    avg_tool_latency_ms: float
    active_custom_agents: int
    installed_plugins: int
    agent_runs: int
    top_tools: List[dict] = Field(default_factory=list)
