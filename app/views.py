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

# ==========================
# Jugadores: lista / búsqueda
# ==========================
@login_required
def jugadores_lista(request):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para ver jugadores.")
        return redirect("dashboard")

    q = (request.GET.get("q") or "").strip()

    qs = (Jugador.objects
          .select_related("perfil__user", "equipo__categoria", "equipo__entrenador")
          .order_by("perfil__apellido_paterno", "perfil__apellido_materno", "perfil__primer_nombre"))

    if q:
        qs = qs.filter(
            Q(perfil__user__username__icontains=q) |
            Q(perfil__primer_nombre__icontains=q) |
            Q(perfil__segundo_nombre__icontains=q) |
            Q(perfil__apellido_paterno__icontains=q) |
            Q(perfil__apellido_materno__icontains=q) |
            Q(perfil__run__icontains=q) |
            Q(equipo__nombre__icontains=q) |
            Q(equipo__categoria__slug__icontains=q)
        )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "jugadores/lista.html", {"page_obj": page_obj, "q": q})


# ==========================
# Jugadores: editar
# ==========================
@login_required
def jugadores_editar(request, jugador_id):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para editar jugadores.")
        return redirect("jugadores_lista")

    jugador = get_object_or_404(
        Jugador.objects.select_related("perfil__user", "equipo"),
        pk=jugador_id
    )
    perfil = jugador.perfil

    initial = dict(
        username=perfil.user.username,
        email=perfil.user.email,
        tipo=PerfilTipo.JUGADOR,  # Forzar tipo JUGADOR
        run=perfil.run,
        telefono=perfil.telefono,
        primer_nombre=perfil.primer_nombre,
        segundo_nombre=perfil.segundo_nombre,
        apellido_paterno=perfil.apellido_paterno,
        apellido_materno=perfil.apellido_materno,
        fecha_nacimiento=jugador.fecha_nacimiento,
        tipo_sangre=jugador.tipo_sangre or "",
        equipo=jugador.equipo,
    )

    form = UsuarioEditarForm(
        request.POST or None,
        initial=initial,
        user_obj=perfil.user,
        perfil_obj=perfil,
    )
    
    # Deshabilitar el campo tipo para que no se pueda cambiar
    if 'tipo' in form.fields:
        form.fields['tipo'].disabled = True
        form.fields['tipo'].widget.attrs['readonly'] = True

    if request.method == "POST":
        # Debug: ver qué datos llegan
        print("POST data:", request.POST)
        print("Form errors:", form.errors)
        
        if form.is_valid():
            cd = form.cleaned_data
            
            # Debug: ver datos limpios
            print("Cleaned data:", cd)

            # 1) User
            perfil.user.username = cd["username"]
            perfil.user.email = cd.get("email") or ""
            if cd.get("password1"):
                perfil.user.set_password(cd["password1"])
            perfil.user.save()

            # 2) Perfil (mantener tipo JUGADOR siempre)
            perfil.tipo = PerfilTipo.JUGADOR  # Forzar tipo
            perfil.run = cd["run"]
            perfil.telefono = cd.get("telefono") or ""
            perfil.primer_nombre = cd["primer_nombre"]
            perfil.segundo_nombre = cd.get("segundo_nombre") or ""
            perfil.apellido_paterno = cd["apellido_paterno"]
            perfil.apellido_materno = cd["apellido_materno"]
            perfil.save()

            # 3) Jugador
            jugador.fecha_nacimiento = cd.get("fecha_nacimiento")
            jugador.tipo_sangre = cd.get("tipo_sangre") or None
            jugador.equipo = cd.get("equipo")
            jugador.save()

            messages.success(request, f"Jugador '{perfil.nombre_completo}' actualizado correctamente.")
            return redirect("jugadores_lista")
        else:
            # Si hay errores, mostrarlos
            messages.error(request, "Por favor corrige los errores en el formulario.")

    return render(request, "jugadores/form.html", {
        "form": form,
        "modo": "editar",
        "jugador": jugador
    })


