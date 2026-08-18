"""
Phase 7: Capability Orchestration Tests

Tests the intelligent tool/capability selection layer.
"""

from __future__ import annotations

import asyncio

from backend.capability_orchestration import capability_decide, CapabilityDecision
from backend.response_intelligence import classify_query_mode, detect_intent_signals
from backend.response_intelligence.schema import IntentSignal, QueryMode, ResponseGuidance
from backend.tools.registry import registry
from backend.tools.schemas import ToolDefinition


def make_tool(name: str, category: str = "general") -> ToolDefinition:
    """Create a test tool definition."""
    return ToolDefinition(
        name=name,
        description=f"Test {name} tool",
        parameters={"type": "object", "properties": {}},
        handler=lambda: "test",
        capabilities=[category],
        category=category,
    )


def make_guidance(mode: QueryMode = QueryMode.CONVERSATIONAL, intent: IntentSignal | None = None) -> ResponseGuidance:
    """Create a test response guidance."""
    if intent is None:
        intent = IntentSignal()
    return ResponseGuidance(mode=mode, intent=intent)


def test_explicit_list_files():
    """Test: Explicit list files request -> filtered to list_files."""
    user_msg = "List the files in the project."
    tools = [make_tool("list_files", "file"), make_tool("read_file", "file"), make_tool("web_search", "web")]
    guidance = make_guidance(QueryMode.INSTRUCTIONAL)

    decision = capability_decide(user_msg, tools, guidance)

    assert decision.capability_required == "tool"
    assert decision.tool_requirement == "required"
    assert decision.action_mode == "execute"
    assert decision.confidence == "high"
    assert len(decision.filtered_tools) == 1
    assert decision.filtered_tools[0].name == "list_files"


def test_explicit_read_file():
    """Test: Explicit read file request -> filtered to read_file."""
    user_msg = "Read the file config.py"
    tools = [make_tool("list_files", "file"), make_tool("read_file", "file")]
    guidance = make_guidance(QueryMode.INSTRUCTIONAL)

    decision = capability_decide(user_msg, tools, guidance)

    assert decision.capability_required == "tool"
    assert decision.tool_requirement == "required"
    assert len(decision.filtered_tools) == 1
    assert decision.filtered_tools[0].name == "read_file"


def test_explicit_web_search():
    """Test: Explicit web search request -> filtered to web_search."""
    user_msg = "Search the web for Python news"
    tools = [make_tool("web_search", "web"), make_tool("list_files", "file")]
    guidance = make_guidance(QueryMode.FACTUAL)

    decision = capability_decide(user_msg, tools, guidance)

    assert decision.capability_required == "research"
    assert decision.tool_requirement == "required"
    assert len(decision.filtered_tools) == 1
    assert decision.filtered_tools[0].name == "web_search"


def test_explicit_execute_code():
    """Test: Explicit execute code request -> filtered to execute_code."""
    user_msg = "Execute this code: print('hello')"
    tools = [make_tool("execute_code", "code"), make_tool("list_files", "file")]
    guidance = make_guidance(QueryMode.CODING)

    decision = capability_decide(user_msg, tools, guidance)

    assert decision.capability_required == "tool"
    assert decision.tool_requirement == "required"
    assert len(decision.filtered_tools) == 1
    assert decision.filtered_tools[0].name == "execute_code"


def test_pure_explanation_no_tool():
    """Test: Pure explanation request -> no tools needed."""
    user_msg = "What is Python?"
    tools = [make_tool("list_files", "file"), make_tool("web_search", "web")]
    guidance = make_guidance(QueryMode.FACTUAL)

    decision = capability_decide(user_msg, tools, guidance)

    assert decision.capability_required == "none"
    assert decision.tool_requirement == "none"
    assert decision.action_mode == "answer"
    assert decision.confidence == "high"
    assert len(decision.filtered_tools) == 0


def test_explain_python_no_tool():
    """Test: Explain Python concept -> no tools."""
    user_msg = "Explain Python lists"
    tools = [make_tool("list_files", "file"), make_tool("execute_code", "code")]
    guidance = make_guidance(QueryMode.INSTRUCTIONAL)

    decision = capability_decide(user_msg, tools, guidance)

    # Explanation doesn't need tools even in instructional mode
    assert decision.capability_required == "none"
    assert len(decision.filtered_tools) == 0


def test_filesystem_context_instructional():
    """Test: Filesystem context + instructional mode -> file tools available."""
    user_msg = "Show me the project structure"
    tools = [make_tool("list_files", "file"), make_tool("read_file", "file"), make_tool("web_search", "web")]
    guidance = make_guidance(QueryMode.INSTRUCTIONAL)

    decision = capability_decide(user_msg, tools, guidance)

    assert decision.capability_required == "file"
    assert decision.tool_requirement == "possible"
    assert decision.action_mode == "investigate"
    assert decision.confidence == "medium"
    # Should have list_files and read_file
    tool_names = {t.name for t in decision.filtered_tools}
    assert "list_files" in tool_names
    assert "read_file" in tool_names
    assert "web_search" not in tool_names


