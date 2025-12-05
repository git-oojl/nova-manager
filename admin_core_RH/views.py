from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.conf import settings
import logging

from django.contrib import messages
from django.contrib.auth import login
from .forms import ContactForm, EmployeeSignUpForm

from django.contrib.auth.decorators import login_required
from .decorators import admin_required

from .models import Empleado as EmpleadoModel

from django.db.models import Q
from django.http import HttpResponse
import json

from .models import Empleado as EmpleadoModel

import csv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def generar_reporte_csv(empleado_id, empleado_nombre, departamento, puesto,
                        fecha_inicio, fecha_fin, secciones, comentarios):
    response = HttpResponse(content_type="text/csv")
    filename = "reporte_empleado.csv"
    if empleado_id:
        filename = f"reporte_empleado_{empleado_id}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(["Nova Manager - Reporte de Empleado"])
    writer.writerow([])
    writer.writerow(["Empleado ID", empleado_id])
    writer.writerow(["Nombre", empleado_nombre])
    writer.writerow(["Departamento", departamento])
    writer.writerow(["Puesto", puesto])
    writer.writerow(["Periodo", f"{fecha_inicio} a {fecha_fin}"])
    writer.writerow([])
    writer.writerow(["Secciones incluidas"])
    for s in secciones:
        writer.writerow([s])
    writer.writerow([])
    writer.writerow(["Comentarios"])
    writer.writerow([comentarios])
    return response


def generar_reporte_pdf(empleado_id, empleado_nombre, departamento, puesto,
                        fecha_inicio, fecha_fin, secciones, comentarios):
    response = HttpResponse(content_type="application/pdf")
    filename = "reporte_empleado.pdf"
    if empleado_id:
        filename = f"reporte_empleado_{empleado_id}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    p = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    y = height - 50
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, y, "Reporte de Empleado - Nova Manager")
    y -= 30

    p.setFont("Helvetica", 11)
    lines = [
        f"Empleado ID: {empleado_id}",
        f"Nombre: {empleado_nombre}",
        f"Departamento: {departamento}",
        f"Puesto: {puesto}",
        f"Periodo: {fecha_inicio} a {fecha_fin}",
        "",
        "Secciones incluidas:",
    ]

    for line in lines:
        p.drawString(50, y, line)
        y -= 18

    # secciones
    for s in secciones:
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 11)
        p.drawString(70, y, f"- {s}")
        y -= 16

    # comentarios (si hay)
    if comentarios:
        import textwrap

        if y < 70:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 11)
        p.drawString(50, y, "Comentarios:")
        y -= 18

        for line in textwrap.wrap(comentarios, 90):
            if y < 50:
                p.showPage()
                y = height - 50
                p.setFont("Helvetica", 11)
            p.drawString(70, y, line)
            y -= 16

    p.showPage()
    p.save()
    return response

# Create your views here.
# Anyone logged in can see Menu
@login_required
def Menu(request):
    return render(request, 'Menu.html')

@login_required
def Dashboard(request):
    return render(request, 'Dashboard.html')

