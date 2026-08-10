import re
with open('tests/test_response_events.py', 'r') as f:
    content = f.read()

# Use regex to fix indentation of async for loops inside nested with blocks
# Match: with patch, with patch, events = [], async for (not properly indented)
# Replace with proper 4-space indentation for the inner block

lines = content.split('\n')
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)
    if 'with patch(\
providers.resolve_api_key\, return_value=\test-key\):' in line:
        # Next few lines until the closing ) or : need indentation fix
        j = i + 1
        # events = []
        if j < len(lines):
            new_lines[-1] = line  # Keep the with line
            new_lines.append('        ' + lines[j].lstrip())
            j += 1
        # async for event in providers.stream_response_events(
        while j < len(lines) and not lines[j].strip().startswith('events.append'):
            if j < len(lines):
                new_lines.append('        ' + lines[j].lstrip())
            j += 1
        # events.append(event)
        if j < len(lines):
            new_lines.append('        ' + lines[j].lstrip())
            j += 1
        # close the async for ) or :
        if j < len(lines):
            new_lines.append('        ' + lines[j].lstrip())
            j += 1
        i = j - 1
    i += 1

content = '\n'.join(new_lines)
with open('tests/test_response_events.py', 'w') as f:
    f.write(content)
print('Done')
