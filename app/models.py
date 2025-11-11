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
    descripcion = models.TextField(blank=True)
    cancelada = models.BooleanField(default=False)
    motivo_cancelacion = models.TextField(blank=True, null=True, verbose_name="Motivo de Cancelación")
    equipos = models.ManyToManyField(Equipo, through="EquipoActividad", related_name="actividades")

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
