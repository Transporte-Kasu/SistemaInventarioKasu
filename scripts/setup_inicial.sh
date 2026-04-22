#!/usr/bin/env bash
# Ejecutar UNA SOLA VEZ después del primer despliegue en producción.
# Crea el superusuario y carga el inventario inicial.
set -e

echo "==> Aplicando migraciones..."
uv run python manage.py migrate --noinput

echo "==> Cargando inventario inicial (13 equipos)..."
uv run python manage.py loaddata apps/inventario/fixtures/inventario_inicial.json

echo "==> Creando superusuario admin / Kasu2026! ..."
uv run python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='zuly.becerra@loginco.com.mx',
        password='Kasu2026!',
        first_name='Zuly',
        last_name='Becerra',
    )
    User.objects.create_superuser(
        username='xoyoc',
        email='xoyocl2@gmail.com',
        password='Azrael1977$2025',
        first_name='Antonio Xoyoc',
        last_name='Becerra Farias',
    )
    print('Superusuario admin creado.')
else:
    print('Superusuario admin ya existe.')
"

echo "==> Listo. Sistema inicializado correctamente."