# ==========================
# Jugadores: habilitar / deshabilitar
# ==========================
@login_required
def jugadores_toggle(request, jugador_id):
    if request.method != "POST":
        return redirect("jugadores_lista")

    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para modificar jugadores.")
        return redirect("jugadores_lista")

    jugador = get_object_or_404(
        Jugador.objects.select_related("perfil__user"),
        id=jugador_id
    )

    # Cambiar estado activo del jugador
    jugador.activo = not jugador.activo
    jugador.save(update_fields=["activo"])

    # También deshabilitar/habilitar la cuenta de usuario
    jugador.perfil.user.is_active = jugador.activo
    jugador.perfil.user.save(update_fields=["is_active"])

    if jugador.activo:
        messages.success(request, f"Jugador '{jugador.perfil.nombre_completo}' habilitado.")
    else:
        messages.warning(request, f"Jugador '{jugador.perfil.nombre_completo}' deshabilitado.")

    return redirect("jugadores_lista")

# ==========================
# Entrenadores: lista / búsqueda
# ==========================
@login_required
def entrenadores_lista(request):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para ver entrenadores.")
        return redirect("dashboard")

    q = (request.GET.get("q") or "").strip()

    # Los entrenadores son Perfiles con tipo ENTRENADOR
    qs = (Perfil.objects
          .filter(tipo=PerfilTipo.ENTRENADOR)
          .select_related("user")
          .prefetch_related("equipos_dirigidos")
          .order_by("apellido_paterno", "apellido_materno", "primer_nombre"))

    if q:
        qs = qs.filter(
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q) |
            Q(primer_nombre__icontains=q) |
            Q(segundo_nombre__icontains=q) |
            Q(apellido_paterno__icontains=q) |
            Q(apellido_materno__icontains=q) |
            Q(run__icontains=q)
        )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "entrenadores/lista.html", {"page_obj": page_obj, "q": q})


# ==========================
# Entrenadores: editar
# ==========================
@login_required
def entrenadores_editar(request, perfil_id):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para editar entrenadores.")
        return redirect("entrenadores_lista")

    perfil = get_object_or_404(
        Perfil.objects.select_related("user").filter(tipo=PerfilTipo.ENTRENADOR),
        pk=perfil_id
    )

    initial = dict(
        username=perfil.user.username,
        email=perfil.user.email,
        tipo=PerfilTipo.ENTRENADOR,
        run=perfil.run,
        telefono=perfil.telefono,
        primer_nombre=perfil.primer_nombre,
        segundo_nombre=perfil.segundo_nombre,
        apellido_paterno=perfil.apellido_paterno,
        apellido_materno=perfil.apellido_materno,
    )

    form = UsuarioEditarForm(
        request.POST or None,
        initial=initial,
        user_obj=perfil.user,
        perfil_obj=perfil,
    )
    
    # Deshabilitar el campo tipo para que no se pueda cambiar
    if 'tipo' in form.fields:
        form.fields['tipo'].disabled = True
        form.fields['tipo'].widget.attrs['readonly'] = True

    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data

        # 1) User
        perfil.user.username = cd["username"]
        perfil.user.email = cd.get("email") or ""
        if cd.get("password1"):
            perfil.user.set_password(cd["password1"])
        perfil.user.save()

        # 2) Perfil (mantener tipo ENTRENADOR)
        perfil.tipo = PerfilTipo.ENTRENADOR
        perfil.run = cd["run"]
        perfil.telefono = cd.get("telefono") or ""
        perfil.primer_nombre = cd["primer_nombre"]
        perfil.segundo_nombre = cd.get("segundo_nombre") or ""
        perfil.apellido_paterno = cd["apellido_paterno"]
        perfil.apellido_materno = cd["apellido_materno"]
        perfil.save()

        messages.success(request, f"Entrenador '{perfil.nombre_completo}' actualizado correctamente.")
        return redirect("entrenadores_lista")

    return render(request, "entrenadores/form.html", {
        "form": form,
        "modo": "editar",
        "perfil": perfil
    })


