from rest_framework.permissions import BasePermission
import logging

security_logger = logging.getLogger("security")

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        is_admin = request.session.get('role') == 'admin'
        if not is_admin:
            security_logger.warning(
                "Admin permission denied ip=%s path=%s role=%s",
                request.META.get("REMOTE_ADDR", "unknown"),
                getattr(request, "path", "unknown"),
                request.session.get("role"),
            )
        return is_admin
