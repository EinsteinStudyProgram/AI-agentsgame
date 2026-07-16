from django.contrib import admin
from django.utils.html import format_html
from .models import World, City, District, Scene, AgentPosition, WorldEvent


@admin.register(World)
class WorldAdmin(admin.ModelAdmin):
    list_display = ["name", "dimensions", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    list_editable = ["is_active"]
    readonly_fields = ["id", "created_at", "updated_at"]

    @admin.display(description="??")
    def dimensions(self, obj):
        return f"{obj.width} x {obj.height}"


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "world", "pos_x", "pos_y"]
    list_filter = ["world"]
    search_fields = ["name", "world__name"]


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ["name", "colored_type", "city"]
    list_filter = ["district_type", "city__world"]
    search_fields = ["name", "city__name"]

    @admin.display(description="??")
    def colored_type(self, obj):
        cm = dict(obj.DISTRICT_TYPES)
        colors = {"residential":"#2ECC71","commercial":"#3498DB","entertainment":"#E67E22",
                  "park":"#1ABC9C","education":"#9B59B6","industrial":"#E74C3C",
                  "administrative":"#2C3E50","transportation":"#F39C12"}
        c = colors.get(obj.district_type, "#666")
        return format_html(f'<span style="color:{c};font-weight:bold;">{cm.get(obj.district_type, obj.district_type)}</span>')


@admin.register(Scene)
class SceneAdmin(admin.ModelAdmin):
    list_display = ["name", "district_path", "max_occupancy", "current_occupancy", "function_tags"]
    list_filter = ["district__district_type"]
    search_fields = ["name", "district__name"]

    @admin.display(description="??")
    def district_path(self, obj):
        return f"{obj.district.city.world.name} > {obj.district.city.name} > {obj.district.name}"

    @admin.action(description="?????0")
    def reset_occupancy(self, request, qs):
        u = qs.update(current_occupancy=0)
        self.message_user(request, f"??? {u} ???")
    actions = [reset_occupancy]


@admin.register(AgentPosition)
class AgentPositionAdmin(admin.ModelAdmin):
    list_display = ["agent", "scene", "pos_x", "pos_y", "heading"]
    search_fields = ["agent__name", "scene__name"]


@admin.register(WorldEvent)
class WorldEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "scene", "radius", "created_at"]
    list_filter = ["event_type"]
    search_fields = ["event_type", "description"]
