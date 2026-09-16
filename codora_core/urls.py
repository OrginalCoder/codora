from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.shortcuts import render


def custom_404(request, exception):
    return render(request, 'errors/404.html', status=404)


def custom_403(request, exception):
    return render(request, 'errors/403.html', status=403)


def custom_500(request):
    return render(request, 'errors/500.html', status=500)


handler404 = custom_404
handler403 = custom_403
handler500 = custom_500

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.accounts.urls')),
    path('', include('apps.marketplace.urls')),
    path('', include('apps.orders.urls')),
    path('', include('apps.dashboard.urls')),
    path('', include('apps.notifications.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

