from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.conf import settings
import logging

from django.contrib import messages
from django.contrib.auth import login
from .forms import ContactForm, EmployeeSignUpForm

from django.contrib.auth.decorators import login_required
from .decorators import admin_required

from .models import Empleado as EmpleadoModel, Permiso, Horario, Asistencia

from django.db.models import Q
from django.http import HttpResponse
import json

import csv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from datetime import datetime
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import render, redirect

logger = logging.getLogger(__name__)

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

        if empleado:
            if not empleado_nombre:
                empleado_nombre = f"{empleado.nombre} {empleado.apellido}".strip()
            if not puesto:
                puesto = empleado.puesto or ""

        # parsear fechas a date
        fi_date = ff_date = None
        if fecha_inicio and fecha_fin:
            try:
                fi_date = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                ff_date = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            except ValueError:
                fi_date = ff_date = None

        secciones = []
        if "asistencia" in request.POST:
            secciones.append("Registro de asistencia (fuente: módulo Asistencia)")
        if "puntualidad" in request.POST:
            secciones.append("Puntualidad (fuente: Asistencia + Horarios)")
        if "horarios" in request.POST:
            secciones.append("Horarios asignados (fuente: módulo Horarios)")
        if "faltas" in request.POST:
            secciones.append("Faltas y retardos (fuente: módulo Asistencia)")
        if "vacaciones" in request.POST:
            secciones.append("Vacaciones y permisos (fuente: módulo Permisos)")

        # permisos aprobados del empleado en el periodo
        permisos_periodo = []
        if "vacaciones" in request.POST and empleado and fi_date and ff_date:
            permisos_periodo = list(
                Permiso.objects.filter(
                    empleado=empleado,
                    estado="aprobado",
                    fecha_inicio__lte=ff_date,
                    fecha_fin__gte=fi_date,
                ).order_by("fecha_inicio")
            )

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
                permisos_periodo,
            )
        else:
            return generar_reporte_pdf(
                empleado_id,
                empleado_nombre,
                departamento,
                puesto,
                fecha_inicio,
                fecha_fin,
                secciones,
                comentarios,
                permisos_periodo,
            )

    # GET => mostrar formulario (prefill desde Empleado / búsqueda)
    empleado_id = (request.GET.get("empleado_id") or "").strip()
    empleado_nombre = (request.GET.get("empleado_nombre") or "").strip()
    departamento = (request.GET.get("departamento") or "").strip()
    puesto = (request.GET.get("puesto") or "").strip()

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


def generar_reporte_csv(empleado_id, empleado_nombre, departamento, puesto,
                        fecha_inicio, fecha_fin, secciones, comentarios, permisos):
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

    if permisos:
        writer.writerow([])
        writer.writerow(["Vacaciones y permisos aprobados en el periodo"])
        writer.writerow(["Tipo", "Inicio", "Fin", "Días", "Estado", "Aprobado por"])
        for p in permisos:
            writer.writerow([
                p.get_tipo_display(),
                p.fecha_inicio.strftime("%d/%m/%Y"),
                p.fecha_fin.strftime("%d/%m/%Y"),
                p.duracion_dias,
                p.get_estado_display(),
                p.aprobado_por,
            ])

    writer.writerow([])
    writer.writerow(["Comentarios"])
    writer.writerow([comentarios])
    return response


def generar_reporte_pdf(empleado_id, empleado_nombre, departamento, puesto,
                        fecha_inicio, fecha_fin, secciones, comentarios, permisos):
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

    for s in secciones:
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 11)
        p.drawString(70, y, f"- {s}")
        y -= 16

    if permisos:
        if y < 70:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 11)
        p.drawString(50, y, "Vacaciones y permisos aprobados en el periodo:")
        y -= 18
        for perm in permisos:
            text = (
                f"{perm.get_tipo_display()} "
                f"del {perm.fecha_inicio.strftime('%d/%m/%Y')} "
                f"al {perm.fecha_fin.strftime('%d/%m/%Y')} "
                f"({perm.duracion_dias} días) "
                f"- Estado: {perm.get_estado_display()}, "
                f"Aprobado por: {perm.aprobado_por or 'N/D'}"
            )
            if y < 50:
                p.showPage()
                y = height - 50
                p.setFont("Helvetica", 11)
            p.drawString(70, y, text)
            y -= 16

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

