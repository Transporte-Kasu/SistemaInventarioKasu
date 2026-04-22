from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


def _send(subject, to_list, template, context):
    html = render_to_string(template, context)
    send_mail(
        subject=subject,
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=to_list,
        html_message=html,
        fail_silently=True,
    )


def notificar_ticket_abierto(ticket):
    _send(
        subject=f'[Kasu TI] Nuevo ticket {ticket.folio} — {ticket.get_categoria_display()}',
        to_list=[settings.EMAIL_TI],
        template='emails/ticket_abierto.html',
        context={'ticket': ticket},
    )


def notificar_ticket_cerrado(ticket):
    destinatarios = [ticket.email_solicitante]
    _send(
        subject=f'[Kasu TI] Tu reporte {ticket.folio} fue resuelto',
        to_list=destinatarios,
        template='emails/ticket_cerrado.html',
        context={'ticket': ticket},
    )
