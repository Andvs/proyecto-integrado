from datetime import date
from django import forms
from app.models import *
import bcrypt
from django.contrib.auth.hashers import make_password

# ====================== USUARIO ======================

class UsuarioForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre_usuario','contraseña','rol']
        widgets = {
            'nombre_usuario':forms.TextInput(attrs={
                'placeholder': 'Nombre de Usuarios (solo letras)',
                'class': 'form-control',
                'minlength': '3', 'maxlength': '50'}),
            'contraseña':forms.PasswordInput(attrs={
                'placeholder': 'Contraseña (8–20, con mayúscula y minúscula)',
                'class': 'form-control',
                'minlength': '8', 'maxlength': '20'}),
            'rol':forms.Select(attrs={'class': 'form-control'})
        }
        error_messages = {
            'nombre_usuario': {
                'required': 'El nombre es obligatorio.',
                'min_length': 'El nombre debe tener al menos 3 caracteres.',
            },
            'contraseña': {
                'required': 'La contraseña es obligatoria.',
                'min_length': 'La contraseña debe tener al menos 8 caracteres.',
                'max_length': 'La contraseña no puede superar 20 caracteres.',
            },
            'rol': {
                'required': 'Debe seleccionar un rol.',
            }}
    def save(self, commit=True):
        usuario = super().save(commit=False)
        password_plano = self.cleaned_data['contraseña']
        usuario.contraseña = make_password(password_plano)  # usar hasher de Django
        if commit:
            usuario.save()
        return usuario

from .models import Usuario  # Asegúrate de importar tu modelo de usuario

class UsuarioEditForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre_usuario', 'activo', 'rol']
        widgets = {
            'nombre_usuario': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
        }


# =============== MIXIN EDAD–CATEGORÍA (SOLO FORM) ===============