# ==========================
# Entrenadores: habilitar / deshabilitar
# ==========================
@login_required
def entrenadores_toggle(request, perfil_id):
    if request.method != "POST":
        return redirect("entrenadores_lista")

    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para modificar entrenadores.")
        return redirect("entrenadores_lista")

    perfil = get_object_or_404(
        Perfil.objects.select_related("user").filter(tipo=PerfilTipo.ENTRENADOR),
        id=perfil_id
    )

    # Evita deshabilitar tu propia cuenta
    if perfil.user_id == request.user.id:
        messages.warning(request, "No puedes deshabilitar tu propia cuenta.")
        return redirect("entrenadores_lista")

    perfil.user.is_active = not perfil.user.is_active
    perfil.user.save(update_fields=["is_active"])

    if perfil.user.is_active:
        messages.success(request, f"Entrenador '{perfil.nombre_completo}' habilitado.")
    else:
        messages.warning(request, f"Entrenador '{perfil.nombre_completo}' deshabilitado.")

    return redirect("entrenadores_lista")



# ==========================
# Equipos: lista / búsqueda
# ==========================
@login_required
def equipos_lista(request):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para ver equipos.")
        return redirect("dashboard")

    q = (request.GET.get("q") or "").strip()

    qs = (Equipo.objects
          .select_related("categoria", "entrenador")
          .prefetch_related("jugadores")
          .order_by("categoria__slug", "nombre"))

    if q:
        qs = qs.filter(
            Q(nombre__icontains=q) |
            Q(categoria__slug__icontains=q) |
            Q(categoria__descripcion__icontains=q) |
            Q(entrenador__primer_nombre__icontains=q) |
            Q(entrenador__apellido_paterno__icontains=q)
        )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "equipos/lista.html", {"page_obj": page_obj, "q": q})


# ==========================
# Equipos: crear
# ==========================
@login_required
def equipos_crear(request):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para crear equipos.")
        return redirect("equipos_lista")

    from .models import Categoria
    
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        categoria_id = request.POST.get("categoria")
        entrenador_id = request.POST.get("entrenador")

        # Validaciones
        if not nombre:
            messages.error(request, "El nombre del equipo es obligatorio.")
        elif not categoria_id:
            messages.error(request, "Debes seleccionar una categoría.")
        elif not entrenador_id:
            messages.error(request, "Debes asignar un entrenador.")
        else:
            try:
                categoria = Categoria.objects.get(pk=categoria_id)
                entrenador = Perfil.objects.get(pk=entrenador_id, tipo=PerfilTipo.ENTRENADOR)
                
                # Verificar duplicados
                if Equipo.objects.filter(nombre=nombre, categoria=categoria).exists():
                    messages.error(request, f"Ya existe un equipo '{nombre}' en la categoría '{categoria}'.")
                else:
                    Equipo.objects.create(
                        nombre=nombre,
                        categoria=categoria,
                        entrenador=entrenador
                    )
                    messages.success(request, f"Equipo '{nombre}' creado correctamente.")
                    return redirect("equipos_lista")
            except (Categoria.DoesNotExist, Perfil.DoesNotExist):
                messages.error(request, "Categoría o entrenador inválido.")

    # Obtener datos para el formulario
    categorias = Categoria.objects.all().order_by("slug")
    entrenadores = Perfil.objects.filter(tipo=PerfilTipo.ENTRENADOR, user__is_active=True).order_by("apellido_paterno", "primer_nombre")

    return render(request, "equipos/form.html", {
        "categorias": categorias,
        "entrenadores": entrenadores,
        "modo": "crear"
    })


# ==========================
# Equipos: editar
# ==========================
@login_required
def equipos_editar(request, equipo_id):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para editar equipos.")
        return redirect("equipos_lista")

    from .models import Categoria
    equipo = get_object_or_404(Equipo.objects.select_related("categoria", "entrenador"), pk=equipo_id)

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        categoria_id = request.POST.get("categoria")
        entrenador_id = request.POST.get("entrenador")

        # Validaciones
        if not nombre:
            messages.error(request, "El nombre del equipo es obligatorio.")
        elif not categoria_id:
            messages.error(request, "Debes seleccionar una categoría.")
        elif not entrenador_id:
            messages.error(request, "Debes asignar un entrenador.")
        else:
            try:
                categoria = Categoria.objects.get(pk=categoria_id)
                entrenador = Perfil.objects.get(pk=entrenador_id, tipo=PerfilTipo.ENTRENADOR)
                
                # Verificar duplicados (excluyendo el actual)
                if Equipo.objects.filter(nombre=nombre, categoria=categoria).exclude(pk=equipo.pk).exists():
                    messages.error(request, f"Ya existe otro equipo '{nombre}' en la categoría '{categoria}'.")
                else:
                    equipo.nombre = nombre
                    equipo.categoria = categoria
                    equipo.entrenador = entrenador
                    equipo.save()
                    messages.success(request, f"Equipo '{nombre}' actualizado correctamente.")
                    return redirect("equipos_lista")
            except (Categoria.DoesNotExist, Perfil.DoesNotExist):
                messages.error(request, "Categoría o entrenador inválido.")

    # Obtener datos para el formulario
    categorias = Categoria.objects.all().order_by("slug")
    entrenadores = Perfil.objects.filter(tipo=PerfilTipo.ENTRENADOR, user__is_active=True).order_by("apellido_paterno", "primer_nombre")

    return render(request, "equipos/form.html", {
        "equipo": equipo,
        "categorias": categorias,
        "entrenadores": entrenadores,
        "modo": "editar"
    })


