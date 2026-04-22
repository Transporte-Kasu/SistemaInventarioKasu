from django.contrib import admin
from .models import Equipo


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tipo', 'marca', 'modelo', 'numero_serie', 'estado', 'fecha_registro']
    list_filter = ['estado', 'tipo', 'marca']
    search_fields = ['usuario', 'numero_serie', 'marca', 'modelo', 'mac_address']
    readonly_fields = ['uuid', 'qr_code', 'fecha_registro']
    fieldsets = (
        ('Identificación', {
            'fields': ('uuid', 'usuario', 'tipo', 'marca', 'modelo', 'numero_serie', 'estado')
        }),
        ('Detalles técnicos', {
            'fields': ('mac_address', 'telefono_interno', 'monitores_cantidad', 'monitores_marca', 'ubicacion')
        }),
        ('Archivos', {
            'fields': ('foto', 'qr_code')
        }),
        ('Fechas y notas', {
            'fields': ('fecha_adquisicion', 'fecha_registro', 'fecha_baja', 'notas')
        }),
    )
