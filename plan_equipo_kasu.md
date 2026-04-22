# Plan de Desarrollo — Sistema de Inventario de Equipos TI
## Transportes Kasu

**Versión:** 1.2  
**Fecha:** 2026-04-22  
**Referencia protocolo:** PROT-TI-001  

### Decisiones confirmadas

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 1 | Destinatarios de correos | TI: `zuly.becerra@loginco.com.mx` · Gerencia: `gerencia.general@transporteskasu.com.mx` |
| 2 | Custodios con login | No. Solo personal de TI y Gerencia acceden al sistema |
| 3 | Flujo de baja | Completo: 4 fases según PROT-TI-001 §7.3 |
| 4 | Formulario público de ticket | 100% optimizado para móvil (se escanea QR desde celular) |
| 5 | Idioma del sistema | Español completo (Django i18n `es`) |
| 6 | Dominio | URL temporal de Digital Ocean (App Platform) por ahora |
| 7 | Categorías de tickets | Predefinidas + descripción breve + prioridad |

---

## 1. Resumen del Proyecto

Aplicación web Django para la gestión integral del inventario de equipos de cómputo de Transportes Kasu. El sistema contempla registro de activos, mantenimiento preventivo cada 4 meses, sistema de tickets vía QR, reportes automáticos alineados al protocolo PROT-TI-001, y flujo de baja de equipos. Desplegado en Digital Ocean con PostgreSQL, SendGrid y Spaces.

---

## 2. Stack Tecnológico

| Componente        | Tecnología                              |
|-------------------|-----------------------------------------|
| Backend           | Django 5.x + Django REST Framework      |
| Idioma            | Español completo (`LANGUAGE_CODE = 'es'`, i18n activo) |
| Base de datos     | PostgreSQL (Digital Ocean Managed DB)   |
| Almacenamiento    | Digital Ocean Spaces (S3-compatible)    |
| Correo            | SendGrid (`invetario@transporteskasu.com.mx`) |
| Tareas programadas| APScheduler (django-apscheduler)        |
| QR Codes          | `qrcode` (Python library)               |
| PDF Reports       | `WeasyPrint`                            |
| Frontend          | Django Templates + Bootstrap 5 + HTMX  |
| Deploy            | Digital Ocean App Platform (URL temporal) |
| Variables entorno | `.env` (python-decouple)                |

---

## 3. Módulos del Sistema

### 3.1 Inventario de Equipos
- Alta, edición y baja de equipos
- Campos mínimos según PROT-TI-001 §6.1:
  - Responsable / Custodio
  - Tipo de equipo (Desktop, Laptop, Servidor, Teléfono, USB, etc.)
  - Marca y modelo
  - Número de serie
  - Estado operativo: `activo | almacén | pendiente_de_baja | dado_de_baja`
- Campos adicionales (datos actuales del inventario):
  - MAC address
  - Teléfono interno
  - Número y marca de monitores
  - Ubicación / área
  - Foto del equipo (almacenada en Spaces)
  - Fecha de adquisición
  - Código QR generado automáticamente al crear el equipo

### 3.2 Mantenimiento Preventivo
- Registro de mantenimiento realizado por el técnico de TI autenticado
- Campos:
  - Fecha del mantenimiento (automática)
  - Próximo mantenimiento (automático: +4 meses)
  - Técnico responsable (usuario autenticado)
  - Tipo: preventivo | correctivo | limpieza | actualización
  - Observaciones
- Dashboard con equipos próximos a mantenimiento (ámbar: ≤15 días, rojo: vencido)
- Historial completo de mantenimientos por equipo

### 3.3 Sistema de Tickets
- **Acceso público (sin login) — 100% optimizado para móvil:**
  - Diseño mobile-first (viewport, botones táctiles grandes, teclado virtual optimizado)
  - Nombre del solicitante
  - Correo electrónico
  - Categoría predefinida (ver tabla abajo)
  - Descripción breve del problema (textarea corto, obligatorio)
  - Prioridad: `Baja | Media | Alta | Urgente`
  - El equipo se pre-carga automáticamente desde el QR (el usuario no lo selecciona)
  - Confirmación visual clara al enviar (pantalla de éxito con número de folio)

**Categorías predefinidas de tickets:**

