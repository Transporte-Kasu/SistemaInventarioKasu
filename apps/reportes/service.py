"""
Servicio de generación de reportes PDF + envío por correo.
Cada función pública crea un ReporteInventario, genera el PDF,
lo sube a Spaces y lo envía por SendGrid.
"""
import os
import uuid
from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML, CSS

from apps.inventario.models import Equipo
from apps.mantenimiento.models import Mantenimiento
from apps.tickets.models import Ticket
from .models import ReporteInventario


# ── Helpers ──────────────────────────────────────────────────────────────────

def _logo_path():
    return os.path.join(settings.BASE_DIR, 'static', 'img', 'logo-small.png')


def _render_pdf(template_name, context):
    context.setdefault('logo_path', _logo_path())
    context.setdefault('fecha_generacion', timezone.now().strftime('%d/%m/%Y %H:%M'))
    context.setdefault('generado_por', 'Sistema automático')
    context.setdefault('folio', str(uuid.uuid4())[:8].upper())
    html_string = render_to_string(template_name, context)
    pdf_bytes = HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf()
    return pdf_bytes


def _guardar_pdf(reporte, pdf_bytes, nombre_archivo):
    reporte.archivo_pdf.save(nombre_archivo, ContentFile(pdf_bytes), save=True)


def _enviar_correo(asunto, destinatarios, cuerpo_html, pdf_bytes, nombre_adjunto):
    email = EmailMessage(
        subject=asunto,
        body=cuerpo_html,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=destinatarios,
    )
    email.content_subtype = 'html'
    email.attach(nombre_adjunto, pdf_bytes, 'application/pdf')
    email.send(fail_silently=True)


