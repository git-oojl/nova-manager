from django.urls import path
from .views import *
from . import views


urlpatterns = [
    path('Menu/', Menu, name='Menu'),
    path('Dashboard/', Dashboard, name='Dashboard'),
    path('Empleado/', Empleado, name='Empleado'),
    path('Asistencia/', Asistencia, name='Asistencia'),
    path('Reportes/', Reportes, name='Reportes'),
    path('Horarios/', Horarios, name='Horarios'),
    path('Permisos/', Permisos, name='Permisos'),
    path('Contacto/', Contacto, name='Contacto'),

    # NEW:
    path('registro/', views.signup_employee, name='signup_employee'),
    
]
