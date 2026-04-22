from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView
from django.utils import timezone

from apps.inventario.models import Equipo
from .models import BajaEquipo
from .forms import BajaSolicitudForm, BajaEjecucionForm, BajaDestruccionForm, BajaCierreForm


class BajaListView(LoginRequiredMixin, ListView):
    model = BajaEquipo
    template_name = 'bajas/lista.html'
    context_object_name = 'bajas'
    paginate_by = 20

    def get_queryset(self):
        return BajaEquipo.objects.select_related('equipo', 'solicitante').order_by('-fecha_solicitud')


class BajaDetailView(LoginRequiredMixin, DetailView):
    model = BajaEquipo
    template_name = 'bajas/detalle.html'
    context_object_name = 'baja'


@login_required
def iniciar_baja(request, equipo_pk):
    equipo = get_object_or_404(Equipo, pk=equipo_pk)
    if hasattr(equipo, 'baja'):
        messages.warning(request, 'Este equipo ya tiene un proceso de baja en curso.')
        return redirect('bajas:detalle', pk=equipo.baja.pk)

    if request.method == 'POST':
        form = BajaSolicitudForm(request.POST)
        if form.is_valid():
            baja = form.save(commit=False)
            baja.equipo = equipo
            baja.solicitante = request.user
            baja.fase_actual = BajaEquipo.Fase.SOLICITUD
            baja.save()
            equipo.estado = Equipo.Estado.PENDIENTE_BAJA
            equipo.save()
            messages.success(request, f'Proceso de baja iniciado para {equipo}. Fase 1 completada.')
            return redirect('bajas:detalle', pk=baja.pk)
    else:
        form = BajaSolicitudForm()

    return render(request, 'bajas/fase1_solicitud.html', {'equipo': equipo, 'form': form})


@login_required
def avanzar_fase2(request, pk):
    baja = get_object_or_404(BajaEquipo, pk=pk)
    if baja.fase_actual != BajaEquipo.Fase.SOLICITUD:
        messages.error(request, 'Esta baja no está en Fase 1.')
        return redirect('bajas:detalle', pk=pk)

    if request.method == 'POST':
        form = BajaEjecucionForm(request.POST, request.FILES, instance=baja)
        if form.is_valid():
            baja = form.save(commit=False)
            baja.fase_actual = BajaEquipo.Fase.EJECUCION
            baja.fecha_ejecucion = timezone.now()
            baja.autorizado_por = request.user
            baja.save()
            messages.success(request, 'Fase 2 completada — ejecución de formateo registrada.')
            return redirect('bajas:detalle', pk=pk)
    else:
        form = BajaEjecucionForm(instance=baja)

    return render(request, 'bajas/fase2_ejecucion.html', {'baja': baja, 'form': form})


@login_required
def avanzar_fase3(request, pk):
    baja = get_object_or_404(BajaEquipo, pk=pk)
    if baja.fase_actual != BajaEquipo.Fase.EJECUCION:
        messages.error(request, 'Esta baja no está en Fase 2.')
        return redirect('bajas:detalle', pk=pk)

    if request.method == 'POST':
        aplica = request.POST.get('aplica_destruccion') == '1'
        if aplica:
            form = BajaDestruccionForm(request.POST, request.FILES, instance=baja)
            if form.is_valid():
                baja = form.save(commit=False)
                baja.fase_actual = BajaEquipo.Fase.DESTRUCCION
                baja.save()
                messages.success(request, 'Fase 3 completada — destrucción física registrada.')
                return redirect('bajas:detalle', pk=pk)
        else:
            baja.fase_actual = BajaEquipo.Fase.DESTRUCCION
            baja.save()
            messages.info(request, 'Fase 3 omitida — método no requiere destrucción física.')
            return redirect('bajas:detalle', pk=pk)
    else:
        form = BajaDestruccionForm(instance=baja)

    return render(request, 'bajas/fase3_destruccion.html', {'baja': baja, 'form': form})


@login_required
def avanzar_fase4(request, pk):
    baja = get_object_or_404(BajaEquipo, pk=pk)
    if baja.fase_actual != BajaEquipo.Fase.DESTRUCCION:
        messages.error(request, 'Esta baja no está en Fase 3.')
        return redirect('bajas:detalle', pk=pk)

    if request.method == 'POST':
        form = BajaCierreForm(request.POST, instance=baja)
        if form.is_valid():
            baja = form.save(commit=False)
            baja.fase_actual = BajaEquipo.Fase.CIERRE
            baja.fecha_cierre = timezone.now()
            baja.save()
            form.save_m2m()
            equipo = baja.equipo
            equipo.estado = Equipo.Estado.DADO_DE_BAJA
            equipo.save()
            try:
                from .service import generar_acta_baja
                generar_acta_baja(baja)
                messages.success(request, 'Proceso de baja completado. Acta PDF generada.')
            except Exception as exc:
                messages.warning(request, f'Baja completada, pero no se pudo generar el acta: {exc}')
            return redirect('bajas:detalle', pk=pk)
    else:
        form = BajaCierreForm(instance=baja)

    return render(request, 'bajas/fase4_cierre.html', {'baja': baja, 'form': form})


@login_required
def descargar_acta(request, pk):
    baja = get_object_or_404(BajaEquipo, pk=pk)
    if not baja.acta_pdf:
        raise Http404
    response = HttpResponse(baja.acta_pdf.read(), content_type='application/pdf')
    nombre = baja.acta_pdf.name.split('/')[-1]
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return response
