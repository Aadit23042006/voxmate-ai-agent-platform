"""Generic webhook-backed tool: makes app/tools/registry.py's static
TOOL_REGISTRY extensible at runtime. A user registers a name/description/
URL via POST /account/webhooks, and from that point the agent can call it
like any built-in tool — no code deploy needed.

Kept deliberately simple (a plain POST with the tool's arguments as JSON,
a short timeout, no auth/retry/schema validation) since this is meant as
a portfolio-grade extensibility demo, not a production plugin platform.
A real version would add per-webhook auth headers, a declared JSON-schema
for arguments (validated before the call), and a retry/circuit-breaker
policy.
"""
import requests

from app.tools.base import BaseTool, ToolError

TIMEOUT_S = 8


class WebhookTool(BaseTool):
    """Not registered in TOOL_REGISTRY — instantiated on the fly by
    registry.get_tool() when a tool name matches a user's Webhook row.
    """

    def __init__(self, name: str, url: str, description: str):
        self.name = name
        self.url = url
        self.description = description

    def validate(self, arguments):
        return arguments or {}

    def run(self, db, user, arguments):
        args = self.validate(arguments)
        try:
            response = requests.post(
                self.url,
                json={"tool": self.name, "arguments": args, "user_id": user.id if user else None},
                timeout=TIMEOUT_S,
            )
        except requests.RequestException as e:
            raise ToolError(f"webhook '{self.name}' request failed: {e}")

        if response.status_code >= 400:
            raise ToolError(f"webhook '{self.name}' returned HTTP {response.status_code}")

        try:
            return response.json()
        except ValueError:
            return {"raw_response": response.text[:2000]}
