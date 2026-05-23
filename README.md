# UOCRA Sistema — CL Gestión Laboral

Sistema web de gestión laboral para estudios contables.
Reemplaza el sistema híbrido Google Sheets + Apps Script por una aplicación web completa instalada en servidor propio.

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Backend | Python 3 + Flask |
| Base de datos | SQLite |
| Servidor WSGI | Gunicorn |
| Proxy reverso | Nginx |
| Sistema operativo | Ubuntu 22.04 LTS |

---

## Arquitectura

```
Internet
    │
    ▼
 Nginx (puerto 80 / 443)
    │
    ▼
 Gunicorn (127.0.0.1:8000)
    │
    ▼
 Flask app (app.py)
    │
    ▼
 SQLite (uocra.db)
```

---

## Estructura de archivos

```
/opt/uocra/
├── app.py                  # Rutas y lógica principal
├── models.py               # Base de datos y queries
├── mail.py                 # Módulo de envío de mails
├── requirements.txt        # Dependencias Python
├── setup.sh                # Script de instalación
├── uocra.db                # Base de datos (no tocar)
└── templates/
    ├── base.html           # Plantilla base con nav
    ├── login.html          # Pantalla de acceso
    ├── dashboard.html      # Panel principal
    ├── nomina.html         # Lista de empleados
    ├── empleado_form.html  # Alta de empleado
    ├── novedades.html      # Novedades por período
    ├── novedad_form.html   # Carga por empleado
    ├── informe.html        # Informe de control
    ├── config_empresa.html # Datos de la empresa
    ├── docs_empleado.html  # Documentación empleado
    ├── docs_pendientes.html# Docs por revisar
    └── admin/
        ├── log.html        # Log de auditoría
        ├── usuarios.html   # Gestión de usuarios
        └── config_mail.html# Config SMTP
```

---

## Instalación en Ubuntu

### Requisitos previos
- Ubuntu 22.04 LTS
- Usuario con privilegios sudo
- Acceso por SSH al servidor

### Paso 1 — Obtener el código

**Opción A — Desde el repositorio (recomendado):**
```bash
git clone https://github.com/clgest/auditoria-system.git /tmp/uocra_app
cd /tmp/uocra_app/uocra_app
```

**Opción B — Desde ZIP:**
```bash
# Subir el ZIP al servidor desde tu máquina local:
scp uocra_app_mvp.zip usuario@IP-DEL-SERVIDOR:/tmp/

# En el servidor:
cd /tmp
unzip uocra_app_mvp.zip -d uocra_app
cd uocra_app
```

### Paso 2 — Ejecutar el instalador

```bash
sudo bash setup.sh
```

El script realiza automáticamente:
1. Instala Python 3, pip, venv y Nginx
2. Crea el usuario del sistema `uocra`
3. Copia los archivos a `/opt/uocra/`
4. Crea el entorno virtual e instala dependencias
5. Inicializa la base de datos con usuarios por defecto
6. Configura el servicio systemd `uocra`
7. Configura Nginx como proxy reverso
8. Inicia ambos servicios

### Paso 3 — Verificar

```bash
# Estado del servicio
sudo systemctl status uocra

# Ver logs en tiempo real
sudo journalctl -u uocra -f
```

El sistema queda disponible en: `http://IP-DEL-SERVIDOR`

---

## Actualización del sistema

**Opción A — Desde el repositorio (recomendado):**
```bash
cd /tmp/uocra_app
git pull origin master
sudo bash uocra_app/setup.sh
```

**Opción B — Desde ZIP:**
```bash
# Subir nuevo ZIP
scp uocra_app_mvp.zip usuario@IP:/tmp/

# En el servidor
cd /tmp
unzip -o uocra_app_mvp.zip -d uocra_app
cd uocra_app
sudo bash setup.sh
```

> **La base de datos `uocra.db` nunca se toca.** El script no la borra ni la modifica.

---

## Usuarios iniciales

| Email | Clave | Rol |
|---|---|---|
| clgest@gmail.com | lescgo1 | estudio |
| clgestad@gmail.com | lescgo2 | estudio |

