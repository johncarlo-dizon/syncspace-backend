from celery import shared_task
from django.utils import timezone


@shared_task
def clean_expired_invitations():
    """
    Runs every night at midnight.
    Marks pending invitations that have passed
    their expiry date as expired.
    """
    from .models import WorkspaceInvitation

    expired = WorkspaceInvitation.objects.filter(
        status='pending',
        expires_at__lt=timezone.now()
    )
    count = expired.count()
    expired.update(status='expired')

    return f'Marked {count} invitations as expired.'