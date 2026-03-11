from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


@shared_task(bind=True, max_retries=3)
def send_weekly_digest(self):
    """
    Runs every Monday at 8AM.
    Sends each user a summary of their assigned tasks
    and unread notifications from the past week.
    """
    try:
        from django.contrib.auth import get_user_model
        from tasks.models import Task
        from notifications.models import Notification

        User = get_user_model()
        one_week_ago = timezone.now() - timedelta(days=7)
        sent_count = 0

        for user in User.objects.filter(is_active=True):
            # Get tasks assigned to user due this week
            upcoming_tasks = Task.objects.filter(
                assignees=user,
                due_date__gte=timezone.now(),
                due_date__lte=timezone.now() + timedelta(days=7),
            )

            # Get unread notifications from last week
            unread_count = Notification.objects.filter(
                recipient=user,
                is_read=False,
                created_at__gte=one_week_ago,
            ).count()

            if not upcoming_tasks.exists() and unread_count == 0:
                continue

            # Build email body
            task_lines = '\n'.join(
                f'  - {t.title} (due {t.due_date.strftime("%b %d")})' for t in upcoming_tasks
            ) or '  No upcoming tasks.'

            body = f"""
Hi {user.username},

Here's your weekly SyncSpace digest:

📋 UPCOMING TASKS THIS WEEK:
{task_lines}

🔔 UNREAD NOTIFICATIONS: {unread_count}

Log in to SyncSpace to stay on top of your work.

— The SyncSpace Team
            """.strip()

            send_mail(
                subject='Your Weekly SyncSpace Digest',
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
            sent_count += 1

        return f'Weekly digest sent to {sent_count} users.'

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_invitation_email(self, invitation_id):
    """
    Sends an email invitation to join a workspace.
    Called immediately when an invite is created.
    """
    try:
        from workspaces.models import WorkspaceInvitation
        invitation = WorkspaceInvitation.objects.get(id=invitation_id)

        accept_url = f'http://localhost:3000/invite/{invitation.id}'

        body = f"""
You've been invited to join "{invitation.workspace.name}" on SyncSpace!

Invited by: {invitation.invited_by.username}
Your role: {invitation.role.capitalize()}

Click the link below to accept your invitation:
{accept_url}

This invitation expires in 7 days.

— The SyncSpace Team
        """.strip()

        send_mail(
            subject=f'You\'re invited to join {invitation.workspace.name} on SyncSpace',
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invitation.email],
            fail_silently=False,
        )

        return f'Invitation email sent to {invitation.email}'

    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)