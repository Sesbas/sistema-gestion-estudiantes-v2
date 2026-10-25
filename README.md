# Sistema de Gestión de Estudiantes

Aplicación web con Flask, HTML, CSS y JavaScript, conectada a la base de datos de XAMPP. Incluye registro, inicio de sesión, roles, gestión de estudiantes, búsqueda, paginación, estadísticas y auditoría.

## Uso diario

1. Abre XAMPP e inicia **Apache** y **MySQL**.
2. Haz doble clic en **iniciar.bat** y deja la ventana abierta.
3. Abre [la aplicación](http://127.0.0.1:5000/).

Administrador de la práctica local: **admin** / **admin123**.

La base actual ya está configurada. Puedes consultarla en [phpMyAdmin](http://localhost/phpmyadmin/), seleccionando `universidad_db`. No necesitas importar el SQL cada vez que inicias.

Para detener Flask pulsa **Ctrl+C** en su ventana.

## Archivos principales

| Archivo o carpeta | Para qué sirve |
| --- | --- |
| `backend/app.py` | Inicia Flask y sirve la interfaz y la API |
| `backend/config.py` | Lee la configuración de conexión y JWT |
| `backend/db.py` | Conecta con la base y ejecuta consultas |
| `backend/models.py` | Valida los datos de los formularios |
| `backend/middleware.py` | Comprueba la sesión y los permisos |
| `backend/routes/auth.py` | Registro, login, logout y perfil |
| `backend/routes/estudiantes.py` | Gestión de estudiantes y estadísticas |
| `backend/universidad_db.sql` | Crea tablas, índices, vistas y auditoría en una instalación nueva |
| `frontend/index.html` | Pantalla de la aplicación |
| `frontend/css/styles.css` | Estilos de escritorio y móvil |
| `frontend/js/app.js` | Formularios y conexión con la API |
| `backend/tests/` | Pruebas de la API con datos temporales |
| `iniciar.bat` | Abre Flask en una ventana visible |

Los usuarios pueden crear, consultar y editar estudiantes. Solo el administrador puede eliminarlos. Las sesiones duran una hora y cerrar sesión revoca el token.

## Instalación en otro equipo

Necesitas Python 3.10 o superior y XAMPP con MySQL/MariaDB. La guía especifica MySQL 8; XAMPP en este equipo incluye MariaDB 10.4.

Desde la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Edita `backend/.env`: coloca la clave generada en `JWT_SECRET` y revisa las credenciales de XAMPP. No sobrescribas un `.env` que ya esté configurado.

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=universidad_db
```

En phpMyAdmin usa **Importar** y selecciona `backend/universidad_db.sql` para crear una base nueva. El script no migra automáticamente estructuras antiguas diferentes. Después crea el administrador:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend/app.py crear-admin
```

Ya puedes usar `iniciar.bat`. El proyecto puede permanecer en cualquier carpeta; no necesita estar dentro de `htdocs`.

## Pruebas opcionales

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Las pruebas usan SQLite temporal, sin modificar los datos de XAMPP. Cubren autenticación, permisos, validaciones, CRUD, búsqueda, paginación, estadísticas y entrega de la interfaz. La aplicación normal se conecta a MySQL/MariaDB.

## Si algo falla

- **No abre la aplicación:** revisa que la ventana de Flask siga abierta y usa el puerto 5000.
- **Error de base de datos:** inicia MySQL en XAMPP y comprueba `backend/.env`.
- **El puerto 5000 está ocupado:** cierra la otra instancia de Flask antes de volver a abrirla.
- **phpMyAdmin no abre:** inicia Apache y comprueba el puerto configurado en XAMPP.
- **Sesión expirada:** inicia sesión de nuevo.

## Respaldos

La carpeta `.backups/` conserva la copia de la base anterior a la migración, el proyecto Android original y las herramientas que ya no se necesitan para el uso diario. No forma parte de la aplicación y está excluida del control de versiones. Conserva la copia SQL si necesitas recuperar la base anterior.
