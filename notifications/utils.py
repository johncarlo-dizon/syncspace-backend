from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification


def send_notification(recipient, sender, notification_type, title, message, task=None, project=None):
    """
    Creates a notification in the DB and pushes it
    to the recipient's WebSocket connection in real-time.
    """
    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=title,
        message=message,
        task=task,
        project=project,
    )

    # Push to WebSocket if user is connected
    channel_layer = get_channel_layer()
    if channel_layer and project:
        group_name = f'board_{project.id}'
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'notification_event',
                'data': {
                    'id': str(notification.id),
                    'notification_type': notification_type,
                    'title': title,
                    'message': message,
                    'created_at': str(notification.created_at),
                }
            }
        )

    return notification