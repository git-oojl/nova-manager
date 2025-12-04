from django.db import models
from django.contrib.auth.models import User

class Empleado (models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15)
    puesto = models.CharField(max_length=100)
    dias_de_trabajo = models.CharField(max_length=100)
    estado = models.BooleanField(default=True)


class Registro (models.Model):
    Registro = models.ForeignKey(User, on_delete=models.CASCADE)
    Fecha = models.DateTimeField(auto_now_add=True)
    Datos_Extras = models.TextField(blank=True)

class Departamento (models.Model):
    Departamento = models.ForeignKey(User, on_delete=models.CASCADE)
    Nombre = models.CharField(max_length=100)

class Usuario (models.Model):
    Usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    Nombre = models.CharField(max_length=100)
    Rol = models.CharField(max_length=100)