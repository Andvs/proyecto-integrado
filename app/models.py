from datetime import date
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q, F


# -------------------------
# Validadores simples (CL)
# -------------------------
RUN_CL = RegexValidator(
    regex=r'^\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]$',
    message="RUN inválido. Ejemplo: 12.345.678-5"
)

PHONE = RegexValidator(
    regex=r'^\+?\d{7,15}$',
    message="Teléfono inválido. Usa sólo dígitos y opcional '+'."
)


# -------------------------
# Utilitarios / Catálogos
# -------------------------
class TimeStampedModel(models.Model):
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


class Cargo(models.Model):
    """Puesto organizacional del staff (distinto del rol del sistema)."""
    nombre = models.CharField(max_length=60, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)
    class Meta:
        ordering = ["nombre"]
    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    """Catálogo flexible: 'sub-14', 'adulto', 'mixto', etc."""
    slug = models.SlugField(max_length=32, unique=True)
    descripcion = models.CharField(max_length=200, blank=True)
    class Meta:
        ordering = ["slug"]
    def __str__(self):
        return self.descripcion or self.slug


# -------------------------
# Usuario extendido
# -------------------------
class PerfilTipo(models.TextChoices):
    ADMIN        = "ADMIN", "Administrador"
    EQUIPO_ADMIN = "EQUIP", "Equipo Administrativo"
    ENTRENADOR   = "ENTRE", "Entrenador"
    JUGADOR      = "JUGAD", "Jugador"
    SOCIO        = "SOCIO", "Socio"