@login_required
@admin_required(redirect_to='Menu')
def Permisos(request):
    today = timezone.localdate()
    mensaje = None
    error = None
    permiso_edit = None

    if request.method == "POST":
        accion = request.POST.get("accion")
        if accion in ("crear", "actualizar"):
            permiso_id = request.POST.get("permiso_id")
            emp_id = (request.POST.get("empleado-id") or "").strip()
            tipo = request.POST.get("tipo-permiso") or ""
            f_inicio = request.POST.get("fecha-inicio") or ""
            f_fin = request.POST.get("fecha-fin") or ""
            motivo = (request.POST.get("motivo") or "").strip()

            if not emp_id or not tipo or not f_inicio or not f_fin or not motivo:
                error = "Por favor completa todos los campos obligatorios."
            else:
                try:
                    empleado = EmpleadoModel.objects.get(pk=int(emp_id))
                except (ValueError, EmpleadoModel.DoesNotExist):
                    empleado = None

                if not empleado:
                    error = "No se encontró el empleado indicado."
                else:
                    try:
                        fi = datetime.strptime(f_inicio, "%Y-%m-%d").date()
                        ff = datetime.strptime(f_fin, "%Y-%m-%d").date()
                    except ValueError:
                        fi = ff = None

                    if not fi or not ff:
                        error = "Las fechas no son válidas."
                    else:
                        if accion == "crear":
                            Permiso.objects.create(
                                empleado=empleado,
                                tipo=tipo,
                                fecha_inicio=fi,
                                fecha_fin=ff,
                                motivo=motivo,
                            )
                            mensaje = "Solicitud de permiso registrada y pendiente de aprobación."
                        else:  # actualizar
                            try:
                                permiso = Permiso.objects.get(pk=int(permiso_id))
                                permiso.empleado = empleado
                                permiso.tipo = tipo
                                permiso.fecha_inicio = fi
                                permiso.fecha_fin = ff
                                permiso.motivo = motivo
                                permiso.save()
                                mensaje = "Permiso actualizado correctamente."
                            except (ValueError, Permiso.DoesNotExist):
                                error = "No se encontró el permiso a actualizar."

        elif accion in ("aprobar", "rechazar"):
            permiso_id = request.POST.get("permiso_id")
            try:
                permiso = Permiso.objects.get(pk=int(permiso_id))
                permiso.estado = "aprobado" if accion == "aprobar" else "rechazado"
                if accion == "aprobar":
                    permiso.aprobado_por = request.user.get_full_name() or request.user.username
                permiso.save()
                mensaje = "Permiso actualizado correctamente."
            except (ValueError, Permiso.DoesNotExist):
                error = "No se encontró el permiso seleccionado."

    empleado_id = (request.GET.get("empleado_id") or "").strip()
    editar_id = request.GET.get("editar")

    empleado_prefill = None
    if empleado_id:
        try:
            empleado_prefill = EmpleadoModel.objects.get(pk=int(empleado_id))
        except (ValueError, EmpleadoModel.DoesNotExist):
            empleado_prefill = None

    if editar_id:
        try:
            permiso_edit = Permiso.objects.select_related("empleado").get(pk=int(editar_id))
        except (ValueError, Permiso.DoesNotExist):
            permiso_edit = None

    # estadísticas
    permisos_qs = Permiso.objects.select_related("empleado")
    permisos_activos = permisos_qs.filter(
        estado="aprobado",
        fecha_inicio__lte=today,
        fecha_fin__gte=today,
    ).count()
    permisos_pendientes = permisos_qs.filter(estado="pendiente").count()
    permisos_aprobados_mes = permisos_qs.filter(
        estado="aprobado",
        fecha_solicitud__year=today.year,
        fecha_solicitud__month=today.month,
    ).count()
    vacaciones_hoy = permisos_qs.filter(
        estado="aprobado",
        tipo="vacaciones",
        fecha_inicio__lte=today,
        fecha_fin__gte=today,
    ).count()

    recientes = permisos_qs.order_by("-fecha_solicitud", "-fecha_inicio")[:10]

    empleado_id_prefill = ""
    empleado_nombre_prefill = ""
    if permiso_edit:
        empleado_id_prefill = permiso_edit.empleado.id
        empleado_nombre_prefill = f"{permiso_edit.empleado.nombre} {permiso_edit.empleado.apellido}".strip()
    elif empleado_prefill:
        empleado_id_prefill = empleado_prefill.id
        empleado_nombre_prefill = f"{empleado_prefill.nombre} {empleado_prefill.apellido}".strip()

    context = {
        "empleado_id_prefill": empleado_id_prefill,
        "empleado_nombre_prefill": empleado_nombre_prefill,
        "tipo_permiso_prefill": permiso_edit.tipo if permiso_edit else "",
        "fecha_inicio_prefill": permiso_edit.fecha_inicio.strftime("%Y-%m-%d") if permiso_edit else "",
        "fecha_fin_prefill": permiso_edit.fecha_fin.strftime("%Y-%m-%d") if permiso_edit else "",
        "motivo_prefill": permiso_edit.motivo if permiso_edit else "",
        "permiso_edit": permiso_edit,
        "permisos_recientes": recientes,
        "permisos_activos": permisos_activos,
        "permisos_pendientes": permisos_pendientes,
        "permisos_aprobados_mes": permisos_aprobados_mes,
        "vacaciones_hoy": vacaciones_hoy,
        "mensaje": mensaje,
        "error": error,
    }
    return render(request, "Permisos.html", context)

