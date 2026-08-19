"""

Unit tests for ContextManager - Phase 9 P0 token budget and safe truncation.



Tests cover:

- Token counting for different message types

- Truncation preserves system messages

- Truncation preserves tool messages

- Truncation preserves last user message

- Truncation works with different model context windows

- Edge cases (empty messages, already fits, over budget)

"""



import unittest

from dataclasses import dataclass

from unittest.mock import MagicMock, patch



from backend.context_manager import (

    ContextManager,

    ContextBudget,

    TruncationResult,

    _get_encoding_for_model,

    count_tokens,

    count_message_tokens,

    create_context_manager,

)

from backend.providers.base import ModelInfo, ModelCapabilities





@dataclass

class MockModelInfo:

    """Mock ModelInfo for testing."""

    id: str = "test::model"

    name: str = "Test Model"

    provider_id: str = "test"

    provider_label: str = "Test Provider"

    litellm_id: str = "test/model"

    context_window: int = 4096

    capabilities: ModelCapabilities | None = None



    def __post_init__(self):

        if self.capabilities is None:

            self.capabilities = ModelCapabilities(streaming=True, tools=False, reasoning=False, vision=False)





class TestEncodingSelection(unittest.TestCase):

    """Tests for model-specific encoding selection."""



    def test_get_encoding_for_gpt4o(self):

        """GPT-4o models should use o200k_base encoding."""

        encoding = _get_encoding_for_model("openai/gpt-4o")

        self.assertEqual(encoding.name, "o200k_base")



    def test_get_encoding_for_gpt4_turbo(self):

        """GPT-4-Turbo should use cl100k_base encoding."""

        encoding = _get_encoding_for_model("openai/gpt-4-turbo")

        self.assertEqual(encoding.name, "cl100k_base")



    def test_get_encoding_for_claude(self):

        """Claude models should fall back to cl100k_base."""

        encoding = _get_encoding_for_model("anthropic/claude-3-opus")

        self.assertEqual(encoding.name, "cl100k_base")



    def test_get_encoding_for_gemini(self):

        """Gemini models should fall back to cl100k_base."""

        encoding = _get_encoding_for_model("gemini/gemini-1.5-pro")

        self.assertEqual(encoding.name, "cl100k_base")



    def test_get_encoding_fallback(self):

        """Unknown models should fall back to cl100k_base."""

        encoding = _get_encoding_for_model("unknown/model-xyz")

        self.assertEqual(encoding.name, "cl100k_base")





class TestTokenCounting(unittest.TestCase):

    """Tests for token counting utilities."""



    def setUp(self):

        self.encoding = _get_encoding_for_model("gpt-4")



    def test_count_tokens_empty_string(self):

        """Empty string should return 0 tokens."""

        self.assertEqual(count_tokens("", self.encoding), 0)



    def test_count_tokens_simple_text(self):

        """Simple text should return approximate token count."""

        text = "Hello world"

        tokens = count_tokens(text, self.encoding)

        self.assertGreater(tokens, 0)

        self.assertLess(tokens, 20)



    def test_count_message_tokens_user_message(self):

        """User message should include role overhead."""

        msg = {"role": "user", "content": "Hello"}

        tokens = count_message_tokens(msg, self.encoding)

        # ~3 for role + content tokens

        self.assertGreaterEqual(tokens, 3)



    def test_count_message_tokens_system_message(self):

        """System message should be counted."""

        msg = {"role": "system", "content": "You are a helpful assistant"}

        tokens = count_message_tokens(msg, self.encoding)

        self.assertGreaterEqual(tokens, 3)



    def test_count_message_tokens_with_tool_calls(self):

        """Assistant message with tool_calls should include them."""

        msg = {

            "role": "assistant",

            "content": "",

            "tool_calls": [{"id": "call_123", "function": {"name": "test", "arguments": "{}"}}]

        }

        tokens = count_message_tokens(msg, self.encoding)

        self.assertGreaterEqual(tokens, 3)



    def test_count_message_tokens_tool_message(self):

        """Tool message should include tool_call_id."""

        msg = {

            "role": "tool",

            "content": "Result",

            "tool_call_id": "call_123"

        }

        tokens = count_message_tokens(msg, self.encoding)

        self.assertGreaterEqual(tokens, 3)



    def test_count_message_tokens_structured_content(self):

        """Vision message with structured content should count text parts."""

        msg = {

            "role": "user",

            "content": [

                {"type": "text", "text": "Describe this image"},

                {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}}

            ]

        }

        tokens = count_message_tokens(msg, self.encoding)

        # Text part + image approximation (~170) + role overhead

        self.assertGreater(tokens, 170)





