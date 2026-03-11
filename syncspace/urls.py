from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/workspaces/', include('workspaces.urls')),
    path('api/workspaces/<uuid:workspace_id>/projects/', include('projects.urls')),  # 👈
    path('api/', include('tasks.urls')),  
    path('api/notifications/', include('notifications.urls')), 
    path('api/projects/', include('projects.urls')), 
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)