from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/agents/", include("backend.apps.agents.urls")),
    path("api/v1/memory/", include("backend.apps.memory.urls")),
    path("api/v1/world/", include("backend.apps.world.urls")),
]
