"""
测试用 Django 配置
使用 SQLite 替代 PostgreSQL 进行测试
pgvector 包可用时自动使用 VectorField，不可用则降级 JSONField
"""
import os
from pathlib import Path

# ------------------------------------------
# 强制让 memory/models.py 走 JSONField fallback
# 因为 SQLite 不支持 pgvector 的 VectorField
# ------------------------------------------
import sys

# 移除真实 pgvector 模块，让 models.py 的 except ImportError 生效
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("pgvector"):
        del sys.modules[mod_name]
# ====== Django Settings ======
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = "test-secret-key-for-testing-only"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "channels",
    "backend.apps.agents",
    "backend.apps.memory",
    "backend.apps.world",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "backend.config.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.debug",
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]

WSGI_APPLICATION = "backend.config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

STATIC_URL = "/static/"
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LLM_CONFIG = {
    "deepseek": {
        "api_key": "",
        "api_base": "https://api.deepseek.com/v1",
        "model_pro": "deepseek-chat",
        "model_flash": "deepseek-chat",
    },
    "embedding_model": "text-embedding-ada-002",
}

MEMORY_CONFIG = {
    "retrieval_count": 10,
    "importance_decay_hours": 24,
    "recency_weight": 0.3,
    "importance_weight": 0.3,
    "relevance_weight": 0.4,
}

