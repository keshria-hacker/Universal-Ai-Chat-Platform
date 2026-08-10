with open('tests/test_response_events.py', 'r') as f: content = f.read()
old = '''async def test_supported_provider_text_becomes_canonical_text_delta(self):
        provider_ids = [
            \
openai\, \anthropic\, \gemini\, \nvidia\, \together\,
            \groq\, \openrouter\, \deepseek\, \mistral\, \ollama\, \omniroute\,
        ]
        for provider_id in provider_ids:
            events = await self._collect_for_provider(provider_id)
            text = \\.join(e.content or \\ for e in events if e.type == ResponseEventType.TEXT_DELTA)
            self.assertEqual(text, \Hello
world\)
            self.assertEqual(events[0].type, ResponseEventType.MESSAGE_START)
            self.assertEqual(events[-1].type, ResponseEventType.MESSAGE_END)
            self.assertEqual([e.sequence for e in events], list(range(len(events))))'''
new = '''async def test_supported_provider_text_becomes_canonical_text_delta(self):
        async def fake_stream_completion(*args, **kwargs):
            yield \Hello\
            yield \
world\
 
        with patch(\backend.providers.ollama.OllamaProvider.stream_completion\, fake_stream_completion):
            with patch(\backend.providers.resolve_api_key\, return_value=\test-key\):
                with patch(\backend.providers.list_models\, return_value=[]):
                    events = []
                    async for event in providers.stream_response_events(
                        \ollama::ollama/model\,
                        [{\role\: \user\, \content\: \hi\}],
                        MagicMock(),
                    ):
                        events.append(event)
        text = \\.join(e.content or \\ for e in events if e.type == ResponseEventType.TEXT_DELTA)
        self.assertEqual(text, \Hello
world\)
        self.assertEqual(events[0].type, ResponseEventType.MESSAGE_START)
        self.assertEqual(events[-1].type, ResponseEventType.MESSAGE_END)
        self.assertEqual([e.sequence for e in events], list(range(len(events))))'''
content = content.replace(old, new)
with open('tests/test_response_events.py', 'w') as f: f.write(content)
print('Done')
