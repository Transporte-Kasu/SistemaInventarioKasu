# Contexto técnico — Sistema de Inventario TI Transportes Kasu

Este documento describe el estado actual completo del proyecto: arquitectura, modelos, URLs, lógica de negocio y decisiones técnicas tomadas. Sirve como punto de partida para cualquier sesión nueva de desarrollo o para incorporar a un nuevo desarrollador.

---

## Descripción general

Sistema web interno para la gestión del ciclo de vida de equipos de cómputo de **Transportes Kasu**. Implementa el protocolo **PROT-TI-001** de la empresa, que cubre inventario, mantenimiento preventivo, tickets de soporte vía QR y baja formal de activos.

- **13 equipos** registrados (11 Lenovo ThinkCenter, 2 HP AllOne22LA)
- **Custodios** (Mariela, Frances, Luis, etc.) no tienen login — solo interactúan escaneando el QR del equipo para abrir tickets desde su celular
- **TI** (Zuly Becerra — `zuly.becerra@loginco.com.mx`) tiene acceso completo al sistema
- **Gerencia** (`gerencia.general@transporteskasu.com.mx`) recibe reportes semestrales por correo

---

## Stack técnico

| Componente | Tecnología |
|---|---|
| Backend | Django 5.2, Python 3.12 |
| Base de datos | PostgreSQL (Digital Ocean Managed DB) |
| Archivos / media | Digital Ocean Spaces (S3-compatible, `django-storages`) |
| Correo | SendGrid vía SMTP (`django.core.mail`) |
| PDFs | WeasyPrint (renderiza HTML → PDF) |
| Scheduler | APScheduler + `django-apscheduler` (jobs persistidos en BD) |
| Static files | Whitenoise (integrado en middleware) |
| Frontend | Bootstrap 5.3 + Bootstrap Icons 1.11 |
| Package manager | `uv` (no pip ni pipenv) |
| Deploy | Docker + Digital Ocean App Platform |

---

## Estructura de apps Django

```
apps/
├── usuarios/       # Login/logout/perfil (usa auth.User de Django)
├── inventario/     # Equipo — modelo central, QR, dashboard
├── mantenimiento/  # Mantenimiento preventivo, alertas
├── tickets/        # Tickets de soporte (público vía QR + panel TI)
├── bajas/          # Flujo 4 fases PROT-TI-001 §7.3, acta PDF
└── reportes/       # Reportes PDF, APScheduler, historial
```

---

## Modelos

### `apps.inventario.Equipo`

Campo central del sistema. Cada equipo tiene un `uuid` (UUID4) que forma la URL pública del QR.

```
uuid            UUIDField       — único, usado en URL /q/<uuid>/
usuario         CharField       — nombre del custodio (no FK, custodios sin login)
tipo            TextChoices     — desktop | laptop | servidor | telefono | tablet | usb | impresora | otro
marca / modelo  CharField
numero_serie    CharField       — único
estado          TextChoices     — activo | almacen | pendiente_baja | dado_de_baja
mac_address     CharField       — opcional
ubicacion       CharField       — área/departamento
foto            ImageField      — upload_to='equipos/fotos/'
qr_code         ImageField      — upload_to='equipos/qr/'  (auto-generado en save())
fecha_adquisicion DateField     — opcional
fecha_registro  DateTimeField   — auto_now_add
```

**Lógica de negocio en `save()`:** si `qr_code` está vacío, llama a `_generar_qr()` que construye la URL `{BASE_URL}/q/{uuid}/` y genera la imagen PNG con la librería `qrcode[pil]`.

**Propiedades:**
- `necesita_mantenimiento` → `True` si no hay mantenimientos o el último `proxima_fecha <= hoy`
- `proximo_mantenimiento` → fecha del último mantenimiento registrado

**Índices:** `estado`, `numero_serie`, `uuid`

---

### `apps.mantenimiento.Mantenimiento`

```
equipo          FK(Equipo)      — related_name='mantenimientos'
tecnico         FK(User)        — técnico que realizó el mantenimiento
tipo            TextChoices     — preventivo | correctivo | limpieza | actualizacion
fecha           DateField       — default=today
proxima_fecha   DateField       — auto-calculado en save() como fecha + 4 meses
estado_equipo   TextChoices     — bueno | regular | deteriorado
observaciones   TextField
```

**Lógica en `save()`:** si `proxima_fecha` está vacía, calcula `fecha + relativedelta(months=4)` usando `python-dateutil`.

---

### `apps.tickets.Ticket`

