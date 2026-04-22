from django.core.management.base import BaseCommand
from apps.inventario.models import Equipo


class Command(BaseCommand):
    help = 'Regenera los QR de todos los equipos (fuerza sobreescritura con BASE_URL actual)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--solo-faltantes',
            action='store_true',
            help='Solo genera QR para equipos que no tienen ninguno',
        )

    def handle(self, *args, **options):
        if options['solo_faltantes']:
            equipos = Equipo.objects.filter(qr_code='')
            self.stdout.write(f'Equipos sin QR: {equipos.count()}')
        else:
            equipos = Equipo.objects.all()
            self.stdout.write(f'Regenerando QR para todos los equipos ({equipos.count()})...')

        ok = 0
        err = 0
        for equipo in equipos:
            try:
                equipo.qr_code = None
                equipo._generar_qr()
                equipo.save()
                ok += 1
                self.stdout.write(f'  ✓ {equipo.numero_serie}')
            except Exception as e:
                err += 1
                self.stdout.write(self.style.ERROR(f'  ✗ {equipo.numero_serie}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'\nListo: {ok} generados, {err} errores.'))
