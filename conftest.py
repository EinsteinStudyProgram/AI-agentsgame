"""
pytest 全局 conftest
在 Django 初始化之前 mock pgvector，以便在 SQLite 上运行测试
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.test_settings")
