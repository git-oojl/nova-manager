from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Empleado

class ContactForm(forms.Form):
    nombre = forms.CharField(max_length=100, label="Nombre")
    correo = forms.EmailField(label="Correo")
    asunto = forms.CharField(max_length=150, label="Asunto")
    mensaje = forms.CharField(widget=forms.Textarea, label="Mensaje")

class EmployeeSignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, label="Nombre")
    last_name = forms.CharField(max_length=30, label="Apellidos")
    email = forms.EmailField(label="Correo electrónico")
    telefono = forms.CharField(max_length=15, label="Teléfono", required=False)

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"]
        # If your Empleado model doesn't have an email field, replace this check
        # with User.objects.filter(email=email).exists() instead
        if Empleado.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe un empleado con ese correo.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        # ensure this account is a regular employee
        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()
            # Create the Empleado record with minimal fields
            Empleado.objects.create(
                usuario=user,
                nombre=user.first_name or "",
                apellido=user.last_name or "",
                email=user.email or "",
                telefono=self.cleaned_data.get("telefono", ""),
                # puesto and dias_de_trabajo are intentionally left empty;
                # admins can fill them later from the Empleado page / Django admin.
                estado=True,
            )
        return user