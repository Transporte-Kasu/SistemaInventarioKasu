from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.views.generic import ListView
from .models import ReporteInventario


class ReporteListView(LoginRequiredMixin, ListView):
    model = ReporteInventario
    template_name = 'reportes/lista.html'
    context_object_name = 'reportes'
    paginate_by = 20

    def get_queryset(self):
        return ReporteInventario.objects.select_related('generado_por').order_by('-fecha_generacion')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tipos'] = ReporteInventario.Tipo.choices
        return ctx


@login_required
def generar_reporte(request, tipo):
    from .service import (
        generar_inventario_completo,
        generar_alerta_mantenimiento,
        generar_resumen_tickets,
    )
    generadores = {
        'completo': generar_inventario_completo,
        'mantenimiento': generar_alerta_mantenimiento,
        'tickets': generar_resumen_tickets,
    }
    fn = generadores.get(tipo)
    if not fn:
        raise Http404

    try:
        reporte = fn(usuario=request.user)
        if reporte:
            messages.success(
                request,
                f'Reporte "{reporte.get_tipo_display()}" generado y enviado por correo.'
            )
        else:
            messages.info(request, 'No hay datos que reportar en este momento.')
    except Exception as exc:
        messages.error(request, f'Error generando reporte: {exc}')

    return redirect('reportes:lista')


@login_required
def descargar_reporte(request, pk):
    try:
        reporte = ReporteInventario.objects.get(pk=pk)
    except ReporteInventario.DoesNotExist:
        raise Http404
    if not reporte.archivo_pdf:
        raise Http404
    response = HttpResponse(reporte.archivo_pdf.read(), content_type='application/pdf')
    nombre = reporte.archivo_pdf.name.split('/')[-1]
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return response
