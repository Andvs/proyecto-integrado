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
    
    # Usuarios
    path("usuarios/", v.usuarios_lista, name="usuarios_lista"),
    path("usuarios/nuevo/", v.usuarios_crear, name="usuarios_crear"),
    path("usuarios/<int:perfil_id>/editar/", v.usuarios_editar, name="usuarios_editar"),
    path("usuarios/<int:perfil_id>/toggle/", v.usuarios_toggle, name="usuarios_toggle"),
    
    # Jugadores
    path("jugadores/", v.jugadores_lista, name="jugadores_lista"),
    path("jugadores/<int:jugador_id>/editar/", v.jugadores_editar, name="jugadores_editar"),
    path("jugadores/<int:jugador_id>/toggle/", v.jugadores_toggle, name="jugadores_toggle"),
    
    # Entrenadores
    path("entrenadores/", v.entrenadores_lista, name="entrenadores_lista"),
    path("entrenadores/<int:perfil_id>/editar/", v.entrenadores_editar, name="entrenadores_editar"),
    path("entrenadores/<int:perfil_id>/toggle/", v.entrenadores_toggle, name="entrenadores_toggle"),
    
    # Equipos
    path("equipos/", v.equipos_lista, name="equipos_lista"),
    path("equipos/nuevo/", v.equipos_crear, name="equipos_crear"),
    path("equipos/<int:equipo_id>/editar/", v.equipos_editar, name="equipos_editar"),
    path("equipos/<int:equipo_id>/eliminar/", v.equipos_eliminar, name="equipos_eliminar"),
    path("equipos/<int:equipo_id>/detalle/", v.equipos_detalle, name="equipos_detalle"),
    
    # Actividades Deportivas
    path("actividades/", v.actividades_lista, name="actividades_lista"),
    path("actividades/nueva/", v.actividades_crear, name="actividades_crear"),
    path("actividades/<int:actividad_id>/editar/", v.actividades_editar, name="actividades_editar"),
    path('actividades/<int:actividad_id>/cancelar/', v.actividad_cancelar, name='actividad_cancelar'),
    path("actividades/<int:actividad_id>/detalle/", v.actividades_detalle, name="actividades_detalle"),
    
    # Asistencias
    path("asistencias/", v.asistencias_lista, name="asistencias_lista"),
    path("asistencias/registrar/", v.asistencias_registrar, name="asistencias_registrar"),
    path("asistencias/<int:asistencia_id>/editar/", v.asistencias_editar, name="asistencias_editar"),
    path("asistencias/<int:asistencia_id>/eliminar/", v.asistencias_eliminar, name="asistencias_eliminar"),
    path("asistencias/actividad/<int:actividad_id>/jugadores/", v.asistencias_jugadores_actividad, name="asistencias_jugadores_actividad"),
]