def test_web_search_context_factual():
    """Test: Web search context + factual mode -> web_search available."""
    user_msg = "What's the latest Python version today?"
    tools = [make_tool("web_search", "web"), make_tool("list_files", "file")]
    guidance = make_guidance(QueryMode.FACTUAL)

    decision = capability_decide(user_msg, tools, guidance)

    assert decision.capability_required == "research"
    assert decision.tool_requirement == "possible"
    assert len(decision.filtered_tools) == 1
    assert decision.filtered_tools[0].name == "web_search"


def test_code_execution_context():
    """Test: Code execution context + coding mode -> execute_code available."""
    user_msg = "Please try running the following Python function in the sandbox"
    tools = [make_tool("execute_code", "code"), make_tool("list_files", "file")]
    guidance = make_guidance(QueryMode.CODING)

    decision = capability_decide(user_msg, tools, guidance)

    assert decision.capability_required == "tool"
    assert decision.tool_requirement == "possible"
    assert decision.action_mode == "execute"
    assert decision.confidence == "medium"
    assert len(decision.filtered_tools) == 1
    assert decision.filtered_tools[0].name == "execute_code"


def test_ambiguous_request_preserves_tools():
    """Test: Ambiguous request -> all tools preserved (conservative)."""
    user_msg = "Investigate why my project is broken"
    tools = [make_tool("list_files", "file"), make_tool("read_file", "file"), make_tool("web_search", "web")]
    guidance = make_guidance(QueryMode.ANALYSIS)

    decision = capability_decide(user_msg, tools, guidance)

    # Conservative: all tools available when uncertain
    assert len(decision.filtered_tools) == 3
    assert decision.confidence in ("low", "medium")


def test_disabled_tool_not_in_filtered():
    """Test: Disabled tool is not included in filtered tools."""
    from backend.tools.registry import ToolRegistry

    # Use a clean registry
    test_registry = ToolRegistry()
    test_registry.register(make_tool("list_files", "file"))
    test_registry.register(make_tool("read_file", "file"))
    test_registry.disable("read_file")

    tools = test_registry.get_enabled()
    guidance = make_guidance(QueryMode.INSTRUCTIONAL)

    user_msg = "List files in project"
    decision = capability_decide(user_msg, tools, guidance)

    # Only enabled tools should be in filtered
    assert len(decision.filtered_tools) == 1
    assert decision.filtered_tools[0].name == "list_files"


def test_coding_mode_all_tools():
    """Test: Coding mode without explicit execution -> all tools available (model decides)."""
    user_msg = "Write a Python function"
    tools = [make_tool("list_files", "file"), make_tool("execute_code", "code")]
    guidance = make_guidance(QueryMode.CODING)

    decision = capability_decide(user_msg, tools, guidance)

    # Coding mode keeps all tools for model to decide
    assert decision.capability_required == "tool"
    assert decision.tool_requirement == "possible"
    assert decision.confidence == "low"
    assert len(decision.filtered_tools) == 2


def test_factual_question_no_tools():
    """Test: Simple factual question -> no tools."""
    user_msg = "Capital of France?"
    tools = [make_tool("web_search", "web"), make_tool("list_files", "file")]
    guidance = make_guidance(QueryMode.FACTUAL)

    decision = capability_decide(user_msg, tools, guidance)

    # Factual question with direct answer trigger doesn't need tools
    assert decision.capability_required == "none"
    assert len(decision.filtered_tools) == 0


def test_phase6_signals_preserved():
    """Test: Phase 6 response guidance remains functional."""
    user_msg = "What is Python?"

    signals = detect_intent_signals(user_msg)
    mode = classify_query_mode(user_msg)

    # Phase 6 signals should work
    assert signals.wants_direct_answer is True
    assert mode == QueryMode.FACTUAL
    assert signals.capability_hint == "none"
    assert signals.tool_need == "none"


def test_capability_decision_structure():
    """Test: CapabilityDecision has all expected fields."""
    user_msg = "List files"
    tools = [make_tool("list_files", "file")]
    guidance = make_guidance(QueryMode.INSTRUCTIONAL)

    decision = capability_decide(user_msg, tools, guidance)

    # Verify all dataclass fields exist
    assert hasattr(decision, "capability_required")
    assert hasattr(decision, "tool_requirement")
    assert hasattr(decision, "action_mode")
    assert hasattr(decision, "confidence")
    assert hasattr(decision, "filtered_tools")
    assert hasattr(decision, "reasoning")
    assert hasattr(decision, "phase6_tool_signals")
    assert decision.reasoning != ""


def test_no_regressions_max_tool_rounds():
    """Test: MAX_TOOL_ROUNDS constant unchanged."""
    from backend.providers import MAX_TOOL_ROUNDS, DEFAULT_TOOL_TIMEOUT
    assert MAX_TOOL_ROUNDS == 10
    assert DEFAULT_TOOL_TIMEOUT == 30.0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])