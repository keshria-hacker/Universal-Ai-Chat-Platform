with open('tests/test_response_events.py', 'r') as f: lines = f.readlines()
new_lines = []
for i, line in enumerate(lines):
    if 'list_models' in line and 'return_value' in line:
        new_lines.append(line)
        if i + 1 < len(lines) and 'events = []' in lines[i+1] and lines[i+1].startswith('                '):
            new_lines.append('                    events = []\n')
            continue
    elif 'async for event' in line and line.startswith('                ') and not line.startswith('                    '):
        new_lines.append('                    ' + line.lstrip())
    elif line.strip() == '):' and line.startswith('                ') and not line.startswith('                    '):
        new_lines.append('                    ):\n')
    elif 'events.append' in line and line.startswith('                    ') and not line.startswith('                        '):
        new_lines.append('                        ' + line.lstrip())
    else:
        new_lines.append(line)
with open('tests/test_response_events.py', 'w') as f: f.writelines(new_lines)
print('Done')