| Categoría         | Descripción de uso                                   |
|-------------------|------------------------------------------------------|
| Hardware          | Fallas físicas: teclado, mouse, pantalla, CPU        |
| Software          | Errores de aplicaciones, sistema operativo           |
| Red / Internet    | Sin conexión, lentitud de red, VPN                   |
| Impresora         | Atascos, sin tinta, no imprime                       |
| Cuenta / Acceso   | Contraseña, permisos, bloqueo de usuario             |
| Periféricos       | USB, monitores externos, bocinas, cámara             |
| Otro              | Cualquier problema no contemplado en las categorías  |
- **Gestión de tickets (requiere login):**
  - Ver, asignar, cambiar estado y cerrar tickets
  - Estados: `abierto | en_proceso | cerrado`
  - Al abrir: notificación inmediata a TI (`zuly.becerra@loginco.com.mx`)
  - Al cerrar: notificación de resolución al correo del solicitante

### 3.4 Sistema QR Dual
Cada equipo tiene un UUID único que genera una URL pública:

```
GET /q/{equipo_uuid}/
```

**Lógica de redirección según estado del usuario:**

| Usuario             | Resultado al escanear QR                          |
|---------------------|---------------------------------------------------|
| No autenticado      | Formulario público de creación de ticket          |
| Autenticado (staff) | Formulario de registro de mantenimiento del equipo|

- Los QR se generan como imagen PNG y se almacenan en Spaces
- Se pueden descargar e imprimir desde el panel de administración
- El QR incluye el número de serie y nombre del equipo en el sticker

### 3.5 Baja de Equipos (PROT-TI-001 §7)
Flujo de 4 fases documentadas en el sistema:

| Fase | Acción                          | Responsable         |
|------|---------------------------------|---------------------|
| 1    | Solicitud de baja               | Custodio            |
| 2    | Ejecución de formateo/desinfección | Técnico TI       |
| 3    | Destrucción física (si aplica)  | TI + Cumplimiento   |
| 4    | Actualización inventario        | Responsable TI      |

- Tabla de decisión de método (formateo estándar / degaussing / destrucción física)
- Adjuntar evidencia fotográfica (almacenada en Spaces)
- Generación de acta de baja en PDF
- Retención de expediente: 5 años (campo `fecha_purga` calculado automáticamente)

### 3.6 Reportes Automáticos (APScheduler)

| Reporte                           | Frecuencia           | Destinatarios                                                    |
|-----------------------------------|----------------------|------------------------------------------------------------------|
| Inventario completo (PDF)         | Semestral            | TI (zuly.becerra@loginco.com.mx) + Gerencia (gerencia.general@transporteskasu.com.mx) |
| Inventario parcial (25% muestra)  | Trimestral           | TI (zuly.becerra@loginco.com.mx)                                 |
| Alerta equipos sin mantenimiento  | Mensual              | TI (zuly.becerra@loginco.com.mx)                                 |
| Resumen de tickets abiertos       | Semanal (lunes)      | TI (zuly.becerra@loginco.com.mx)                                 |
| Equipos próximos a mantenimiento  | 15 días antes        | TI (zuly.becerra@loginco.com.mx)                                 |
| Nuevo ticket creado (alerta inmediata) | Al crear ticket | TI (zuly.becerra@loginco.com.mx)                            |
| Ticket cerrado (confirmación)     | Al cerrar ticket     | Solicitante (correo capturado en formulario)                     |

Los reportes en PDF siguen la estructura del protocolo PROT-TI-001 e incluyen:
- Encabezado con logo Kasu
- Fecha de generación y periodo
- Listado de activos con estado
- Evidencia de mantenimientos realizados
- Firma de Responsable TI (campo editable)

---

## 4. Modelos de Base de Datos

### `Equipo`
```python
uuid            # UUID4 único (usado en URL del QR)
usuario         # CharField (nombre custodio, sin FK — no tienen login)
tipo            # choices: desktop, laptop, servidor, telefono, usb, tablet, otro
marca
modelo
numero_serie    # único
estado          # activo | almacen | pendiente_baja | dado_de_baja
mac_address
telefono_interno
monitores_cantidad
monitores_marca
ubicacion
foto            # ImageField → Spaces
qr_code         # ImageField → Spaces (auto-generado al crear)
fecha_adquisicion
fecha_registro  # auto_now_add
fecha_baja
notas
```

### `Mantenimiento`
```python
equipo          # FK → Equipo
tecnico         # FK → User
tipo            # preventivo | correctivo | limpieza | actualizacion
fecha           # auto (DateTimeField)
proxima_fecha   # fecha + 4 meses (auto-calculado en save())
observaciones
estado_equipo   # bueno | regular | deteriorado
```

