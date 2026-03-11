from django.urls import path
from .views import (
    ColumnListCreateView, ColumnDetailView, ReorderColumnsView,
    TaskListCreateView, TaskDetailView, MoveTaskView,
    CommentListCreateView, ActivityLogView,
    ChecklistItemListCreateView, ChecklistItemDetailView,
    TaskAssigneeView,
)

urlpatterns = [
    path('projects/<uuid:project_id>/columns/', ColumnListCreateView.as_view()),
    path('columns/<uuid:pk>/', ColumnDetailView.as_view()),
    path('projects/<uuid:project_id>/columns/reorder/', ReorderColumnsView.as_view()),
    path('columns/<uuid:column_id>/tasks/', TaskListCreateView.as_view()),
    path('tasks/<uuid:pk>/', TaskDetailView.as_view()),
    path('tasks/<uuid:pk>/move/', MoveTaskView.as_view()),
    path('tasks/<uuid:pk>/assignees/', TaskAssigneeView.as_view()),
    path('tasks/<uuid:pk>/assignees/<uuid:user_id>/', TaskAssigneeView.as_view()),
    path('tasks/<uuid:task_id>/comments/', CommentListCreateView.as_view()),
    path('tasks/<uuid:task_id>/checklist/', ChecklistItemListCreateView.as_view()),
    path('tasks/<uuid:task_id>/checklist/<uuid:item_id>/', ChecklistItemDetailView.as_view()),
    path('projects/<uuid:project_id>/activity/', ActivityLogView.as_view()),
]