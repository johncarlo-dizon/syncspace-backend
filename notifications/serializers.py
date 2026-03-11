from rest_framework import serializers
from .models import Notification
from users.serializers import UserSerializer


class NotificationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    type = serializers.CharField(source='notification_type', read_only=True)  # ← add this
    class Meta:
        model = Notification
        fields = ['id', 'type', 'title', 'message', 'is_read', 'sender', 'created_at']
        read_only_fields = ['id', 'type', 'title', 'message', 'sender', 'created_at']