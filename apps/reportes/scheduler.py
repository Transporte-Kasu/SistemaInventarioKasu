"""
Jobs de APScheduler para reportes automáticos.
Se registran en AppConfig.ready() para arrancar con el servidor.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution

logger = logging.getLogger(__name__)
_scheduler = None


def job_inventario_completo():
    """Inventario completo semestral — 1 ene y 1 jul."""
    from apps.reportes.service import generar_inventario_completo
    try:
        r = generar_inventario_completo()
        logger.info('Reporte inventario completo generado: %s', r)
    except Exception as exc:
        logger.error('Error generando inventario completo: %s', exc)


def job_alerta_mantenimiento():
    """Alerta mensual de mantenimientos vencidos / próximos."""
    from apps.reportes.service import generar_alerta_mantenimiento
    try:
        r = generar_alerta_mantenimiento()
        if r:
            logger.info('Alerta mantenimiento generada: %s', r)
        else:
            logger.info('Alerta mantenimiento: sin equipos que alertar.')
    except Exception as exc:
        logger.error('Error generando alerta mantenimiento: %s', exc)


def job_resumen_tickets():
    """Resumen semanal de tickets — cada lunes a las 8 am."""
    from apps.reportes.service import generar_resumen_tickets
    try:
        r = generar_resumen_tickets()
        logger.info('Resumen tickets generado: %s', r)
    except Exception as exc:
        logger.error('Error generando resumen tickets: %s', exc)


def job_alerta_mantenimiento_diaria():
    """Revisión diaria — envía alerta solo si hay equipos que vencen en 15 días."""
    from apps.reportes.service import generar_alerta_mantenimiento
    from django.utils import timezone
    from datetime import timedelta
    from apps.inventario.models import Equipo

    hoy = timezone.now().date()
    limite = hoy + timedelta(days=15)
    activos = Equipo.objects.filter(estado=Equipo.Estado.ACTIVO).prefetch_related('mantenimientos')
    hay_proximos = any(
        e.proximo_mantenimiento and hoy <= e.proximo_mantenimiento <= limite
        for e in activos
    )
    hay_vencidos = any(
        e.proximo_mantenimiento and e.proximo_mantenimiento < hoy
        for e in activos
    )
    hay_sin = any(not e.proximo_mantenimiento for e in activos)

    if hay_proximos or hay_vencidos or hay_sin:
        generar_alerta_mantenimiento()


def iniciar_scheduler():
    global _scheduler
    if _scheduler is not None:
        return

    scheduler = BackgroundScheduler(timezone='America/Mexico_City')
    scheduler.add_jobstore(DjangoJobStore(), 'default')

    # Inventario completo — 1 enero y 1 julio a las 7 am
    scheduler.add_job(
        job_inventario_completo,
        trigger=CronTrigger(month='1,7', day=1, hour=7, minute=0),
        id='inventario_completo_semestral',
        replace_existing=True,
        max_instances=1,
    )

    # Alerta mantenimiento mensual — día 1 de cada mes
    scheduler.add_job(
        job_alerta_mantenimiento,
        trigger=CronTrigger(day=1, hour=8, minute=0),
        id='alerta_mantenimiento_mensual',
        replace_existing=True,
        max_instances=1,
    )

    # Resumen tickets semanal — lunes 8 am
    scheduler.add_job(
        job_resumen_tickets,
        trigger=CronTrigger(day_of_week='mon', hour=8, minute=0),
        id='resumen_tickets_semanal',
        replace_existing=True,
        max_instances=1,
    )

    # Alerta diaria proximos vencimientos — 8 am
    scheduler.add_job(
        job_alerta_mantenimiento_diaria,
        trigger=CronTrigger(hour=8, minute=30),
        id='alerta_mantenimiento_diaria',
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info('APScheduler iniciado con %d jobs.', len(scheduler.get_jobs()))
