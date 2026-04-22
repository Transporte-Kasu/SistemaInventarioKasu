from datetime import date
from dateutil.relativedelta import relativedelta
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Mantenimiento(models.Model):
    class Tipo(models.TextChoices):
        PREVENTIVO = 'preventivo', 'Preventivo'
        CORRECTIVO = 'correctivo', 'Correctivo'
        LIMPIEZA = 'limpieza', 'Limpieza'
        ACTUALIZACION = 'actualizacion', 'Actualización de software'

    class EstadoEquipo(models.TextChoices):
        BUENO = 'bueno', 'Bueno'
        REGULAR = 'regular', 'Regular'
        DETERIORADO = 'deteriorado', 'Deteriorado'

    equipo = models.ForeignKey(
        'inventario.Equipo',
        on_delete=models.CASCADE,
        related_name='mantenimientos',
        verbose_name='Equipo',
    )
    tecnico = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='mantenimientos_realizados',
        verbose_name='Técnico responsable',
    )
    tipo = models.CharField('Tipo', max_length=20, choices=Tipo.choices, default=Tipo.PREVENTIVO)
    fecha = models.DateField('Fecha de mantenimiento', default=date.today)
    proxima_fecha = models.DateField('Próximo mantenimiento', blank=True)
    estado_equipo = models.CharField(
        'Estado del equipo', max_length=15, choices=EstadoEquipo.choices, default=EstadoEquipo.BUENO
    )
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Mantenimiento'
        verbose_name_plural = 'Mantenimientos'
        ordering = ['-fecha']
        indexes = [models.Index(fields=['proxima_fecha'])]

    def __str__(self):
        return f'{self.equipo} — {self.get_tipo_display()} {self.fecha}'

    def save(self, *args, **kwargs):
        if not self.proxima_fecha:
            self.proxima_fecha = self.fecha + relativedelta(months=4)
        super().save(*args, **kwargs)
