"""Sandboxed Python execution tool.

This is what lets the agent "solve" math/logic/data problems instead of
just talking about them: the LLM writes a short Python snippet, this tool
runs it in an isolated subprocess with a restricted builtin set, a hard
timeout, and no filesystem/network/OS access, and returns whatever it
printed.

Isolation model (good enough for a portfolio demo, not a hardened
multi-tenant sandbox):
  - runs in its own OS process (multiprocessing, spawn context) — a crash
    or infinite loop can't take down the FastAPI process
  - hard wall-clock timeout; the process is killed if it overruns
  - `__builtins__` is replaced with a small allowlist — no `open`,
    `__import__`, `eval`, `exec`, `input`, or access to `os`/`sys`/`socket`
  - only a few safe stdlib modules (math, statistics, itertools, random,
    json, re, datetime) are pre-injected; nothing else can be imported
  - stdout is captured and returned; nothing is written to disk

For production hardening beyond this: run inside a locked-down container
(gVisor/Firecracker), enforce RLIMIT_AS/RLIMIT_CPU via `resource`, and
strip network namespace access entirely.
"""
import contextlib
import io
import multiprocessing

from app.tools.base import BaseTool, ToolError

TIMEOUT_S = 6
MAX_OUTPUT_CHARS = 4000
MAX_CODE_CHARS = 8000

_SAFE_BUILTIN_NAMES = (
    "abs", "all", "any", "bin", "bool", "chr", "dict", "divmod", "enumerate",
    "filter", "float", "format", "frozenset", "hex", "int", "isinstance",
    "len", "list", "map", "max", "min", "oct", "ord", "pow", "print",
    "range", "repr", "reversed", "round", "set", "slice", "sorted", "str",
    "sum", "tuple", "type", "zip", "True", "False", "None",
)


def _build_safe_globals():
    import builtins as _builtins
    import math
    import statistics
    import itertools
    import random
    import json
    import re
    import datetime

    safe_builtins = {name: getattr(_builtins, name) for name in _SAFE_BUILTIN_NAMES}
    return {
        "__builtins__": safe_builtins,
        "math": math,
        "statistics": statistics,
        "itertools": itertools,
        "random": random,
        "json": json,
        "re": re,
        "datetime": datetime,
    }


def _worker(code: str, queue: "multiprocessing.Queue"):
    output = io.StringIO()
    try:
        safe_globals = _build_safe_globals()
        with contextlib.redirect_stdout(output):
            exec(compile(code, "<agent_code>", "exec"), safe_globals)
        queue.put({"success": True, "output": output.getvalue()[-MAX_OUTPUT_CHARS:]})
    except Exception as e:  # noqa: BLE001 - deliberately broad, sandboxed process
        queue.put({
            "success": False,
            "output": output.getvalue()[-MAX_OUTPUT_CHARS:],
            "error": f"{type(e).__name__}: {e}",
        })


class CodeExecutionTool(BaseTool):
    name = "run_code"

    def validate(self, arguments):
        code = (arguments or {}).get("code")
        if not code or not isinstance(code, str):
            raise ToolError("run_code requires a non-empty 'code' string")
        if len(code) > MAX_CODE_CHARS:
            raise ToolError(f"code is too long (max {MAX_CODE_CHARS} chars)")
        return {"code": code}

    def run(self, db, user, arguments):
        args = self.validate(arguments)

        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        proc = ctx.Process(target=_worker, args=(args["code"], queue))
        proc.start()
        proc.join(TIMEOUT_S)

        if proc.is_alive():
            proc.terminate()
            proc.join(1)
            raise ToolError(f"Code execution timed out after {TIMEOUT_S}s (possible infinite loop)")

        if queue.empty():
            raise ToolError("Code execution crashed with no output")

        result = queue.get()
        return {
            "success": result["success"],
            "output": result["output"].strip(),
            "error": result.get("error"),
            "code": args["code"],
        }
