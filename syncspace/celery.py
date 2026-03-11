import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'syncspace.settings')

app = Celery('syncspace')

# Explicitly set Redis as broker here directly
app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.result_backend = 'redis://localhost:6379/0'

# Load rest of config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'check-due-date-reminders': {
        'task': 'tasks.tasks.send_due_date_reminders',
        'schedule': crontab(minute=0),
    },
    'weekly-digest': {
        'task': 'notifications.tasks.send_weekly_digest',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),
    },
    'clean-expired-invitations': {
        'task': 'workspaces.tasks.clean_expired_invitations',
        'schedule': crontab(hour=0, minute=0),
    },
}