def _cuerpo_correo(tipo_label, fecha, descripcion):
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <div style="background:#e0007c;padding:16px 20px;border-radius:8px 8px 0 0;">
        <h2 style="color:#fff;margin:0;font-size:16px;">Reporte automático — {tipo_label}</h2>
      </div>
      <div style="padding:20px;border:1px solid #eee;border-top:none;border-radius:0 0 8px 8px;">
        <p>{descripcion}</p>
        <p style="color:#888;font-size:12px;">
          Generado el {fecha} — Transportes Kasu · Sistema de Inventario TI · PROT-TI-001
        </p>
        <p style="color:#aaa;font-size:11px;">CONFIDENCIAL – Uso interno exclusivo</p>
      </div>
    </div>
    """


# ── Reportes públicos ─────────────────────────────────────────────────────────

def generar_inventario_completo(usuario=None):
    hoy = timezone.now().date()
    limite = hoy + timedelta(days=15)
    activos = list(Equipo.objects.filter(estado=Equipo.Estado.ACTIVO).prefetch_related('mantenimientos'))

    stats = {
        'total': Equipo.objects.count(),
        'activos': Equipo.objects.filter(estado=Equipo.Estado.ACTIVO).count(),
        'almacen': Equipo.objects.filter(estado=Equipo.Estado.ALMACEN).count(),
        'baja': Equipo.objects.filter(estado__in=[
            Equipo.Estado.PENDIENTE_BAJA, Equipo.Estado.DADO_DE_BAJA
        ]).count(),
        'sin_mantenimiento': sum(1 for e in activos if not e.proximo_mantenimiento),
        'proximos': sum(
            1 for e in activos
            if e.proximo_mantenimiento and hoy <= e.proximo_mantenimiento <= limite
        ),
    }

    mantenimientos_recientes = (
        Mantenimiento.objects.filter(fecha__gte=hoy - timedelta(days=30))
        .select_related('equipo', 'tecnico')
        .order_by('-fecha')
    )

    inicio = hoy.replace(day=1)
    reporte = ReporteInventario.objects.create(
        tipo=ReporteInventario.Tipo.COMPLETO,
        periodo_inicio=inicio,
        periodo_fin=hoy,
        generado_por=usuario,
        destinatarios=[settings.EMAIL_TI, settings.EMAIL_GERENCIA],
    )

    pdf = _render_pdf('reportes/pdf/inventario_completo.html', {
        'equipos': Equipo.objects.all().prefetch_related('mantenimientos'),
        'stats': stats,
        'mantenimientos_recientes': mantenimientos_recientes,
        'periodo_inicio': inicio.strftime('%d/%m/%Y'),
        'periodo_fin': hoy.strftime('%d/%m/%Y'),
        'generado_por': usuario.get_full_name() if usuario else 'Sistema automático',
    })

    nombre = f'inventario_completo_{hoy.strftime("%Y%m%d")}.pdf'
    _guardar_pdf(reporte, pdf, nombre)

    destinatarios = [settings.EMAIL_TI, settings.EMAIL_GERENCIA]
    _enviar_correo(
        asunto=f'[Kasu TI] Inventario completo — {hoy.strftime("%d/%m/%Y")}',
        destinatarios=destinatarios,
        cuerpo_html=_cuerpo_correo(
            'Inventario Completo',
            hoy.strftime('%d/%m/%Y'),
            'Se adjunta el reporte de inventario completo de activos tecnológicos (PROT-TI-001 §6.2).',
        ),
        pdf_bytes=pdf,
        nombre_adjunto=nombre,
    )

    reporte.enviado_por_correo = True
    reporte.save()
    return reporte


def generar_alerta_mantenimiento(usuario=None):
    hoy = timezone.now().date()
    limite = hoy + timedelta(days=15)
    activos = list(Equipo.objects.filter(estado=Equipo.Estado.ACTIVO).prefetch_related('mantenimientos'))

    sin_mantenimiento = [e for e in activos if not e.proximo_mantenimiento]
    vencidos = [e for e in activos if e.proximo_mantenimiento and e.proximo_mantenimiento < hoy]
    proximos = [
        e for e in activos
        if e.proximo_mantenimiento and hoy <= e.proximo_mantenimiento <= limite
    ]

    if not (sin_mantenimiento or vencidos or proximos):
        return None

    reporte = ReporteInventario.objects.create(
        tipo=ReporteInventario.Tipo.MANTENIMIENTO,
        periodo_inicio=hoy,
        periodo_fin=hoy,
        generado_por=usuario,
        destinatarios=[settings.EMAIL_TI],
    )

    pdf = _render_pdf('reportes/pdf/alerta_mantenimiento.html', {
        'sin_mantenimiento': sin_mantenimiento,
        'vencidos': vencidos,
        'proximos': proximos,
        'periodo_inicio': hoy.strftime('%d/%m/%Y'),
        'periodo_fin': hoy.strftime('%d/%m/%Y'),
        'generado_por': usuario.get_full_name() if usuario else 'Sistema automático',
    })

    nombre = f'alerta_mantenimiento_{hoy.strftime("%Y%m%d")}.pdf'
    _guardar_pdf(reporte, pdf, nombre)

    total = len(sin_mantenimiento) + len(vencidos)
    _enviar_correo(
        asunto=f'[Kasu TI] ⚠ Alerta mantenimiento — {total} equipo(s) requieren atención',
        destinatarios=[settings.EMAIL_TI],
        cuerpo_html=_cuerpo_correo(
            'Alerta de Mantenimiento',
            hoy.strftime('%d/%m/%Y'),
            f'{len(vencidos)} equipo(s) con mantenimiento vencido y {len(sin_mantenimiento)} sin registro. '
            f'Se adjunta el reporte detallado.',
        ),
        pdf_bytes=pdf,
        nombre_adjunto=nombre,
    )

    reporte.enviado_por_correo = True
    reporte.save()
    return reporte


def generar_resumen_tickets(usuario=None):
    hoy = timezone.now().date()
    inicio = hoy - timedelta(days=7)
    tickets = Ticket.objects.filter(
        fecha_apertura__date__gte=inicio
    ).select_related('equipo').order_by('-fecha_apertura')

    stats = {
        'total': tickets.count(),
        'abiertos': tickets.filter(estado=Ticket.Estado.ABIERTO).count(),
        'en_proceso': tickets.filter(estado=Ticket.Estado.EN_PROCESO).count(),
        'cerrados': tickets.filter(estado=Ticket.Estado.CERRADO).count(),
        'urgentes': tickets.filter(prioridad='urgente').count(),
    }

    reporte = ReporteInventario.objects.create(
        tipo=ReporteInventario.Tipo.TICKETS,
        periodo_inicio=inicio,
        periodo_fin=hoy,
        generado_por=usuario,
        destinatarios=[settings.EMAIL_TI],
    )

    pdf = _render_pdf('reportes/pdf/resumen_tickets.html', {
        'tickets': tickets,
        'stats': stats,
        'periodo_inicio': inicio.strftime('%d/%m/%Y'),
        'periodo_fin': hoy.strftime('%d/%m/%Y'),
        'generado_por': usuario.get_full_name() if usuario else 'Sistema automático',
    })

    nombre = f'resumen_tickets_{hoy.strftime("%Y%m%d")}.pdf'
    _guardar_pdf(reporte, pdf, nombre)

    _enviar_correo(
        asunto=f'[Kasu TI] Resumen semanal tickets — {stats["abiertos"]} abierto(s)',
        destinatarios=[settings.EMAIL_TI],
        cuerpo_html=_cuerpo_correo(
            'Resumen Semanal de Tickets',
            hoy.strftime('%d/%m/%Y'),
            f'Semana del {inicio.strftime("%d/%m")} al {hoy.strftime("%d/%m/%Y")}: '
            f'{stats["total"]} tickets, {stats["abiertos"]} abiertos, {stats["cerrados"]} cerrados.',
        ),
        pdf_bytes=pdf,
        nombre_adjunto=nombre,
    )

    reporte.enviado_por_correo = True
    reporte.save()
    return reporte
