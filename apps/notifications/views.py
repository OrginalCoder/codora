from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Notification


@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(recipient=request.user)
    unread = notifications.filter(is_read=False)
    unread.update(is_read=True)

    return render(request, 'notifications/notifications_list.html', {
        'notifications': notifications
    })


@login_required
def mark_all_read(request):
    if request.method == 'POST':
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect('notifications')
