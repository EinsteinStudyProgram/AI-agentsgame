from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # Gateway 统一入口（REST API）
    path("", include("backend.apps.gateway.urls")),

    # 各模块独立入口（兼容旧路由）
    path("api/v1/agents/", include("backend.apps.agents.urls")),
    path("api/v1/memory/", include("backend.apps.memory.urls")),
    path("api/v1/world/", include("backend.apps.world.urls")),
]