```
equipo              FK(Equipo)      — related_name='tickets'
folio               CharField       — auto-generado TKT-YYYYMMDD-XXXX
nombre_solicitante  CharField       — llenado en formulario público (custodio)
email_solicitante   EmailField      — para notificación al cerrar
categoria           TextChoices     — hardware | software | red | impresora | acceso | perifericos | otro
descripcion         TextField
prioridad           TextChoices     — baja | media | alta | urgente
estado              TextChoices     — abierto | en_proceso | cerrado
asignado_a          FK(User)        — técnico TI asignado (nullable)
fecha_apertura      DateTimeField   — auto_now_add
fecha_cierre        DateTimeField   — nullable
notas_cierre        TextField
```

**Lógica en `save()`:** genera folio secuencial del día si no existe: busca el último `TKT-{YYYYMMDD}-*` y suma 1.

**Método `cerrar(notas='')`:** cambia estado a CERRADO, registra fecha_cierre.

---

### `apps.bajas.BajaEquipo`

Relación `OneToOneField` con `Equipo` — un equipo solo puede tener un proceso de baja.

```
equipo              OneToOneField(Equipo)   — related_name='baja'
solicitante         FK(User)                — quien inicia el proceso
motivo              TextField
metodo_sanitizacion TextChoices             — formateo_logico | degaussing | destruccion_fisica | factory_reset
fase_actual         IntegerChoices          — 1=Solicitud | 2=Ejecución | 3=Destrucción | 4=Cierre
autorizado_por      FK(User)                — asignado en Fase 2
testigos            ManyToManyField(User)   — registrados en Fase 4
fecha_solicitud     DateTimeField           — auto_now_add
fecha_ejecucion     DateTimeField           — nullable, puesto en Fase 2
fecha_cierre        DateTimeField           — nullable, puesto en Fase 4
herramienta_utilizada CharField             — Ej: DBAN 2.3
numero_pasadas      PositiveSmallIntegerField
verificacion_borrado BooleanField
evidencia_foto      FileField               — upload_to='bajas/evidencias/'
acta_pdf            FileField               — upload_to='bajas/actas/' (generado en Fase 4)
observaciones       TextField
```

**Propiedad `esta_completada`:** `True` si `fase_actual == 4`.

---

### `apps.reportes.ReporteInventario`

```
tipo            TextChoices     — completo | parcial | tickets | mantenimiento | extraordinario
periodo_inicio  DateField       — nullable
periodo_fin     DateField       — nullable
fecha_generacion DateTimeField  — auto_now_add
generado_por    FK(User)        — nullable (None = generado automáticamente por scheduler)
archivo_pdf     FileField       — upload_to='reportes/'
enviado_por_correo BooleanField
destinatarios   JSONField       — lista de emails a quienes se envió
notas           TextField
```

---

## URLs completas

### config/urls.py

```python
path('admin/', admin.site.urls)
path('', include('apps.inventario.urls'))        # app_name='inventario'
path('mantenimiento/', include('apps.mantenimiento.urls'))  # app_name='mantenimiento'
path('tickets/', include('apps.tickets.urls'))   # app_name='tickets'
path('bajas/', include('apps.bajas.urls'))        # app_name='bajas'
path('reportes/', include('apps.reportes.urls')) # app_name='reportes'
path('usuarios/', include('apps.usuarios.urls')) # app_name='usuarios'
path('q/', include('apps.tickets.urls_qr'))      # sin app_name — rutas públicas QR
```

### Rutas por módulo

| URL | Nombre | Vista |
|---|---|---|
| `/` | `inventario:dashboard` | Dashboard con métricas y alertas |
| `/equipos/` | `inventario:lista` | Lista con filtros (q, estado, tipo) |
| `/equipos/nuevo/` | `inventario:crear` | Formulario nuevo equipo |
| `/equipos/<pk>/` | `inventario:detalle` | Detalle + mantenimientos + tickets |
| `/equipos/<pk>/editar/` | `inventario:editar` | Editar equipo |
| `/equipos/<pk>/qr/` | `inventario:qr_download` | Descarga PNG del QR |
| `/mantenimiento/` | `mantenimiento:lista` | Historial de mantenimientos |
| `/mantenimiento/alertas/` | `mantenimiento:alertas` | Sin mant. / vencidos / próximos ≤15d |
| `/mantenimiento/registrar/<uuid>/` | `mantenimiento:registrar_qr` | Registrar mant. desde QR (auth requerida) |
| `/tickets/` | `tickets:lista` | Panel de tickets TI |
| `/tickets/<pk>/` | `tickets:detalle` | Detalle + notas |
| `/tickets/<pk>/asignar/` | `tickets:asignar` | Asignar técnico |
| `/tickets/<pk>/cerrar/` | `tickets:cerrar` | Cerrar ticket + notificación email |
| `/bajas/` | `bajas:lista` | Lista de procesos de baja |
| `/bajas/iniciar/<equipo_pk>/` | `bajas:iniciar` | Fase 1 — solicitud |
| `/bajas/<pk>/` | `bajas:detalle` | Detalle con stepper de fases |
| `/bajas/<pk>/fase2/` | `bajas:fase2` | Fase 2 — ejecución formateo |
| `/bajas/<pk>/fase3/` | `bajas:fase3` | Fase 3 — destrucción física |
| `/bajas/<pk>/fase4/` | `bajas:fase4` | Fase 4 — cierre + acta PDF |
| `/bajas/<pk>/acta/` | `bajas:acta` | Descarga acta PDF |
| `/reportes/` | `reportes:lista` | Historial de reportes |
| `/reportes/generar/<tipo>/` | `reportes:generar` | Generar y enviar manualmente |
| `/reportes/<pk>/descargar/` | `reportes:descargar` | Descarga PDF del reporte |
| `/usuarios/login/` | `usuarios:login` | Login |
| `/usuarios/logout/` | `usuarios:logout` | Logout (POST) |
| `/usuarios/perfil/` | `usuarios:perfil` | Perfil del usuario |
| `/q/<uuid>/` | `ticket_qr` | **Público** — dual: sin auth → form ticket, con auth → registrar mantenimiento |

