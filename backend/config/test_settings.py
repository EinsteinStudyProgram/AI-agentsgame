"""
测试用 Django 配置
使用 SQLite 替代 PostgreSQL，mock pgvector
"""
import os
from pathlib import Path

# 先 mock pgvector 的 VectorField，因为 SQLite 不支持
import sys
import types

# 创建 pgvector mock 模块
pgvector_mock = types.ModuleType('pgvector')
pgvector_django_mock = types.ModuleType('pgvector.django')
pgvector_django_vector_mock = types.ModuleType('pgvector.django.vector')

class MockVectorField:
    """Mock pgvector VectorField - 在 SQLite 下使用 JSONField 替代"""
    def __init__(self, dimensions=1536, null=True, blank=True, verbose_name=""):
        self.dimensions = dimensions
        self.null = null
        self.blank = blank
        self.verbose_name = verbose_name

    def deconstruct(self):
        from django.db import models
        name, path, args, kwargs = models.JSONField(
            null=self.null, blank=self.blank, default=list
        ).deconstruct()
        return name, 'django.db.models.JSONField', args, kwargs

    def contribute_to_class(self, cls, name, **kwargs):
        from django.db import models
        field = models.JSONField(
            null=self.null, blank=self.blank, default=list,
            verbose_name=self.verbose_name
        )
        field.contribute_to_class(cls, name, **kwargs)

class MockCosineDistance:
    def __init__(self, *args, **kwargs):
        pass

    def resolve_expression(self, *args, **kwargs):
        return None

pgvector_django_vector_mock.VectorField = MockVectorField
pgvector_django_mock.vector = pgvector_django_vector_mock
pgvector_django_mock.VectorField = MockVectorField
pgvector_django_mock.CosineDistance = MockCosineDistance
pgvector_mock.django = pgvector_django_mock

sys.modules['pgvector'] = pgvector_mock
sys.modules['pgvector.django'] = pgvector_django_mock
sys.modules['pgvector.django.vector'] = pgvector_django_vector_mock

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

