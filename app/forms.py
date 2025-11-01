# app/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import Perfil, PerfilTipo, Equipo

User = get_user_model()

class UsuarioCrearForm(forms.Form):
    username = forms.CharField(
        label="Usuario",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Usuario"}),
    )
    email = forms.EmailField(
        label="Correo",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Correo electrónico"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña"}),
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
        max_length=40,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    segundo_nombre = forms.CharField(
        label="Segundo nombre",
        max_length=40,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    apellido_paterno = forms.CharField(
        label="Apellido paterno",
        max_length=40,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    apellido_materno = forms.CharField(
        label="Apellido materno",
        max_length=40,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    
    # ======== extras para jugador ========
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"})
    )
    tipo_sangre = forms.ChoiceField(
        label="Tipo de sangre",
        required=False,
        choices=[("", "— Selecciona —"), ("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"),
                 ("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-")],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    
    equipo = forms.ModelChoiceField(                 # ← NUEVO (opcional)
        label="Equipo",
        queryset=Equipo.objects.all().order_by("categoria__slug", "nombre"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"})
    )

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

    def clean(self):
        cd = super().clean()
        p1, p2 = cd.get("password1"), cd.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if cd.get("run") and Perfil.objects.filter(run=cd["run"]).exists():
            self.add_error("run", "Ese RUN ya está registrado.")
        return cd


class UsuarioEditarForm(UsuarioCrearForm):
    """Versión para edición: contraseña opcional."""
    password1 = forms.CharField(
        label="Nueva contraseña",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Nueva contraseña"}),
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
        if User.objects.filter(username=u).exclude(pk=self.user_obj.pk).exists():
            raise forms.ValidationError("Ese nombre de usuario ya existe.")
        return u

    def clean_email(self):
        e = self.cleaned_data.get("email")
        if e and User.objects.filter(email=e).exclude(pk=self.user_obj.pk).exists():
            raise forms.ValidationError("Ese correo ya está en uso.")
        return e

    def clean(self):
        cd = super().clean()
        p1, p2 = cd.get("password1"), cd.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
        if cd.get("run") and Perfil.objects.filter(run=cd["run"]).exclude(pk=self.perfil_obj.pk).exists():
            self.add_error("run", "Ese RUN ya está registrado.")
        return cd