# ==========================
# Equipos: eliminar
# ==========================
@login_required
def equipos_eliminar(request, equipo_id):
    if request.method != "POST":
        return redirect("equipos_lista")

    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para eliminar equipos.")
        return redirect("equipos_lista")

    equipo = get_object_or_404(Equipo, pk=equipo_id)
    
    # Verificar si tiene jugadores asignados
    num_jugadores = equipo.jugadores.count()
    if num_jugadores > 0:
        messages.warning(request, f"No se puede eliminar el equipo '{equipo.nombre}' porque tiene {num_jugadores} jugador(es) asignado(s).")
        return redirect("equipos_lista")

    nombre = equipo.nombre
    equipo.delete()
    messages.success(request, f"Equipo '{nombre}' eliminado correctamente.")
    return redirect("equipos_lista")


# ==========================
# Equipos: detalle (ver jugadores)
# ==========================
@login_required
def equipos_detalle(request, equipo_id):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para ver detalles de equipos.")
        return redirect("dashboard")

    equipo = get_object_or_404(
        Equipo.objects
        .select_related("categoria", "entrenador")
        .prefetch_related("jugadores__perfil__user"),
        pk=equipo_id
    )

    jugadores = equipo.jugadores.filter(activo=True).order_by("perfil__apellido_paterno", "perfil__apellido_materno")

    return render(request, "equipos/detalle.html", {
        "equipo": equipo,
        "jugadores": jugadores
    })


# ==========================
# Actividades Deportivas: lista / búsqueda
# ==========================
@login_required
def actividades_lista(request):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para ver actividades deportivas.")
        return redirect("dashboard")

    q = (request.GET.get("q") or "").strip()
    tipo_filtro = request.GET.get("tipo", "")

    qs = (ActividadDeportiva.objects
          .prefetch_related("equipos__categoria")
          .order_by("-fecha_inicio", "titulo"))

    if q:
        qs = qs.filter(
            Q(titulo__icontains=q) |
            Q(descripcion__icontains=q) |
            Q(equipos__nombre__icontains=q)
        ).distinct()

    if tipo_filtro:
        qs = qs.filter(tipo=tipo_filtro)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    
    from .models import ActividadTipo
    return render(request, "actividades/lista.html", {
        "page_obj": page_obj,
        "q": q,
        "tipo_filtro": tipo_filtro,
        "tipos": ActividadTipo.choices
    })


