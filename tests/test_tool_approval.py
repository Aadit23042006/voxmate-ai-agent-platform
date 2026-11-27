import uuid
from types import SimpleNamespace

from app.agents import orchestrator as orchestrator_module
from app.agents.orchestrator import SessionOrchestrator
from app.agents.planner import AgentPlan, PlanStep
from app.models.models import ToolApproval, VoiceSession


def test_rejected_tool_is_never_executed(
    db_session, test_user, monkeypatch
):
    session_id = str(uuid.uuid4())

    voice_session = VoiceSession(
        id=session_id,
        user_id=test_user.id,
        status="active",
    )
    db_session.add(voice_session)
    db_session.commit()

    approval = ToolApproval(
        session_id=session_id,
        user_id=test_user.id,
        tool_name="create_reminder",
        arguments={"title": "Rejected reminder"},
        status="pending",
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)

    approval_id = approval.id
    execution_count = {"value": 0}
    recorded_results = []

    def forbidden_tool_lookup(*args, **kwargs):
        execution_count["value"] += 1
        raise AssertionError(
            "Rejected tool must never be looked up or executed"
        )

    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        forbidden_tool_lookup,
    )

    orchestrator = SessionOrchestrator()

    plan = AgentPlan(
        id=str(uuid.uuid4()),
        goal="Create a reminder",
        steps=[
            PlanStep(
                id=str(uuid.uuid4()),
                tool="create_reminder",
                purpose="Create the requested reminder",
            )
        ],
    )
    orchestrator._plans[session_id] = plan

    orchestrator._pending_approvals[approval_id] = {
        "session_id": session_id,
        "agent": SimpleNamespace(key="general"),
        "config": None,
        "plan": plan,
        "tool_name": "create_reminder",
        "args": {"title": "Rejected reminder"},
        "call_id": "test-rejection-1",
        "hop": 0,
        "tool_results": [],
    }

    monkeypatch.setattr(
        orchestrator,
        "_append_tool_result",
        lambda *args: recorded_results.append(args),
    )

    result = orchestrator.approve_tool(
        approval_id=approval_id,
        approved=False,
        db=db_session,
        user=test_user,
        session_id=session_id,
    )

    db_session.expire(approval)
    db_session.refresh(approval)

    assert approval.status == "rejected"
    assert approval.resolved_at is not None
    assert execution_count["value"] == 0
    assert len(recorded_results) == 1
    assert recorded_results[0][5] == "rejected"
    assert "rejected" in result.text.lower()
    assert approval_id not in orchestrator._pending_approvals


def test_invalid_approval_uuid_returns_unavailable_without_execution(
    db_session, test_user, monkeypatch
):
    orchestrator = SessionOrchestrator()
    execution_count = {"value": 0}

    def forbidden_tool_lookup(*args, **kwargs):
        execution_count["value"] += 1
        raise AssertionError("Invalid UUID must never reach tool execution")

    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        forbidden_tool_lookup,
    )

    result = orchestrator.approve_tool(
        approval_id="not-a-valid-uuid",
        approved=True,
        db=db_session,
        user=test_user,
        session_id=str(uuid.uuid4()),
    )

    assert result.text == "That tool approval is no longer available."
    assert execution_count["value"] == 0
    assert orchestrator._pending_approvals == {}


