from django.contrib import admin
from django.urls import path

from app import views as v

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rutas de la aplicación
    path('', v.index, name="index"),
    path('login/', v.login_view, name='login'),
    path('dashboard/', v.dashboard, name="dashboard"),
    path("logout/", v.logout_view, name="logout"),
    path("usuarios/", v.usuarios_lista, name="usuarios_lista"),
    path("usuarios/nuevo/", v.usuarios_crear, name="usuarios_crear"),   # placeholder
    path("usuarios/<int:perfil_id>/editar/", v.usuarios_editar, name="usuarios_editar"),  # placeholder
    path("usuarios/<int:perfil_id>/toggle/", v.usuarios_toggle, name="usuarios_toggle"),
]