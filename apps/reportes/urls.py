from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.ReporteListView.as_view(), name='lista'),
    path('generar/<str:tipo>/', views.generar_reporte, name='generar'),
    path('<int:pk>/descargar/', views.descargar_reporte, name='descargar'),
]
