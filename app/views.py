# app/views.py
from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import UsuarioCrearForm, UsuarioEditarForm
from .models import (
    Perfil, PerfilTipo,
    ActividadDeportiva, Jugador, Equipo,
)

User = get_user_model()


# ==========================
# Público
# ==========================
def index(request):
    """Landing pública (index.html)."""
    return render(request, "index.html")


# ==========================
# Autenticación
# ==========================
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = AuthenticationForm(request, data=request.POST or None)

    # Estilo Bootstrap rápido
    for name, field in form.fields.items():
        css = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = (css + " form-control").strip()
        field.widget.attrs.setdefault("placeholder", field.label)

    # Marcar errores de campo
    if form.is_bound and form.errors:
        for name in form.errors.keys():
            css = form.fields[name].widget.attrs.get("class", "")
            if "is-invalid" not in css:
                form.fields[name].widget.attrs["class"] = (css + " is-invalid").strip()

    if request.method == "POST":
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "¡Bienvenido/a!")
            return redirect("dashboard")
        messages.error(request, "Usuario o contraseña inválidos.")

    return render(request, "login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada correctamente.")
    return redirect("index")


# ==========================
# Helpers de permisos
# ==========================
def _es_admin_equipo(user):
    """
    True si el usuario es superusuario o si su perfil es ADMIN / EQUIPO_ADMIN.
    """
    if user.is_superuser:
        return True
    perfil = getattr(user, "perfil", None)
    return bool(perfil and perfil.tipo in (PerfilTipo.ADMIN, PerfilTipo.EQUIPO_ADMIN))


# ==========================
# Dashboard
# ==========================
@login_required
def dashboard(request):
    """
    'dashboard.html' hereda de 'inicio.html' (sidebar).
    El centro cambia según Perfil.tipo. Superusuario funciona aunque no tenga Perfil.
    """
    user = request.user
    perfil = getattr(user, "perfil", None)
    hoy = date.today()
    ctx = {"perfil": perfil, "hoy": hoy}

    # ✅ Superusuario: mostrar tablero admin aunque no tenga Perfil
    if user.is_superuser:
        ctx.update({
            "total_equipos": Equipo.objects.count(),
            "total_actividades": ActividadDeportiva.objects.count(),
            "actividades_proximas": (ActividadDeportiva.objects
                                     .filter(fecha_inicio__gte=hoy)
                                     .order_by("fecha_inicio")[:8]),
        })
        return render(request, "dashboard.html", ctx)

    # Usuarios “normales”: requieren Perfil
    if not perfil:
        messages.warning(request, "Tu usuario no tiene un Perfil asociado.")
        return render(request, "dashboard.html", ctx)

    if perfil.tipo in (PerfilTipo.ADMIN, PerfilTipo.EQUIPO_ADMIN):
        ctx.update({
            "total_equipos": Equipo.objects.count(),
            "total_actividades": ActividadDeportiva.objects.count(),
            "actividades_proximas": (ActividadDeportiva.objects
                                     .filter(fecha_inicio__gte=hoy)
                                     .order_by("fecha_inicio")[:8]),
        })

    elif perfil.tipo == PerfilTipo.ENTRENADOR:
        equipos_ids = perfil.equipos_dirigidos.values_list("id", flat=True)
        actividades = (ActividadDeportiva.objects
                       .filter(equipos__in=equipos_ids, fecha_inicio__gte=hoy)
                       .order_by("fecha_inicio", "titulo")
                       .distinct()[:10])
        ctx.update({
            "mis_equipos": perfil.equipos_dirigidos.all(),
            "actividades_proximas": actividades,
        })

    elif perfil.tipo == PerfilTipo.JUGADOR:
        jugador = getattr(perfil, "jugador", None)
        if jugador:
            ctx.update({
                "jugador": jugador,
                "actividades_proximas": getattr(jugador, "actividades_proximas", lambda **kw: [])(desde=hoy)[:10],
                "entrenamientos_proximos": getattr(jugador, "entrenamientos_proximos", lambda **kw: [])(desde=hoy)[:10],
            })
        else:
            messages.warning(request, "Tu perfil no está vinculado a un Jugador.")

    elif perfil.tipo == PerfilTipo.SOCIO:
        pass

    return render(request, "dashboard.html", ctx)


# ==========================
# Usuarios: lista / búsqueda
# ==========================
@login_required
def usuarios_lista(request):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para ver usuarios.")
        return redirect("dashboard")

    q = (request.GET.get("q") or "").strip()

    qs = (Perfil.objects
          .select_related("user")
          .order_by("apellido_paterno", "apellido_materno", "primer_nombre"))

    if q:
        qs = qs.filter(
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q) |
            Q(primer_nombre__icontains=q) |
            Q(segundo_nombre__icontains=q) |
            Q(apellido_paterno__icontains=q) |
            Q(apellido_materno__icontains=q) |
            Q(run__icontains=q) |
            Q(tipo__icontains=q)
        )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "usuarios/lista.html", {"page_obj": page_obj, "q": q})


