from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Ticket(models.Model):
    class Categoria(models.TextChoices):
        HARDWARE = 'hardware', 'Hardware'
        SOFTWARE = 'software', 'Software'
        RED = 'red', 'Red / Internet'
        IMPRESORA = 'impresora', 'Impresora'
        ACCESO = 'acceso', 'Cuenta / Acceso'
        PERIFERICOS = 'perifericos', 'Periféricos'
        OTRO = 'otro', 'Otro'

    class Prioridad(models.TextChoices):
        BAJA = 'baja', 'Baja'
        MEDIA = 'media', 'Media'
        ALTA = 'alta', 'Alta'
        URGENTE = 'urgente', 'Urgente'

    class Estado(models.TextChoices):
        ABIERTO = 'abierto', 'Abierto'
        EN_PROCESO = 'en_proceso', 'En proceso'
        CERRADO = 'cerrado', 'Cerrado'

    equipo = models.ForeignKey(
        'inventario.Equipo',
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name='Equipo',
    )
    folio = models.CharField('Folio', max_length=25, unique=True, blank=True)
    nombre_solicitante = models.CharField('Nombre del solicitante', max_length=120)
    email_solicitante = models.EmailField('Correo del solicitante')
    categoria = models.CharField('Categoría', max_length=15, choices=Categoria.choices)
    descripcion = models.TextField('Descripción del problema')
    prioridad = models.CharField('Prioridad', max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField('Estado', max_length=15, choices=Estado.choices, default=Estado.ABIERTO)
    asignado_a = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets_asignados',
        verbose_name='Asignado a',
    )
    fecha_apertura = models.DateTimeField('Fecha de apertura', auto_now_add=True)
    fecha_cierre = models.DateTimeField('Fecha de cierre', blank=True, null=True)
    notas_cierre = models.TextField('Notas de cierre', blank=True)

    class Meta:
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-fecha_apertura']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['prioridad']),
        ]

    def __str__(self):
        return f'{self.folio} — {self.get_categoria_display()} ({self.get_estado_display()})'

    def save(self, *args, **kwargs):
        if not self.folio:
            self.folio = self._generar_folio()
        super().save(*args, **kwargs)

    def _generar_folio(self):
        hoy = timezone.now().strftime('%Y%m%d')
        ultimo = (
            Ticket.objects.filter(folio__startswith=f'TKT-{hoy}')
            .order_by('-folio')
            .first()
        )
        if ultimo:
            secuencia = int(ultimo.folio.split('-')[-1]) + 1
        else:
            secuencia = 1
        return f'TKT-{hoy}-{secuencia:04d}'

    def cerrar(self, notas=''):
        self.estado = self.Estado.CERRADO
        self.fecha_cierre = timezone.now()
        self.notas_cierre = notas
        self.save()
