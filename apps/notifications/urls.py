from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/mark-read/', views.mark_all_read, name='mark_all_notifications_read'),
]
