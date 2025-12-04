from django.shortcuts import render, redirect
from django.core.mail import EmailMessage
from django.conf import settings
import logging

from django.contrib import messages
from django.contrib.auth import login
from .forms import ContactForm, EmployeeSignUpForm

# admin_core_RH/views.py
from django.contrib.auth.decorators import login_required
from .decorators import admin_required

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
    return render(request, 'Empleado.html')

@login_required
def Asistencia(request):
    return render(request, 'Asistencia.html')

@login_required
@admin_required(redirect_to='Menu')
def Reportes(request):
    return render(request, 'Reportes.html')

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
            # Log the new employee in immediately
            login(request, user)
            messages.success(request, "Cuenta de empleado creada correctamente. ¡Bienvenido a Nova Manager!")
            return redirect('Menu')
    else:
        form = EmployeeSignUpForm()

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


