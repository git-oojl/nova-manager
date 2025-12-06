from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

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

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="asistencias")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    fecha_hora = models.DateTimeField()
    es_retardo = models.BooleanField(default=False)
    es_falta = models.BooleanField(default=False)
    comentario = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-fecha_hora"]

class Horario(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="horarios")
    nombre_turno = models.CharField(max_length=100)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre_turno} {self.hora_inicio}–{self.hora_fin}"

class Permiso(models.Model):
    TIPO_CHOICES = [
        ("vacaciones", "Vacaciones"),
        ("personal", "Permiso personal"),
        ("medico", "Permiso médico"),
        ("familiar", "Asunto familiar"),
        ("estudio", "Permiso de estudio"),
        ("maternidad", "Maternidad/Paternidad"),
        ("otro", "Otro"),
    ]

    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
    ]

    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE, related_name="permisos")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    motivo = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="pendiente")
    fecha_solicitud = models.DateField(default=timezone.localdate)
    aprobado_por = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-fecha_solicitud", "-fecha_inicio"]

    @property
    def duracion_dias(self) -> int:
        # +1 para incluir ambos días
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def __str__(self):
        return f"{self.empleado.nombre} {self.empleado.apellido} - {self.get_tipo_display()} ({self.get_estado_display()})"
    
class Notificacion(models.Model):
    PRIORIDAD_CHOICES = [
        ("normal", "Normal"),
        ("alta", "Alta"),
        ("urgente", "Urgente"),
    ]

    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default="normal")
    asunto = models.CharField(max_length=255)
    mensaje = models.TextField()
    remitente_nombre = models.CharField(max_length=255, blank=True)
    remitente_email = models.EmailField(blank=True)
    destinatarios = models.TextField(blank=True)  # ej. "todos,rh,ventas"
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return f"{self.asunto} ({self.prioridad})"