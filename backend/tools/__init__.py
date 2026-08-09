"""Tools package - Tool execution infrastructure."""
from __future__ import annotations

from tools.schemas import (
    ToolDefinition,
    ToolCall,
    ToolResult,
    validate_tool_arguments,
    tool_definition_to_openai_function,
    tool_definition_to_anthropic_tool,
)
from tools.registry import ToolRegistry, registry
from tools.executor import ToolExecutor, ToolExecutionError, ToolTimeoutError, ToolValidationError, executor
from tools.builtin import register_builtin_tools

__all__ = [
    # Schemas
    "ToolDefinition",
    "ToolCall",
    "ToolResult",
    "validate_tool_arguments",
    "tool_definition_to_openai_function",
    "tool_definition_to_anthropic_tool",
    # Registry
    "ToolRegistry",
    "registry",
    # Executor
    "ToolExecutor",
    "ToolExecutionError",
    "ToolTimeoutError",
    "ToolValidationError",
    "executor",
    # Built-ins
    "register_builtin_tools",
]
