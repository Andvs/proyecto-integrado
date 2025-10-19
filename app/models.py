from django.db import models

class Rol(models.Model):
    nombre = models.CharField(max_length=45, unique=True)
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    def __str__(self):
        return self.nombre

class Permiso(models.Model):
    nombre = models.CharField(max_length=45, unique=True)
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    def __str__(self):
        return self.nombre

class Usuario(models.Model):
    nombre_usuario = models.CharField(max_length=50, unique=True)
    contraseña = models.CharField(max_length=128)
    activo = models.BooleanField(default=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT)
    def __str__(self):
        return self.nombre_usuario

class PermisoRol(models.Model):
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('permiso', 'rol')

class Categoria(models.Model):
    SUBCATEGORIAS = [
        ('sub_14', 'Sub 14'),
        ('sub_16', 'Sub 16'),
        ('sub_18', 'Sub 18'),
    ]
    nombre = models.CharField(max_length=6, choices=SUBCATEGORIAS)
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    def __str__(self):
        return self.get_nombre_display()

class Entrenador(models.Model):
    run = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField()
    direccion = models.CharField(max_length=45, null=True, blank=True)
    num_celular = models.PositiveIntegerField(null=True, blank=True)
    correo = models.EmailField(null=True, blank=True)
    fecha_contratacion = models.DateField(null=True, blank=True)
    activo = models.BooleanField()
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, null=True, blank=True)
    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Equipo(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    entrenador = models.ForeignKey(Entrenador, on_delete=models.PROTECT)
    class Meta:
        unique_together = ('id', 'categoria')
    def __str__(self):
        return self.nombre

class Socio(models.Model):
    run = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField()
    direccion = models.CharField(max_length=100, null=True, blank=True)
    num_celular = models.PositiveIntegerField()
    correo = models.EmailField(null=True, blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    activo = models.BooleanField()
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, null=True, blank=True)
    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Jugador(models.Model):
    CURSOS = [
        ('octavo_basico', 'Octavo Básico'),
        ('primero_medio', 'Primero Medio'),
        ('segundo_medio', 'Segundo Medio'),
        ('tercero_medio', 'Tercero Medio'),
        ('cuarto_medio', 'Cuarto Medio'),
    ]

    run = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField()
    num_celular = models.PositiveIntegerField(null=True, blank=True)
    correo = models.EmailField(null=True, blank=True)
    colegio = models.CharField(max_length=60, null=True, blank=True)
    curso = models.CharField(max_length=20, choices=CURSOS, null=True, blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    activo = models.BooleanField()
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT)
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, null=True, blank=True)
    socio = models.ForeignKey(Socio, on_delete=models.PROTECT, null=True, blank=True)
    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class Entrenamiento(models.Model):
    nombre = models.CharField(max_length=45)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    lugar = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=400, null=True, blank=True)
    def __str__(self):
        return self.nombre

class EncuentroDeportivo(models.Model):
    TIPOS = [
        ('Entrenamiento', 'Entrenamiento'),
        ('Práctica', 'Práctica'),
        ('Acondicionamiento', 'Acondicionamiento'),
        ('Taller', 'Taller'),
        ('Otro', 'Otro'),
    ]
    nombre = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    lugar = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=400, null=True, blank=True)
    def __str__(self):
        return self.nombre

class EquipoEntrenamiento(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    evento_deportivo = models.ForeignKey(Entrenamiento, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('equipo', 'evento_deportivo')

class EquipoEncuentroDeportivo(models.Model):
    actividad_deportiva = models.ForeignKey(EncuentroDeportivo, on_delete=models.CASCADE)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    class Meta:
        unique_together = ('actividad_deportiva', 'equipo')

class Asistencia(models.Model):
    fecha_hora_marcaje = models.DateTimeField()
    jugador = models.ForeignKey(Jugador, on_delete=models.SET_NULL, null=True, blank=True)
    entrenador = models.ForeignKey(Entrenador, on_delete=models.SET_NULL, null=True, blank=True)
    actividad_deportiva = models.ForeignKey(EncuentroDeportivo, on_delete=models.SET_NULL, null=True, blank=True)
    evento_deportivo = models.ForeignKey(Entrenamiento, on_delete=models.SET_NULL, null=True, blank=True)
    marcaje_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    anotaciones = models.CharField(max_length=200, null=True, blank=True)
    def __str__(self):
        return f"Asistencia {self.id} - {self.fecha_hora_marcaje}"

class Cargo(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=100, null=True, blank=True)
    def __str__(self):
        return self.nombre

class EquipoAdministrativo(models.Model):
    run = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField()
    direccion = models.CharField(max_length=45, null=True, blank=True)
    num_celular = models.PositiveIntegerField()
    correo = models.EmailField()
    fecha_contratacion = models.DateField(null=True, blank=True)
    activo = models.BooleanField()
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT)
    def __str__(self):
        return f"{self.nombre} {self.apellido}"
