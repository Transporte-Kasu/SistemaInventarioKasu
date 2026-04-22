import uuid
import qrcode
from io import BytesIO
from django.db import models
from django.core.files import File


class Equipo(models.Model):
    class Tipo(models.TextChoices):
        DESKTOP = 'desktop', 'Computadora de escritorio'
        LAPTOP = 'laptop', 'Laptop'
        SERVIDOR = 'servidor', 'Servidor'
        TELEFONO = 'telefono', 'Teléfono corporativo'
        TABLET = 'tablet', 'Tablet'
        USB = 'usb', 'Memoria USB'
        IMPRESORA = 'impresora', 'Impresora / Escáner'
        OTRO = 'otro', 'Otro'

    class Estado(models.TextChoices):
        ACTIVO = 'activo', 'Activo'
        ALMACEN = 'almacen', 'En almacén'
        PENDIENTE_BAJA = 'pendiente_baja', 'Pendiente de baja'
        DADO_DE_BAJA = 'dado_de_baja', 'Dado de baja'

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    usuario = models.CharField('Responsable / Custodio', max_length=120)
    tipo = models.CharField('Tipo de equipo', max_length=20, choices=Tipo.choices, default=Tipo.DESKTOP)
    marca = models.CharField('Marca', max_length=80)
    modelo = models.CharField('Modelo', max_length=120)
    numero_serie = models.CharField('Número de serie', max_length=100, unique=True)
    estado = models.CharField('Estado operativo', max_length=20, choices=Estado.choices, default=Estado.ACTIVO)

    mac_address = models.CharField('MAC Address', max_length=17, blank=True)
    telefono_interno = models.CharField('Teléfono interno', max_length=30, blank=True)
    monitores_cantidad = models.PositiveSmallIntegerField('Cantidad de monitores', default=0)
    monitores_marca = models.CharField('Marca del monitor', max_length=80, blank=True)
    ubicacion = models.CharField('Ubicación / Área', max_length=120, blank=True)

    foto = models.ImageField('Foto del equipo', upload_to='equipos/fotos/', blank=True, null=True)
    qr_code = models.ImageField('Código QR', upload_to='equipos/qr/', blank=True, null=True)

    fecha_adquisicion = models.DateField('Fecha de adquisición', blank=True, null=True)
    fecha_registro = models.DateTimeField('Fecha de registro', auto_now_add=True)
    fecha_baja = models.DateField('Fecha de baja', blank=True, null=True)
    notas = models.TextField('Notas', blank=True)

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering = ['usuario', 'marca']
        indexes = [
            models.Index(fields=['estado']),
            models.Index(fields=['numero_serie']),
            models.Index(fields=['uuid']),
        ]

    def __str__(self):
        return f'{self.marca} {self.modelo} — {self.usuario} ({self.numero_serie})'

    def save(self, *args, **kwargs):
        if not self.qr_code:
            self._generar_qr()
        super().save(*args, **kwargs)

    def _generar_qr(self):
        from django.conf import settings
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        url = f'{base_url}/q/{self.uuid}/'
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr_{self.numero_serie}.png'
        self.qr_code.save(filename, File(buffer), save=False)

    @property
    def necesita_mantenimiento(self):
        from django.utils import timezone
        ultimo = self.mantenimientos.order_by('-proxima_fecha').first()
        if not ultimo:
            return True
        return ultimo.proxima_fecha <= timezone.now().date()

    @property
    def proximo_mantenimiento(self):
        ultimo = self.mantenimientos.order_by('-proxima_fecha').first()
        return ultimo.proxima_fecha if ultimo else None