# ==========================
# Actividades Deportivas: crear
# ==========================
@login_required
def actividades_crear(request):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para crear actividades deportivas.")
        return redirect("actividades_lista")

    from .models import ActividadTipo
    from datetime import datetime

    if request.method == "POST":
        titulo = request.POST.get("titulo", "").strip()
        tipo = request.POST.get("tipo", "")
        fecha_inicio = request.POST.get("fecha_inicio", "")
        fecha_fin = request.POST.get("fecha_fin", "")
        descripcion = request.POST.get("descripcion", "").strip()
        equipos_ids = request.POST.getlist("equipos")

        # Validaciones
        if not titulo:
            messages.error(request, "El título es obligatorio.")
        elif not tipo:
            messages.error(request, "Debes seleccionar un tipo de actividad.")
        elif not fecha_inicio or not fecha_fin:
            messages.error(request, "Las fechas de inicio y fin son obligatorias.")
        elif not equipos_ids:
            messages.error(request, "Debes seleccionar al menos un equipo.")
        else:
            try:
                # Convertir fechas
                fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

                if fecha_fin_obj < fecha_inicio_obj:
                    messages.error(request, "La fecha de fin no puede ser anterior a la fecha de inicio.")
                else:
                    # Crear actividad
                    actividad = ActividadDeportiva.objects.create(
                        titulo=titulo,
                        tipo=tipo,
                        fecha_inicio=fecha_inicio_obj,
                        fecha_fin=fecha_fin_obj,
                        descripcion=descripcion
                    )

                    # Asociar equipos
                    equipos = Equipo.objects.filter(id__in=equipos_ids)
                    actividad.equipos.set(equipos)

                    messages.success(request, f"Actividad '{titulo}' creada correctamente.")
                    return redirect("actividades_lista")

            except ValueError:
                messages.error(request, "Formato de fecha inválido.")
            except Exception as e:
                messages.error(request, f"Error al crear la actividad: {str(e)}")

    # Obtener datos para el formulario
    equipos = Equipo.objects.select_related("categoria").order_by("categoria__slug", "nombre")
    tipos = ActividadTipo.choices

    return render(request, "actividades/form.html", {
        "equipos": equipos,
        "tipos": tipos,
        "modo": "crear"
    })


# ==========================
# Actividades Deportivas: editar
# ==========================
@login_required
def actividades_editar(request, actividad_id):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para editar actividades deportivas.")
        return redirect("actividades_lista")

    from .models import ActividadTipo
    from datetime import datetime

    actividad = get_object_or_404(
        ActividadDeportiva.objects.prefetch_related("equipos"),
        pk=actividad_id
    )

    if request.method == "POST":
        titulo = request.POST.get("titulo", "").strip()
        tipo = request.POST.get("tipo", "")
        fecha_inicio = request.POST.get("fecha_inicio", "")
        fecha_fin = request.POST.get("fecha_fin", "")
        descripcion = request.POST.get("descripcion", "").strip()
        equipos_ids = request.POST.getlist("equipos")

        # Validaciones
        if not titulo:
            messages.error(request, "El título es obligatorio.")
        elif not tipo:
            messages.error(request, "Debes seleccionar un tipo de actividad.")
        elif not fecha_inicio or not fecha_fin:
            messages.error(request, "Las fechas de inicio y fin son obligatorias.")
        elif not equipos_ids:
            messages.error(request, "Debes seleccionar al menos un equipo.")
        else:
            try:
                # Convertir fechas
                fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

                if fecha_fin_obj < fecha_inicio_obj:
                    messages.error(request, "La fecha de fin no puede ser anterior a la fecha de inicio.")
                else:
                    # Actualizar actividad
                    actividad.titulo = titulo
                    actividad.tipo = tipo
                    actividad.fecha_inicio = fecha_inicio_obj
                    actividad.fecha_fin = fecha_fin_obj
                    actividad.descripcion = descripcion
                    actividad.save()

                    # Actualizar equipos
                    equipos = Equipo.objects.filter(id__in=equipos_ids)
                    actividad.equipos.set(equipos)

                    messages.success(request, f"Actividad '{titulo}' actualizada correctamente.")
                    return redirect("actividades_lista")

            except ValueError:
                messages.error(request, "Formato de fecha inválido.")
            except Exception as e:
                messages.error(request, f"Error al actualizar la actividad: {str(e)}")

    # Obtener datos para el formulario
    equipos = Equipo.objects.select_related("categoria").order_by("categoria__slug", "nombre")
    tipos = ActividadTipo.choices
    equipos_seleccionados = list(actividad.equipos.values_list("id", flat=True))

    return render(request, "actividades/form.html", {
        "actividad": actividad,
        "equipos": equipos,
        "tipos": tipos,
        "equipos_seleccionados": equipos_seleccionados,
        "modo": "editar"
    })


