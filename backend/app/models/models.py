"""SQLAlchemy models matching the DB design in the VoxMate blueprint."""
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Float, Boolean, JSON, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Personalization preferences (all have sane defaults so existing rows
    # created before this migration still work without a NULL check).
    tts_voice = Column(String, default="Kore")
    assistant_name = Column(String, default="VoxMate")
    tone = Column(String, default="casual")  # "casual" | "formal"

    sessions = relationship("VoiceSession", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    memories = relationship("Memory", back_populates="user")


class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    status = Column(String, default="active")  # active | ended | error

    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")
    tool_calls = relationship("ToolCall", back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id = Column(UUID(as_uuid=False), ForeignKey("voice_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # user | assistant | system | tool
    transcript = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("VoiceSession", back_populates="messages")


class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    type = Column(String, default="fact")  # fact | preference | summary
    content = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="memories")


class ToolDef(Base):
    __tablename__ = "tools"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, unique=True, nullable=False)
    version = Column(String, default="1.0")
    enabled = Column(Boolean, default=True)


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id = Column(UUID(as_uuid=False), ForeignKey("voice_sessions.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    arguments = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    latency_ms = Column(Integer, nullable=True)
    status = Column(String, default="success")  # success | error
    idempotency_key = Column(String, nullable=True, unique=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("VoiceSession", back_populates="tool_calls")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    due_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending | done | cancelled

    user = relationship("User", back_populates="tasks")


class Document(Base):
    """A file the user uploaded for Q&A (RAG). Text is extracted and split
    into DocumentChunk rows with embeddings at ingest time.
    """
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """One retrievable chunk of a Document, with its embedding vector
    stored as JSON (a plain float list). Similarity is computed in Python
    at query time — fine at portfolio scale; swap for pgvector/a real
    vector DB if this needs to scale past a few thousand chunks per user.
    """
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)  # list[float], null if embedding failed
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")


class Webhook(Base):
    """A user-defined tool: give it a name, description, and a URL, and
    the agent can call it like any built-in tool — no code change or
    registry.py edit needed. See app/tools/webhook_tool.py for how this
    gets invoked at runtime.
    """
    __tablename__ = "webhooks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)  # the tool name the LLM will call, e.g. "check_inventory"
    description = Column(Text, nullable=False)  # shown to the LLM so it knows when/how to call this
    url = Column(String, nullable=False)  # POST target; called with {"arguments": {...}} as JSON body
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentEvaluation(Base):
    __tablename__ = "agent_evaluations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id = Column(UUID(as_uuid=False), ForeignKey("voice_sessions.id"), nullable=False)
    success = Column(Boolean, default=True)
    latency_ms = Column(Integer, nullable=True)
    tool_success = Column(Boolean, default=True)
    user_feedback = Column(String, nullable=True)


class AgentPlan(Base):
    """Persisted execution plan for an agent turn."""
    __tablename__ = "agent_plans"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id = Column(UUID(as_uuid=False), ForeignKey("voice_sessions.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    goal = Column(Text, nullable=False)
    status = Column(String, default="active")  # active | completed | blocked | failed
    steps = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ToolApproval(Base):
    """Pending user approval for a tool execution."""
    __tablename__ = "tool_approvals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id = Column(UUID(as_uuid=False), ForeignKey("voice_sessions.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    arguments = Column(JSON, default=dict)
    reason = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending | approved | rejected | expired
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

class MemoryEmbedding(Base):
    """Optional semantic index for Memory without changing the existing table."""
    __tablename__ = "memory_embeddings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    memory_id = Column(UUID(as_uuid=False), ForeignKey("memories.id"), nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GoogleConnection(Base):
    """OAuth connection for Google Calendar and Gmail."""
    __tablename__ = "google_connections"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, unique=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    scope = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class NotificationDevice(Base):
    """Expo push token registered by a user's mobile device."""
    __tablename__ = "notification_devices"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    expo_push_token = Column(String, nullable=False, unique=True)
    platform = Column(String, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    data = Column(JSON, default=dict)
    scheduled_for = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending | sent | failed | cancelled
    created_at = Column(DateTime, default=datetime.utcnow)


class Workflow(Base):
    """User-defined automation: trigger + ordered action definitions."""
    __tablename__ = "workflows"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    trigger_type = Column(String, nullable=False)  # schedule | task_due | webhook
    trigger_config = Column(JSON, default=dict)
    actions = Column(JSON, default=list)
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class OAuthState(Base):
    __tablename__ = "oauth_states"
    id = Column(String, primary_key=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ResearchReport(Base):
    """Persisted deep-research report with sources and synthesis."""
    __tablename__ = "research_reports"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentNote(Base):
    """User notes attached to an uploaded document."""
    __tablename__ = "document_notes"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class DocumentRevision(Base):
    """Lightweight version history for workspace notes/metadata."""
    __tablename__ = "document_revisions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Meeting(Base):
    """Persistent meeting transcript and AI-generated meeting package."""
    __tablename__ = "meetings"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False, default="Untitled meeting")
    status = Column(String, default="recording")  # recording | completed
    transcript = Column(Text, default="")
    summary = Column(Text, nullable=True)
    action_items = Column(JSON, default=list)
    decisions = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)


class MeetingSegment(Base):
    __tablename__ = "meeting_segments"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    meeting_id = Column(UUID(as_uuid=False), ForeignKey("meetings.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    speaker = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GitHubConnection(Base):
    """Encrypted per-user GitHub token used by the coding agent."""
    __tablename__ = "github_connections"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, unique=True)
    encrypted_token = Column(Text, nullable=False)
    login = Column(String, nullable=True)
    scope = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class CustomAgent(Base):
    """User-owned persona/agent definition."""
    __tablename__ = "custom_agents"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    persona = Column(Text, nullable=False)
    tool_names = Column(JSON, default=list)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MarketplacePlugin(Base):
    """Safe, declarative plugin catalog entry. Plugins can expose existing VoxMate tools."""
    __tablename__ = "marketplace_plugins"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slug = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    version = Column(String, default="1.0.0")
    author = Column(String, default="VoxMate")
    icon = Column(String, default="extension-puzzle-outline")
    tool_names = Column(JSON, default=list)
    category = Column(String, default="productivity")
    featured = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PluginInstallation(Base):
    """Per-user installed marketplace plugins."""
    __tablename__ = "plugin_installations"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    plugin_id = Column(UUID(as_uuid=False), ForeignKey("marketplace_plugins.id"), nullable=False)
    enabled = Column(Boolean, default=True)
    installed_at = Column(DateTime, default=datetime.utcnow)


class AgentRun(Base):
    """Records multi-agent delegations for analytics and auditability."""
    __tablename__ = "agent_runs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    session_id = Column(UUID(as_uuid=False), ForeignKey("voice_sessions.id"), nullable=True)
    agent_key = Column(String, nullable=False)
    role = Column(String, nullable=False, default="worker")
    status = Column(String, default="success")
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
