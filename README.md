# Sistema de Inventario TI — Transportes Kasu

Aplicación web para la gestión del inventario de equipos de cómputo de Transportes Kasu. Cubre el ciclo de vida completo de los activos TI: registro, mantenimiento preventivo, tickets de soporte, bajas y reportes automáticos, conforme al protocolo interno **PROT-TI-001**.

---

## Módulos

| Módulo | Ruta | Descripción |
|---|---|---|
| **Inventario** | `/equipos/` | CRUD de equipos, generación automática de QR, foto |
| **Mantenimiento** | `/mantenimiento/` | Historial de mantenimientos preventivos + alertas |
| **Tickets** | `/tickets/` | Gestión de reportes de soporte. Los custodios los abren escaneando el QR del equipo |
| **Bajas** | `/bajas/` | Flujo de 4 fases (PROT-TI-001 §7.3) con acta PDF |
| **Reportes** | `/reportes/` | Reportes automáticos vía APScheduler + generación manual |
| **QR público** | `/q/<uuid>/` | Formulario móvil para custodios (sin login) |

---

## Stack

- **Backend:** Django 5.2, Python 3.12
- **Base de datos:** PostgreSQL (Digital Ocean Managed DB)
- **Archivos / media:** Digital Ocean Spaces (S3-compatible)
- **Correo:** SendGrid vía SMTP
- **PDFs:** WeasyPrint
- **Scheduler:** APScheduler + django-apscheduler
- **Static files:** Whitenoise
- **Frontend:** Bootstrap 5 + Bootstrap Icons
- **Package manager:** uv
- **Deploy:** Docker + Digital Ocean App Platform

---

## Desarrollo local

### 1. Requisitos previos

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- PostgreSQL accesible (local o Digital Ocean)

### 2. Clonar e instalar

```bash
git clone https://github.com/TU_USUARIO/SistemaInventarioKasu.git
cd SistemaInventarioKasu
uv sync
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con los valores reales
```

Variables mínimas para desarrollo local:

```env
SECRET_KEY=cualquier-clave-larga
DEBUG=True
DBURL=postgres://usuario:contraseña@localhost:5432/kasu_inventario
USE_SPACES=False
```

### 4. Migraciones e inicialización

```bash
uv run python manage.py migrate
bash scripts/setup_inicial.sh   # solo la primera vez
```

Esto crea:
- Superusuario `admin` / `Kasu2026!` (email: `zuly.becerra@loginco.com.mx`)
- 13 equipos iniciales del inventario

### 5. Levantar el servidor

```bash
uv run python manage.py runserver
```

Acceder a [http://localhost:8000](http://localhost:8000).

---

## Comportamiento del QR dual

Cada equipo tiene una URL pública `/q/<uuid>/`:

- **Usuario no autenticado** (custodio) → formulario móvil para abrir un ticket de soporte
- **Usuario autenticado** (TI) → pantalla para registrar mantenimiento preventivo

El QR se genera automáticamente al crear o editar un equipo y se almacena en Spaces.

---

## Reportes automáticos (APScheduler)

| Reporte | Frecuencia | Destinatarios |
|---|---|---|
| Inventario completo | 1 ene y 1 jul, 7:00 am | TI + Gerencia |
| Alerta de mantenimiento | Día 1 de cada mes, 8:00 am | TI |
| Alerta diaria (próximos 15 días) | Diario 8:30 am (solo si hay alertas) | TI |
| Resumen de tickets | Lunes 8:00 am | TI |

Todos los reportes generan un PDF adjunto y se guardan en historial. También se pueden lanzar manualmente desde `/reportes/`.

---

## Flujo de baja de equipos (PROT-TI-001 §7.3)

```
Fase 1 — Solicitud      →  motivo + método de sanitización
Fase 2 — Ejecución      →  herramienta, pasadas, verificación, evidencia foto
Fase 3 — Destrucción    →  evidencia física (opcional según método)
Fase 4 — Cierre         →  testigos, actualización inventario, acta PDF
```

Al completar la Fase 4:
- El equipo queda marcado como **Dado de baja**
- Se genera el **Acta PDF** oficial con firmas y datos del proceso
- El acta queda disponible para descarga desde el detalle de la baja

---

## Despliegue en Digital Ocean App Platform

### Requisitos previos en DO

1. **Spaces bucket** `kasu-inventario` en la región `nyc3` (acceso público para media)
2. **PostgreSQL Managed Database** — copiar la connection string
3. **SendGrid API key** con verificación del dominio `transporteskasu.com.mx`

### Pasos

```bash
# 1. Subir código a GitHub
git init && git add . && git commit -m "Initial commit"
git remote add origin https://github.com/TU_USUARIO/SistemaInventarioKasu.git
git push -u origin main

# 2. En la consola de Digital Ocean:
#    Apps → Create App → GitHub → seleccionar repo
#    Subir .do/app.yaml como spec, o configurar manualmente
```

### Variables de entorno (secrets en DO)

Configurar en la consola de DO → App → Settings → Environment Variables:

| Variable | Tipo | Valor |
|---|---|---|
| `SECRET_KEY` | Secret | Clave aleatoria larga |
| `DBURL` | Secret | Connection string de Managed PostgreSQL |
| `SPACES_KEY` | Secret | Access key de Spaces |
| `SPACES_SECRET` | Secret | Secret key de Spaces |
| `EMAIL_HOST_PASSWORD` | Secret | `SG.` + API key de SendGrid |

Las demás variables (`DEBUG=False`, `SPACES_BUCKET`, etc.) ya están definidas en `.do/app.yaml`.

### Setup inicial (una sola vez)

Después del primer deploy exitoso, ejecutar desde la consola de DO o via `doctl`:

```bash
bash scripts/setup_inicial.sh
```

---

## Estructura del proyecto

```
SistemaInventarioKasu/
├── apps/
│   ├── inventario/       # Modelos Equipo, QR, fixtures iniciales
│   ├── mantenimiento/    # Modelo Mantenimiento, alertas
│   ├── tickets/          # Tickets públicos + panel TI, notificaciones email
│   ├── bajas/            # Flujo 4 fases, acta PDF
│   ├── reportes/         # PDF WeasyPrint, APScheduler, historial
│   └── usuarios/         # Login/logout/perfil
├── config/               # settings.py, urls.py, wsgi.py
├── templates/            # HTML base + por módulo + PDF templates
├── static/               # kasu.css (tema rosa #e0007c)
├── scripts/              # setup_inicial.sh
├── .do/                  # app.yaml (DO App Platform spec)
├── Dockerfile
└── .env.example
```

---

## Credenciales por defecto (desarrollo)

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `Kasu2026!` | Superusuario TI (Zuly Becerra) |

> Cambiar la contraseña inmediatamente en producción desde `/admin/`.