### `Ticket`
```python
equipo          # FK → Equipo
folio           # auto (TKT-YYYYMMDD-XXXX)
nombre_solicitante
email_solicitante
categoria       # hardware | software | red | impresora | acceso | perifericos | otro
descripcion     # texto breve obligatorio
prioridad       # baja | media | alta | urgente
estado          # abierto | en_proceso | cerrado
asignado_a      # FK → User (nullable)
fecha_apertura  # auto_now_add
fecha_cierre
notas_cierre
```

### `BajaEquipo`
```python
equipo          # OneToOne → Equipo
solicitante     # FK → User (custodio)
motivo
metodo_sanitizacion  # formateo_logico | degaussing | destruccion_fisica | factory_reset
fase_actual     # 1 | 2 | 3 | 4
autorizado_por  # FK → User (gerencia)
fecha_solicitud
fecha_ejecucion
fecha_cierre
evidencia_foto  # FileField → Spaces
acta_pdf        # FileField → Spaces (auto-generado)
testigos        # ManyToMany → User
```

### `ReporteInventario`
```python
tipo            # completo | parcial | extraordinario | tickets | mantenimiento
periodo_inicio
periodo_fin
fecha_generacion  # auto
generado_por    # FK → User
archivo_pdf     # FileField → Spaces
enviado_por_correo  # BooleanField
destinatarios   # JSONField
```

---

## 5. Estructura del Proyecto Django

```
sistemaKasu/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── inventario/       # Equipos, CRUD, QR
│   ├── mantenimiento/    # Mantenimientos preventivos
│   ├── tickets/          # Tickets (público + admin)
│   ├── bajas/            # Flujo de baja PROT-TI-001
│   ├── reportes/         # Generación y envío de reportes
│   └── usuarios/         # Auth, perfiles, roles
├── templates/
│   ├── base.html
│   ├── inventario/
│   ├── mantenimiento/
│   ├── tickets/
│   └── reportes/
├── static/
│   ├── img/logo.png
│   └── css/
├── scheduler.py          # APScheduler jobs
├── manage.py
├── requirements.txt
├── Dockerfile
└── .env
```

---

## 6. Roles y Permisos

| Rol                | Usuario(s)                                    | Permisos                                                        |
|--------------------|-----------------------------------------------|-----------------------------------------------------------------|
| Admin / TI         | zuly.becerra@loginco.com.mx                   | Acceso total: inventario, tickets, mantenimientos, bajas, reportes |
| Gerencia           | gerencia.general@transporteskasu.com.mx       | Ver dashboards y reportes, autorizar bajas, ver inventario      |
| Público (sin auth) | Custodios y cualquier empleado con el QR      | Solo formulario de ticket vía QR (móvil)                        |

> Los custodios (Mariela, Frances, Luis, Nivey, etc.) **no tienen login**. Su única interacción es escanear el QR para abrir un ticket.

---

## 7. APScheduler — Trabajos Programados

```python
# scheduler.py
scheduler.add_job(reporte_inventario_completo,    'cron', month='1,7',  day=1)
scheduler.add_job(reporte_inventario_parcial,     'cron', month='3,6,9,12', day=1)
scheduler.add_job(alerta_mantenimientos_vencidos, 'cron', day=1)
scheduler.add_job(alerta_mantenimientos_proximos, 'cron', hour=8)  # diario
scheduler.add_job(resumen_tickets_semanal,        'cron', day_of_week='mon', hour=8)
```

Cada job:
1. Consulta la base de datos
2. Genera PDF con logo Kasu y datos del protocolo
3. Sube el PDF a Digital Ocean Spaces
4. Guarda registro en `ReporteInventario`
5. Envía correo vía SendGrid con PDF adjunto

---

## 8. Flujo QR — Detalle Técnico

```
QR generado → URL: https://inventario.kasu.com/q/{uuid}/

View: QRRedirectView
  ├── request.user.is_authenticated == True
  │     └── Redirect → /mantenimiento/registrar/{uuid}/
  └── request.user.is_authenticated == False
        └── Render → tickets/formulario_publico.html (equipo pre-cargado)
```

El QR se regenera automáticamente si cambia el UUID. El UUID no cambia después de creado.

---

## 9. Dashboard Principal