from datetime import datetime
from django.db.models import Q

@login_required
@admin_required(redirect_to='Menu')
def Horarios(request):
    mensaje = None
    error = None
    empleado = None

    # --------- POST: asignar / actualizar horario ----------
    if request.method == "POST":
        emp_id = (request.POST.get("id") or "").strip()
        turno = (request.POST.get("turno") or "").strip()
        entrada = (request.POST.get("entrada") or "").strip()
        salida = (request.POST.get("salida") or "").strip()

        if not emp_id or not turno or not entrada or not salida:
            error = "Por favor completa todos los campos obligatorios."
        else:
            try:
                empleado = EmpleadoModel.objects.get(pk=int(emp_id))
            except (ValueError, EmpleadoModel.DoesNotExist):
                error = "No se encontró el empleado indicado."

        if empleado and not error:
            try:
                hora_inicio = datetime.strptime(entrada, "%H:%M").time()
                hora_fin = datetime.strptime(salida, "%H:%M").time()
            except ValueError:
                hora_inicio = hora_fin = None

            if not hora_inicio or not hora_fin:
                error = "Las horas no tienen un formato válido (HH:MM)."
            else:
                nombre_turno_map = {
                    "matutino": "Matutino",
                    "vespertino": "Vespertino",
                    "nocturno": "Nocturno",
                    "mixto": "Mixto",
                    "personalizado": "Personalizado",
                }
                nombre_turno = nombre_turno_map.get(turno, turno)

                # opcional: desactivar horarios anteriores del empleado
                Horario.objects.filter(empleado=empleado, activo=True).update(activo=False)

                Horario.objects.create(
                    empleado=empleado,
                    nombre_turno=nombre_turno,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    activo=True,
                )
                mensaje = "Horario asignado correctamente."

        # valores para rellenar el formulario después del POST
        empleado_id_prefill = emp_id
        empleado_nombre_prefill = ""
        if empleado:
            empleado_nombre_prefill = f"{empleado.nombre} {empleado.apellido}".strip()

    else:
        # --------- GET simple: pre-relleno por ID ----------
        empleado_id_prefill = (request.GET.get("empleado_id") or "").strip()
        empleado_nombre_prefill = ""
        if empleado_id_prefill:
            try:
                emp = EmpleadoModel.objects.get(pk=int(empleado_id_prefill))
                empleado_nombre_prefill = f"{emp.nombre} {emp.apellido}".strip()
            except (ValueError, EmpleadoModel.DoesNotExist):
                empleado_nombre_prefill = ""

    # --------- filtros para la tabla ----------
    busqueda_tipo = (request.GET.get("busqueda_tipo") or "").strip()
    busqueda_valor = (request.GET.get("busqueda_valor") or "").strip()

    horarios_qs = Horario.objects.select_related("empleado").filter(activo=True)

    if busqueda_valor:
        if busqueda_tipo == "id":
            try:
                horarios_qs = horarios_qs.filter(empleado__id=int(busqueda_valor))
            except ValueError:
                horarios_qs = horarios_qs.none()
        elif busqueda_tipo == "nombre":
            horarios_qs = horarios_qs.filter(
                Q(empleado__nombre__icontains=busqueda_valor) |
                Q(empleado__apellido__icontains=busqueda_valor)
            )
        elif busqueda_tipo == "horario":
            horarios_qs = horarios_qs.filter(nombre_turno__icontains=busqueda_valor)

    horarios = horarios_qs.order_by("empleado__nombre", "empleado__apellido")

    # --------- estadísticas superiores ----------
    total_empleados = EmpleadoModel.objects.count()
    empleados_con_horario = (
        Horario.objects.filter(activo=True).values("empleado").distinct().count()
    )
    turnos_activos = (
        Horario.objects.filter(activo=True).values("nombre_turno").distinct().count()
    )
    cobertura_porcentaje = int(empleados_con_horario * 100 / total_empleados) if total_empleados else 0

    context = {
        "horarios": horarios,
        "empleados_con_horario": empleados_con_horario,
        "turnos_activos": turnos_activos,
        "cobertura_porcentaje": cobertura_porcentaje,
        "mensaje": mensaje,
        "error": error,
        "empleado_id_prefill": empleado_id_prefill,
        "empleado_nombre_prefill": empleado_nombre_prefill,
        "busqueda_tipo": busqueda_tipo,
        "busqueda_valor": busqueda_valor,
    }
    return render(request, "Horarios.html", context)

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

