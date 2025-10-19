from django.contrib import admin
from .models import *
# Register your models here.
class RolAdmin(admin.ModelAdmin):
    list_display = ["nombre","descripcion"]
class PermisoAdmin(admin.ModelAdmin):
    list_display = ["nombre","descripcion"]
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ["nombre_usuario","activo","rol"]
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nombre","descripcion"]
class EntrenadorAdmin(admin.ModelAdmin):
    list_display = ["run","nombre","apellido","fecha_nacimiento","direccion","num_celular","correo","fecha_contratacion","activo","usuario"]
class EquipoAdmin(admin.ModelAdmin):
    list_display = ["nombre","descripcion","categoria","entrenador"]
class SocioAdmin(admin.ModelAdmin):
    list_display = ["run","nombre","apellido","fecha_nacimiento","direccion","num_celular","correo","fecha_ingreso","activo","usuario"]
class JugadorAdmin(admin.ModelAdmin):
    list_display = ["run","nombre","apellido","fecha_nacimiento","num_celular","correo","colegio","curso","fecha_ingreso","activo","equipo","usuario","socio"]
class EntrenamientoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'fecha_inicio', 'fecha_fin', 'lugar', 'descripcion']
class EncuentroDeportivoAdmin(admin.ModelAdmin):
    list_display = ["nombre","tipo","fecha_inicio","fecha_fin","lugar","descripcion"]
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ['fecha_hora_marcaje', 'jugador', 'entrenador', 'actividad_deportiva', 'evento_deportivo', 'marcaje_por','anotaciones']
class CargoAdmin(admin.ModelAdmin):
    list_display = ["nombre","descripcion"]
class EquipoAdministrativoAdmin(admin.ModelAdmin):
    list_display = ["run","nombre","apellido","fecha_nacimiento","direccion","num_celular","correo","fecha_contratacion","activo","usuario","cargo"]

admin.site.register(Rol,RolAdmin)
admin.site.register(Permiso,PermisoAdmin)
admin.site.register(Usuario,UsuarioAdmin)
admin.site.register(Categoria,CategoriaAdmin)
admin.site.register(Entrenador,EntrenadorAdmin)
admin.site.register(Equipo,EquipoAdmin)
admin.site.register(Socio,SocioAdmin)
admin.site.register(Jugador,JugadorAdmin)
admin.site.register(Entrenamiento,EntrenamientoAdmin)
admin.site.register(EncuentroDeportivo,EncuentroDeportivoAdmin)
admin.site.register(Asistencia,AsistenciaAdmin)
admin.site.register(Cargo,CargoAdmin)
admin.site.register(EquipoAdministrativo,EquipoAdministrativoAdmin)