def test_wrong_owner_cannot_approve_another_users_tool(
    db_session, test_user, monkeypatch
):
    from app.models.models import User

    owner = test_user

    attacker = User(
        email=f"attacker-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="test-password",
    )
    db_session.add(attacker)
    db_session.commit()
    db_session.refresh(attacker)

    session_id = str(uuid.uuid4())

    voice_session = VoiceSession(
        id=session_id,
        user_id=owner.id,
        status="active",
    )
    db_session.add(voice_session)
    db_session.commit()

    approval = ToolApproval(
        session_id=session_id,
        user_id=owner.id,
        tool_name="create_reminder",
        arguments={"title": "Owner private reminder"},
        status="pending",
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)

    approval_id = approval.id
    execution_count = {"value": 0}

    def forbidden_tool_lookup(*args, **kwargs):
        execution_count["value"] += 1
        raise AssertionError("Wrong owner must never execute the tool")

    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        forbidden_tool_lookup,
    )

    orchestrator = SessionOrchestrator()
    plan = AgentPlan(
        id=str(uuid.uuid4()),
        goal="Create a private reminder",
        steps=[
            PlanStep(
                id=str(uuid.uuid4()),
                tool="create_reminder",
                purpose="Create owner's reminder",
            )
        ],
    )
    orchestrator._plans[session_id] = plan

    orchestrator._pending_approvals[approval_id] = {
        "session_id": session_id,
        "agent": SimpleNamespace(key="general"),
        "config": None,
        "plan": plan,
        "tool_name": "create_reminder",
        "args": {"title": "Owner private reminder"},
        "call_id": "wrong-owner-test",
        "hop": 0,
        "tool_results": [],
    }

    result = orchestrator.approve_tool(
        approval_id=approval_id,
        approved=True,
        db=db_session,
        user=attacker,
        session_id=session_id,
    )

    db_session.expire(approval)
    db_session.refresh(approval)

    assert result.text == "That tool approval is no longer available."
    assert approval.status == "pending"
    assert approval.resolved_at is None
    assert execution_count["value"] == 0
    assert approval_id in orchestrator._pending_approvals


def test_wrong_session_cannot_consume_pending_approval(
    db_session, test_user, monkeypatch
):
    owner_session_id = str(uuid.uuid4())
    attacker_session_id = str(uuid.uuid4())

    owner_session = VoiceSession(
        id=owner_session_id,
        user_id=test_user.id,
        status="active",
    )
    attacker_session = VoiceSession(
        id=attacker_session_id,
        user_id=test_user.id,
        status="active",
    )
    db_session.add_all([owner_session, attacker_session])
    db_session.commit()

    approval = ToolApproval(
        session_id=owner_session_id,
        user_id=test_user.id,
        tool_name="create_reminder",
        arguments={"title": "Session A reminder"},
        status="pending",
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)

    approval_id = approval.id
    execution_count = {"value": 0}

    def forbidden_tool_lookup(*args, **kwargs):
        execution_count["value"] += 1
        raise AssertionError("Wrong session must never execute the tool")

    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        forbidden_tool_lookup,
    )

    orchestrator = SessionOrchestrator()
    plan = AgentPlan(
        id=str(uuid.uuid4()),
        goal="Create a reminder",
        steps=[
            PlanStep(
                id=str(uuid.uuid4()),
                tool="create_reminder",
                purpose="Create the requested reminder",
            )
        ],
    )
    orchestrator._plans[owner_session_id] = plan

    orchestrator._pending_approvals[approval_id] = {
        "session_id": owner_session_id,
        "agent": SimpleNamespace(key="general"),
        "config": None,
        "plan": plan,
        "tool_name": "create_reminder",
        "args": {"title": "Session A reminder"},
        "call_id": "wrong-session-test",
        "hop": 0,
        "tool_results": [],
    }

    result = orchestrator.approve_tool(
        approval_id=approval_id,
        approved=True,
        db=db_session,
        user=test_user,
        session_id=attacker_session_id,
    )

    db_session.expire(approval)
    db_session.refresh(approval)

    assert result.text == "That tool approval is no longer available."
    assert approval.status == "pending"
    assert approval.resolved_at is None
    assert execution_count["value"] == 0
    assert approval_id in orchestrator._pending_approvals


