with open('backend/apps/agents/tests/test_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove all @pytest.mark.asyncio lines since we us