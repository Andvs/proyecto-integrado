# --- Importaciones estándar de Django y del proyecto ---
from django.shortcuts import render, redirect, get_object_or_404  # helpers para vistas y redirecciones
from django.core.paginator import Paginator                         # paginación de listas
from django.db.models import Q                                      # consultas OR/AND dinámicas
from django.contrib import messages                                 # sistema de mensajes flash
from django.contrib.auth.hashers import make_password, check_password  # hash/verificación de contraseñas
from .form import *                                                 # formularios locales (UsuarioForm, etc.)
from .models import *                                               # modelos locales (Usuario, Jugador, etc.)
from urllib.parse import unquote                                    # decodificar 'next' en URLs

# Create your views here.
def index(request):
    """
    Vista simple de inicio.
    Renderiza la plantilla 'index.html' sin contexto adicional.
    """
    return render(request, "index.html")

def formulario(request):
    """
    Crea un Usuario usando UsuarioForm.
    - Si es POST: valida el formulario, hashea la contraseña y guarda.
    - Si es GET: muestra el formulario vacío.
    Importante: la contraseña NO se guarda en texto plano; se usa make_password.
    """
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            # Guardamos el usuario sin escribir aún en BD para poder intervenir la contraseña
            usuario = form.save(commit=False)

            # Tomamos la contraseña validada del form y la transformamos a hash seguro
            contraseña_plana = form.cleaned_data['contraseña']
            usuario.contraseña = make_password(contraseña_plana)

            # Persistimos el usuario
            usuario.save()
            # Volvemos a la lista/visualización de usuarios
            return redirect("visualizacion")
    else:
        # Primera carga o petición GET: formulario vacío
        form = UsuarioForm()

    # Volvemos a pintar el formulario (con errores si los hubiera)
    return render(request, "usuarios/formulario.html", {"form": form})

# --- VISTA DE LOGIN CON DEPURACIÓN ---
def login(request):
    """
    Autenticación manual basada en el modelo Usuario del proyecto (no el auth.User estándar).
    Flujo:
        1) Busca el usuario por nombre de usuario.
        2) Verifica la contraseña con check_password.
        3) Bloquea el ingreso si Usuario.activo == False.
        4) Si el usuario tiene un Jugador vinculado y ese Jugador está inactivo, también bloquea.
        5) En caso OK, guarda 'usuario_id' en la sesión y redirige a 'next' o 'dashboard'.
    """
    if request.method == 'POST':
        # Normalizamos entradas del form
        nombre_usuario = (request.POST.get('nombre_usuario') or '').strip()
        contrasena = request.POST.get('contraseña') or ''

        # 1) Buscar usuario por nombre de usuario
        try:
            usuario = Usuario.objects.get(nombre_usuario=nombre_usuario)
        except Usuario.DoesNotExist:
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
            return redirect('login')

        # 2) Validar contraseña usando el hash almacenado
        if not check_password(contrasena, usuario.contraseña):
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
            return redirect('login')

        # 3) Bloqueo por cuenta de Usuario inactiva
        if not usuario.activo:
            messages.error(request, 'Esta cuenta ha sido deshabilitada.')
            return redirect('login')

        # 4) Bloqueo si existe Jugador vinculado y está inactivo
        jugador = Jugador.objects.filter(usuario=usuario).first()
        if jugador is not None and not jugador.activo:
            messages.error(request, 'Tu perfil de jugador está deshabilitado; no puedes ingresar.')
            return redirect('login')

        # 5) Autenticación exitosa: persistimos el id en la sesión y redirigimos
        request.session['usuario_id'] = usuario.id
        messages.success(request, f'Bienvenido, {usuario.nombre_usuario}')
        next_url = request.GET.get('next')  # permite volver a la página que pidió login
        return redirect(next_url or 'dashboard')

    # GET: mostrar formulario de login
    return render(request, 'login.html')

