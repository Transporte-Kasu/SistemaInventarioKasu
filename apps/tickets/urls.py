from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('', views.TicketListView.as_view(), name='lista'),
    path('<int:pk>/', views.TicketDetailView.as_view(), name='detalle'),
    path('<int:pk>/asignar/', views.ticket_asignar, name='asignar'),
    path('<int:pk>/cerrar/', views.ticket_cerrar, name='cerrar'),
]
