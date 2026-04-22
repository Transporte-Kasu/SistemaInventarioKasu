from django.urls import path
from . import views

app_name = 'mantenimiento'

urlpatterns = [
    path('', views.MantenimientoListView.as_view(), name='lista'),
    path('alertas/', views.AlertasMantenimientoView.as_view(), name='alertas'),
    path('registrar/<uuid:equipo_uuid>/', views.registrar_qr, name='registrar_qr'),
]