# ==========================
# Usuarios: crear
# ==========================
@login_required
def usuarios_crear(request):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para crear usuarios.")
        return redirect("usuarios_lista")

    form = UsuarioCrearForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data

        # 1) User
        user = User.objects.create_user(
            username=cd["username"],
            email=cd.get("email") or "",
            password=cd["password1"],
            is_active=True,
        )

        # 2) Perfil
        perfil = Perfil.objects.create(
            user=user,
            tipo=cd["tipo"],
            run=cd["run"],
            telefono=cd.get("telefono") or "",
            primer_nombre=cd["primer_nombre"],
            segundo_nombre=cd.get("segundo_nombre") or "",
            apellido_paterno=cd["apellido_paterno"],
            apellido_materno=cd["apellido_materno"],
        )

        # 3) Datos extra si es JUGADOR (equipo opcional)
        if cd["tipo"] == PerfilTipo.JUGADOR:
            Jugador.objects.update_or_create(
                perfil=perfil,
                defaults={
                    "fecha_nacimiento": cd.get("fecha_nacimiento"),
                    "tipo_sangre": cd.get("tipo_sangre") or None,
                    "equipo": cd.get("equipo") or None,  # opcional
                }
            )

        messages.success(request, f"Usuario '{user.username}' creado correctamente.")
        return redirect("usuarios_lista")

    return render(request, "usuarios/form.html", {"form": form, "modo": "crear"})


# ==========================
# Usuarios: editar
# ==========================
@login_required
def usuarios_editar(request, perfil_id):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para editar usuarios.")
        return redirect("usuarios_lista")

    perfil = get_object_or_404(Perfil.objects.select_related("user"), pk=perfil_id)

    initial = dict(
        username=perfil.user.username,
        email=perfil.user.email,
        tipo=perfil.tipo,
        run=perfil.run,
        telefono=perfil.telefono,
        primer_nombre=perfil.primer_nombre,
        segundo_nombre=perfil.segundo_nombre,
        apellido_paterno=perfil.apellido_paterno,
        apellido_materno=perfil.apellido_materno,
        # Prefill de jugador
        fecha_nacimiento=getattr(getattr(perfil, "jugador", None), "fecha_nacimiento", None),
        tipo_sangre=getattr(getattr(perfil, "jugador", None), "tipo_sangre", "") or "",
        equipo=getattr(getattr(perfil, "jugador", None), "equipo", None),
    )

    form = UsuarioEditarForm(
        request.POST or None,
        initial=initial,
        user_obj=perfil.user,
        perfil_obj=perfil,
    )

    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data

        # 1) User
        perfil.user.username = cd["username"]
        perfil.user.email = cd.get("email") or ""
        if cd.get("password1"):
            perfil.user.set_password(cd["password1"])
        perfil.user.save()

        # 2) Perfil
        perfil.tipo = cd["tipo"]
        perfil.run = cd["run"]
        perfil.telefono = cd.get("telefono") or ""
        perfil.primer_nombre = cd["primer_nombre"]
        perfil.segundo_nombre = cd.get("segundo_nombre") or ""
        perfil.apellido_paterno = cd["apellido_paterno"]
        perfil.apellido_materno = cd["apellido_materno"]
        perfil.save()

        # 3) Jugador: crear/actualizar o eliminar según tipo (equipo opcional)
        if cd["tipo"] == PerfilTipo.JUGADOR:
            Jugador.objects.update_or_create(
                perfil=perfil,
                defaults={
                    "fecha_nacimiento": cd.get("fecha_nacimiento"),
                    "tipo_sangre": cd.get("tipo_sangre") or None,
                    "equipo": cd.get("equipo") or None,  # opcional
                }
            )
        else:
            Jugador.objects.filter(perfil=perfil).delete()

        messages.success(request, f"Usuario '{perfil.user.username}' actualizado.")
        return redirect("usuarios_lista")

    return render(request, "usuarios/form.html", {"form": form, "modo": "editar", "perfil": perfil})


# ==========================
# Usuarios: habilitar / deshabilitar
# ==========================
@login_required
def usuarios_toggle(request, perfil_id):
    if request.method != "POST":
        return redirect("usuarios_lista")

    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para modificar usuarios.")
        return redirect("usuarios_lista")

    perfil = get_object_or_404(Perfil.objects.select_related("user"), id=perfil_id)

    # Evita deshabilitar tu propia cuenta
    if perfil.user_id == request.user.id:
        messages.warning(request, "No puedes deshabilitar tu propia cuenta.")
        return redirect("usuarios_lista")

    perfil.user.is_active = not perfil.user.is_active
    perfil.user.save(update_fields=["is_active"])

    if perfil.user.is_active:
        messages.success(request, f"Usuario '{perfil.user.username}' habilitado.")
    else:
        messages.warning(request, f"Usuario '{perfil.user.username}' deshabilitado.")

    return redirect("usuarios_lista")
