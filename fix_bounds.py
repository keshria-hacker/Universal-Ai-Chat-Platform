import re
with open('tests/test_response_events.py', 'r') as f:
    content = f.read()

lines = content.split('\n')
start = None
end = None
for i, line in enumerate(lines):
    if 'class ProviderEventFacadeTests' in line:
        start = i
    if start is not None and i > start and line.strip() == 'if __name__ == \
__main__\:':
        end = i
        break

print('start=', start, 'end=', end)
