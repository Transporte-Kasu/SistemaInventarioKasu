from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ReporteInventario(models.Model):
    class Tipo(models.TextChoices):
        COMPLETO = 'completo', 'Inventario completo (semestral)'
        PARCIAL = 'parcial', 'Inventario parcial (trimestral)'
        TICKETS = 'tickets', 'Resumen de tickets'
        MANTENIMIENTO = 'mantenimiento', 'Alerta de mantenimientos'
        EXTRAORDINARIO = 'extraordinario', 'Extraordinario'

    tipo = models.CharField('Tipo', max_length=20, choices=Tipo.choices)
    periodo_inicio = models.DateField('Periodo inicio', blank=True, null=True)
    periodo_fin = models.DateField('Periodo fin', blank=True, null=True)
    fecha_generacion = models.DateTimeField('Generado el', auto_now_add=True)
    generado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reportes_generados', verbose_name='Generado por',
    )
    archivo_pdf = models.FileField(
        'Archivo PDF', upload_to='reportes/', blank=True, null=True
    )
    enviado_por_correo = models.BooleanField('Enviado por correo', default=False)
    destinatarios = models.JSONField('Destinatarios', default=list)
    notas = models.TextField('Notas', blank=True)

    class Meta:
        verbose_name = 'Reporte'
        verbose_name_plural = 'Reportes'
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.fecha_generacion.strftime("%d/%m/%Y")}'
