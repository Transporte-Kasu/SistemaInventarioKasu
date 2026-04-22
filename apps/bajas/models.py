from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class BajaEquipo(models.Model):
    class MetodoSanitizacion(models.TextChoices):
        FORMATEO_LOGICO = 'formateo_logico', 'Formateo lógico estándar'
        DEGAUSSING = 'degaussing', 'Desmagnetización (Degaussing)'
        DESTRUCCION_FISICA = 'destruccion_fisica', 'Destrucción física'
        FACTORY_RESET = 'factory_reset', 'Restablecimiento de fábrica'

    class Fase(models.IntegerChoices):
        SOLICITUD = 1, 'Fase 1 — Solicitud de baja'
        EJECUCION = 2, 'Fase 2 — Ejecución de formateo / desinfección'
        DESTRUCCION = 3, 'Fase 3 — Destrucción física (si aplica)'
        CIERRE = 4, 'Fase 4 — Actualización de inventario y cierre'

    equipo = models.OneToOneField(
        'inventario.Equipo',
        on_delete=models.PROTECT,
        related_name='baja',
        verbose_name='Equipo',
    )
    solicitante = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='bajas_solicitadas',
        verbose_name='Solicitante',
    )
    motivo = models.TextField('Motivo de baja')
    metodo_sanitizacion = models.CharField(
        'Método de sanitización',
        max_length=20,
        choices=MetodoSanitizacion.choices,
    )
    fase_actual = models.IntegerField('Fase actual', choices=Fase.choices, default=Fase.SOLICITUD)
    autorizado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bajas_autorizadas',
        verbose_name='Autorizado por',
    )
    testigos = models.ManyToManyField(
        User,
        blank=True,
        related_name='bajas_como_testigo',
        verbose_name='Testigos',
    )
    fecha_solicitud = models.DateTimeField('Fecha de solicitud', auto_now_add=True)
    fecha_ejecucion = models.DateTimeField('Fecha de ejecución', blank=True, null=True)
    fecha_cierre = models.DateTimeField('Fecha de cierre', blank=True, null=True)
    herramienta_utilizada = models.CharField('Herramienta utilizada', max_length=120, blank=True)
    numero_pasadas = models.PositiveSmallIntegerField('Número de pasadas', default=0)
    verificacion_borrado = models.BooleanField('Verificación de borrado realizada', default=False)
    evidencia_foto = models.FileField(
        'Evidencia fotográfica', upload_to='bajas/evidencias/', blank=True, null=True
    )
    acta_pdf = models.FileField(
        'Acta de baja (PDF)', upload_to='bajas/actas/', blank=True, null=True
    )
    observaciones = models.TextField('Observaciones', blank=True)

    class Meta:
        verbose_name = 'Baja de equipo'
        verbose_name_plural = 'Bajas de equipos'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'Baja: {self.equipo} — Fase {self.fase_actual}'

    @property
    def esta_completada(self):
        return self.fase_actual == self.Fase.CIERRE
