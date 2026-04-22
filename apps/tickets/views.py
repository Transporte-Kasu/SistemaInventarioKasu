from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import ListView, DetailView
from django.http import HttpResponseForbidden
from apps.inventario.models import Equipo
from .models import Ticket
from .forms import TicketPublicoForm, TicketCierreForm
from .notifications import notificar_ticket_abierto, notificar_ticket_cerrado

User = get_user_model()


class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = 'tickets/lista.html'
    context_object_name = 'tickets'
    paginate_by = 25

    def get_queryset(self):
        qs = Ticket.objects.select_related('equipo', 'asignado_a')
        estado = self.request.GET.get('estado', '')
        prioridad = self.request.GET.get('prioridad', '')
        if estado:
            qs = qs.filter(estado=estado)
        if prioridad:
            qs = qs.filter(prioridad=prioridad)
        return qs.order_by('-fecha_apertura')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estados'] = Ticket.Estado.choices
        ctx['prioridades'] = Ticket.Prioridad.choices
        ctx['estado_sel'] = self.request.GET.get('estado', '')
        ctx['prioridad_sel'] = self.request.GET.get('prioridad', '')
        ctx['total_abiertos'] = Ticket.objects.filter(estado=Ticket.Estado.ABIERTO).count()
        ctx['total_en_proceso'] = Ticket.objects.filter(estado=Ticket.Estado.EN_PROCESO).count()
        return ctx


class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = 'tickets/detalle.html'
    context_object_name = 'ticket'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form_cierre'] = TicketCierreForm()
        ctx['tecnicos'] = User.objects.filter(is_staff=True)
        return ctx


@login_required
def ticket_asignar(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        user_id = request.POST.get('asignado_a')
        ticket.asignado_a_id = user_id or None
        ticket.estado = Ticket.Estado.EN_PROCESO
        ticket.save()
        messages.success(request, 'Ticket asignado correctamente.')
    return redirect('tickets:detalle', pk=pk)


@login_required
def ticket_cerrar(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if request.method == 'POST':
        form = TicketCierreForm(request.POST)
        if form.is_valid():
            ticket.cerrar(notas=form.cleaned_data['notas_cierre'])
            notificar_ticket_cerrado(ticket)
            messages.success(request, f'Ticket {ticket.folio} cerrado. Notificación enviada a {ticket.email_solicitante}.')
        else:
            messages.error(request, 'Por favor agrega una nota de cierre.')
    return redirect('tickets:detalle', pk=pk)


def ticket_qr(request, equipo_uuid):
    equipo = get_object_or_404(Equipo, uuid=equipo_uuid)
    if request.user.is_authenticated:
        return redirect('mantenimiento:registrar_qr', equipo_uuid=equipo_uuid)

    if request.method == 'POST':
        form = TicketPublicoForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.equipo = equipo
            ticket.save()
            notificar_ticket_abierto(ticket)
            return render(request, 'tickets/ticket_enviado.html', {'ticket': ticket, 'equipo': equipo})
    else:
        form = TicketPublicoForm()

    return render(request, 'tickets/ticket_publico.html', {'form': form, 'equipo': equipo})
