*Descarga (.zip) o clona

*Extrae a su propio folder (nova-manager)

*Abrir PowerShell dentro de ese folder (cd)

**Si no te permite ejecutarlo: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

*Crear ambiente virtual: py -m venv .venv

*Activar ambiente: .\.venv\Scripts\Activate.ps1

*INSTALAR DEPENDENCIAS: pip install -r requirements.txt

*Crear base de datos limpia: python manage.py migrate

*Crear superuser: python manage.py createsuperuser

*Ejecutar: python manage.py runserver

- Crear admins en: http://127.0.0.1:8000/admin/ (Tienen que ser staff)

- Crear empleados dentro de la interfaz (login) o tambien desde /admin/ (No tienen privilegios de staff)

Accesos:

- Admins (staff): Empleado, Asistencia, Horarios, Reportes, Permisos, Contacto

- Empleados normales (no staff): Asistencia, Contacto