# Admin-only: Empleado, Reportes, Horarios, Permisos
@login_required
@admin_required(redirect_to='Menu')
def Empleado(request):
    empleado_seleccionado = None
    mensaje = None
    error = None

    # --- Export quick action: /Empleado/?export=json ---
    if request.method == "GET" and request.GET.get("export") == "json":
        data = list(
            EmpleadoModel.objects.values(
                "id", "nombre", "apellido", "email", "telefono", "puesto", "estado"
            )
        )
        response = HttpResponse(
            json.dumps(data, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
        response["Content-Disposition"] = 'attachment; filename="empleados.json"'
        return response

    # --- Handle form actions (POST) ---
    if request.method == "POST":
        action = request.POST.get("action")
        form_id = (request.POST.get("id") or "").strip()
        nombre_full = (request.POST.get("nombre") or "").strip()
        departamento = (request.POST.get("departamento") or "").strip()  # de momento no se usa
        puesto = (request.POST.get("puesto") or "").strip()
        estatus = (request.POST.get("estatus") or "").strip()
        empleado_pk = (request.POST.get("empleado_pk") or "").strip()

        empleado_qs = EmpleadoModel.objects.all()

        # Buscar por ID o nombre
        if form_id:
            if form_id.isdigit():
                empleado_qs = empleado_qs.filter(id=int(form_id))
            else:
                # Permite cosas tipo EMP001 o usuario
                digits = "".join(ch for ch in form_id if ch.isdigit())
                q = Q(usuario__username__iexact=form_id)
                if digits.isdigit():
                    q |= Q(id=int(digits))
                empleado_qs = empleado_qs.filter(q)
        elif nombre_full:
            partes = nombre_full.split()
            q = Q()
            for p in partes:
                q |= Q(nombre__icontains=p) | Q(apellido__icontains=p)
            empleado_qs = empleado_qs.filter(q)

        # --- Buscar ---
        if action == "buscar":
            empleado_seleccionado = empleado_qs.first()
            if empleado_seleccionado:
                mensaje = "Empleado encontrado."
            else:
                error = "No se encontró ningún empleado con esos datos."

        # --- Agregar / Actualizar (realmente editar) ---
        elif action in ("agregar", "actualizar"):
            # Sólo editamos empleados existentes
            if empleado_pk:
                try:
                    empleado_seleccionado = EmpleadoModel.objects.get(pk=int(empleado_pk))
                except (EmpleadoModel.DoesNotExist, ValueError):
                    empleado_seleccionado = None
            if empleado_seleccionado is None:
                empleado_seleccionado = empleado_qs.first()

            if empleado_seleccionado is None:
                error = "Primero busca un empleado para poder actualizar sus datos."
            else:
                if puesto:
                    empleado_seleccionado.puesto = puesto
                # Estatus simple: activo = True, todo lo demás = False
                if estatus:
                    if estatus == "activo":
                        empleado_seleccionado.estado = True
                    else:
                        empleado_seleccionado.estado = False
                empleado_seleccionado.save()
                mensaje = "Datos del empleado actualizados correctamente."

        # --- Eliminar (baja lógica) ---
        elif action == "eliminar":
            if empleado_pk:
                try:
                    empleado_seleccionado = EmpleadoModel.objects.get(pk=int(empleado_pk))
                except (EmpleadoModel.DoesNotExist, ValueError):
                    empleado_seleccionado = None
            if empleado_seleccionado is None:
                empleado_seleccionado = empleado_qs.first()
            if empleado_seleccionado is None:
                error = "No se encontró el empleado a eliminar."
            else:
                empleado_seleccionado.estado = False
                empleado_seleccionado.save()
                mensaje = "Empleado marcado como inactivo."

    # --- Datos para estadísticas y tabla ---
    empleados_qs = EmpleadoModel.objects.select_related("usuario").all().order_by("nombre", "apellido")
    total_empleados = empleados_qs.count()
    empleados_activos = empleados_qs.filter(estado=True).count()
    departamentos_count = (
        empleados_qs.exclude(puesto="")
        .values_list("puesto", flat=True)
        .distinct()
        .count()
    )

    estatus_actual = None
    if empleado_seleccionado is not None:
        estatus_actual = "activo" if empleado_seleccionado.estado else "inactivo"

    context = {
        "empleados": empleados_qs,
        "total_empleados": total_empleados,
        "empleados_activos": empleados_activos,
        "departamentos_count": departamentos_count,
        "empleado_seleccionado": empleado_seleccionado,
        "estatus_actual": estatus_actual,
        "mensaje": mensaje,
        "error": error,
    }
    return render(request, "Empleado.html", context)

@login_required
def Asistencia(request):
    return render(request, 'Asistencia.html')

@login_required
@admin_required(redirect_to='Menu')
def Reportes(request):
    # POST => generate file (PDF or CSV)
    if request.method == "POST":
        empleado_id = (request.POST.get("empleado-id") or "").strip()
        empleado_nombre = (request.POST.get("empleado-nombre") or "").strip()
        departamento = (request.POST.get("departamento") or "").strip()
        puesto = (request.POST.get("puesto") or "").strip()
        fecha_inicio = (request.POST.get("fecha-inicio") or "").strip()
        fecha_fin = (request.POST.get("fecha-fin") or "").strip()
        comentarios = (request.POST.get("notas") or "").strip()
        formato = (request.POST.get("formato") or "pdf").lower()

        empleado = None
        if empleado_id:
            try:
                empleado = EmpleadoModel.objects.get(pk=int(empleado_id))
            except (ValueError, EmpleadoModel.DoesNotExist):
                empleado = None

        # si encontramos al empleado en BD, completamos datos faltantes
        if empleado:
            if not empleado_nombre:
                empleado_nombre = f"{empleado.nombre} {empleado.apellido}".strip()
            if not puesto:
                puesto = empleado.puesto or ""

        # secciones seleccionadas
        secciones = []
        if "asistencia" in request.POST:
            secciones.append("Registro de asistencia")
        if "puntualidad" in request.POST:
            secciones.append("Puntualidad")
        if "horarios" in request.POST:
            secciones.append("Horarios asignados")
        if "faltas" in request.POST:
            secciones.append("Faltas y retardos")
        if "vacaciones" in request.POST:
            secciones.append("Vacaciones y permisos")
        if "evaluacion" in request.POST:
            secciones.append("Evaluación de desempeño")
        if "incidencias" in request.POST:
            secciones.append("Incidencias")
        if "horas-extra" in request.POST:
            secciones.append("Horas extra")

        if formato == "csv":
            return generar_reporte_csv(
                empleado_id,
                empleado_nombre,
                departamento,
                puesto,
                fecha_inicio,
                fecha_fin,
                secciones,
                comentarios,
            )
        else:
            # default: PDF
            return generar_reporte_pdf(
                empleado_id,
                empleado_nombre,
                departamento,
                puesto,
                fecha_inicio,
                fecha_fin,
                secciones,
                comentarios,
            )

    # GET => mostrar formulario con prefill desde Empleado o búsqueda local
    empleado_id = (request.GET.get("empleado_id") or "").strip()
    empleado_nombre = (request.GET.get("empleado_nombre") or "").strip()
    departamento = (request.GET.get("departamento") or "").strip()
    puesto = (request.GET.get("puesto") or "").strip()

    # si llega sólo el ID, intentamos resolver nombre/puesto desde BD
    if empleado_id:
        try:
            emp = EmpleadoModel.objects.get(pk=int(empleado_id))
            if not empleado_nombre:
                empleado_nombre = f"{emp.nombre} {emp.apellido}".strip()
            if not puesto:
                puesto = emp.puesto or ""
        except (ValueError, EmpleadoModel.DoesNotExist):
            pass

    context = {
        "empleado_id_prefill": empleado_id,
        "empleado_nombre_prefill": empleado_nombre,
        "empleado_departamento_prefill": departamento,
        "empleado_puesto_prefill": puesto,
    }
    return render(request, "Reportes.html", context)

@login_required
@admin_required(redirect_to='Menu')
def Permisos(request):
    return render(request, 'Permisos.html')

@login_required
@admin_required(redirect_to='Menu')
def Horarios(request):
    return render(request, 'Horarios.html')

from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from .forms import ContactForm
# later we'll also import models here (Empleado, etc.) when we add CRUD
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def signup_employee(request):
    if request.method == "POST":
        form = EmployeeSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Is the creator an admin (using the Empleado page)?
            is_admin_creator = (
                request.user.is_authenticated
                and (request.user.is_staff or request.user.is_superuser)
            )

            if is_admin_creator:
                # Keep the admin logged in, just create the employee
                messages.success(
                    request,
                    f"Empleado '{user.get_full_name() or user.username}' creado correctamente. "
                    "Ahora puedes completar su información en el módulo Empleado."
                )
                return redirect("Empleado")
            else:
                # Normal self-registration: log in the new employee
                login(request, user)
                messages.success(
                    request,
                    "Cuenta de empleado creada correctamente. ¡Bienvenido a Nova Manager!"
                )
                return redirect("Menu")
    else:
        # Prefill from GET ?nombre=...
        initial = {}
        full_name = (request.GET.get("nombre") or "").strip()
        if full_name:
            partes = full_name.split()
            if partes:
                initial["first_name"] = partes[0]
            if len(partes) > 1:
                initial["last_name"] = " ".join(partes[1:])
        form = EmployeeSignUpForm(initial=initial)

    return render(request, 'registration/signup.html', {"form": form})

def Contacto(request):
    enviado = False
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data['nombre']
            correo = form.cleaned_data['correo']
            asunto = form.cleaned_data['asunto']
            mensaje = form.cleaned_data['mensaje']

            # Construir el cuerpo del correo
            cuerpo = f"Nombre: {nombre}\nCorreo: {correo}\n\nMensaje:\n{mensaje}"

            email = EmailMessage(
                subject=f"[Contacto] {asunto}",
                body=cuerpo,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.EMAIL_HOST_USER],  # destinatario: cuenta del RH
                reply_to=[correo],
            )

            try:
                email.send(fail_silently=False)
                enviado = True
                # opcional: redirect('contacto_exito')
            except Exception as e:
                logger.exception("Error al enviar correo: %s", e)
                form.add_error(None, "Ocurrió un error al enviar el correo. Intenta de nuevo más tarde.")

    else:
        form = ContactForm()

    return render(request, 'contacto.html', {'form': form, 'enviado': enviado})


