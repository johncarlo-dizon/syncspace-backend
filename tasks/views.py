from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Column, Task, ChecklistItem, Comment, ActivityLog
from .serializers import (
    ColumnSerializer, TaskSerializer,
    CommentSerializer, ActivityLogSerializer, ChecklistItemSerializer
)
from projects.models import Project


def log_activity(project, user, action, task=None):
    ActivityLog.objects.create(
        project=project, user=user, action=action, task=task
    )


def broadcast_board_event(project_id, event_type, payload):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'board_{project_id}',
            {
                'type': event_type,
                **payload,
            }
        )
    except Exception as e:
        print(f'[WS Broadcast Error] {e}')


class ColumnListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ColumnSerializer

    def get_queryset(self):
        return Column.objects.filter(
            project__id=self.kwargs['project_id'],
            project__workspace__members__user=self.request.user
        ).prefetch_related('tasks').order_by('order')

    def perform_create(self, serializer):
        project = get_object_or_404(Project, id=self.kwargs['project_id'])
        column = serializer.save(project=project)
        broadcast_board_event(
            project.id,
            'column_created',
            {'column': ColumnSerializer(column).data}
        )


class ColumnDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ColumnSerializer

    def get_queryset(self):
        return Column.objects.filter(
            project__workspace__members__user=self.request.user
        )

    def perform_update(self, serializer):
        column = serializer.save()
        broadcast_board_event(
            column.project.id,
            'column_updated',
            {'column': ColumnSerializer(column).data}
        )

    def perform_destroy(self, instance):
        project_id = instance.project.id
        column_id = str(instance.id)
        instance.delete()
        broadcast_board_event(
            project_id,
            'column_deleted',
            {'column_id': column_id}
        )


class ReorderColumnsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id):
        columns_data = request.data.get('columns', [])
        for item in columns_data:
            Column.objects.filter(id=item['id']).update(order=item['order'])
        return Response({'message': 'Columns reordered.'})


class TaskListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(
            column__id=self.kwargs['column_id'],
            column__project__workspace__members__user=self.request.user
        ).order_by('order')

    def perform_create(self, serializer):
        column = get_object_or_404(Column, id=self.kwargs['column_id'])
        task = serializer.save(column=column, created_by=self.request.user)
        log_activity(column.project, self.request.user, f'Created task "{task.title}"', task)

        broadcast_board_event(
            column.project.id,
            'task_created',
            {'task': TaskSerializer(task, context={'request': self.request}).data}
        )

        # Notify assignees
        from notifications.utils import send_notification
        for assignee in task.assignees.all():
            if assignee != self.request.user:
                send_notification(
                    recipient=assignee,
                    sender=self.request.user,
                    notification_type='task_assigned',
                    title='You were assigned a task',
                    message=f'{self.request.user.username} assigned you "{task.title}"',
                    task=task,
                    project=column.project,
                )


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(
            column__project__workspace__members__user=self.request.user
        )

    def perform_update(self, serializer):
        task = serializer.save()
        log_activity(task.column.project, self.request.user, f'Updated task "{task.title}"', task)
        broadcast_board_event(
            task.column.project.id,
            'task_updated',
            {'task': TaskSerializer(task, context={'request': self.request}).data}
        )

    def perform_destroy(self, instance):
        project_id = instance.column.project.id
        task_id = str(instance.id)
        log_activity(instance.column.project, self.request.user, f'Deleted task "{instance.title}"')
        instance.delete()
        broadcast_board_event(
            project_id,
            'task_deleted',
            {'task_id': task_id}
        )


class MoveTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        task = get_object_or_404(Task, id=pk)
        new_column = get_object_or_404(Column, id=request.data.get('column_id'))
        old_column_name = task.column.name
        task.column = new_column
        task.order = request.data.get('order', 0)
        task.save()
        log_activity(
            new_column.project,
            request.user,
            f'Moved task "{task.title}" from {old_column_name} to {new_column.name}',
            task
        )
        broadcast_board_event(
            new_column.project.id,
            'task_moved',
            {
                'task_id': str(task.id),
                'column_id': str(new_column.id),
                'order': task.order,
            }
        )
        return Response(TaskSerializer(task, context={'request': request}).data)


class CommentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(task__id=self.kwargs['task_id'])

    def perform_create(self, serializer):
        task = get_object_or_404(Task, id=self.kwargs['task_id'])
        comment = serializer.save(task=task, author=self.request.user)
        log_activity(task.column.project, self.request.user, f'Commented on "{task.title}"', task)


class ActivityLogView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ActivityLogSerializer

    def get_queryset(self):
        return ActivityLog.objects.filter(
            project__id=self.kwargs['project_id'],
            project__workspace__members__user=self.request.user
        ).order_by('-created_at')
    
class ChecklistItemListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChecklistItemSerializer

    def get_queryset(self):
        return ChecklistItem.objects.filter(
            task__id=self.kwargs['task_id']
        ).order_by('order')

    def perform_create(self, serializer):
        task = get_object_or_404(Task, id=self.kwargs['task_id'])
        last = ChecklistItem.objects.filter(task=task).count()
        serializer.save(task=task, order=last)


class ChecklistItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChecklistItemSerializer
    lookup_url_kwarg = 'item_id'

    def get_queryset(self):
        return ChecklistItem.objects.filter(task__id=self.kwargs['task_id'])

class TaskAssigneeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        task = get_object_or_404(Task, id=pk)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_id = request.data.get('user_id')
        user = get_object_or_404(User, id=user_id)
        task.assignees.add(user)
        task.save()

        # Send notification
        if user != request.user:
            from notifications.utils import send_notification
            send_notification(
                recipient=user,
                sender=request.user,
                notification_type='task_assigned',
                title='You were assigned a task',
                message=f'{request.user.username} assigned you "{task.title}"',
                task=task,
                project=task.column.project,
            )

        # Broadcast update
        broadcast_board_event(
            task.column.project.id,
            'task_updated',
            {'task': TaskSerializer(task, context={'request': request}).data}
        )

        return Response(TaskSerializer(task, context={'request': request}).data)

    def delete(self, request, pk, user_id):
        task = get_object_or_404(Task, id=pk)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = get_object_or_404(User, id=user_id)
        task.assignees.remove(user)

        broadcast_board_event(
            task.column.project.id,
            'task_updated',
            {'task': TaskSerializer(task, context={'request': request}).data}
        )

        return Response(TaskSerializer(task, context={'request': request}).data)