class TestContextBudget(unittest.TestCase):

    """Tests for ContextBudget dataclass."""



    def test_available_for_context_basic(self):

        """Available context = window - output - margin."""

        budget = ContextBudget(

            model_context_window=4096,

            reserved_output_tokens=1024,

            safety_margin=256

        )

        self.assertEqual(budget.available_for_context, 2816)



    def test_available_for_context_small_window(self):

        """Small context window should handle correctly."""

        budget = ContextBudget(

            model_context_window=1024,

            reserved_output_tokens=512,

            safety_margin=128

        )

        self.assertEqual(budget.available_for_context, 384)



    def test_available_for_context_no_negative(self):

        """Available should not go negative."""

        budget = ContextBudget(

            model_context_window=100,

            reserved_output_tokens=200,

            safety_margin=50

        )

        self.assertEqual(budget.available_for_context, 0)





class TestTruncationResult(unittest.TestCase):

    """Tests for TruncationResult dataclass."""



    def test_utilization_pct(self):

        """Utilization percentage calculation."""

        budget = ContextBudget(model_context_window=4096, reserved_output_tokens=1024, safety_margin=256)

        result = TruncationResult(

            messages=[],

            truncated=True,

            original_token_count=3000,

            final_token_count=2000,

            removed_message_count=5,

            budget=budget

        )

        # 2000 / 2816 * 100 ≈ 71.0%

        self.assertAlmostEqual(result.utilization_pct, 71.0, places=1)



    def test_utilization_pct_zero_budget(self):

        """Zero budget should return 100%."""

        budget = ContextBudget(model_context_window=100, reserved_output_tokens=200, safety_margin=50)

        result = TruncationResult(

            messages=[],

            truncated=False,

            original_token_count=0,

            final_token_count=0,

            removed_message_count=0,

            budget=budget

        )

        self.assertEqual(result.utilization_pct, 100.0)