class Perfil(TimeStampedModel):
    """Extiende User con RUN, teléfono, tipo y nombres desglosados."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil"
    )
    tipo = models.CharField(
        max_length=5,
        choices=PerfilTipo.choices,
        default=PerfilTipo.SOCIO,
        db_index=True
    )
    run = models.CharField("RUN/DNI", max_length=20, unique=True, validators=[RUN_CL])
    telefono = models.CharField(max_length=20, blank=True, validators=[PHONE])

    # Nombres y apellidos (Chile)
    primer_nombre    = models.CharField(max_length=40)
    segundo_nombre   = models.CharField(max_length=40, blank=True)  # opcional
    apellido_paterno = models.CharField(max_length=40)
    apellido_materno = models.CharField(max_length=40)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.nombre_completo

    @property
    def nombre_completo(self) -> str:
        partes = [self.primer_nombre]
        if self.segundo_nombre:
            partes.append(self.segundo_nombre)
        partes.extend([self.apellido_paterno, self.apellido_materno])
        return " ".join(partes)

    @property
    def apellidos(self) -> str:
        return f"{self.apellido_paterno} {self.apellido_materno}"


# -------------------------
# Actores del club (cada uno fuerza su tipo)
# -------------------------
class EquipoAdministrativo(TimeStampedModel):
    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.PROTECT,
        limit_choices_to={"tipo": PerfilTipo.EQUIPO_ADMIN},
        related_name="equipo_administrativo",
    )
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT)
    def __str__(self):
        return f"{self.perfil} · {self.cargo}"


# class Entrenador(TimeStampedModel):
#     perfil = models.OneToOneField(
#         Perfil,
#         on_delete=models.PROTECT,
#         limit_choices_to={"tipo": PerfilTipo.ENTRENADOR},
#         related_name="entrenador",
#     )
#     def __str__(self):
#         return f"Entrenador: {self.perfil.nombre_completo}"


class Socio(TimeStampedModel):
    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.PROTECT,
        limit_choices_to={"tipo": PerfilTipo.SOCIO},
        related_name="socio",
    )
    def __str__(self):
        return f"Socio: {self.perfil.nombre_completo}"


# -------------------------
# Estructura deportiva
# -------------------------
class Equipo(TimeStampedModel):
    nombre = models.CharField(max_length=60)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="equipos")
    entrenador = models.ForeignKey(
        Perfil,
        on_delete=models.PROTECT,
        related_name="equipos_dirigidos",
        limit_choices_to={"tipo": PerfilTipo.ENTRENADOR},
    )
    class Meta:
        ordering = ["categoria__slug", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["nombre", "categoria"], name="uq_equipo_nombre_categoria")
        ]
    def __str__(self):
        return f"{self.nombre} ({self.categoria})"


class TipoSangre(models.TextChoices):
    A_POS = "A+", "A+"
    A_NEG = "A-", "A-"
    B_POS = "B+", "B+"
    B_NEG = "B-", "B-"
    AB_POS = "AB+", "AB+"
    AB_NEG = "AB-", "AB-"
    O_POS = "O+", "O+"
    O_NEG = "O-", "O-"


class Jugador(TimeStampedModel):
    """
    Jugador con cuenta propia:
    - 1:1 con Perfil (tipo JUGADOR) → de ahí salen los nombres.
    - Pertenece a un Equipo.
    - Tipo de sangre opcional.
    """
    perfil = models.OneToOneField(
        Perfil,
        on_delete=models.PROTECT,
        limit_choices_to={"tipo": PerfilTipo.JUGADOR},
        related_name="jugador",
    )
    fecha_nacimiento = models.DateField(null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name="jugadores", db_index=True, null=True, blank=True)
    tipo_sangre = models.CharField(max_length=3, choices=TipoSangre.choices, null=True, blank=True)
    activo = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["equipo__categoria__slug", "equipo__nombre", "perfil__apellido_paterno", "perfil__apellido_materno"]
        indexes = [
            models.Index(fields=["equipo"]),
            models.Index(fields=["activo"]),
        ]

    def __str__(self):
        return f"{self.perfil.nombre_completo} · {self.equipo}"

    # Conveniencias para el panel del jugador
    def actividades_proximas(self, desde: date | None = None):
        desde = desde or date.today()
        return (ActividadDeportiva.objects
                .filter(equipos=self.equipo, fecha_inicio__gte=desde)
                .order_by("fecha_inicio", "titulo"))

    def entrenamientos_proximos(self, desde: date | None = None):
        desde = desde or date.today()
        return (ActividadDeportiva.objects
                .filter(equipos=self.equipo,
                        tipo=ActividadTipo.ENTRENAMIENTO,
                        fecha_inicio__gte=desde)
                .order_by("fecha_inicio", "titulo"))


class ActividadTipo(models.TextChoices):
    ENTRENAMIENTO = "ENTRENAMIENTO", "Entrenamiento"
    PARTIDO = "PARTIDO", "Partido"
    TORNEO = "TORNEO", "Torneo"


class ActividadDeportiva(TimeStampedModel):
    """Evento deportivo (entrenamiento/partido/torneo) para uno o varios equipos."""
    titulo = models.CharField(max_length=100)
    tipo = models.CharField(max_length=15, choices=ActividadTipo.choices, db_index=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    descripcion = models.TextField(blank=True)
    equipos = models.ManyToManyField(Equipo, through="EquipoActividad", related_name="actividades")
    # NUEVO CAMPO: Entrenador responsable de la actividad
    entrenador_responsable = models.ForeignKey(
        Perfil,
        on_delete=models.PROTECT,
        related_name="actividades_responsable",
        limit_choices_to={"tipo": PerfilTipo.ENTRENADOR},
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-fecha_inicio", "titulo"]
        constraints = [
            models.CheckConstraint(
                check=Q(fecha_fin__gte=F("fecha_inicio")),
                name="ck_actividad_rango_fechas"
            )
        ]

    def __str__(self):
        return f"{self.titulo} · {self.get_tipo_display()} ({self.fecha_inicio} → {self.fecha_fin})"
    
    def clean(self):
        """Validar que no haya solapamiento de horarios."""
        super().clean()
        
        # Si no hay horas definidas, no validar solapamiento
        if not self.hora_inicio or not self.hora_fin:
            return
        
        # Validar que hora_fin sea mayor que hora_inicio
        if self.hora_fin <= self.hora_inicio:
            raise ValidationError({
                'hora_fin': 'La hora de fin debe ser posterior a la hora de inicio.'
            })
    
    def verificar_solapamiento_equipos(self, equipos_ids):
        """
        Verificar si hay solapamiento con otras actividades de los mismos equipos.
        Retorna lista de conflictos o None.
        """
        if not self.hora_inicio or not self.hora_fin:
            return None
        
        # Buscar actividades que tengan al menos un equipo en común
        actividades_solapadas = ActividadDeportiva.objects.filter(
            equipos__in=equipos_ids,
            fecha_inicio__lte=self.fecha_fin,
            fecha_fin__gte=self.fecha_inicio
        ).exclude(pk=self.pk).distinct()
        
        conflictos = []
        for actividad in actividades_solapadas:
            # Si ambas actividades tienen horarios definidos, verificar solapamiento
            if actividad.hora_inicio and actividad.hora_fin:
                # Verificar si las fechas se solapan
                if self.fecha_inicio <= actividad.fecha_fin and self.fecha_fin >= actividad.fecha_inicio:
                    # Si es el mismo día, verificar horarios
                    if self.fecha_inicio == actividad.fecha_inicio:
                        if self.hora_inicio < actividad.hora_fin and self.hora_fin > actividad.hora_inicio:
                            equipos_comunes = set(equipos_ids) & set(actividad.equipos.values_list('id', flat=True))
                            conflictos.append({
                                'actividad': actividad,
                                'equipos_comunes': Equipo.objects.filter(id__in=equipos_comunes),
                                'tipo': 'equipo'
                            })
        
        return conflictos if conflictos else None
    
    def verificar_disponibilidad_entrenador(self, entrenador_id):
        """
        Verificar si el entrenador está disponible en el horario de la actividad.
        Retorna lista de conflictos o None.
        """
        if not self.hora_inicio or not self.hora_fin or not entrenador_id:
            return None
        
        # Buscar actividades del mismo entrenador en las mismas fechas
        actividades_entrenador = ActividadDeportiva.objects.filter(
            entrenador_responsable_id=entrenador_id,
            fecha_inicio__lte=self.fecha_fin,
            fecha_fin__gte=self.fecha_inicio
        ).exclude(pk=self.pk)
        
        # También buscar equipos que el entrenador dirige y tienen actividades
        equipos_entrenador = Equipo.objects.filter(entrenador_id=entrenador_id).values_list('id', flat=True)
        actividades_equipos = ActividadDeportiva.objects.filter(
            equipos__in=equipos_entrenador,
            fecha_inicio__lte=self.fecha_fin,
            fecha_fin__gte=self.fecha_inicio
        ).exclude(pk=self.pk).distinct()
        
        # Combinar ambas consultas
        todas_actividades = (actividades_entrenador | actividades_equipos).distinct()
        
        conflictos = []
        for actividad in todas_actividades:
            # Si la actividad tiene horarios definidos, verificar solapamiento
            if actividad.hora_inicio and actividad.hora_fin:
                # Si es el mismo día, verificar horarios
                if self.fecha_inicio == actividad.fecha_inicio:
                    if self.hora_inicio < actividad.hora_fin and self.hora_fin > actividad.hora_inicio:
                        conflictos.append({
                            'actividad': actividad,
                            'tipo': 'entrenador'
                        })
        
        return conflictos if conflictos else None
    
    def obtener_entrenadores_disponibles(self):
        """
        Obtener lista de entrenadores que están disponibles para esta actividad.
        Útil para mostrar en el formulario.
        """
        if not self.hora_inicio or not self.hora_fin or not self.fecha_inicio:
            # Si no hay horarios, retornar todos los entrenadores activos
            return Perfil.objects.filter(
                tipo=PerfilTipo.ENTRENADOR,
                user__is_active=True
            )
        
        # Obtener todos los entrenadores
        todos_entrenadores = Perfil.objects.filter(
            tipo=PerfilTipo.ENTRENADOR,
            user__is_active=True
        ).values_list('id', flat=True)
        
        # Encontrar entrenadores ocupados
        entrenadores_ocupados = set()
        
        # Buscar por actividades donde son responsables
        actividades_conflicto = ActividadDeportiva.objects.filter(
            fecha_inicio=self.fecha_inicio,
            hora_inicio__lt=self.hora_fin,
            hora_fin__gt=self.hora_inicio,
            entrenador_responsable__isnull=False
        ).exclude(pk=self.pk).values_list('entrenador_responsable_id', flat=True)
        
        entrenadores_ocupados.update(actividades_conflicto)
        
        # Buscar por equipos que dirigen con actividades
        equipos_con_actividades = Equipo.objects.filter(
            actividades__fecha_inicio=self.fecha_inicio,
            actividades__hora_inicio__lt=self.hora_fin,
            actividades__hora_fin__gt=self.hora_inicio
        ).exclude(actividades__pk=self.pk).values_list('entrenador_id', flat=True)
        
        entrenadores_ocupados.update(equipos_con_actividades)
        
        # Retornar entrenadores disponibles
        entrenadores_disponibles = set(todos_entrenadores) - entrenadores_ocupados
        
        return Perfil.objects.filter(id__in=entrenadores_disponibles)

class EquipoActividad(models.Model):
    """Tabla intermedia simple para ActividadDeportiva ↔ Equipo."""
    actividad = models.ForeignKey(ActividadDeportiva, on_delete=models.CASCADE)
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("actividad", "equipo")

    def __str__(self):
        return f"{self.actividad} ↔ {self.equipo}"


# -------------------------
# Asistencia
# -------------------------
class AsistenciaEstado(models.TextChoices):
    PRESENTE = "P", "Presente"
    AUSENTE  = "A", "Ausente"


class Asistencia(TimeStampedModel):
    jugador = models.ForeignKey(Jugador, on_delete=models.PROTECT, related_name="asistencias")
    actividad = models.ForeignKey(ActividadDeportiva, on_delete=models.PROTECT, related_name="asistencias")
    entrenador = models.ForeignKey(
        Perfil,
        on_delete=models.PROTECT,
        related_name="asistencias_registradas",
        limit_choices_to={"tipo": PerfilTipo.ENTRENADOR},
    )
    estado = models.CharField(max_length=1, choices=AsistenciaEstado.choices, default=AsistenciaEstado.PRESENTE, db_index=True)
    fecha_hora_marcaje = models.DateTimeField()
    class Meta:
        ordering = ["-fecha_hora_marcaje"]
        constraints = [
            models.UniqueConstraint(fields=["jugador", "actividad"], name="uq_asistencia_jugador_actividad"),
        ]
        indexes = [
            models.Index(fields=["actividad"]),
            models.Index(fields=["entrenador"]),
            models.Index(fields=["fecha_hora_marcaje"]),
        ]
    def clean(self):
        equipos_participantes = set(self.actividad.equipos.values_list("id", flat=True))
        if self.jugador.equipo_id not in equipos_participantes:
            raise ValidationError("El jugador no pertenece a un equipo que participa en esta actividad.")
        if not (self.actividad.fecha_inicio <= self.fecha_hora_marcaje.date() <= self.actividad.fecha_fin):
            raise ValidationError("La marcación debe estar dentro del rango de la actividad.")

    def clean(self):
        # 1) Jugador debe pertenecer a un equipo que participa en la actividad
        equipos_participantes = set(self.actividad.equipos.values_list("id", flat=True))
        if self.jugador.equipo_id not in equipos_participantes:
            raise ValidationError("El jugador no pertenece a un equipo que participa en esta actividad.")
        # 2) La marcación debe caer dentro del rango de la actividad
        if not (self.actividad.fecha_inicio <= self.fecha_hora_marcaje.date() <= self.actividad.fecha_fin):
            raise ValidationError("La marcación debe estar dentro del rango de la actividad.")

    def __str__(self):
        return f"Asistencia {self.jugador.perfil.nombre_completo} · {self.actividad} · {self.get_estado_display()}"