---

## Lógica de negocio clave

### QR dual (`/q/<uuid>/`)

Vista `ticket_qr` en `apps/tickets/views.py`:
- `request.user.is_authenticated` → `True`: redirige a `mantenimiento:registrar_qr`
- `request.user.is_authenticated` → `False`: muestra formulario móvil de ticket (100% mobile-first, sin Bootstrap completo)

Al hacer POST en el formulario público: crea el `Ticket` y llama `notificar_ticket_abierto(ticket)` que envía email a `settings.EMAIL_TI`.

### Mantenimiento preventivo

- Cada registro de `Mantenimiento` calcula `proxima_fecha = fecha + 4 meses` automáticamente en `save()`
- `Equipo.necesita_mantenimiento` compara `proxima_fecha` del último mantenimiento con hoy
- La vista `AlertasMantenimientoView` categoriza todos los equipos activos en tres grupos:
  - `sin_mantenimiento`: nunca han tenido mantenimiento registrado
  - `vencidos`: `proximo_mantenimiento < hoy`
  - `proximos`: `hoy ≤ proximo_mantenimiento ≤ hoy + 15 días`

### Flujo de baja (4 fases)

```
Fase 1 (Solicitud)    → BajaEquipo creado, equipo.estado = 'pendiente_baja'
Fase 2 (Ejecución)    → herramienta, pasadas, verificacion_borrado, evidencia_foto, fecha_ejecucion
Fase 3 (Destrucción)  → opcional (checkbox "aplica_destruccion"). Si no aplica, se omite y avanza directo
Fase 4 (Cierre)       → testigos M2M, fecha_cierre, equipo.estado = 'dado_de_baja', genera acta PDF via WeasyPrint
```

El PDF del acta se genera en `apps/bajas/service.py::generar_acta_baja()` y se guarda como `FileField` en Spaces.

### Reportes automáticos

Scheduler iniciado en `ReportesConfig.ready()` — solo en el proceso principal (chequea `RUN_MAIN` en env o si el proceso es gunicorn):

| Job ID | Trigger | Descripción |
|---|---|---|
| `inventario_completo_semestral` | 1 ene + 1 jul, 7:00 am | PDF inventario completo → TI + Gerencia |
| `alerta_mantenimiento_mensual` | Día 1 de cada mes, 8:00 am | Alertas mantenimiento → TI |
| `resumen_tickets_semanal` | Lunes, 8:00 am | Tickets últimos 7 días → TI |
| `alerta_mantenimiento_diaria` | Diario, 8:30 am | Solo envía si hay equipos próximos a vencer (≤15d) o vencidos |

Los jobs son persistidos en BD por `DjangoJobStore` (tabla `django_apscheduler_djangojob`).

### Generación de PDFs

`apps/reportes/service.py`:
1. `_render_pdf(template, context)` → renderiza HTML con `render_to_string` + convierte con `WeasyPrint HTML(...).write_pdf()`
2. `_guardar_pdf(reporte, bytes, nombre)` → guarda en `ReporteInventario.archivo_pdf` via `ContentFile`
3. `_enviar_correo(asunto, destinatarios, html, bytes, nombre_adjunto)` → `EmailMessage` con el PDF como adjunto

### Notificaciones de tickets

`apps/tickets/notifications.py`:
- `notificar_ticket_abierto(ticket)` → email a `settings.EMAIL_TI` al abrir ticket
- `notificar_ticket_cerrado(ticket)` → email a `ticket.email_solicitante` al cerrar

---

## Decisiones técnicas importantes

### `DBURL` en lugar de `DATABASE_URL`

