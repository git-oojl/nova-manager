from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='Menu', permanent=False), name='home'),
    path('admin/', admin.site.urls),
    path('', include('admin_core_RH.urls')),
    path('accounts/', include('django.contrib.auth.urls')),  
]