def test_duplicate_approval_executes_tool_only_once(
    db_session, test_user, monkeypatch
):
    session_id = str(uuid.uuid4())

    voice_session = VoiceSession(
        id=session_id,
        user_id=test_user.id,
        status="active",
    )
    db_session.add(voice_session)
    db_session.commit()

    approval = ToolApproval(
        session_id=session_id,
        user_id=test_user.id,
        tool_name="create_reminder",
        arguments={"title": "Exactly once reminder"},
        status="pending",
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)

    approval_id = str(approval.id)
    execution_count = {"value": 0}

    class FakeTool:
        def run(self, db, user, args):
            execution_count["value"] += 1
            return {"success": True, "title": args["title"]}

    fake_tool = FakeTool()

    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        lambda *args, **kwargs: fake_tool,
    )
    monkeypatch.setattr(
        orchestrator_module,
        "validate_tool_arguments",
        lambda tool, args: args,
    )

    orchestrator = SessionOrchestrator()

    plan = AgentPlan(
        id=str(uuid.uuid4()),
        goal="Create a reminder",
        steps=[
            PlanStep(
                id=str(uuid.uuid4()),
                tool="create_reminder",
                purpose="Create the requested reminder",
            )
        ],
    )

    orchestrator._plans[session_id] = plan
    orchestrator._histories[session_id] = []

    orchestrator._pending_approvals[approval_id] = {
        "session_id": session_id,
        "agent": SimpleNamespace(key="general"),
        "config": None,
        "plan": plan,
        "tool_name": "create_reminder",
        "args": {"title": "Exactly once reminder"},
        "call_id": "duplicate-approval-test",
        "hop": 0,
        "tool_results": [],
    }

    monkeypatch.setattr(
        orchestrator,
        "_append_tool_result",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        orchestrator,
        "_mark_plan_tool",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        orchestrator,
        "_run_model_loop",
        lambda **kwargs: SimpleNamespace(text="Continuation completed"),
    )

    first_result = orchestrator.approve_tool(
        approval_id=approval_id,
        approved=True,
        db=db_session,
        user=test_user,
        session_id=session_id,
    )

    assert first_result.text == "Continuation completed"
    assert execution_count["value"] == 1
    assert approval_id not in orchestrator._pending_approvals

    second_result = orchestrator.approve_tool(
        approval_id=approval_id,
        approved=True,
        db=db_session,
        user=test_user,
        session_id=session_id,
    )

    db_session.expire(approval)
    db_session.refresh(approval)

    assert second_result.text == "That tool approval is no longer available."
    assert approval.status == "approved"
    assert execution_count["value"] == 1


def test_missing_continuation_expires_pending_approval_without_execution(
    db_session, test_user, monkeypatch
):
    session_id = str(uuid.uuid4())

    voice_session = VoiceSession(
        id=session_id,
        user_id=test_user.id,
        status="active",
    )
    db_session.add(voice_session)
    db_session.commit()

    approval = ToolApproval(
        session_id=session_id,
        user_id=test_user.id,
        tool_name="create_reminder",
        arguments={"title": "Must not execute after restart"},
        status="pending",
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)

    approval_id = str(approval.id)
    tool_lookup_count = {"value": 0}

    def forbidden_tool_lookup(*args, **kwargs):
        tool_lookup_count["value"] += 1
        raise AssertionError("Expired approval must never look up or execute a tool")

    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        forbidden_tool_lookup,
    )

    orchestrator = SessionOrchestrator()

    # Simulate a backend restart: no in-memory continuation exists.
    assert approval_id not in orchestrator._pending_approvals

    result = orchestrator.approve_tool(
        approval_id=approval_id,
        approved=True,
        db=db_session,
        user=test_user,
        session_id=session_id,
    )

    db_session.expire(approval)
    db_session.refresh(approval)

    assert result.text == "That tool approval is no longer available."
    assert approval.status == "expired"
    assert approval.resolved_at is not None
    assert tool_lookup_count["value"] == 0
    assert approval_id not in orchestrator._pending_approvals


