from django.urls import path
from .views import NotificationListView, NotificationDetailView, MarkAllReadView

urlpatterns = [
    path('', NotificationListView.as_view()),
    path('<uuid:pk>/', NotificationDetailView.as_view()),
    path('mark-all-read/', MarkAllReadView.as_view()),
]