# ==========================
# Actividades Deportivas: eliminar
# ==========================
@login_required
def actividades_eliminar(request, actividad_id):
    if request.method != "POST":
        return redirect("actividades_lista")

    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para eliminar actividades deportivas.")
        return redirect("actividades_lista")

    actividad = get_object_or_404(ActividadDeportiva, pk=actividad_id)
    
    # Verificar si tiene asistencias registradas
    from .models import Asistencia
    num_asistencias = Asistencia.objects.filter(actividad=actividad).count()
    
    if num_asistencias > 0:
        messages.warning(request, f"No se puede eliminar la actividad '{actividad.titulo}' porque tiene {num_asistencias} asistencia(s) registrada(s).")
        return redirect("actividades_lista")

    titulo = actividad.titulo
    actividad.delete()
    messages.success(request, f"Actividad '{titulo}' eliminada correctamente.")
    return redirect("actividades_lista")


# ==========================
# Actividades Deportivas: detalle
# ==========================
@login_required
def actividades_detalle(request, actividad_id):
    if not _es_admin_equipo(request.user):
        messages.error(request, "No tienes permisos para ver detalles de actividades.")
        return redirect("dashboard")

    actividad = get_object_or_404(
        ActividadDeportiva.objects.prefetch_related(
            "equipos__categoria",
            "equipos__jugadores__perfil"
        ),
        pk=actividad_id
    )

    # Obtener todos los jugadores de los equipos participantes
    jugadores_totales = []
    for equipo in actividad.equipos.all():
        jugadores = equipo.jugadores.filter(activo=True).select_related("perfil")
        jugadores_totales.extend(jugadores)

    return render(request, "actividades/detalle.html", {
        "actividad": actividad,
        "jugadores_totales": jugadores_totales
    })


# ==========================
# Asistencias: lista / búsqueda
# ==========================
@login_required
def asistencias_lista(request):
    # Permisos: Admin, Equipo Admin o Entrenador
    perfil = getattr(request.user, "perfil", None)
    es_entrenador = perfil and perfil.tipo == PerfilTipo.ENTRENADOR
    
    if not (_es_admin_equipo(request.user) or es_entrenador):
        messages.error(request, "No tienes permisos para ver asistencias.")
        return redirect("dashboard")

    q = (request.GET.get("q") or "").strip()
    actividad_id = request.GET.get("actividad", "")
    estado_filtro = request.GET.get("estado", "")

    from .models import Asistencia, AsistenciaEstado
    
    qs = (Asistencia.objects
          .select_related("jugador__perfil", "jugador__equipo", "actividad", "entrenador")
          .order_by("-fecha_hora_marcaje"))

    # Si es entrenador, solo ver sus propias asistencias
    if es_entrenador and not request.user.is_superuser:
        qs = qs.filter(entrenador=perfil)

    if q:
        qs = qs.filter(
            Q(jugador__perfil__primer_nombre__icontains=q) |
            Q(jugador__perfil__apellido_paterno__icontains=q) |
            Q(jugador__perfil__apellido_materno__icontains=q) |
            Q(actividad__titulo__icontains=q)
        )

    if actividad_id:
        qs = qs.filter(actividad_id=actividad_id)

    if estado_filtro:
        qs = qs.filter(estado=estado_filtro)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    
    # Para los filtros
    actividades = ActividadDeportiva.objects.order_by("-fecha_inicio")[:50]
    
    return render(request, "asistencias/lista.html", {
        "page_obj": page_obj,
        "q": q,
        "actividad_id": actividad_id,
        "estado_filtro": estado_filtro,
        "actividades": actividades,
        "estados": AsistenciaEstado.choices
    })


