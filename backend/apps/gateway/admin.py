from django.contrib import admin
from django.contrib import messages

class WebSocketConnectionAdmin(admin.ModelAdmin):
    @admin.action(description="???? WebSocket ???")
    def show_connections(self, request):
        try:
            from django.core.management import call_command
            from io import StringIO
            out = StringIO()
            call_command("show_ws_connections", stdout=out)
            self.message_user(request, out.getvalue(), level=messages.INFO)
        except Exception as e:
            self.message_user(request, f"????????: {e}", level=messages.ERROR)

    actions = [show_connections]
    has_add_permission = lambda s, r: False
    has_change_permission = lambda s, r: True
    has_delete_permission = lambda s, r: False