def visualizacion(request):
    """
    Lista paginada de Usuarios con búsqueda flexible:
    - Busca por texto en nombre de usuario y nombre del rol.
    - Si el query coincide con términos de 'activo'/'inactivo', filtra por el booleano además del texto.
    - Paginación de 10 elementos por página.
    Contexto expuesto: page_obj (página actual) y search_query (cadena de búsqueda).
    """
    query = request.GET.get('q')
    usuarios_list = Usuario.objects.all().order_by('id')

    if query:
        # Búsqueda textual base
        text_query = (
            Q(nombre_usuario__icontains=query) |
            Q(rol__nombre__icontains=query)  # Asumiendo que rol tiene campo 'nombre'
        )

        # Soporte a búsquedas tipo "activo"/"inactivo" interpretando la cadena del usuario
        query_lower = query.lower()

        # Palabras que interpretamos como "activo=True"
        palabras_activo = ['si', 'sí', 'activo', 'activos', 'true', '1']

        # Palabras que interpretamos como "activo=False"
        palabras_inactivo = ['no', 'inactivo', 'inactivos', 'false', '0']

        if query_lower in palabras_activo:
            final_query = text_query | Q(activo=True)
        elif query_lower in palabras_inactivo:
            final_query = text_query | Q(activo=False)
        else:
            final_query = text_query

        # Filtramos y evitamos duplicados por joins
        usuarios_list = usuarios_list.filter(final_query).distinct()

    # Paginación (10 por página)
    paginator = Paginator(usuarios_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': query,
    }
    return render(request, 'usuarios/visualizacion.html', context)

def editar_usuario(request, usuario_id):
    """
    Edita un Usuario existente.
    - GET: muestra el formulario precargado.
    - POST: valida y guarda cambios; luego redirige a la visualización.
    """
    usuario = get_object_or_404(Usuario, pk=usuario_id)

    if request.method == 'POST':
        # Cargamos datos enviados sobre la instancia existente
        form = UsuarioEditForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'¡Usuario "{usuario.nombre_usuario}" actualizado correctamente!')
            return redirect('visualizacion')  # usar el name de la URL de visualización
    else:
        # Mostramos el formulario con los datos actuales
        form = UsuarioEditForm(instance=usuario)

    context = {
        'form': form,
        'usuario': usuario,
    }
    return render(request, 'usuarios/editar.html', context)

def desabilitar_usuario(request, user_id):
    """
    Deshabilita (activo=False) un Usuario por su id.
    Seguridad/UX:
    - Previene que el usuario actualmente logueado se deshabilite a sí mismo.
    - Muestra mensajes de éxito/error y vuelve a la lista de usuarios.
    Nota: el nombre de la función mantiene el mismo identificador aunque “desabilitar” está con una ‘b’.
    """
    # Evita que el usuario activo se autodeshabilite
    logged_in_user_id = request.session.get('usuario_id')
    if logged_in_user_id == user_id:
        messages.error(request, 'No puedes deshabilitar tu propia cuenta mientras la usas.', extra_tags='danger')
        return redirect('visualizacion')

    # Marcamos el usuario como inactivo
    usuario = get_object_or_404(Usuario, id=user_id)
    usuario.activo = False
    usuario.save()
    messages.success(request, f'El usuario "{usuario.nombre_usuario}" ha sido deshabilitado correctamente.')
    return redirect('visualizacion')

def dashboard(request):
    """
    Muestra un panel simple (placeholder) tras el login correcto.
    """
    return render(request, "dashboard.html")

# -------------------------
#   SECCIÓN: JUGADORES
# -------------------------
def formulario_jugadores(request):
    """
    Crea un Jugador utilizando JugadorForm.
    - POST válido: guarda y redirige a listado de jugadores.
    - POST inválido: muestra errores.
    - GET: muestra formulario vacío.
    """
    if request.method == "POST":
        form = JugadorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Jugador registrado exitosamente!")
            return redirect("visualizacion_jugadores")
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = JugadorForm()

    return render(request, "jugadores/formulario.html", {"form": form})

