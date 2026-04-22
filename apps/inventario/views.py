from datetime import timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView
from django.http import HttpResponse
from .models import Equipo
from .forms import EquipoForm


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoy = timezone.now().date()
        limite_proximo = hoy + timedelta(days=15)

        # IDs de equipos activos con su último mantenimiento
        activos = Equipo.objects.filter(estado=Equipo.Estado.ACTIVO)

        sin_mantenimiento = [e for e in activos if not e.proximo_mantenimiento]
        vencidos = [e for e in activos if e.proximo_mantenimiento and e.proximo_mantenimiento < hoy]
        proximos = [
            e for e in activos
            if e.proximo_mantenimiento and hoy <= e.proximo_mantenimiento <= limite_proximo
        ]

        from apps.tickets.models import Ticket
        tickets_abiertos = Ticket.objects.filter(
            estado=Ticket.Estado.ABIERTO
        ).select_related('equipo').order_by('-fecha_apertura')[:8]

        ctx.update({
            'total_equipos': Equipo.objects.count(),
            'total_activos': activos.count(),
            'total_almacen': Equipo.objects.filter(estado=Equipo.Estado.ALMACEN).count(),
            'total_baja': Equipo.objects.filter(estado__in=[
                Equipo.Estado.PENDIENTE_BAJA, Equipo.Estado.DADO_DE_BAJA
            ]).count(),
            'sin_mantenimiento': sin_mantenimiento,
            'vencidos': vencidos,
            'proximos': proximos,
            'tickets_abiertos': tickets_abiertos,
            'tickets_urgentes': Ticket.objects.filter(
                estado=Ticket.Estado.ABIERTO,
                prioridad='urgente'
            ).count(),
            'tickets_total_abiertos': Ticket.objects.filter(estado=Ticket.Estado.ABIERTO).count(),
            'hoy': hoy,
        })
        return ctx


class EquipoListView(LoginRequiredMixin, ListView):
    model = Equipo
    template_name = 'inventario/lista.html'
    context_object_name = 'equipos'
    paginate_by = 20

    def get_queryset(self):
        qs = Equipo.objects.all()
        q = self.request.GET.get('q', '').strip()
        estado = self.request.GET.get('estado', '')
        tipo = self.request.GET.get('tipo', '')
        if q:
            qs = (
                qs.filter(usuario__icontains=q)
                | qs.filter(numero_serie__icontains=q)
                | qs.filter(marca__icontains=q)
            )
        if estado:
            qs = qs.filter(estado=estado)
        if tipo:
            qs = qs.filter(tipo=tipo)
        return qs.distinct()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estados'] = Equipo.Estado.choices
        ctx['tipos'] = Equipo.Tipo.choices
        ctx['q'] = self.request.GET.get('q', '')
        ctx['estado_sel'] = self.request.GET.get('estado', '')
        ctx['tipo_sel'] = self.request.GET.get('tipo', '')
        ctx['total'] = Equipo.objects.count()
        ctx['activos'] = Equipo.objects.filter(estado=Equipo.Estado.ACTIVO).count()
        return ctx


class EquipoDetailView(LoginRequiredMixin, DetailView):
    model = Equipo
    template_name = 'inventario/detalle.html'
    context_object_name = 'equipo'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['mantenimientos'] = self.object.mantenimientos.select_related('tecnico').order_by('-fecha')[:10]
        ctx['tickets'] = self.object.tickets.order_by('-fecha_apertura')[:10]
        return ctx


class EquipoCreateView(LoginRequiredMixin, CreateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'inventario/form.html'
    success_url = reverse_lazy('inventario:lista')

    def form_valid(self, form):
        messages.success(self.request, 'Equipo registrado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Registrar equipo'
        return ctx


class EquipoUpdateView(LoginRequiredMixin, UpdateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'inventario/form.html'
    success_url = reverse_lazy('inventario:lista')

    def form_valid(self, form):
        messages.success(self.request, 'Equipo actualizado correctamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar — {self.object}'
        return ctx


def qr_download(request, pk):
    equipo = Equipo.objects.get(pk=pk)
    if equipo.qr_code:
        response = HttpResponse(equipo.qr_code.read(), content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="qr_{equipo.numero_serie}.png"'
        return response
    return HttpResponse('QR no disponible', status=404)


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

@login_required
def regenerar_qr_masivo(request):
    """Genera QR para todos los equipos que no lo tienen todavía. Acepta GET y POST."""
    sin_qr = Equipo.objects.filter(qr_code='')
    total = sin_qr.count()
    generados = 0
    errores = 0
    for equipo in sin_qr:
        try:
            equipo._generar_qr()
            equipo.save()
            generados += 1
        except Exception:
            errores += 1
    if generados:
        messages.success(request, f'QR generado para {generados} equipo(s).')
    if errores:
        messages.error(request, f'No se pudo generar QR para {errores} equipo(s).')
    if total == 0:
        messages.info(request, 'Todos los equipos ya tienen QR generado.')
    return redirect('inventario:lista')


@login_required
def etiquetas_qr(request):
    ids_raw = request.GET.get('ids', '')
    if ids_raw:
        ids = [i for i in ids_raw.split(',') if i.strip().isdigit()]
        equipos = Equipo.objects.filter(pk__in=ids).order_by('usuario', 'marca')
    else:
        equipos = Equipo.objects.exclude(estado=Equipo.Estado.DADO_DE_BAJA).order_by('usuario', 'marca')

    # Pre-encode QR images as base64 so they work sin depender de URLs de media
    import base64
    etiquetas = []
    for eq in equipos:
        qr_b64 = None
        if eq.qr_code:
            try:
                eq.qr_code.seek(0)
                qr_b64 = base64.b64encode(eq.qr_code.read()).decode('utf-8')
            except Exception:
                pass
        etiquetas.append({'equipo': eq, 'qr_b64': qr_b64})

    return render(request, 'inventario/etiquetas_qr.html', {
        'etiquetas': etiquetas,
        'total': len(etiquetas),
    })
