import os
os.chdir(r'D:\\\\projects\\\\chat_app\\\\Universal-Ai-Chat-Platform')
files = [
    'tests/test_providers.py',
    'tests/test_response_events.py',
    'tests/test_frontend_response_controller.py',
    'tests/test_providers_init_coverage.py',
    'tests/test_llm.py',
    'tests/test_model_fetch.py',
    'tests/test_model_selection.py',
    'tests/test_schemas.py',
]
for path in files:
    if os.path.exists(path):
        with open(path, 'r') as f:
            content = f.read()
        content = content.replace('sys.path.insert(0, str(ROOT / \
backend\))', 'sys.path.insert(0, str(ROOT))')
        with open(path, 'w') as f:
            f.write(content)
        print('Fixed ' + path)
    else:
        print('Not found: ' + path)