def visualizacion_jugadores(request):
    """
    Lista paginada de Jugadores con filtros de búsqueda:
    - Campos de texto: nombre, apellido, RUN, nombre de equipo, categoría de equipo.
    - Palabras clave para estado: 'activo'/'inactivo' como en usuarios.
    - Optimización: select_related para evitar N+1 en equipo/categoría/entrenador.
    """
    query = request.GET.get('q')
    jugadores_list = (
        Jugador.objects
        .select_related('equipo', 'equipo__categoria', 'equipo__entrenador')  # join para rendimiento
        .all()
        .order_by('id')
    )

    if query:
        # Filtro textual
        text_query = (
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query) |
            Q(run__icontains=query) |
            Q(equipo__nombre__icontains=query) |
            Q(equipo__categoria__nombre__icontains=query)
        )

        # Filtro por estado activo/inactivo interpretando texto ingresado
        query_lower = query.lower()
        palabras_activo = ['si', 'sí', 'activo', 'activos', 'true', '1']
        palabras_inactivo = ['no', 'inactivo', 'inactivos', 'false', '0']

        if query_lower in palabras_activo:
            final_query = text_query | Q(activo=True)
        elif query_lower in palabras_inactivo:
            final_query = text_query | Q(activo=False)
        else:
            final_query = text_query

        jugadores_list = jugadores_list.filter(final_query).distinct()

    # Paginación
    paginator = Paginator(jugadores_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': query,
    }
    return render(request, "jugadores/visualizacion.html", context)

def editar_jugador(request, jugador_id):
    """
    Edita un Jugador existente.
    - GET: muestra el formulario precargado.
    - POST: valida y guarda cambios; luego redirige a la visualización de jugadores.
    """
    jugador = get_object_or_404(Jugador, pk=jugador_id)

    if request.method == 'POST':
        form = JugadorEditForm(request.POST, instance=jugador)
        if form.is_valid():
            form.save()
            messages.success(request, f'¡Jugador "{jugador.nombre} {jugador.apellido}" actualizado correctamente!')
            return redirect('visualizacion_jugadores')
    else:
        form = JugadorEditForm(instance=jugador)

    context = {
        'form': form,
        'jugador': jugador,
    }
    return render(request, "jugadores/editar.html", context)

def deshabilitar_jugador(request, jugador_id):
    """
    Deshabilita (activo=False) un Jugador.
    - Usa update_fields para tocar sólo el campo 'activo'.
    - Si viene parámetro ?next=..., regresa a esa misma URL (útil para mantener la página actual de la paginación/filtros).
    - Si no, vuelve al listado de jugadores.
    """
    jugador = get_object_or_404(Jugador, id=jugador_id)
    jugador.activo = False
    jugador.save(update_fields=["activo"])
    messages.warning(request, f'Jugador "{jugador.nombre} {jugador.apellido}" deshabilitado correctamente.')

    # Mantenerse en la misma URL si viene ?next=...
    next_url = request.GET.get("next")
    if next_url:
        return redirect(unquote(next_url))
    return redirect("visualizacion_jugadores")  # <- lista de jugadores, NO usuarios

def habilitar_jugador(request, jugador_id):
    """
    Habilita (activo=True) un Jugador.
    - Mismo manejo de ?next=... que en deshabilitar.
    """
    jugador = get_object_or_404(Jugador, id=jugador_id)
    jugador.activo = True
    jugador.save(update_fields=["activo"])
    messages.success(request, f'Jugador "{jugador.nombre} {jugador.apellido}" habilitado correctamente.')

    next_url = request.GET.get("next")
    if next_url:
        return redirect(unquote(next_url))
    return redirect("visualizacion_jugadores")  # <- lista de jugadores, NO usuarios
