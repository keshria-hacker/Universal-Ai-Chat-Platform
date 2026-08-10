with open('tests/test_response_events.py', 'r') as f: content = f.read()
content = content.replace('with patch(\
backend.providers.list_models\, return_value=[]):\n                events = []', 'with patch(\backend.providers.list_models\, return_value=[]):\n                    events = []')
content = content.replace('events.append(event)\n        return events', 'events.append(event)\n            return events')
with open('tests/test_response_events.py', 'w') as f: f.write(content)
print('Fixed')
