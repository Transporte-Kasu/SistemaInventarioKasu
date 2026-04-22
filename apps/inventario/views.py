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