Cambiar las claves desde **Admin → Usuarios** una vez instalado.

---

## Roles y permisos

### Rol: estudio
Acceso completo al sistema:
- Todas las empresas
- Gestión de usuarios
- Log de auditoría
- Config mail SMTP
- Documentos pendientes de todas las empresas
- TXT Tiempsoft, informe liquidación

### Rol: cliente
Acceso restringido a sus empresas asignadas:
- Carga de novedades
- Informe de control
- Subida de documentación
- Confirmación de período

---

## Módulos activos

| # | Módulo | Estado |
|---|---|---|
| 1 | Login con roles y audit log | OK |
| 2 | Nómina y alta de empleados | OK |
| 3 | Carga de novedades por quincena | OK |
| 4 | Confirmar período + mail automático | OK |
| 5 | Config empresa (CUIT, domicilio, mail, CBU) | OK |
| 6 | Config mail SMTP | OK |
| 7 | Documentación bidireccional con estados | OK |
| 8 | TXT Tiempsoft | Pendiente |
| 9 | Informe de liquidación | Pendiente |
| 10 | Conversor UOCRA integrado | Pendiente |
| 11 | Multi-sindicato | Pendiente |

---

## Flujo de documentación

```
Cliente sube documento
        │
        ▼
Mail automático al estudio
(clgest@gmail.com + clgestad@gmail.com)
        │
        ▼
Estudio revisa en /docs/<empresa>/pendientes
        │
   ┌────┴────┐
   ▼         ▼
Aprueba   Rechaza
   │         │
   └────┬────┘
        ▼
Mail automático al cliente
(mail configurado en la empresa)
```

---

## Flujo de confirmación de período

```
Cliente carga todas las novedades del mes
        │
        ▼
Botón "Confirmar período" en pantalla Novedades
        │
        ▼
Sistema marca todas las novedades como confirmadas
        │
        ▼
Mail automático silencioso al estudio
con resumen del período (sin que el cliente lo vea)
```

---

## Configuración de mail SMTP

Desde el menú **Config Mail** (solo rol estudio):

| Campo | Descripción |
|---|---|
| Servidor SMTP | smtp.gmail.com (Gmail) |
| Puerto | 587 |
| Usuario | cuenta de Gmail emisora |
| Contraseña | App Password de Google |
| Mail estudio 1 | clgest@gmail.com |
| Mail estudio 2 | clgestad@gmail.com |

> Para Gmail con verificación en dos pasos: usá una **contraseña de aplicación**.
> Configuración → Seguridad → Contraseñas de aplicaciones.

---

## Comandos útiles en el servidor

```bash
# Reiniciar el sistema
sudo systemctl restart uocra

# Ver logs
sudo journalctl -u uocra -f

# Ver logs de Nginx
sudo tail -f /var/log/nginx/error.log

# Estado general
sudo systemctl status uocra nginx
```

---

## HTTPS con dominio propio

Una vez que tengas un dominio apuntando al servidor:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tudominio.com
```

---

## Reglas de operación

| Situación | Acción |
|---|---|
| Nueva versión del sistema | `git pull` + `sudo bash setup.sh` (o ZIP + setup.sh) |
| La base de datos `uocra.db` | **Nunca se toca, nunca se borra** |
| Cambio de clave SMTP | Admin → Config Mail |
| Agregar empresa nueva | Dashboard → Nueva empresa |
| Agregar usuario cliente | Admin → Usuarios → Nuevo |
| Asignar empresa a usuario | Al crear el usuario, seleccionar empresas |

---

## Documentación de estados de empleados

| Estado | Documentación requerida |
|---|---|
| I — Incorporación | Preocupacional, Solicitud ingreso, DNI, Alta temprana AFIP, EDET |
| E — Enfermedad | Certificado médico |
| V — Vacaciones | Notificación firmada |
| ART — Accidente | Informe ART, Parte médico, Recibo firmado |
| B — Baja | Telegrama, Liq. final, Últ. recibo, Art.80 LCT, ANSES PS6.2, ARDA, Certif. bancaria, Acuse recibo |