from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.conf import settings
import logging

from django.contrib import messages
from django.contrib.auth import login
from .forms import ContactForm, EmployeeSignUpForm

from django.contrib.auth.decorators import login_required
from .decorators import admin_required

from .models import Empleado as EmpleadoModel, Permiso

from django.db.models import Q
from django.http import HttpResponse
import json

import csv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from datetime import datetime
from django.utils import timezone
from django.http import HttpResponse

import logging

logger = logging.getLogger(__name__)

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

        if empleado:
            if not empleado_nombre:
                empleado_nombre = f"{empleado.nombre} {empleado.apellido}".strip()
            if not puesto:
                puesto = empleado.puesto or ""

        # parsear fechas a date
        fi_date = ff_date = None
        if fecha_inicio and fecha_fin:
            try:
                fi_date = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                ff_date = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            except ValueError:
                fi_date = ff_date = None

        secciones = []
        if "asistencia" in request.POST:
            secciones.append("Registro de asistencia (fuente: módulo Asistencia)")
        if "puntualidad" in request.POST:
            secciones.append("Puntualidad (fuente: Asistencia + Horarios)")
        if "horarios" in request.POST:
            secciones.append("Horarios asignados (fuente: módulo Horarios)")
        if "faltas" in request.POST:
            secciones.append("Faltas y retardos (fuente: módulo Asistencia)")
        if "vacaciones" in request.POST:
            secciones.append("Vacaciones y permisos (fuente: módulo Permisos)")

        # permisos aprobados del empleado en el periodo
        permisos_periodo = []
        if "vacaciones" in request.POST and empleado and fi_date and ff_date:
            permisos_periodo = list(
                Permiso.objects.filter(
                    empleado=empleado,
                    estado="aprobado",
                    fecha_inicio__lte=ff_date,
                    fecha_fin__gte=fi_date,
                ).order_by("fecha_inicio")
            )

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
                permisos_periodo,
            )
        else:
            return generar_reporte_pdf(
                empleado_id,
                empleado_nombre,
                departamento,
                puesto,
                fecha_inicio,
                fecha_fin,
                secciones,
                comentarios,
                permisos_periodo,
            )

    # GET => mostrar formulario (prefill desde Empleado / búsqueda)
    empleado_id = (request.GET.get("empleado_id") or "").strip()
    empleado_nombre = (request.GET.get("empleado_nombre") or "").strip()
    departamento = (request.GET.get("departamento") or "").strip()
    puesto = (request.GET.get("puesto") or "").strip()

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