`python-decouple` lee variables de entorno del sistema antes que el `.env`. En Linux, `USERNAME=tony` ya existe en el entorno, lo que sobreescribe la variable `USERNAME` del connection string de PostgreSQL. La solución fue usar una variable diferente (`DBURL`) y parsearla con `dj_database_url.parse()`.

```python
# settings.py
DATABASES = {
    'default': dj_database_url.parse(
        config('DBURL'),
        conn_max_age=600,
        ssl_require=config('SSLMODE', default='require') == 'require',
    )
}
```

### `USE_SPACES` toggle

En desarrollo local (`USE_SPACES=False`), los archivos se guardan en `media/` local. En producción (`USE_SPACES=True`), `django-storages` usa `S3Boto3Storage` apuntando al bucket de Digital Ocean Spaces.

### Custodios sin login

`Equipo.usuario` es un `CharField`, no un `ForeignKey`. Los custodios no tienen cuenta en el sistema; solo interactúan via el QR. El formulario público en `/q/<uuid>/` captura `nombre_solicitante` y `email_solicitante` del ticket.

### `generado_por` nullable en reportes

`ReporteInventario.generado_por` puede ser `None` cuando el reporte fue generado por el scheduler. En la plantilla se usa `{% if r.generado_por %}...{% else %}Automático{% endif %}` para evitar el crash al acceder `.username` en `None`.

### Scheduler solo en proceso principal

`ReportesConfig.ready()` chequea `RUN_MAIN` (variable que Django StatReloader pone en el proceso hijo) y `--noreload`/gunicorn para evitar doble arranque:

```python
if not is_migration and (is_worker or 'RUN_MAIN' in os.environ):
    from .scheduler import iniciar_scheduler
    iniciar_scheduler()
```

---

## Variables de entorno

Todas definidas en `.env` (ver `.env.example`):

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta Django |
| `DEBUG` | `True` local, `False` producción |
| `ALLOWED_HOSTS` | Hostnames separados por coma |
| `CSRF_TRUSTED_ORIGINS` | URL(s) confiables para CSRF (incluir `https://`) |
| `DBURL` | Connection string completo de PostgreSQL |
| `SSLMODE` | `require` en producción, `disable` en local sin SSL |
| `USE_SPACES` | `True` / `False` — toggle para Spaces vs media local |
| `SPACES_KEY` | Access key de Digital Ocean Spaces |
| `SPACES_SECRET` | Secret key de Spaces |
| `SPACES_BUCKET` | Nombre del bucket (`kasu-inventario`) |
| `SPACES_ENDPOINT` | `https://nyc3.digitaloceanspaces.com` |
| `SPACES_REGION` | `nyc3` |
| `SPACES_CDN_ENDPOINT` | Dominio CDN del bucket |
| `EMAIL_HOST_PASSWORD` | API key de SendGrid (con prefijo `SG.`) |
| `FROM_EMAIL` | `invetario@transporteskasu.com.mx` |
| `BASE_URL` | URL base del servidor (usada para generar URLs en QR) |

---

## Archivos de despliegue

| Archivo | Propósito |
|---|---|
| `Dockerfile` | Python 3.12-slim + dependencias WeasyPrint + gunicorn |
| `.dockerignore` | Excluye `.env`, `media/`, PDFs, logos |
| `.do/app.yaml` | Spec completo Digital Ocean App Platform (web service + job `migrate`) |
| `scripts/setup_inicial.sh` | One-time: migrate + loaddata + crear superusers |
| `.env.example` | Plantilla documentada de variables de entorno |

### Proceso de deploy en DO

1. Push a GitHub (`main`)
2. DO App Platform detecta cambio, ejecuta build Docker
3. **Pre-deploy job** `migrate`: corre `python manage.py migrate --noinput`
4. Servidor inicia con `gunicorn config.wsgi:application --workers 2 --timeout 120`
5. `collectstatic --noinput` corre dentro del Dockerfile en build time

---

## Credenciales de desarrollo

| Acceso | Valor |
|---|---|
| URL local | `http://localhost:8000` |
| Superusuario | `admin` / `Kasu2026!` |
| Email TI | `zuly.becerra@loginco.com.mx` |
| Email Gerencia | `gerencia.general@transporteskasu.com.mx` |
| Email sistema | `invetario@transporteskasu.com.mx` |

---

## Comandos frecuentes

```bash
# Levantar servidor local
uv run python manage.py runserver

# Crear / aplicar migraciones
uv run python manage.py makemigrations
uv run python manage.py migrate

# Cargar inventario inicial (13 equipos)
uv run python manage.py loaddata apps/inventario/fixtures/inventario_inicial.json

# Colectar estáticos
uv run python manage.py collectstatic --noinput

# Shell Django
uv run python manage.py shell

# Agregar dependencia
uv add nombre-paquete
```
