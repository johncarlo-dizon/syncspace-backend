from django.urls import path
from .views import (
    WorkspaceListCreateView,
    WorkspaceDetailView,
    WorkspaceMemberListView,
    InviteMemberView,
    GenerateInviteLinkView,
    RemoveMemberView,
    UpdateMemberRoleView,
    AcceptInviteView,
    GetInviteInfoView,
)

urlpatterns = [
    path('', WorkspaceListCreateView.as_view()),
    path('<uuid:pk>/', WorkspaceDetailView.as_view()),
    path('<uuid:pk>/members/', WorkspaceMemberListView.as_view()),
    path('<uuid:pk>/members/<int:user_id>/', RemoveMemberView.as_view()),
    path('<uuid:pk>/members/<int:user_id>/role/', UpdateMemberRoleView.as_view()),
    path('<uuid:pk>/invite/', InviteMemberView.as_view()),
    path('<uuid:pk>/invite-link/', GenerateInviteLinkView.as_view()),
    path('invite/<uuid:token>/info/', GetInviteInfoView.as_view()),
    path('invite/<uuid:token>/accept/', AcceptInviteView.as_view()),
]