def generar_reporte_csv(empleado_id, empleado_nombre, departamento, puesto,
                        fecha_inicio, fecha_fin, secciones, comentarios, permisos):
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

    if permisos:
        writer.writerow([])
        writer.writerow(["Vacaciones y permisos aprobados en el periodo"])
        writer.writerow(["Tipo", "Inicio", "Fin", "Días", "Estado", "Aprobado por"])
        for p in permisos:
            writer.writerow([
                p.get_tipo_display(),
                p.fecha_inicio.strftime("%d/%m/%Y"),
                p.fecha_fin.strftime("%d/%m/%Y"),
                p.duracion_dias,
                p.get_estado_display(),
                p.aprobado_por,
            ])

    writer.writerow([])
    writer.writerow(["Comentarios"])
    writer.writerow([comentarios])
    return response


def generar_reporte_pdf(empleado_id, empleado_nombre, departamento, puesto,
                        fecha_inicio, fecha_fin, secciones, comentarios, permisos):
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

    for s in secciones:
        if y < 50:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 11)
        p.drawString(70, y, f"- {s}")
        y -= 16

    if permisos:
        if y < 70:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 11)
        p.drawString(50, y, "Vacaciones y permisos aprobados en el periodo:")
        y -= 18
        for perm in permisos:
            text = (
                f"{perm.get_tipo_display()} "
                f"del {perm.fecha_inicio.strftime('%d/%m/%Y')} "
                f"al {perm.fecha_fin.strftime('%d/%m/%Y')} "
                f"({perm.duracion_dias} días) "
                f"- Estado: {perm.get_estado_display()}, "
                f"Aprobado por: {perm.aprobado_por or 'N/D'}"
            )
            if y < 50:
                p.showPage()
                y = height - 50
                p.setFont("Helvetica", 11)
            p.drawString(70, y, text)
            y -= 16

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

