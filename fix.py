import re
with open('tests/test_response_events.py', 'r') as f:
    content = f.read()

old = '''    async def _collect_for_provider(self, provider_id: str):
        async def fake_stream_completion(*args, **kwargs):
            yield \
Hello\
            yield \
world\

        with patch(\
backend.providers.stream_completion\, fake_stream_completion):
            with patch(\
backend.providers.resolve_api_key\, return_value=\test-key\):
                with patch(\
backend.providers.list_models\, return_value=[]):
                    events = []
                    async for event in providers.stream_response_events(
                        f\
/model\,
                        [{\
role\: \user\, \content\: \hi\}],
                        MagicMock(),  # db mock - won't be used due to patch
                    ):
                        events.append(event)
        return events'''
