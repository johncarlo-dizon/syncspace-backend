from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Column, Task, ChecklistItem, TaskAttachment, Comment, ActivityLog, Label
from users.serializers import UserSerializer

User = get_user_model()


class LabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['id', 'name', 'color']


class ChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChecklistItem
        fields = ['id', 'text', 'is_done', 'order']


class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)

    class Meta:
        model = TaskAttachment
        fields = ['id', 'file', 'filename', 'uploaded_by', 'uploaded_at']


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'author', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class TaskSerializer(serializers.ModelSerializer):
    assignees = UserSerializer(many=True, read_only=True)
    assignee_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True,
        queryset=User.objects.all(),
        source='assignees', required=False
    )
    labels = LabelSerializer(many=True, read_only=True)
    label_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True,
        queryset=Label.objects.all(),
        source='labels', required=False
    )
    checklist = ChecklistItemSerializer(many=True, read_only=True)
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)
    checklist_progress = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id', 'column', 'title', 'description', 'order',
            'priority', 'assignees', 'assignee_ids',
            'labels', 'label_ids', 'due_date',
            'checklist', 'checklist_progress',
            'attachments', 'comments',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'column', 'created_by', 'created_at', 'updated_at']  # ← add 'column' here

    def get_checklist_progress(self, obj):
        total = obj.checklist.count()
        if total == 0:
            return None
        done = obj.checklist.filter(is_done=True).count()
        return {'done': done, 'total': total}

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ColumnSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = Column
        fields = ['id', 'project', 'name', 'order', 'tasks', 'task_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_task_count(self, obj):
        return obj.tasks.count()


class ActivityLogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'action', 'task', 'created_at']