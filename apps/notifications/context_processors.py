from .models import Notification


def notifications_context(request):
    unread_count = 0
    if request.user.is_authenticated:
        try:
            unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        except Exception:
            pass

    return {
        'unread_notifications_count': unread_count,
    }
