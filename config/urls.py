from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.inventario.urls')),
    path('mantenimiento/', include('apps.mantenimiento.urls')),
    path('tickets/', include('apps.tickets.urls')),
    path('bajas/', include('apps.bajas.urls')),
    path('reportes/', include('apps.reportes.urls')),
    path('usuarios/', include('apps.usuarios.urls')),
    path('q/', include('apps.tickets.urls_qr')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
