from django.urls import path
from . import views

app_name = 'bajas'

urlpatterns = [
    path('', views.BajaListView.as_view(), name='lista'),
    path('iniciar/<int:equipo_pk>/', views.iniciar_baja, name='iniciar'),
    path('<int:pk>/', views.BajaDetailView.as_view(), name='detalle'),
    path('<int:pk>/fase2/', views.avanzar_fase2, name='fase2'),
    path('<int:pk>/fase3/', views.avanzar_fase3, name='fase3'),
    path('<int:pk>/fase4/', views.avanzar_fase4, name='fase4'),
    path('<int:pk>/acta/', views.descargar_acta, name='acta'),
]
