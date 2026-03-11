from django.urls import path
from .views import (
    ProjectListCreateView,
    ProjectDetailView,
    ProjectMemberListView,
    ProjectInviteMemberView,
    ProjectRemoveMemberView,
)

urlpatterns = [
    path('', ProjectListCreateView.as_view()),
    path('<uuid:pk>/', ProjectDetailView.as_view()),
    path('<uuid:project_id>/members/', ProjectMemberListView.as_view()),
    path('<uuid:project_id>/members/invite/', ProjectInviteMemberView.as_view()),
    path('<uuid:project_id>/members/<uuid:user_id>/', ProjectRemoveMemberView.as_view()),
]