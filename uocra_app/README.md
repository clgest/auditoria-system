# UOCRA Sistema — MVP v1.0

Sistema web para gestión de novedades laborales UOCRA.
Reemplaza el sistema Google Sheets + Apps Script.

## Stack
- Python 3 + Flask
- SQLite (base de datos)
- Gunicorn (servidor WSGI)
- Nginx (proxy reverso)

## Estructura
```
uocra_app/
├── app.py          # Rutas Flask
├── models.py       # Base de datos y queries
├── requirements.txt
├── setup.sh        # Script de instalación Ubuntu
├── templates/      # HTML
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── nomina.html
│   ├── novedades.html
│   ├── novedad_form.html
│   ├── informe.html
│   ├── empleado_form.html
│   └── admin/
│       ├── log.html
│       └── usuarios.html
└── uocra.db        # Base de datos (se crea automáticamente)
```

## Instalación en Ubuntu

```bash
# 1. Subir archivos al servidor
scp -r uocra_app/ usuario@IP-SERVIDOR:/tmp/

# 2. En el servidor
cd /tmp/uocra_app
sudo bash setup.sh
```

## Desarrollo local

```bash
cd uocra_app
pip install -r requirements.txt
python app.py
# Abrir http://localhost:5000
```

## Usuarios iniciales
- `clgest@gmail.com` / `lescgo1` → rol estudio
- `clgestad@gmail.com` / `lescgo2` → rol estudio

## Roles
- **estudio**: acceso completo — todas las empresas, usuarios, log de auditoría
- **cliente**: acceso solo a sus empresas asignadas — novedades e informe

## Próximos módulos (MVP+)
- [ ] TXT Tiempsoft integrado
- [ ] Informe liquidación
- [ ] Conversor UOCRA integrado
- [ ] Multi-sindicato (SMATA, UPCN, etc.)
- [ ] Upload de documentación
- [ ] Email automático al confirmar período
- [ ] HTTPS con Let's Encrypt
