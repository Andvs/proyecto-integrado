import re
from datetime import date
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Perfil, PerfilTipo, Equipo, ActividadDeportiva, Jugador, Certificado, RUN_CL, PHONE

User = get_user_model()

class UsuarioCrearForm(forms.Form):
    username = forms.CharField(
        label="Usuario",
        max_length=30,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Usuario"}),
    )
    email = forms.EmailField(
        label="Correo",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Correo electrónico"}),
        error_messages={
            "invalid": "Ingresa un correo electrónico válido. Ejemplo: usuario@dominio.com",
        },
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"}),
        help_text="Mínimo 8 caracteres con mayúsculas, minúsculas, números y caracteres especiales.",
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Repite la contraseña"}),
    )

    tipo = forms.ChoiceField(
        label="Tipo de usuario",
        choices=PerfilTipo.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    run = forms.CharField(
        label="RUN/DNI",
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: 12.345.678-9"}),
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+56 9 ..."}),
    )

    primer_nombre = forms.CharField(
        label="Primer nombre",
        max_length=30,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    segundo_nombre = forms.CharField(
        label="Segundo nombre",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    apellido_paterno = forms.CharField(
        label="Apellido paterno",
        max_length=30,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    apellido_materno = forms.CharField(
        label="Apellido materno",
        max_length=30,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    
    # ======== extras para jugador ========
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        help_text="Requerido para jugadores. Se validará según la categoría del equipo."
    )
    tipo_sangre = forms.ChoiceField(
        label="Tipo de sangre",
        required=False,
        choices=[("", "— Selecciona —"), ("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"),
                ("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-")],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    equipo = forms.ModelChoiceField(
        label="Equipo",
        queryset=Equipo.objects.all().order_by("categoria__slug", "nombre"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Opcional. Si se asigna, la edad debe coincidir con la categoría."
    )

    colegio = forms.CharField(
        label="Colegio",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    curso = forms.ChoiceField(
        label="Curso",
        required=False,
        choices=[("", "— Selecciona —"), ("Octavo Básico", "Octavo Básico"), ("Primero Medio", "Primero Medio"), ("Segundo Medio", "Segundo Medio"), ("Tercero Medio", "Tercero Medio"),("Cuarto Medio", "Cuarto Medio")],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    


    # === MÉTODO AUXILIAR PARA CALCULAR EDAD ===
    def calcular_edad(self, fecha_nacimiento):
        """Calcula la edad en años a partir de la fecha de nacimiento."""
        hoy = date.today()
        edad = hoy.year - fecha_nacimiento.year
        # Ajustar si aún no ha cumplido años este año
        if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
            edad -= 1
        return edad

    # === MÉTODO AUXILIAR PARA VALIDAR EDAD-CATEGORÍA ===
    def validar_edad_categoria(self, fecha_nacimiento, equipo):
        """
        Valida que la edad del jugador sea coherente con la categoría del equipo.
        
        Reglas:
        - Sub-14: jugadores de 14 años o menos
        - Sub-16: jugadores de 16 años o menos
        - Sub-18: jugadores de 18 años o menos
        """
        if not fecha_nacimiento or not equipo:
            return None  # No validar si falta información
        
        edad = self.calcular_edad(fecha_nacimiento)
        categoria_slug = equipo.categoria.slug.lower()
        
        # Extraer el número de la categoría (ej: "sub-14" -> 14)
        if 'sub-14' in categoria_slug or 'sub14' in categoria_slug:
            edad_maxima = 14
            nombre_categoria = "Sub-14"
        elif 'sub-16' in categoria_slug or 'sub16' in categoria_slug:
            edad_maxima = 16
            nombre_categoria = "Sub-16"
        elif 'sub-18' in categoria_slug or 'sub18' in categoria_slug:
            edad_maxima = 18
            nombre_categoria = "Sub-18"
        else:
            # Si la categoría no tiene restricción de edad, no validar
            return None
        
        # Validar edad - CORREGIDO: ahora permite la edad exacta de la categoría
        if edad > edad_maxima:
            raise ValidationError(
                f"El jugador tiene {edad} años. No puede estar en la categoría {nombre_categoria} "
                f"(edad máxima: {edad_maxima} años). "
                f"Por favor, selecciona un equipo de categoría superior o verifica la fecha de nacimiento."
            )
        
        return edad

    # === VALIDACIONES ===
    def clean_username(self):
        u = self.cleaned_data["username"]
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError("Ese nombre de usuario ya existe.")
        return u

    def clean_email(self):
        e = self.cleaned_data.get("email")
        if e and User.objects.filter(email=e).exists():
            raise forms.ValidationError("Ese correo ya está en uso.")
        return e
    
    def clean_run(self):
        """Validar formato de RUN usando el validador del modelo"""
        run = self.cleaned_data.get("run")
        if run:
            try:
                RUN_CL(run)
            except ValidationError as e:
                raise forms.ValidationError(e.message)
        return run
    
    def clean_telefono(self):
        """Validar formato de teléfono usando el validador del modelo"""
        telefono = self.cleaned_data.get("telefono")
        if telefono:
            # Limpiar espacios y guiones para validación
            telefono_limpio = telefono.replace(" ", "").replace("-", "")
            try:
                PHONE(telefono_limpio)
            except ValidationError as e:
                raise forms.ValidationError(e.message)
            # Retornar el teléfono limpio sin espacios
            return telefono_limpio
        return telefono

    def clean_password1(self):
        """✅ VALIDACIÓN DE COMPLEJIDAD DE CONTRASEÑA"""
        password = self.cleaned_data.get('password1')
        
        if not password:
            return password
        
        errores = []
        
        if len(password) < 8:
            errores.append("La contraseña debe tener al menos 8 caracteres.")
        
        if not re.search(r'[A-Z]', password):
            errores.append("Debe contener al menos una letra MAYÚSCULA.")
        
        if not re.search(r'[a-z]', password):
            errores.append("Debe contener al menos una letra minúscula.")
        
        if not re.search(r'\d', password):
            errores.append("Debe contener al menos un número.")
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            errores.append("Debe contener al menos un carácter especial (!@#$%^&*...).")
        
        if ' ' in password:
            errores.append("No puede contener espacios en blanco.")
        
        username = self.cleaned_data.get('username', '').lower()
        email = self.cleaned_data.get('email', '').lower()
        password_lower = password.lower()
        
        if username and username in password_lower:
            errores.append("No puede ser similar a tu nombre de usuario.")
        
        if email and email.split('@')[0] in password_lower:
            errores.append("No puede ser similar a tu correo electrónico.")
        
        primer_nombre = self.cleaned_data.get('primer_nombre', '').lower()
        apellido_paterno = self.cleaned_data.get('apellido_paterno', '').lower()
        
        if primer_nombre and len(primer_nombre) > 3 and primer_nombre in password_lower:
            errores.append("No puede contener tu nombre.")
        
        if apellido_paterno and len(apellido_paterno) > 3 and apellido_paterno in password_lower:
            errores.append("No puede contener tu apellido.")
        
        if errores:
            raise forms.ValidationError(errores)
        
        return password

    def clean(self):
        cd = super().clean()
        p1, p2 = cd.get("password1"), cd.get("password2")
        
        # Validar coincidencia de contraseñas
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        
        # Validar RUN único
        if cd.get("run") and Perfil.objects.filter(run=cd["run"]).exists():
            self.add_error("run", "Ese RUN ya está registrado.")
        
        # ✅ VALIDAR EDAD-CATEGORÍA (solo para jugadores)
        tipo = cd.get("tipo")
        if tipo == PerfilTipo.JUGADOR:
            fecha_nacimiento = cd.get("fecha_nacimiento")
            equipo = cd.get("equipo")
            
            # Fecha de nacimiento es obligatoria para jugadores
            if not fecha_nacimiento:
                self.add_error("fecha_nacimiento", "La fecha de nacimiento es obligatoria para jugadores.")
            
            # Si hay equipo y fecha, validar coherencia
            if fecha_nacimiento and equipo:
                try:
                    edad = self.validar_edad_categoria(fecha_nacimiento, equipo)
                    # Guardar la edad calculada para referencia
                    cd['edad_calculada'] = edad
                except ValidationError as e:
                    self.add_error("fecha_nacimiento", e.message)
                    self.add_error("equipo", "La categoría del equipo no es apropiada para la edad del jugador.")
        
        return cd


class UsuarioEditarForm(UsuarioCrearForm):
    """Versión para edición: contraseña opcional."""
    password1 = forms.CharField(
        label="Nueva contraseña",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Nueva contraseña (opcional)"}),
        help_text="Déjalo en blanco si no deseas cambiarla. Mínimo 8 caracteres con mayúsculas, minúsculas, números y caracteres especiales.",
    )
    password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Repite la nueva contraseña"}),
    )

    def __init__(self, *args, **kwargs):
        self.user_obj = kwargs.pop("user_obj", None)
        self.perfil_obj = kwargs.pop("perfil_obj", None)
        super().__init__(*args, **kwargs)

    def clean_username(self):
        u = self.cleaned_data["username"]
        if self.user_obj and User.objects.filter(username=u).exclude(pk=self.user_obj.pk).exists():
            raise forms.ValidationError("Ese nombre de usuario ya existe.")
        elif not self.user_obj and User.objects.filter(username=u).exists():
            raise forms.ValidationError("Ese nombre de usuario ya existe.")
        return u

    def clean_email(self):
        e = self.cleaned_data.get("email")
        if e:
            if self.user_obj and User.objects.filter(email=e).exclude(pk=self.user_obj.pk).exists():
                raise forms.ValidationError("Ese correo ya está en uso.")
            elif not self.user_obj and User.objects.filter(email=e).exists():
                raise forms.ValidationError("Ese correo ya está en uso.")
        return e

    def clean_password1(self):
        """✅ VALIDACIÓN DE COMPLEJIDAD - SOLO SI SE PROPORCIONA CONTRASEÑA"""
        password = self.cleaned_data.get('password1')
        
        if not password:
            return password
        
        errores = []
        
        if len(password) < 8:
            errores.append("La contraseña debe tener al menos 8 caracteres.")
        
        if not re.search(r'[A-Z]', password):
            errores.append("Debe contener al menos una letra MAYÚSCULA.")
        
        if not re.search(r'[a-z]', password):
            errores.append("Debe contener al menos una letra minúscula.")
        
        if not re.search(r'\d', password):
            errores.append("Debe contener al menos un número.")
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            errores.append("Debe contener al menos un carácter especial (!@#$%^&*...).")
        
        if ' ' in password:
            errores.append("No puede contener espacios en blanco.")
        
        username = self.cleaned_data.get('username', '').lower()
        email = self.cleaned_data.get('email', '').lower()
        password_lower = password.lower()
        
        if username and username in password_lower:
            errores.append("No puede ser similar a tu nombre de usuario.")
        
        if email and email.split('@')[0] in password_lower:
            errores.append("No puede ser similar a tu correo electrónico.")
        
        primer_nombre = self.cleaned_data.get('primer_nombre', '').lower()
        apellido_paterno = self.cleaned_data.get('apellido_paterno', '').lower()
        
        if primer_nombre and len(primer_nombre) > 3 and primer_nombre in password_lower:
            errores.append("No puede contener tu nombre.")
        
        if apellido_paterno and len(apellido_paterno) > 3 and apellido_paterno in password_lower:
            errores.append("No puede contener tu apellido.")
        
        if errores:
            raise forms.ValidationError(errores)
        
        return password

    def clean(self):
        cd = super(UsuarioCrearForm, self).clean()
        p1, p2 = cd.get("password1"), cd.get("password2")
        
        # Solo validar contraseñas si se proporcionó
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
        
        # Validar RUN único (excluyendo el actual)
        if cd.get("run"):
            if self.perfil_obj and Perfil.objects.filter(run=cd["run"]).exclude(pk=self.perfil_obj.pk).exists():
                self.add_error("run", "Ese RUN ya está registrado.")
            elif not self.perfil_obj and Perfil.objects.filter(run=cd["run"]).exists():
                self.add_error("run", "Ese RUN ya está registrado.")
        
        # ✅ VALIDAR EDAD-CATEGORÍA (solo para jugadores)
        tipo = cd.get("tipo")
        if tipo == PerfilTipo.JUGADOR:
            fecha_nacimiento = cd.get("fecha_nacimiento")
            equipo = cd.get("equipo")
            
            # Fecha de nacimiento es obligatoria para jugadores
            if not fecha_nacimiento:
                self.add_error("fecha_nacimiento", "La fecha de nacimiento es obligatoria para jugadores.")
            
            # Si hay equipo y fecha, validar coherencia
            if fecha_nacimiento and equipo:
                try:
                    edad = self.validar_edad_categoria(fecha_nacimiento, equipo)
                    cd['edad_calculada'] = edad
                except ValidationError as e:
                    self.add_error("fecha_nacimiento", e.message)
                    self.add_error("equipo", "La categoría del equipo no es apropiada para la edad del jugador.")
        
        return cd


class CertificadoGenerarForm(forms.Form):
    actividad = forms.ModelChoiceField(
        queryset=ActividadDeportiva.objects.all().order_by("-fecha_inicio"),
        label="Actividad",
        required=True
    )
    jugadores = forms.ModelMultipleChoiceField(
        queryset=Jugador.objects.filter(activo=True).select_related("perfil", "equipo"),
        widget=forms.CheckboxSelectMultiple,
        label="Jugadores",
        required=True
    )
    prefijo_codigo = forms.CharField(max_length=20, required=False, label="Prefijo de código (opcional)")

    def clean(self):
        cleaned = super().clean()
        actividad = cleaned.get("actividad")
        jugadores = cleaned.get("jugadores")

        if actividad and jugadores:
            equipos_participantes = set(actividad.equipos.values_list("id", flat=True))
            invalid = [j for j in jugadores if (j.equipo_id not in equipos_participantes)]
            if invalid:
                nombres = ", ".join([j.perfil.nombre_completo for j in invalid])
                raise forms.ValidationError(
                    f"Los siguientes jugadores no pertenecen a equipos participantes de la actividad: {nombres}"
                )
        return cleaned