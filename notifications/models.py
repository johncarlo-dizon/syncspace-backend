import uuid
from django.db import models
from django.conf import settings
from tasks.models import Task
from projects.models import Project


class Notification(models.Model):
    class Type(models.TextChoices):
        TASK_ASSIGNED   = 'task_assigned',   'Task Assigned'
        TASK_DUE        = 'task_due',        'Task Due Soon'
        COMMENT_ADDED   = 'comment_added',   'Comment Added'
        MEMBER_JOINED   = 'member_joined',   'Member Joined'
        MEMBER_INVITED  = 'member_invited',  'Member Invited'
        PROJECT_CREATED = 'project_created', 'Project Created'
        TASK_MOVED      = 'task_moved',      'Task Moved'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sent_notifications'
    )
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    task = models.ForeignKey(
        Task, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.notification_type} → {self.recipient.email}'