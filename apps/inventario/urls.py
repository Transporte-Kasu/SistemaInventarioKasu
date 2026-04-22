from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('equipos/', views.EquipoListView.as_view(), name='lista'),
    path('equipos/nuevo/', views.EquipoCreateView.as_view(), name='crear'),
    path('equipos/<int:pk>/', views.EquipoDetailView.as_view(), name='detalle'),
    path('equipos/<int:pk>/editar/', views.EquipoUpdateView.as_view(), name='editar'),
    path('equipos/<int:pk>/qr/', views.qr_download, name='qr_download'),
]
