import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.config.settings')
django.setup()
from django.conf import settings
cfg = settings.LLM_CONFIG
key = cfg.get('deepseek', {}).get('api_key', '')
print(f'Key configured: {bool(key)}')
print(f'Key length: {len(key)}')
print(f'API Base: {cfg.get("deepseek", {}).get("api_base", "")}')
