from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import Equipo


def imprimir_etiquetas_qr(modeladmin, request, queryset):
    ids = ','.join(str(e.pk) for e in queryset)
    url = reverse('inventario:etiquetas_qr') + f'?ids={ids}'
    return HttpResponseRedirect(url)

imprimir_etiquetas_qr.short_description = 'Imprimir etiquetas QR seleccionadas'


def regenerar_qr_seleccionados(modeladmin, request, queryset):
    generados = 0
    errores = 0
    for equipo in queryset:
        try:
            equipo.qr_code = None          # fuerza regeneración en save()
            equipo._generar_qr()
            equipo.save()
            generados += 1
        except Exception:
            errores += 1
    if generados:
        messages.success(request, f'QR generado correctamente para {generados} equipo(s).')
    if errores:
        messages.error(request, f'{errores} equipo(s) no pudieron generar QR.')

regenerar_qr_seleccionados.short_description = 'Regenerar QR de equipos seleccionados'


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tipo', 'marca', 'modelo', 'numero_serie', 'tiene_qr', 'estado', 'fecha_registro']
    list_filter = ['estado', 'tipo', 'marca']
    search_fields = ['usuario', 'numero_serie', 'marca', 'modelo', 'mac_address']
    readonly_fields = ['uuid', 'qr_code', 'fecha_registro']
    actions = [imprimir_etiquetas_qr, regenerar_qr_seleccionados]
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

    @admin.display(boolean=True, description='QR')
    def tiene_qr(self, obj):
        return bool(obj.qr_code)
