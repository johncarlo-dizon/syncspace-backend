from django.urls import path
from .views import (
    WorkspaceListCreateView,
    WorkspaceDetailView,
    WorkspaceMemberListView,
    InviteMemberView,
    RemoveMemberView,
    UpdateMemberRoleView,
    AcceptInviteView,
)

urlpatterns = [
    path('', WorkspaceListCreateView.as_view()),
    path('<uuid:pk>/', WorkspaceDetailView.as_view()),
    path('<uuid:pk>/members/', WorkspaceMemberListView.as_view()),
    path('<uuid:pk>/members/<int:user_id>/', RemoveMemberView.as_view()),
    path('<uuid:pk>/members/<int:user_id>/role/', UpdateMemberRoleView.as_view()),
    path('<uuid:pk>/invite/', InviteMemberView.as_view()),
    path('<uuid:token>/accept-invite/', AcceptInviteView.as_view()),
]