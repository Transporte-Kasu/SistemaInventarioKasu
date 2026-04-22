from django.urls import path
from apps.tickets.views import ticket_qr

urlpatterns = [
    path('<uuid:equipo_uuid>/', ticket_qr, name='ticket_qr'),
]
