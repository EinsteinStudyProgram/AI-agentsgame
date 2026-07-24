"""
记忆管理后台配置
"""
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

    @admin.display(description="摘要")
    def summary_short(self, obj):
        return obj.summary[:40] + "..." if len(obj.summary) > 40 else obj.summary

    @admin.display(description="类型")
    def colored_type(self, obj):
        cm = dict(obj.MEMORY_TYPES)
        colors = {"episodic": "#3498DB", "semantic": "#2ECC71",
                  "reflective": "#9B59B6", "procedural": "#E67E22"}
        c = colors.get(obj.memory_type, "#666")
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>',
            c, cm.get(obj.memory_type, obj.memory_type)
        )

    @admin.display(description="标签")
    def tag_badges(self, obj):
        if not obj.tags:
            return ""
        badges = "".join(
            '<span style="background:#eee;padding:1px 6px;margin:1px;'
            'border-radius:8px;font-size:10px;">{}</span>'.format(t)
            for t in obj.tags[:5]
        )
        return format_html(badges)

    def archive_memories(self, request, qs):
        u = qs.update(status="archived")
        self.message_user(request, f"已归档 {u} 条记忆")
    archive_memories.short_description = "归档选中的记忆"  # type: ignore[attr-defined]

    def boost_importance(self, request, qs):
        for m in qs:
            MemoryEntry.objects.filter(id=m.id).update(importance=min(1.0, m.importance + 0.2))
        self.message_user(request, f"已提升 {qs.count()} 条记忆的重要性")
    boost_importance.short_description = "提升重要性 (+0.2)"  # type: ignore[attr-defined]

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
