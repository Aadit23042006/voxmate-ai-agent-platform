import pytest
from app.tools.code_execution_tool import CodeExecutionTool
from app.tools.document_tool import DocumentQATool
from app.tools.base import ToolError
from app.agents.router import classify_agent


def test_code_execution_runs_and_returns_output():
    tool = CodeExecutionTool()
    result = tool.run(None, None, {"code": "print(2 + 2)"})
    assert result["success"] is True
    assert result["output"] == "4"


def test_code_execution_blocks_dangerous_imports():
    tool = CodeExecutionTool()
    result = tool.run(None, None, {"code": "import os\nprint(os.getcwd())"})
    assert result["success"] is False
    assert "Error" in result["error"]


def test_code_execution_times_out_on_infinite_loop():
    tool = CodeExecutionTool()
    with pytest.raises(ToolError):
        tool.run(None, None, {"code": "while True:\n    pass"})


def test_code_execution_requires_code():
    tool = CodeExecutionTool()
    with pytest.raises(ToolError):
        tool.validate({})


def test_document_qa_requires_question():
    tool = DocumentQATool()
    with pytest.raises(ToolError):
        tool.validate({})


def test_router_classifies_math_intent():
    assert classify_agent("calculate the average of 4, 8, 15").key == "math"


def test_router_classifies_document_intent():
    assert classify_agent("what does my uploaded file say about revenue").key == "document"


def test_router_defaults_to_general():
    assert classify_agent("remind me to call mom tomorrow").key == "general"
