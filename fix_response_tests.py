import re
with open('tests/test_response_events.py', 'r') as f:
    content = f.read()

old = '    async def _collect_for_provider(self, provider_id: str):'
