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

# modelo simple de asistencia
class Asistencia(models.Model):
    TIPO_CHOICES = [
        ("entrada", "Entrada"),
        ("salida", "Salida"),
    ]

    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.CASCADE,
        related_name="asistencias",
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    comentario = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-fecha_hora"]

    def __str__(self):
        return f"{self.empleado.nombre} {self.empleado.apellido} - {self.get_tipo_display()} {self.fecha_hora:%Y-%m-%d %H:%M}"