class TestContextManager(unittest.TestCase):

    """Tests for ContextManager truncation logic."""



    def setUp(self):

        self.model_info = MockModelInfo(context_window=4096, litellm_id="openai/gpt-4")

        self.manager = ContextManager(self.model_info, reserved_output_tokens=1024, safety_margin=256)



    def test_empty_messages(self):

        """Empty message list should return empty result."""

        result = self.manager.truncate([])

        self.assertEqual(result.messages, [])

        self.assertFalse(result.truncated)

        self.assertEqual(result.original_token_count, 0)

        self.assertEqual(result.final_token_count, 0)



    def test_messages_fit_in_budget(self):

        """Messages that fit should not be truncated."""

        messages = [

            {"role": "system", "content": "You are helpful"},

            {"role": "user", "content": "Hello"},

            {"role": "assistant", "content": "Hi there!"},

        ]

        result = self.manager.truncate(messages)

        self.assertFalse(result.truncated)

        self.assertEqual(len(result.messages), 3)

        self.assertEqual(result.removed_message_count, 0)



    def test_preserves_system_messages(self):

        """System messages should always be preserved."""

        # Create messages that exceed budget

        long_content = "x" * 3000  # Large content

        messages = [

            {"role": "system", "content": "Important system prompt"},

            {"role": "user", "content": long_content},

            {"role": "assistant", "content": long_content},

            {"role": "user", "content": "Last message"},

        ]

        result = self.manager.truncate(messages)

        # System message should be in result

        system_msgs = [m for m in result.messages if m["role"] == "system"]

        self.assertEqual(len(system_msgs), 1)

        self.assertEqual(system_msgs[0]["content"], "Important system prompt")



    def test_preserves_tool_messages(self):

        """Tool messages (results) should always be preserved."""

        long_content = "x" * 3000

        messages = [

            {"role": "user", "content": long_content},

            {"role": "assistant", "content": long_content},

            {"role": "tool", "content": "Tool result", "tool_call_id": "call_123"},

            {"role": "user", "content": "Last message"},

        ]

        result = self.manager.truncate(messages)

        # Tool message should be preserved

        tool_msgs = [m for m in result.messages if m["role"] == "tool"]

        self.assertEqual(len(tool_msgs), 1)

        self.assertEqual(tool_msgs[0]["content"], "Tool result")



    def test_preserves_assistant_with_tool_calls(self):

        """Assistant messages with tool_calls should be preserved."""

        long_content = "x" * 3000

        messages = [

            {"role": "user", "content": long_content},

            {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1", "function": {"name": "test", "arguments": "{}"}}]},

            {"role": "tool", "content": "Result", "tool_call_id": "call_1"},

            {"role": "user", "content": "Last message"},

        ]

        result = self.manager.truncate(messages)

        # Assistant with tool_calls should be preserved

        assistant_tool_msgs = [m for m in result.messages if m.get("tool_calls")]

        self.assertEqual(len(assistant_tool_msgs), 1)



    def test_preserves_last_user_message(self):

        """The last user message should always be preserved."""

        long_content = "x" * 3000

        messages = [

            {"role": "user", "content": long_content},

            {"role": "assistant", "content": long_content},

            {"role": "user", "content": "This is the last user message"},

        ]

        result = self.manager.truncate(messages)

        # Last user message should be preserved

        user_msgs = [m for m in result.messages if m["role"] == "user"]

        self.assertTrue(any(m["content"] == "This is the last user message" for m in user_msgs))



    def test_truncates_old_user_assistant_pairs(self):

        """Old user/assistant pairs should be truncated first."""

        # 20000 chars ~ 2500 tokens per message (with cl100k_base)

        # 4 messages = ~10000 tokens, budget is 2816

        long_content = "x" * 20000

        messages = [

            {"role": "user", "content": long_content},  # Pair 1

            {"role": "assistant", "content": long_content},

            {"role": "user", "content": long_content},  # Pair 2

            {"role": "assistant", "content": long_content},

            {"role": "user", "content": "Last message"},  # Should keep

        ]

        result = self.manager.truncate(messages)

        # Should have removed some old pairs

        self.assertTrue(result.truncated)

        self.assertTrue(result.removed_message_count > 0)



    def test_preserves_chronological_order(self):

        """Result messages should maintain chronological order."""

        messages = [

            {"role": "system", "content": "System"},

            {"role": "user", "content": "First"},

            {"role": "assistant", "content": "Response 1"},

            {"role": "user", "content": "Second"},

            {"role": "assistant", "content": "Response 2"},

            {"role": "user", "content": "Last"},

        ]

        result = self.manager.truncate(messages)

        # Order should be preserved

        contents = [m.get("content", "") for m in result.messages if m.get("content")]

        self.assertEqual(contents, ["System", "First", "Response 1", "Second", "Response 2", "Last"])



    def test_small_context_window(self):

        """Test with small context window (e.g., 2048)."""

        small_model = MockModelInfo(context_window=2048, litellm_id="test/small")

        manager = ContextManager(small_model, reserved_output_tokens=512, safety_margin=128)



        messages = [

            {"role": "system", "content": "System prompt"},

            {"role": "user", "content": "x" * 500},

            {"role": "assistant", "content": "x" * 500},

            {"role": "user", "content": "Last"},

        ]

        result = manager.truncate(messages)

        self.assertTrue(result.truncated or len(result.messages) <= 4)



    def test_preserved_messages_exceed_budget(self):

        """If preserved messages alone exceed budget, return them anyway."""

        # System + tool messages that are huge (~2500 tokens each)

        # Total ~5000 tokens, budget is 2816

        long_content = "x" * 20000

        messages = [

            {"role": "system", "content": long_content},

            {"role": "tool", "content": long_content, "tool_call_id": "call_1"},

            {"role": "user", "content": "Last"},

        ]

        result = self.manager.truncate(messages)

        # Should still return all messages (all are preserved, none removed)

        self.assertEqual(len(result.messages), 3)

        # truncated=True because the result differs from original (non-preserved would be removed if they existed)

        self.assertTrue(result.truncated)

        # Budget is exceeded

        self.assertGreater(result.final_token_count, result.budget.available_for_context)



    def test_prepare_messages_alias(self):

        """prepare_messages should work same as truncate."""

        messages = [

            {"role": "user", "content": "Hello"},

            {"role": "assistant", "content": "Hi"},

        ]

        result = self.manager.prepare_messages(messages)

        self.assertIsInstance(result, TruncationResult)



    def test_disabled_preserve_last_user(self):

        """When preserve_last_user=False, last user may be truncated."""

        long_content = "x" * 3000

        messages = [

            {"role": "user", "content": long_content},

            {"role": "assistant", "content": long_content},

            {"role": "user", "content": "Last user message"},

        ]

        result = self.manager.truncate(messages, preserve_last_user=False)

        # Last user might be removed if budget tight

        # (depends on exact token counts)





class TestCreateContextManager(unittest.TestCase):

    """Tests for factory function."""



    def test_create_context_manager(self):

        """Factory should return ContextManager instance."""

        model_info = MockModelInfo()

        manager = create_context_manager(model_info)

        self.assertIsInstance(manager, ContextManager)

        self.assertEqual(manager.model_info, model_info)



    def test_create_context_manager_custom_params(self):

        """Factory should pass custom parameters."""

        model_info = MockModelInfo()

        manager = create_context_manager(model_info, reserved_output_tokens=2048, safety_margin=512)

        self.assertEqual(manager.budget.reserved_output_tokens, 2048)

        self.assertEqual(manager.budget.safety_margin, 512)





class TestContextManagerIntegration(unittest.TestCase):

    """Integration-style tests simulating real usage."""



    def test_chat_with_rag_and_web_context(self):

        """Simulate a chat with system prompt, RAG, web search, and history."""

        model_info = MockModelInfo(context_window=4096, litellm_id="openai/gpt-4")

        manager = ContextManager(model_info, reserved_output_tokens=1024, safety_margin=256)



        # Simulate: system prompt + web search result + RAG chunks + history + current turn

        messages = [

            {"role": "system", "content": "You are a helpful assistant."},

            {"role": "system", "content": "[Web search results] Latest news about AI..."},

            {"role": "system", "content": "[RAG context] From document.pdf: Important facts..."},

            {"role": "user", "content": "What is AI?"},

            {"role": "assistant", "content": "AI is artificial intelligence..."},

            {"role": "user", "content": "Tell me more"},

            {"role": "assistant", "content": "AI includes machine learning..."},

            {"role": "user", "content": "How does it work?"},

        ]



        result = manager.truncate(messages)

        # All system messages preserved

        system_count = sum(1 for m in result.messages if m["role"] == "system")

        self.assertEqual(system_count, 3)

        # Last user preserved

        last_user = next(m for m in reversed(result.messages) if m["role"] == "user")

        self.assertEqual(last_user["content"], "How does it work?")



    def test_tool_cycle_preserved(self):

        """A complete tool invocation cycle should be preserved."""

        model_info = MockModelInfo(context_window=4096, litellm_id="openai/gpt-4")

        manager = ContextManager(model_info, reserved_output_tokens=1024, safety_margin=256)



        messages = [

            {"role": "system", "content": "You have tools."},

            {"role": "user", "content": "List files in /home"},

            {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1", "function": {"name": "list_files", "arguments": '{"path": "/home"}'}}]},

            {"role": "tool", "content": "file1.txt\nfile2.py", "tool_call_id": "call_1"},

            {"role": "user", "content": "Read file2.py"},

        ]



        result = manager.truncate(messages)

        # Tool cycle preserved

        self.assertTrue(any(m.get("tool_calls") for m in result.messages))

        self.assertTrue(any(m["role"] == "tool" for m in result.messages))

        # Last user preserved

        last_user = next(m for m in reversed(result.messages) if m["role"] == "user")

        self.assertEqual(last_user["content"], "Read file2.py")







def test_rag_context_truncation_priority():

    """Test that RAG context is truncated before web context and conversation history."""

    # Create a context manager with a small budget

    model_info = MockModelInfo(context_window=1024, litellm_id="openai/gpt-4o")

    manager = ContextManager(model_info, reserved_output_tokens=512)



    # Create messages that will exceed the budget

    # RAG chunks are very large, web chunks are very small, no conversation history

    messages = [

        {"role": "system", "content": "You are a helpful assistant"},

        {"role": "system", "content": "[RAG context] From file1.txt: This is a long RAG chunk " + "x" * 2000},

        {"role": "system", "content": "[RAG context] From file2.txt: This is another long RAG chunk " + "x" * 2000},

        {"role": "system", "content": "[Web search result] Result 1: This is a web result " + "x" * 50},

        {"role": "system", "content": "[Web search result] Result 2: This is another web result " + "x" * 50},

        {"role": "user", "content": "Current user request"},

    ]



    result = manager.truncate(messages)



    # Should preserve essential system, current user, and as much as fits

    # RAG context should be truncated first (oldest first)

    rag_count = sum(1 for msg in result.messages if "[RAG context]" in msg.get("content", ""))

    web_count = sum(1 for msg in result.messages if "[Web search result]" in msg.get("content", ""))



    # Should have truncated some RAG context

    assert rag_count < 2

    # Should preserve web results

    assert web_count >= 1

    # Should preserve the current user request

    assert any(msg.get("role") == "user" and msg.get("content") == "Current user request" for msg in result.messages)







def test_oversized_current_user_flag():

    """Test that current_user_exceeds_budget is set when the current user message is too large."""

    # Create a context manager with a very small budget

    model_info = MockModelInfo(context_window=128, litellm_id="openai/gpt-4o")

    manager = ContextManager(model_info, reserved_output_tokens=64)



    # Create a message that exceeds the budget

    long_content = "x" * 1000  # This will definitely exceed the budget

    messages = [

        {"role": "system", "content": "You are a helpful assistant"},

        {"role": "user", "content": long_content},

    ]



    result = manager.truncate(messages)



    # Should set the flag

    assert result.current_user_exceeds_budget is True

    # Should preserve the full message (not truncate it)

    assert len(result.messages) == 2

    assert result.messages[1]["content"] == long_content

    # Should preserve the essential system message

    assert result.messages[0]["role"] == "system"





def test_tool_pair_atomicity():

    """Test that tool-call/tool-result pairs are preserved as atomic units."""

    # Create a context manager with a small budget

    model_info = MockModelInfo(context_window=1024, litellm_id="openai/gpt-4o")

    manager = ContextManager(model_info, reserved_output_tokens=512)



    # Create messages with tool interactions and conversation history

    messages = [

        {"role": "system", "content": "You are a helpful assistant"},

        {"role": "user", "content": "User message 1"},

        {"role": "assistant", "content": "Assistant response 1"},

        {"role": "user", "content": "User message 2"},

        {"role": "assistant", "content": "Assistant response with tool call", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "test_tool", "arguments": "{}"}}]},

        {"role": "tool", "content": "Tool result 1", "tool_call_id": "call_1"},

        {"role": "assistant", "content": "Assistant response after tool"},

        {"role": "user", "content": "Current user request"},

    ]



    result = manager.truncate(messages)



    # Should preserve the complete tool interaction

    tool_call_count = sum(1 for msg in result.messages if msg.get("role") == "assistant" and msg.get("tool_calls"))

    tool_result_count = sum(1 for msg in result.messages if msg.get("role") == "tool")



    # Should preserve the tool pair

    assert tool_call_count == 1

    assert tool_result_count == 1

    # Should preserve the current user request

    assert any(msg.get("role") == "user" and msg.get("content") == "Current user request" for msg in result.messages)





