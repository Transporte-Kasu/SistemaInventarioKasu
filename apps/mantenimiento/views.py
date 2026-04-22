from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.generic import ListView, TemplateView
from apps.inventario.models import Equipo
from .models import Mantenimiento
from .forms import MantenimientoForm


class MantenimientoListView(LoginRequiredMixin, ListView):
    model = Mantenimiento
    template_name = 'mantenimiento/lista.html'
    context_object_name = 'mantenimientos'
    paginate_by = 20

    def get_queryset(self):
        return Mantenimiento.objects.select_related('equipo', 'tecnico').order_by('-fecha')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hoy'] = timezone.now().date()
        return ctx


class AlertasMantenimientoView(LoginRequiredMixin, TemplateView):
    template_name = 'mantenimiento/alertas.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoy = timezone.now().date()
        limite = hoy + timedelta(days=15)
        activos = Equipo.objects.filter(estado=Equipo.Estado.ACTIVO).prefetch_related('mantenimientos')

        sin_mantenimiento = [e for e in activos if not e.proximo_mantenimiento]
        vencidos = [e for e in activos if e.proximo_mantenimiento and e.proximo_mantenimiento < hoy]
        proximos = [
            e for e in activos
            if e.proximo_mantenimiento and hoy <= e.proximo_mantenimiento <= limite
        ]
        ctx.update({
            'sin_mantenimiento': sin_mantenimiento,
            'vencidos': vencidos,
            'proximos': proximos,
            'hoy': hoy,
        })
        return ctx


@login_required
def registrar_qr(request, equipo_uuid):
    equipo = get_object_or_404(Equipo, uuid=equipo_uuid)
    if request.method == 'POST':
        form = MantenimientoForm(request.POST)
        if form.is_valid():
            m = form.save(commit=False)
            m.equipo = equipo
            m.tecnico = request.user
            m.save()
            messages.success(request, f'Mantenimiento registrado. Próximo: {m.proxima_fecha.strftime("%d/%m/%Y")}')
            return redirect('inventario:detalle', pk=equipo.pk)
    else:
        form = MantenimientoForm()
    return render(request, 'mantenimiento/registrar_qr.html', {'form': form, 'equipo': equipo})
