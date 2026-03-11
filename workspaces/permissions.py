from rest_framework.permissions import BasePermission
from .models import WorkspaceMember


class IsWorkspaceOwner(BasePermission):
    """Only workspace owner can perform this action."""
    def has_object_permission(self, request, view, obj):
        return obj.members.filter(
            user=request.user,
            role=WorkspaceMember.Role.OWNER
        ).exists()


class IsWorkspaceAdminOrOwner(BasePermission):
    """Only admins and owners can perform this action."""
    def has_object_permission(self, request, view, obj):
        return obj.members.filter(
            user=request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN]
        ).exists()


class IsWorkspaceMember(BasePermission):
    """Any workspace member can perform this action."""
    def has_object_permission(self, request, view, obj):
        return obj.members.filter(user=request.user).exists()