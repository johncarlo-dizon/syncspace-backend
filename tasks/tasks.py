from celery import shared_task
from django.utils import timezone
from datetime import timedelta


@shared_task(bind=True, max_retries=3)
def send_due_date_reminders(self):
    """
    Runs every hour.
    Finds tasks due within the next 24 hours
    and sends reminder notifications to assignees.
    """
    try:
        from .models import Task
        from notifications.utils import send_notification

        now = timezone.now()
        upcoming = now + timedelta(hours=24)

        # Find tasks due soon that haven't been reminded yet
        tasks_due_soon = Task.objects.filter(
            due_date__gte=now,
            due_date__lte=upcoming,
        ).prefetch_related('assignees')

        reminded_count = 0
        for task in tasks_due_soon:
            for assignee in task.assignees.all():
                send_notification(
                    recipient=assignee,
                    sender=None,
                    notification_type='task_due',
                    title='Task due soon',
                    message=f'"{task.title}" is due in less than 24 hours.',
                    task=task,
                    project=task.column.project,
                )
                reminded_count += 1

        return f'Sent {reminded_count} due date reminders.'

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)