@login_required
@admin_required(redirect_to='Menu')
def Permisos(request):
    today = timezone.localdate()
    mensaje = None
    error = None
    permiso_edit = None

    if request.method == "POST":
        accion = request.POST.get("accion")
        if accion in ("crear", "actualizar"):
            permiso_id = request.POST.get("permiso_id")
            emp_id = (request.POST.get("empleado-id") or "").strip()
            tipo = request.POST.get("tipo-permiso") or ""
            f_inicio = request.POST.get("fecha-inicio") or ""
            f_fin = request.POST.get("fecha-fin") or ""
            motivo = (request.POST.get("motivo") or "").strip()

            if not emp_id or not tipo or not f_inicio or not f_fin or not motivo:
                error = "Por favor completa todos los campos obligatorios."
            else:
                try:
                    empleado = EmpleadoModel.objects.get(pk=int(emp_id))
                except (ValueError, EmpleadoModel.DoesNotExist):
                    empleado = None

                if not empleado:
                    error = "No se encontró el empleado indicado."
                else:
                    try:
                        fi = datetime.strptime(f_inicio, "%Y-%m-%d").date()
                        ff = datetime.strptime(f_fin, "%Y-%m-%d").date()
                    except ValueError:
                        fi = ff = None

                    if not fi or not ff:
                        error = "Las fechas no son válidas."
                    else:
                        if accion == "crear":
                            Permiso.objects.create(
                                empleado=empleado,
                                tipo=tipo,
                                fecha_inicio=fi,
                                fecha_fin=ff,
                                motivo=motivo,
                            )
                            mensaje = "Solicitud de permiso registrada y pendiente de aprobación."
                        else:  # actualizar
                            try:
                                permiso = Permiso.objects.get(pk=int(permiso_id))
                                permiso.empleado = empleado
                                permiso.tipo = tipo
                                permiso.fecha_inicio = fi
                                permiso.fecha_fin = ff
                                permiso.motivo = motivo
                                permiso.save()
                                mensaje = "Permiso actualizado correctamente."
                            except (ValueError, Permiso.DoesNotExist):
                                error = "No se encontró el permiso a actualizar."

        elif accion in ("aprobar", "rechazar"):
            permiso_id = request.POST.get("permiso_id")
            try:
                permiso = Permiso.objects.get(pk=int(permiso_id))
                permiso.estado = "aprobado" if accion == "aprobar" else "rechazado"
                if accion == "aprobar":
                    permiso.aprobado_por = request.user.get_full_name() or request.user.username
                permiso.save()
                mensaje = "Permiso actualizado correctamente."
            except (ValueError, Permiso.DoesNotExist):
                error = "No se encontró el permiso seleccionado."

    empleado_id = (request.GET.get("empleado_id") or "").strip()
    editar_id = request.GET.get("editar")

    empleado_prefill = None
    if empleado_id:
        try:
            empleado_prefill = EmpleadoModel.objects.get(pk=int(empleado_id))
        except (ValueError, EmpleadoModel.DoesNotExist):
            empleado_prefill = None

    if editar_id:
        try:
            permiso_edit = Permiso.objects.select_related("empleado").get(pk=int(editar_id))
        except (ValueError, Permiso.DoesNotExist):
            permiso_edit = None

    # estadísticas
    permisos_qs = Permiso.objects.select_related("empleado")
    permisos_activos = permisos_qs.filter(
        estado="aprobado",
        fecha_inicio__lte=today,
        fecha_fin__gte=today,
    ).count()
    permisos_pendientes = permisos_qs.filter(estado="pendiente").count()
    permisos_aprobados_mes = permisos_qs.filter(
        estado="aprobado",
        fecha_solicitud__year=today.year,
        fecha_solicitud__month=today.month,
    ).count()
    vacaciones_hoy = permisos_qs.filter(
        estado="aprobado",
        tipo="vacaciones",
        fecha_inicio__lte=today,
        fecha_fin__gte=today,
    ).count()

    recientes = permisos_qs.order_by("-fecha_solicitud", "-fecha_inicio")[:10]

    empleado_id_prefill = ""
    empleado_nombre_prefill = ""
    if permiso_edit:
        empleado_id_prefill = permiso_edit.empleado.id
        empleado_nombre_prefill = f"{permiso_edit.empleado.nombre} {permiso_edit.empleado.apellido}".strip()
    elif empleado_prefill:
        empleado_id_prefill = empleado_prefill.id
        empleado_nombre_prefill = f"{empleado_prefill.nombre} {empleado_prefill.apellido}".strip()

    context = {
        "empleado_id_prefill": empleado_id_prefill,
        "empleado_nombre_prefill": empleado_nombre_prefill,
        "tipo_permiso_prefill": permiso_edit.tipo if permiso_edit else "",
        "fecha_inicio_prefill": permiso_edit.fecha_inicio.strftime("%Y-%m-%d") if permiso_edit else "",
        "fecha_fin_prefill": permiso_edit.fecha_fin.strftime("%Y-%m-%d") if permiso_edit else "",
        "motivo_prefill": permiso_edit.motivo if permiso_edit else "",
        "permiso_edit": permiso_edit,
        "permisos_recientes": recientes,
        "permisos_activos": permisos_activos,
        "permisos_pendientes": permisos_pendientes,
        "permisos_aprobados_mes": permisos_aprobados_mes,
        "vacaciones_hoy": vacaciones_hoy,
        "mensaje": mensaje,
        "error": error,
    }
    return render(request, "Permisos.html", context)

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

#####################################################################################################