# ==========================
# Asistencias: registrar (por actividad)
# ==========================
@login_required
def asistencias_registrar(request):
    perfil = getattr(request.user, "perfil", None)
    es_entrenador = perfil and perfil.tipo == PerfilTipo.ENTRENADOR
    
    if not (_es_admin_equipo(request.user) or es_entrenador):
        messages.error(request, "No tienes permisos para registrar asistencias.")
        return redirect("dashboard")

    from .models import Asistencia, AsistenciaEstado
    from datetime import datetime, timedelta

    if request.method == "POST":
        actividad_id = request.POST.get("actividad")
        fecha_hora_marcaje = request.POST.get("fecha_hora_marcaje")
        jugadores_presentes = request.POST.getlist("presentes")
        jugadores_ausentes = request.POST.getlist("ausentes")

        # Validaciones
        if not actividad_id:
            messages.error(request, "Debes seleccionar una actividad.")
        elif not fecha_hora_marcaje:
            messages.error(request, "Debes especificar la fecha y hora del marcaje.")
        else:
            try:
                actividad = ActividadDeportiva.objects.get(pk=actividad_id)
                fecha_hora_obj = datetime.strptime(fecha_hora_marcaje, "%Y-%m-%dT%H:%M")

                # Validar que la fecha esté dentro del rango de la actividad
                if not (actividad.fecha_inicio <= fecha_hora_obj.date() <= actividad.fecha_fin):
                    messages.error(request, "La fecha/hora de marcaje debe estar dentro del rango de la actividad.")
                else:
                    # Determinar el entrenador que registra
                    if es_entrenador and not request.user.is_superuser:
                        entrenador_perfil = perfil
                    else:
                        entrenador_id = request.POST.get("entrenador")
                        if not entrenador_id:
                            messages.error(request, "Debes seleccionar un entrenador.")
                            return redirect("asistencias_registrar")
                        entrenador_perfil = Perfil.objects.get(pk=entrenador_id, tipo=PerfilTipo.ENTRENADOR)

                    registros_creados = 0
                    registros_actualizados = 0

                    # Registrar presentes
                    for jugador_id in jugadores_presentes:
                        jugador = Jugador.objects.get(pk=jugador_id)
                        asistencia, created = Asistencia.objects.update_or_create(
                            jugador=jugador,
                            actividad=actividad,
                            defaults={
                                "entrenador": entrenador_perfil,
                                "estado": AsistenciaEstado.PRESENTE,
                                "fecha_hora_marcaje": fecha_hora_obj
                            }
                        )
                        if created:
                            registros_creados += 1
                        else:
                            registros_actualizados += 1

                    # Registrar ausentes
                    for jugador_id in jugadores_ausentes:
                        jugador = Jugador.objects.get(pk=jugador_id)
                        asistencia, created = Asistencia.objects.update_or_create(
                            jugador=jugador,
                            actividad=actividad,
                            defaults={
                                "entrenador": entrenador_perfil,
                                "estado": AsistenciaEstado.AUSENTE,
                                "fecha_hora_marcaje": fecha_hora_obj
                            }
                        )
                        if created:
                            registros_creados += 1
                        else:
                            registros_actualizados += 1

                    messages.success(request, f"Asistencias registradas: {registros_creados} nuevas, {registros_actualizados} actualizadas.")
                    return redirect("asistencias_lista")

            except ActividadDeportiva.DoesNotExist:
                messages.error(request, "Actividad no encontrada.")
            except Jugador.DoesNotExist:
                messages.error(request, "Jugador no encontrado.")
            except Perfil.DoesNotExist:
                messages.error(request, "Entrenador no encontrado.")
            except ValueError:
                messages.error(request, "Formato de fecha/hora inválido.")
            except Exception as e:
                messages.error(request, f"Error al registrar asistencias: {str(e)}")

    # GET: Mostrar formulario
    from datetime import date
    actividades = ActividadDeportiva.objects.filter(
        fecha_fin__gte=date.today()
    ).order_by("fecha_inicio")[:20]
    
    entrenadores = None
    if not es_entrenador or request.user.is_superuser:
        entrenadores = Perfil.objects.filter(
            tipo=PerfilTipo.ENTRENADOR, 
            user__is_active=True
        ).order_by("apellido_paterno", "primer_nombre")

    # Obtener hora actual UTC y convertir a Chile (UTC-3)
    ahora_utc = datetime.utcnow()
    ahora_chile = ahora_utc - timedelta(hours=3)  # Chile está en UTC-3
    fecha_hora_actual = ahora_chile.strftime('%Y-%m-%dT%H:%M')

    return render(request, "asistencias/registrar.html", {
        "actividades": actividades,
        "entrenadores": entrenadores,
        "es_entrenador": es_entrenador,
        "fecha_hora_actual": fecha_hora_actual
    })