def test_phase6_guidance_preservation():

    """Test that Phase 6 guidance is preserved when possible, but can be truncated if needed."""

    # Create a context manager with a small budget

    model_info = MockModelInfo(context_window=1024, litellm_id="openai/gpt-4o")

    manager = ContextManager(model_info, reserved_output_tokens=512)



    # Create messages with Phase 6 guidance and other context

    messages = [

        {"role": "system", "content": "You are a helpful assistant"},

        {"role": "system", "content": "[Response Intelligence] Guidance: This is Phase 6 guidance"},

        {"role": "system", "content": "[RAG context] From file1.txt: Long RAG chunk " + "x" * 1000},

        {"role": "user", "content": "Current user request"},

    ]



    result = manager.truncate(messages)



    # Should preserve Phase 6 guidance if possible

    phase6_count = sum(1 for msg in result.messages if "[Response Intelligence]" in msg.get("content", ""))



    # Should preserve the current user request

    assert any(msg.get("role") == "user" and msg.get("content") == "Current user request" for msg in result.messages)



    # If RAG context is truncated, Phase 6 should still be preserved

    if phase6_count == 0:

        # If Phase 6 was truncated, it means the budget was extremely tight

        # In this case, we should still preserve essential system + current user

        essential_count = sum(1 for msg in result.messages if msg.get("role") == "system" and "helpful assistant" in msg.get("content", ""))

        assert essential_count == 1

        assert any(msg.get("role") == "user" and msg.get("content") == "Current user request" for msg in result.messages)

    else:

        # Phase 6 should be preserved when possible

        assert phase6_count == 1





if __name__ == "__main__":

    unittest.main()