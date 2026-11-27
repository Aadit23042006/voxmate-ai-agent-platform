from datetime import datetime, timezone
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from google.genai import types

from app.agents.llm_client import get_llm_client
from app.agents.router import classify_agent, system_prompt_for
from app.agents.planner import build_plan, AgentPlan
from app.tools.registry import get_tool, get_tool_declarations, TOOL_REGISTRY
from app.tools.base import ToolError
from app.tools.security import confirmation_required, validate_tool_arguments
from app.memory.memory_service import remember_explicit_user_facts, build_memory_context

logger = logging.getLogger("voxmate.orchestrator")

MAX_TOOL_HOPS = 4


@dataclass
class TurnResult:
    text: str
    agent: str
    tool_results: List[dict] = field(default_factory=list)
    plan: Optional[dict] = None
    confirmation: Optional[dict] = None


from app.tools.reminder_tool import ReminderTool


class SessionOrchestrator:
    """Additive agent layer: planner -> execution loop -> confirmation -> memory.

    Existing Gemini function calling remains the final tool-selection mechanism.
    The planner is persisted for observability and multi-step coordination.
    """

    def __init__(self):
        self._histories: Dict[str, List[Any]] = {}
        self._agents: Dict[str, str] = {}
        self._plans: Dict[str, AgentPlan] = {}
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}

    def handle_turn(
        self, session_id: str, user_input: Any, system_context: Optional[str] = None,
        db=None, user=None,
    ) -> TurnResult:
        text_for_classification = user_input if isinstance(user_input, str) else "Attachment/Audio Input"
        agent = classify_agent(text_for_classification)
        self._agents[session_id] = agent.key

        plan = build_plan(text_for_classification, agent.tool_names)
        self._plans[session_id] = plan
        self._persist_plan(db, session_id, user, plan)

        if db is not None and user is not None and isinstance(user_input, str):
            try:
                remember_explicit_user_facts(db, user.id, user_input)
            except Exception:
                logger.exception("Automatic memory extraction failed")

        system_prompt = system_prompt_for(agent, user=user, db=db)
        if db is not None and user is not None:
            try:
                memory_context = build_memory_context(db, user.id, text_for_classification)
                if memory_context:
                    system_prompt += (
                        "\n\nLong-term memory (use only when relevant; never claim "
                        "a memory the user did not state):\n" + memory_context
                    )
            except Exception:
                logger.exception("Long-term memory recall failed")

        if system_context:
            system_prompt += f"\n\nAdditional context:\n{system_context}"

        history = self._histories.setdefault(session_id, [])
        history.append(_to_user_content(user_input))

        # All agents may use user-scoped integrations (for example GitHub).
        # The allowed tool_names list still limits what each agent can call.
        tool_declarations = get_tool_declarations(
            tool_names=agent.tool_names,
            db=db,
            user=user,
        )
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=tool_declarations,
        )
        result = self._run_model_loop(
            session_id=session_id, agent=agent, config=config, history=history,
            db=db, user=user, plan=plan,
            original_user_text=user_input if isinstance(user_input, str) else None,
            start_hop=0,
        )
        return result

    def approve_tool(
        self, approval_id: str, approved: bool, db=None, user=None,
        session_id: Optional[str] = None,
    ) -> TurnResult:
        """Resolve a pending tool approval exactly once for its owner/session."""
        unavailable = TurnResult(
            text="That tool approval is no longer available.",
            agent="general",
        )

        if (
            not isinstance(approval_id, str)
            or not approval_id.strip()
            or type(approved) is not bool
            or db is None
            or user is None
            or not getattr(user, "id", None)
            or not session_id
        ):
            return unavailable

        try:
            import uuid
            from datetime import datetime
            from app.models.models import ToolApproval

            # Reject malformed IDs before sending them to the database.
            uuid.UUID(approval_id)

            pending = self._pending_approvals.get(approval_id)

            # A process restart loses the in-memory model continuation.
            # Expire the owned pending row instead of executing without it.
            if pending is None:
                db.query(ToolApproval).filter(
                    ToolApproval.id == approval_id,
                    ToolApproval.user_id == user.id,
                    ToolApproval.session_id == session_id,
                    ToolApproval.status == "pending",
                ).update(
                    {
                        "status": "expired",
                        "resolved_at": datetime.now(timezone.utc),
                    },
                    synchronize_session=False,
                )
                db.commit()
                return unavailable

            # Do not let a different WebSocket session consume this approval.
            if pending.get("session_id") != session_id:
                return unavailable

            # Atomic compare-and-set: only one request can change pending.
            changed = db.query(ToolApproval).filter(
                ToolApproval.id == approval_id,
                ToolApproval.user_id == user.id,
                ToolApproval.session_id == session_id,
                ToolApproval.status == "pending",
            ).update(
                {
                    "status": "approved" if approved else "rejected",
                    "resolved_at": datetime.now(timezone.utc),
                },
                synchronize_session=False,
            )

            if changed != 1:
                db.rollback()
                return unavailable

            # Commit the one-time claim before any tool execution.
            db.commit()

        except (ValueError, TypeError):
            db.rollback()
            return unavailable
        except Exception:
            db.rollback()
            logger.exception("Failed to resolve tool approval %s", approval_id)
            raise

        # Remove continuation only after the database claim succeeds.
        pending = self._pending_approvals.pop(approval_id, None)
        if pending is None:
            return unavailable

        session_id = pending["session_id"]
        tool_name = pending["tool_name"]

        if not approved:
            result = {
                "error": "User rejected tool execution.",
                "tool": tool_name,
            }
            self._append_tool_result(
                db, session_id, tool_name, pending["args"], result, "rejected", 0
            )
            return TurnResult(
                text=f"I didn't run {tool_name} because you rejected the action.",
                agent=pending["agent"].key,
                plan=self._plan_dict(session_id),
            )

        tool = get_tool(tool_name, db=db, user=user)
        if tool is None:
            return TurnResult(
                text=f"The approved tool '{tool_name}' is no longer available.",
                agent=pending["agent"].key,
                plan=self._plan_dict(session_id),
            )

        started = time.perf_counter()
        try:
            args = validate_tool_arguments(tool, pending["args"])
            result = tool.run(db, user, args)
            status = "success"
        except Exception as exc:
            status = "error"
            result = {"error": str(exc)}
            logger.exception("Approved tool '%s' failed", tool_name)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self._append_tool_result(
            db, session_id, tool_name, pending["args"], result, status, elapsed_ms
        )
        self._mark_plan_tool(session_id, tool_name, status)

        history = self._histories.get(session_id, [])
        history.append(types.Content(
            role="user",
            parts=[types.Part.from_function_response(
                name=tool_name,
                response=result if isinstance(result, dict) else {"result": result},
            )],
        ))
        pending["tool_results"].append({
            "tool": tool_name,
            "result": result,
            "status": status,
            "latency_ms": elapsed_ms,
            "call_id": pending.get("call_id"),
        })

        return self._run_model_loop(
            session_id=session_id,
            agent=pending["agent"],
            config=pending["config"],
            history=history,
            db=db,
            user=user,
            plan=pending["plan"],
            start_hop=pending.get("hop", 0) + 1,
            existing_results=pending["tool_results"],
        )

    def _run_model_loop(
        self, session_id, agent, config, history, db, user, plan,
        start_hop=0, existing_results=None,
        original_user_text=None,
    ) -> TurnResult:
        tool_results = existing_results or []

        for hop in range(start_hop, MAX_TOOL_HOPS + 1):
            logger.info("Gemini turn session=%s agent=%s hop=%s plan=%s",
                        session_id, agent.key, hop, plan.id)
            response = get_llm_client().generate_content(contents=history, config=config)

            model_content = _model_content(response)
            if model_content is not None:
                history.append(model_content)

            calls = _function_calls(response)
            if not calls:
                text = getattr(response, "text", None) or _extract_text(response)
                if not text:
                    text = "I couldn't produce a response for that request."
                self._finish_plan(session_id, db, "completed")
                self._learn_from_turn(db, user, history)
                return TurnResult(
                    text=text, agent=agent.key, tool_results=tool_results,
                    plan=self._plan_dict(session_id),
                )

            response_parts = []
            for call in calls:
                tool_name = getattr(call, "name", None)
                args = dict(getattr(call, "args", None) or {})
                if tool_name == "create_reminder" and not args.get("due_at"):
                    inferred_due_at = ReminderTool.extract_due_at_from_text(original_user_text)
                    if inferred_due_at is not None:
                        args["due_at"] = inferred_due_at.isoformat()
                call_id = getattr(call, "id", None)
                tool = get_tool(tool_name, db=db, user=user)

                # Built-in tools are gated by the agent's static tool_names list.
                # User-defined webhooks aren't in that list (they're created at
                # runtime), so they're allowed through for the general agent only,
                # matching where they're advertised in get_tool_declarations().
                is_allowed = tool_name in agent.tool_names or (
                    agent.key == "general" and tool_name not in TOOL_REGISTRY and tool is not None
                )
                if tool is None or not is_allowed:
                    result = {"error": f"Tool '{tool_name}' is not available to this agent."}
                    status = "error"
                    self._mark_plan_tool(session_id, tool_name, status)
                    response_parts.append(types.Part.from_function_response(
                        name=tool_name, response=result))
                    continue

                # Confirmation is checked before execution.
                if confirmation_required(tool_name):
                    approval_id = self._create_approval(
                        db, session_id, user, tool_name, args,
                        reason=f"VoxMate wants to run '{tool_name}' as part of your plan.",
                    )
                    self._pending_approvals[approval_id] = {
                        "session_id": session_id,
                        "agent": agent,
                        "config": config,
                        "plan": plan,
                        "tool_name": tool_name,
                        "args": args,
                        "call_id": call_id,
                        "hop": hop,
                        "tool_results": tool_results,
                    }
                    if response_parts:
                        history.append(types.Content(role="user", parts=response_parts))
                    return TurnResult(
                        text=f"I need your confirmation before I run {tool_name}.",
                        agent=agent.key,
                        tool_results=tool_results,
                        plan=self._plan_dict(session_id),
                        confirmation={
                            "id": approval_id,
                            "tool": tool_name,
                            "arguments": args,
                            "reason": f"VoxMate wants to run '{tool_name}' as part of your plan.",
                        },
                    )

                started = time.perf_counter()
                try:
                    args = validate_tool_arguments(tool, args)
                    result = tool.run(db, user, args)
                    status = "success"
                except Exception as exc:
                    status = "error"
                    result = {"error": str(exc)}
                    logger.exception("Tool '%s' failed", tool_name)
                elapsed_ms = int((time.perf_counter() - started) * 1000)

                event = {
                    "tool": tool_name, "result": result, "status": status,
                    "latency_ms": elapsed_ms, "call_id": call_id,
                }
                tool_results.append(event)
                self._append_tool_result(db, session_id, tool_name, args, result, status, elapsed_ms)
                self._mark_plan_tool(session_id, tool_name, status)
                response_parts.append(types.Part.from_function_response(
                    name=tool_name,
                    response=result if isinstance(result, dict) else {"result": result},
                ))

            if response_parts:
                history.append(types.Content(role="user", parts=response_parts))

        self._finish_plan(session_id, db, "failed")
        return TurnResult(
            text="I couldn't finish the tool workflow within the allowed number of steps.",
            agent=agent.key, tool_results=tool_results, plan=self._plan_dict(session_id),
        )

    def handle_attachment_turn(self, session_id, attachment_part, prompt="Please analyze this uploaded file.",
                               system_context=None, db=None, user=None):
        return self.handle_turn(
            session_id=session_id, user_input=[attachment_part, prompt],
            system_context=system_context, db=db, user=user,
        )

    def clear_session(self, session_id: str) -> None:
        self._histories.pop(session_id, None)
        self._agents.pop(session_id, None)
        self._plans.pop(session_id, None)
        for key, pending in list(self._pending_approvals.items()):
            if pending["session_id"] == session_id:
                self._pending_approvals.pop(key, None)

    def _create_approval(self, db, session_id, user, tool_name, args, reason):
        from app.models.models import ToolApproval
        row = ToolApproval(
            session_id=session_id, user_id=user.id, tool_name=tool_name,
            arguments=args, reason=reason, status="pending",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id

    def _persist_plan(self, db, session_id, user, plan):
        if db is None or user is None:
            return
        try:
            from app.models.models import AgentPlan
            row = AgentPlan(
                id=plan.id, session_id=session_id, user_id=user.id,
                goal=plan.goal, status=plan.status, steps=plan.as_dict()["steps"],
            )
            db.add(row)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to persist agent plan")

    def _mark_plan_tool(self, session_id, tool_name, status):
        plan = self._plans.get(session_id)
        if not plan:
            return
        for step in plan.steps:
            if step.tool == tool_name and step.status == "pending":
                step.status = status
                break

    def _finish_plan(self, session_id, db, status):
        plan = self._plans.get(session_id)
        if not plan:
            return
        plan.status = status
        if db is not None:
            try:
                from app.models.models import AgentPlan
                row = db.query(AgentPlan).filter(AgentPlan.id == plan.id).first()
                if row:
                    row.status = status
                    row.steps = plan.as_dict()["steps"]
                    from datetime import datetime
                    row.updated_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception:
                db.rollback()
                logger.exception("Failed to update agent plan")

    def _plan_dict(self, session_id):
        plan = self._plans.get(session_id)
        return plan.as_dict() if plan else None

    def _append_tool_result(self, db, session_id, tool_name, args, result, status, elapsed_ms):
        _record_tool_call(db, session_id, tool_name, args, result, status, elapsed_ms)

    def _learn_from_turn(self, db, user, history):
        # Explicit memory extraction already happens at turn start. This hook
        # exists so future memory signals can be added without changing flow.
        return None


def _to_user_content(user_input: Any) -> Any:
    if isinstance(user_input, list):
        parts = []
        for item in user_input:
            if isinstance(item, str):
                parts.append(types.Part.from_text(text=item))
            elif isinstance(item, dict) and item.get("data") is not None:
                parts.append(types.Part.from_bytes(
                    data=item["data"], mime_type=item.get("mime_type", "application/octet-stream")))
            else:
                parts.append(item)
        return types.Content(role="user", parts=parts)
    return types.Content(role="user", parts=[types.Part.from_text(text=str(user_input))])


def _model_content(response: Any) -> Any:
    try:
        return response.candidates[0].content
    except (AttributeError, IndexError, TypeError):
        return None


def _function_calls(response: Any) -> List[Any]:
    calls = []
    try:
        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                call = getattr(part, "function_call", None)
                if call is not None:
                    calls.append(call)
    except (AttributeError, TypeError):
        pass
    return calls


def _extract_text(response: Any) -> str:
    parts = []
    try:
        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                text = getattr(part, "text", None)
                if text:
                    parts.append(text)
    except (AttributeError, TypeError):
        pass
    return "\n".join(parts).strip()


def _record_tool_call(db, session_id, tool_name, arguments, result, status, latency_ms):
    if db is None:
        return
    try:
        from app.models.models import ToolCall
        db.add(ToolCall(
            session_id=session_id, tool_name=tool_name, arguments=arguments,
            result=result if isinstance(result, dict) else {"result": result},
            status=status, latency_ms=latency_ms,
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist tool call")


orchestrator = SessionOrchestrator()


def handle_turn(session_id, user_input, system_context=None, db=None, user=None):
    return orchestrator.handle_turn(session_id, user_input, system_context, db, user)


def handle_attachment_turn(session_id, attachment_part, prompt="Please analyze this file.",
                           system_context=None, db=None, user=None):
    return orchestrator.handle_attachment_turn(
        session_id, attachment_part, prompt, system_context, db, user)


def approve_tool(
    approval_id: str, approved: bool, db=None, user=None,
    session_id: Optional[str] = None,
) -> TurnResult:
    return orchestrator.approve_tool(
        approval_id, approved, db=db, user=user, session_id=session_id
    )


def clear_orchestrator_session(session_id: str) -> None:
    orchestrator.clear_session(session_id)