def test_already_resolved_approval_cannot_execute_stale_continuation(
    db_session, test_user, monkeypatch
):
    session_id = str(uuid.uuid4())

    voice_session = VoiceSession(
        id=session_id,
        user_id=test_user.id,
        status="active",
    )
    db_session.add(voice_session)
    db_session.commit()

    approval = ToolApproval(
        session_id=session_id,
        user_id=test_user.id,
        tool_name="create_reminder",
        arguments={"title": "Already resolved"},
        status="approved",
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)

    approval_id = str(approval.id)
    tool_lookup_count = {"value": 0}

    def forbidden_tool_lookup(*args, **kwargs):
        tool_lookup_count["value"] += 1
        raise AssertionError("Already-resolved approval must not execute")

    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        forbidden_tool_lookup,
    )

    orchestrator = SessionOrchestrator()

    plan = AgentPlan(
        id=str(uuid.uuid4()),
        goal="Create a reminder",
        steps=[
            PlanStep(
                id=str(uuid.uuid4()),
                tool="create_reminder",
                purpose="Create the requested reminder",
            )
        ],
    )

    # Simulate stale in-memory state with an already-resolved DB record.
    orchestrator._pending_approvals[approval_id] = {
        "session_id": session_id,
        "agent": SimpleNamespace(key="general"),
        "config": None,
        "plan": plan,
        "tool_name": "create_reminder",
        "args": {"title": "Already resolved"},
        "call_id": "already-resolved-test",
        "hop": 0,
        "tool_results": [],
    }

    result = orchestrator.approve_tool(
        approval_id=approval_id,
        approved=True,
        db=db_session,
        user=test_user,
        session_id=session_id,
    )

    db_session.expire(approval)
    db_session.refresh(approval)

    assert result.text == "That tool approval is no longer available."
    assert approval.status == "approved"
    assert tool_lookup_count["value"] == 0

    # A failed DB claim must not consume another request's continuation.
    assert approval_id in orchestrator._pending_approvals


def test_successful_tool_approval_executes_and_resolves(
    db_session, test_user, monkeypatch
):
    session_id = str(uuid.uuid4())

    voice_session = VoiceSession(
        id=session_id,
        user_id=test_user.id,
        status="active",
    )
    db_session.add(voice_session)
    db_session.commit()

    approval = ToolApproval(
        session_id=session_id,
        user_id=test_user.id,
        tool_name="create_reminder",
        arguments={"title": "Approved reminder"},
        status="pending",
    )
    db_session.add(approval)
    db_session.commit()
    db_session.refresh(approval)

    approval_id = str(approval.id)
    executions = []

    class FakeTool:
        def run(self, db, user, args):
            executions.append({
                "user_id": user.id,
                "args": args,
            })
            return {"success": True, "title": args["title"]}

    monkeypatch.setattr(
        orchestrator_module,
        "get_tool",
        lambda *args, **kwargs: FakeTool(),
    )
    monkeypatch.setattr(
        orchestrator_module,
        "validate_tool_arguments",
        lambda tool, args: args,
    )

    orchestrator = SessionOrchestrator()

    plan = AgentPlan(
        id=str(uuid.uuid4()),
        goal="Create a reminder",
        steps=[
            PlanStep(
                id=str(uuid.uuid4()),
                tool="create_reminder",
                purpose="Create the requested reminder",
            )
        ],
    )

    orchestrator._plans[session_id] = plan
    orchestrator._histories[session_id] = []

    orchestrator._pending_approvals[approval_id] = {
        "session_id": session_id,
        "agent": SimpleNamespace(key="general"),
        "config": None,
        "plan": plan,
        "tool_name": "create_reminder",
        "args": {"title": "Approved reminder"},
        "call_id": "successful-approval-test",
        "hop": 0,
        "tool_results": [],
    }

    monkeypatch.setattr(
        orchestrator,
        "_append_tool_result",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        orchestrator,
        "_mark_plan_tool",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        orchestrator,
        "_run_model_loop",
        lambda **kwargs: SimpleNamespace(text="Reminder created successfully"),
    )

    result = orchestrator.approve_tool(
        approval_id=approval_id,
        approved=True,
        db=db_session,
        user=test_user,
        session_id=session_id,
    )

    db_session.expire(approval)
    db_session.refresh(approval)

    assert result.text == "Reminder created successfully"
    assert approval.status == "approved"
    assert approval.resolved_at is not None
    assert len(executions) == 1
    assert executions[0]["user_id"] == test_user.id
    assert executions[0]["args"] == {"title": "Approved reminder"}
    assert approval_id not in orchestrator._pending_approvals

