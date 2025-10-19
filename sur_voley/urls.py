from django.contrib import admin
from django.urls import path
# Importamos las vistas desde la app 'core' con el alias 'v'
from app import views as v

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rutas de la aplicación
    path('', v.index, name="index"),
    path('login/', v.login, name='login'),
    path('dashboard/', v.dashboard, name="dashboard"),
    path('formulario/', v.formulario, name="formulario"),
    path("visualizacion/", v.visualizacion, name="visualizacion"),
    
    # Nueva ruta para editar un usuario específico por su ID
    path('usuarios/editar/<int:usuario_id>/', v.editar_usuario, name='editar_usuario'),
    path('desabilitar/<int:user_id>/', v.desabilitar_usuario, name='desabilitar_usuario'),

# Jugadores
path('jugadores/', v.visualizacion_jugadores, name='visualizacion_jugadores'),
path('jugadores/registrar/', v.formulario_jugadores, name='formulario_jugadores'),  
path('jugadores/editar/<int:jugador_id>/', v.editar_jugador, name='editar_jugador'),
path('jugadores/habilitar/<int:jugador_id>/', v.habilitar_jugador, name='habilitar_jugador'),
path('jugadores/deshabilitar/<int:jugador_id>/', v.deshabilitar_jugador, name='deshabilitar_jugador'),


]