class _EdadCategoriaMixin:
    """
    Valida coherencia entre la edad del jugador y la categoría del EQUIPO,
    sin tocar models.py ni usar utils externos.
    - La edad se evalúa al 31/12 del AÑO ANTERIOR (Opción A).
    - Mapea códigos 'sub_14' | 'sub_16' | 'sub_18' de Categoria.nombre.
    """

    CATEGORIAS_LABELS = {
        "sub_14": "Sub 14",
        "sub_16": "Sub 16",
        "sub_18": "Sub 18",
    }

    # Rango permitido (min_edad_inclusiva, max_edad_inclusiva):
    REGLAS_CATEGORIA = {
        "sub_14": (12, 14),
        "sub_16": (14, 16),
        "sub_18": (16, 18),
    }

    @staticmethod
    def fecha_corte(anio=None) -> date:
        """
        Opción A: usar el 31/12 del AÑO ANTERIOR.
        Ej.: En 2025, el corte es 31/12/2024.
        """
        hoy = date.today()
        anio_base = (anio or hoy.year) - 1
        return date(anio_base, 12, 31)

    @classmethod
    def edad_al_corte(cls, fecha_nacimiento: date, corte: date | None = None) -> int:
        corte = corte or cls.fecha_corte()
        return corte.year - fecha_nacimiento.year - (
            (corte.month, corte.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
        )

    def _codigo_categoria_equipo(self, equipo):
        """
        Obtiene el código de categoría desde equipo.categoria.nombre (choices):
        'sub_14' | 'sub_16' | 'sub_18'
        """
        if not equipo or not hasattr(equipo, "categoria") or not equipo.categoria:
            return None
        # En tu models.py, Categoria.nombre guarda el code de choices ('sub_14', etc.)
        return str(getattr(equipo.categoria, "nombre", "")).lower() or None

    def _validar_edad_vs_categoria(self, *, fecha_nacimiento, equipo):
        """Añade error al campo 'equipo' si la edad no cuadra con la categoría."""
        if not fecha_nacimiento or not equipo:
            return

        codigo = self._codigo_categoria_equipo(equipo)
        if not codigo:
            self.add_error("equipo", "No se pudo determinar la categoría del equipo.")
            return

        reglas = self.REGLAS_CATEGORIA.get(codigo)
        if not reglas:
            self.add_error("equipo", "La categoría del equipo es inválida o no está configurada.")
            return

        edad = self.edad_al_corte(fecha_nacimiento)
        min_e, max_e = reglas
        if not (min_e <= edad <= max_e):
            etiqueta = self.CATEGORIAS_LABELS.get(codigo, codigo)
            corte = self.fecha_corte()
            self.add_error(
                "equipo",
                (
                    f"La edad al {corte.strftime('%d-%m-%Y')} es {edad} años, "
                    f"fuera del rango permitido para {etiqueta} ({min_e}–{max_e})."
                ),
            )


# ====================== JUGADOR ======================

class JugadorForm(_EdadCategoriaMixin, forms.ModelForm):
    class Meta:
        model = Jugador
        fields = [
            'run', 'nombre', 'apellido', 'fecha_nacimiento',
            'num_celular', 'correo', 'colegio', 'curso',
            'fecha_ingreso', 'activo', 'equipo', 'usuario', 'socio'
        ]
        widgets = {
            'run': forms.TextInput(attrs={
                'placeholder': 'RUT del jugador (ej. 12345678-9)',
                'class': 'form-control'
            }),
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Nombre',
                'class': 'form-control'
            }),
            'apellido': forms.TextInput(attrs={
                'placeholder': 'Apellido',
                'class': 'form-control'
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'num_celular': forms.NumberInput(attrs={
                'placeholder': 'Número de celular',
                'class': 'form-control'
            }),
            'correo': forms.EmailInput(attrs={
                'placeholder': 'Correo electrónico',
                'class': 'form-control'
            }),
            'colegio': forms.TextInput(attrs={
                'placeholder': 'Nombre del colegio',
                'class': 'form-control'
            }),
            'curso': forms.Select(attrs={'class': 'form-select'}),
            'fecha_ingreso': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'equipo': forms.Select(attrs={'class': 'form-select'}),
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'socio': forms.Select(attrs={'class': 'form-select'}),
        }
        error_messages = {
            'run': {'required': 'El RUT del jugador es obligatorio.'},
            'nombre': {'required': 'El nombre es obligatorio.'},
            'apellido': {'required': 'El apellido es obligatorio.'},
            'fecha_nacimiento': {'required': 'Debe ingresar la fecha de nacimiento.'},
            'equipo': {'required': 'Debe asignar un equipo.'},
            'usuario': {'required': 'Debe asociar un usuario.'},
            'socio': {'required': 'Debe asociar un socio.'},
        }

    # RUT único
    def clean_run(self):
        run = self.cleaned_data.get('run', '').upper().strip()
        if Jugador.objects.filter(run=run).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ya existe un jugador con este RUT.")
        return run

    # Validaciones globales
    def clean(self):
        cleaned_data = super().clean()
        num_celular = cleaned_data.get('num_celular')
        correo = cleaned_data.get('correo')
        equipo = cleaned_data.get('equipo')
        fecha_nacimiento = cleaned_data.get('fecha_nacimiento')

        # Al menos un medio de contacto
        if not num_celular and not correo:
            raise forms.ValidationError(
                "Debe ingresar al menos un medio de contacto (teléfono o correo)."
            )

        # Entrenador activo
        if equipo and hasattr(equipo, 'entrenador') and not equipo.entrenador.activo:
            raise forms.ValidationError("El entrenador del equipo seleccionado no está activo.")

        # Coherencia edad–categoría (corte: 31/12 del año anterior)
        self._validar_edad_vs_categoria(fecha_nacimiento=fecha_nacimiento, equipo=equipo)

        return cleaned_data


class JugadorEditForm(_EdadCategoriaMixin, forms.ModelForm):
    class Meta:
        model = Jugador
        fields = [
            'nombre', 'apellido', 'fecha_nacimiento',
            'num_celular', 'correo', 'colegio', 'curso',
            'fecha_ingreso', 'activo', 'equipo', 'usuario', 'socio'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'num_celular': forms.NumberInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'colegio': forms.TextInput(attrs={'class': 'form-control'}),
            'curso': forms.Select(attrs={'class': 'form-select'}),
            'fecha_ingreso': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'equipo': forms.Select(attrs={'class': 'form-select'}),
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'socio': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        num_celular = cleaned_data.get('num_celular')
        correo = cleaned_data.get('correo')
        equipo = cleaned_data.get('equipo')
        fecha_nacimiento = cleaned_data.get('fecha_nacimiento')

        # Al menos un medio de contacto
        if not num_celular and not correo:
            raise forms.ValidationError(
                "Debe ingresar al menos un medio de contacto (teléfono o correo)."
            )

        # Entrenador activo
        if equipo and hasattr(equipo, 'entrenador') and not equipo.entrenador.activo:
            raise forms.ValidationError("El entrenador del equipo seleccionado no está activo.")

        # Coherencia edad–categoría (corte: 31/12 del año anterior)
        self._validar_edad_vs_categoria(fecha_nacimiento=fecha_nacimiento, equipo=equipo)

        return cleaned_data
