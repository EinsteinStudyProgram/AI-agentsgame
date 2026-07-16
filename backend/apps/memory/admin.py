from django.contrib import admin
from django.utils.html import format_html
from .models import MemoryEntry, MemoryStream, MemoryStreamOrder


@admin.register(MemoryEntry)
class MemoryEntryAdmin(admin.ModelAdmin):
    list_display = ["summary_short", "agent", "colored_type",
                   "importance", "recency_score", "status", "tag_badges", "created_at"]
    list_filter = ["memory_type", "status", "importance", "agent"]
    search_fields = ["content", "summary", "agent__name"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at", "accessed_at"]
    list_per_page = 30

    @admin.display(description="??")
    def summary_short(self, obj):
        return obj.summary[:40] + "..." if len(obj.summary) > 40 else obj.summary

    @admin.display(description="??")
    def colored_type(self, obj):
        cm = dict(obj.MEMORY_TYPES)
        colors = {"episodic":"#3498DB","semantic":"#2ECC71",
                  "reflective":"#9B59B6","procedural":"#E67E22"}
        c = colors.get(obj.memory_type, "#666")
        return format_html(f'<span style="color:{c};font-weight:bold;">{cm.get(obj.memory_type, obj.memory_type)}</span>')

    @admin.display(description="??")
    def tag_badges(self, obj):
        if not obj.tags:
            return ""
        badges = "".join(f'<span style="background:#eee;padding:1px 6px;margin:1px;border-radius:8px;font-size:10px;">{t}</span>' for t in obj.tags[:5])
        return format_html(badges) if badges else ""

    @admin.display(description="???")
    def importance(self, obj):
        return obj.importance

    @admin.display(description="??")
    def recency_score(self, obj):
        return obj.recency_score

    @admin.action(description="????")
    def archive_memories(self, request, qs):
        u = qs.update(status="archived")
        self.message_user(request, f"??? {u} ?")

    @admin.action(description="????? (+0.2)")
    def boost_importance(self, request, qs):
        for m in qs:
            MemoryEntry.objects.filter(id=m.id).update(importance=min(1.0, m.importance + 0.2))
        self.message_user(request, f"??? {qs.count()} ?")

    actions = [archive_memories, boost_importance]


@admin.register(MemoryStream)
class MemoryStreamAdmin(admin.ModelAdmin):
    list_display = ["name", "agent", "stream_type", "created_at"]
    list_filter = ["stream_type"]
    search_fields = ["name", "agent__name"]


@admin.register(MemoryStreamOrder)
class MemoryStreamOrderAdmin(admin.ModelAdmin):
    list_display = ["stream", "memory", "order"]
    list_filter = ["stream__agent"]
