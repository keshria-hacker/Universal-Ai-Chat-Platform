with open('tests/test_response_events.py', 'r') as f: content = f.read()
content = content.replace('patch(\
providers.stream_completion\', 'patch(\backend.providers.stream_completion\')
content = content.replace('patch(\providers.resolve_api_key\', 'patch(\backend.providers.resolve_api_key\')
with open('tests/test_response_events.py', 'w') as f: f.write(content)
print('Fixed')