- Contador de equipos por estado (activo / almacén / baja pendiente)
- Equipos con mantenimiento vencido (rojo) o próximo (ámbar)
- Tickets abiertos por prioridad
- Última fecha de inventario y próxima programada
- Acceso rápido a: Nuevo equipo | Ver tickets | Generar reporte

---

## 10. Despliegue — Digital Ocean

### Variables de entorno (`.env`)
Ya configuradas: PostgreSQL, SendGrid, Spaces, SECRET_KEY.

### Opciones de despliegue recomendadas

**Opción A — App Platform (recomendado):**
- Despliegue automático desde GitHub
- Auto-scaling
- Managed SSL
- Ideal para este proyecto

**Opción B — Droplet + Nginx + Gunicorn:**
- Mayor control
- Requiere configuración manual de SSL (Let's Encrypt)

### Dockerfile básico
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN python manage.py collectstatic --no-input
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## 11. Plan de Fases de Desarrollo

### Fase 1 — Base del Proyecto (Semana 1-2)
- [ ] Crear proyecto Django con estructura de apps
- [ ] Configurar settings: PostgreSQL, Spaces, SendGrid, APScheduler
- [ ] Modelo `Equipo` + migraciones
- [ ] Auth de usuarios y roles
- [ ] Importar inventario inicial (13 equipos del CSV)
- [ ] CRUD de equipos con UI Bootstrap 5

### Fase 2 — QR y Tickets (Semana 2-3)
- [ ] Generación de QR por equipo (`qrcode` library)
- [ ] Vista pública `/q/{uuid}/` con lógica de redirección
- [ ] Formulario público de tickets (sin auth)
- [ ] Gestión de tickets para usuarios autenticados
- [ ] Notificaciones SendGrid para tickets

### Fase 3 — Mantenimiento (Semana 3-4)
- [ ] Modelo `Mantenimiento` con cálculo automático de próxima fecha
- [ ] Formulario de registro de mantenimiento (para usuarios autenticados desde QR)
- [ ] Historial de mantenimientos por equipo
- [ ] Indicadores visuales en dashboard (vencido / próximo)

### Fase 4 — Reportes y APScheduler (Semana 4-5)
- [ ] Generación de PDF con WeasyPrint (logo Kasu + estructura PROT-TI-001)
- [ ] Upload a Digital Ocean Spaces
- [ ] Configurar todos los jobs en APScheduler
- [ ] Envío de correos vía SendGrid con adjunto PDF

### Fase 5 — Flujo de Baja y Pulido (Semana 5-6)
- [ ] Modelo `BajaEquipo` + flujo de 4 fases
- [ ] Generación de acta de baja en PDF
- [ ] Dashboard principal con métricas
- [ ] Tests unitarios críticos
- [ ] Dockerfile y deploy en Digital Ocean

---

## 12. Decisiones Confirmadas — Completo

Todas las definiciones del sistema están resueltas. El plan está listo para comenzar desarrollo.

| # | Decisión | Definición |
|---|----------|------------|
| 1 | Destinatarios correos | TI: `zuly.becerra@loginco.com.mx` + Gerencia: `gerencia.general@transporteskasu.com.mx` |
| 2 | Custodios login | No tienen acceso al sistema |
| 3 | Flujo baja | Completo — 4 fases PROT-TI-001 §7.3 |
| 4 | Formulario ticket | 100% mobile-first |
| 5 | Idioma | Español completo (i18n `es`) |
| 6 | Dominio | URL temporal Digital Ocean App Platform |
| 7 | Categorías ticket | 7 categorías predefinidas + descripción breve + prioridad |

---

## 13. Sugerencias de Mejora

- **UUID en lugar de ID en QRs:** Usar UUID4 en las URLs de QR evita enumeración de equipos.
- **Rate limiting en formulario público:** Proteger el endpoint de tickets público con `django-ratelimit` para evitar spam.
- **Foto de equipo en el sticker QR:** El PDF del QR puede incluir foto del equipo + número de serie para identificación rápida.
- **Historial de cambios (audit log):** `django-simple-history` para rastrear quién cambió qué en cada equipo (útil para auditorías del protocolo).
- **Exportación a Excel:** Permitir exportar el inventario a `.xlsx` además de PDF para que Gerencia pueda trabajarlo.
- **Firma digital en actas:** Para las actas de baja, considerar firma con campo de nombre + fecha + cargo como mínimo.
