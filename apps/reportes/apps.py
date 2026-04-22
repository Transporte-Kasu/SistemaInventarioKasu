import sys
from django.apps import AppConfig


class ReportesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reportes'

    def ready(self):
        # Solo iniciar scheduler en el proceso principal (no en migraciones, tests o autoreload hijo)
        is_manage = 'manage.py' in sys.argv[0] or 'django' in sys.argv[0]
        is_migration = len(sys.argv) > 1 and sys.argv[1] in ('migrate', 'makemigrations', 'test', 'shell')
        is_worker = sys.argv[0].endswith('gunicorn') or '--noreload' in sys.argv

        if not is_migration and (is_worker or 'RUN_MAIN' in __import__('os').environ):
            from .scheduler import iniciar_scheduler
            iniciar_scheduler()
