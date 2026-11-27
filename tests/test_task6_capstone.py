import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

os.environ.setdefault("GEMINI_API_KEY", "")

from app.capstone.service import CapstoneService


def test_task6_retrieval_returns_project_evidence():
    svc = object.__new__(CapstoneService)
    svc.knowledge = [("voxmate_task6.md", "VoxMate uses Gemini, RAG, tools and agents for the capstone project.")]
    results = svc.retrieve("How does VoxMate use Gemini and RAG?")
    assert results and results[0][0] == "voxmate_task6.md"


def test_task6_safe_calculator():
    assert CapstoneService._safe_calculate("125 * (4 + 8)") == "1500"


def test_task6_calculator_rejects_code():
    try:
        CapstoneService._safe_calculate("__import__(\"os\").system(\"whoami\")")
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe expression was accepted")


def test_task6_fallback_planner_is_deterministic():
    svc = object.__new__(CapstoneService)
    class DummyLLM:
        def generate_content(self, **kwargs):
            raise RuntimeError("offline test")
    svc.llm = DummyLLM()
    assert svc._plan("calculate 12 * 4") == ["calculator"]
    assert svc._plan("How does VoxMate RAG work?") == ["retrieve_knowledge"]