# ==========================
# Asistencias: obtener jugadores de actividad (AJAX)
# ==========================
@login_required
def asistencias_jugadores_actividad(request, actividad_id):
    """Endpoint para obtener jugadores de una actividad (para el formulario de registro)"""
    try:
        actividad = ActividadDeportiva.objects.get(pk=actividad_id)
        
        # Obtener todos los jugadores de los equipos participantes
        jugadores_list = []
        for equipo in actividad.equipos.all():
            jugadores = equipo.jugadores.filter(activo=True).select_related("perfil")
            for jugador in jugadores:
                # Verificar si ya tiene asistencia registrada
                asistencia_existente = None
                try:
                    from .models import Asistencia
                    asistencia_existente = Asistencia.objects.get(
                        jugador=jugador,
                        actividad=actividad
                    )
                except Asistencia.DoesNotExist:
                    pass

                jugadores_list.append({
                    "id": jugador.id,
                    "nombre": jugador.perfil.nombre_completo,
                    "equipo": equipo.nombre,
                    "asistencia_actual": asistencia_existente.get_estado_display() if asistencia_existente else None
                })

        from django.http import JsonResponse
        return JsonResponse({"jugadores": jugadores_list})
    
    except ActividadDeportiva.DoesNotExist:
        from django.http import JsonResponse
        return JsonResponse({"error": "Actividad no encontrada"}, status=404)


# ==========================
# Asistencias: editar
# ==========================
@login_required
def asistencias_editar(request, asistencia_id):
    perfil = getattr(request.user, "perfil", None)
    es_entrenador = perfil and perfil.tipo == PerfilTipo.ENTRENADOR
    
    if not (_es_admin_equipo(request.user) or es_entrenador):
        messages.error(request, "No tienes permisos para editar asistencias.")
        return redirect("asistencias_lista")

    from .models import Asistencia, AsistenciaEstado
    from datetime import datetime

    asistencia = get_object_or_404(
        Asistencia.objects.select_related("jugador__perfil", "actividad", "entrenador"),
        pk=asistencia_id
    )

    # Validar que el entrenador solo pueda editar sus propias asistencias
    if es_entrenador and not request.user.is_superuser:
        if asistencia.entrenador != perfil:
            messages.error(request, "Solo puedes editar tus propias asistencias.")
            return redirect("asistencias_lista")

    if request.method == "POST":
        estado = request.POST.get("estado")
        fecha_hora_marcaje = request.POST.get("fecha_hora_marcaje")

        if not estado or not fecha_hora_marcaje:
            messages.error(request, "Todos los campos son obligatorios.")
        else:
            try:
                fecha_hora_obj = datetime.strptime(fecha_hora_marcaje, "%Y-%m-%dT%H:%M")

                # Validar que la fecha esté dentro del rango de la actividad
                if not (asistencia.actividad.fecha_inicio <= fecha_hora_obj.date() <= asistencia.actividad.fecha_fin):
                    messages.error(request, "La fecha/hora de marcaje debe estar dentro del rango de la actividad.")
                else:
                    asistencia.estado = estado
                    asistencia.fecha_hora_marcaje = fecha_hora_obj
                    asistencia.save()

                    messages.success(request, "Asistencia actualizada correctamente.")
                    return redirect("asistencias_lista")

            except ValueError:
                messages.error(request, "Formato de fecha/hora inválido.")

    from .models import AsistenciaEstado
    return render(request, "asistencias/editar.html", {
        "asistencia": asistencia,
        "estados": AsistenciaEstado.choices
    })


# ==========================
# Asistencias: eliminar
# ==========================
@login_required
def asistencias_eliminar(request, asistencia_id):
    if request.method != "POST":
        return redirect("asistencias_lista")

    perfil = getattr(request.user, "perfil", None)
    es_entrenador = perfil and perfil.tipo == PerfilTipo.ENTRENADOR
    
    if not (_es_admin_equipo(request.user) or es_entrenador):
        messages.error(request, "No tienes permisos para eliminar asistencias.")
        return redirect("asistencias_lista")

    from .models import Asistencia
    asistencia = get_object_or_404(Asistencia, pk=asistencia_id)

    # Validar que el entrenador solo pueda eliminar sus propias asistencias
    if es_entrenador and not request.user.is_superuser:
        if asistencia.entrenador != perfil:
            messages.error(request, "Solo puedes eliminar tus propias asistencias.")
            return redirect("asistencias_lista")

    jugador_nombre = asistencia.jugador.perfil.nombre_completo
    actividad_titulo = asistencia.actividad.titulo
    
    asistencia.delete()
    messages.success(request, f"Asistencia de {jugador_nombre} en '{actividad_titulo}' eliminada correctamente.")
    return redirect("asistencias_lista")