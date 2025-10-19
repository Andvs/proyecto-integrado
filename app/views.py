from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .form import *
from .models import *
from urllib.parse import unquote

# Create your views here.
def index(request):
    return render(request,"index.html")

def formulario(request):
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            # --- Líneas de Depuración ---
            contraseña_plana = form.cleaned_data['contraseña']
            usuario.contraseña = make_password(contraseña_plana)
            usuario.save()
            return redirect("visualizacion")
    else:
        form = UsuarioForm()
    return render(request, "usuarios/formulario.html", {"form": form})

# --- VISTA DE LOGIN CON DEPURACIÓN ---

def login(request):
    """
    Opción A: impedir el ingreso si
    - Usuario.activo == False, o
    - existe un Jugador vinculado y jugador.activo == False
    """
    if request.method == 'POST':
        nombre_usuario = (request.POST.get('nombre_usuario') or '').strip()
        contrasena = request.POST.get('contraseña') or ''
        try:
            usuario = Usuario.objects.get(nombre_usuario=nombre_usuario)
        except Usuario.DoesNotExist:
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
            return redirect('login')

        if not check_password(contrasena, usuario.contraseña):
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
            return redirect('login')

        if not usuario.activo:
            messages.error(request, 'Esta cuenta ha sido deshabilitada.')
            return redirect('login')

        # Bloqueo por Jugador vinculado inactivo
        jugador = Jugador.objects.filter(usuario=usuario).first()
        if jugador is not None and not jugador.activo:
            messages.error(request, 'Tu perfil de jugador está deshabilitado; no puedes ingresar.')
            return redirect('login')

        # OK: crear sesión
        request.session['usuario_id'] = usuario.id
        messages.success(request, f'Bienvenido, {usuario.nombre_usuario}')
        next_url = request.GET.get('next')
        return redirect(next_url or 'dashboard')

    return render(request, 'login.html')

def visualizacion(request):
    query = request.GET.get('q')
    usuarios_list = Usuario.objects.all().order_by('id')
    if query:
        # Consulta base para los campos de texto
        text_query = (
            Q(nombre_usuario__icontains=query) |
            Q(rol__nombre__icontains=query) # Asumiendo que 'rol' tiene un campo 'nombre'
        )
        # INICIO: Lógica para buscar por el campo booleano 'activo'
        query_lower = query.lower()
        
        # Palabras que el usuario podría escribir para buscar 'activos'
        palabras_activo = ['si', 'sí', 'activo', 'activos', 'true', '1']
        
        # Palabras que el usuario podría escribir para buscar 'inactivos'
        palabras_inactivo = ['no', 'inactivo', 'inactivos', 'false', '0']
        if query_lower in palabras_activo:
            # Si busca "activo", combinamos la búsqueda de texto CON la condición booleana
            final_query = text_query | Q(activo=True)
        elif query_lower in palabras_inactivo:
            # Si busca "inactivo", combinamos la búsqueda de texto CON la condición booleana
            final_query = text_query | Q(activo=False)
        else:
            # Si no es una palabra booleana, solo buscamos en los campos de texto
            final_query = text_query
        
        # FIN de la lógica para el campo 'activo'
            
        usuarios_list = usuarios_list.filter(final_query).distinct()
    
    paginator = Paginator(usuarios_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': query,
    }
    return render(request, 'usuarios/visualizacion.html', context)

def editar_usuario(request, usuario_id):
    usuario = get_object_or_404(Usuario, pk=usuario_id)

    if request.method == 'POST':
        # Procesa el formulario enviado
        form = UsuarioEditForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'¡Usuario "{usuario.nombre_usuario}" actualizado correctamente!')
            return redirect('visualizacion') # Usa el 'name' de la URL de visualización
    else:
        # Muestra el formulario precargado con los datos del usuario
        form = UsuarioEditForm(instance=usuario)

    context = {
        'form': form,
        'usuario': usuario,
    }
    return render(request, 'usuarios/editar.html', context)


def desabilitar_usuario(request, user_id):
    # --- INICIO DE LA NUEVA COMPROBACIÓN ---
    # Obtenemos el ID del usuario que ha iniciado sesión
    logged_in_user_id = request.session.get('usuario_id')

    # Comparamos si el usuario que se intenta deshabilitar es el mismo que está logueado
    if logged_in_user_id == user_id:
        messages.error(request, 'No puedes deshabilitar tu propia cuenta mientras la usas.', extra_tags='danger')
        return redirect('visualizacion')
    # --- FIN DE LA NUEVA COMPROBACIÓN ---

    # El resto del código continúa igual
    usuario = get_object_or_404(Usuario, id=user_id)
    usuario.activo = False
    usuario.save()

    messages.success(request, f'El usuario "{usuario.nombre_usuario}" ha sido deshabilitado correctamente.')
    return redirect('visualizacion')
def dashboard(request):
    return render(request,"dashboard.html")

#Jugador
def formulario_jugadores(request):
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
    query = request.GET.get('q')
    jugadores_list = (
        Jugador.objects
        .select_related('equipo', 'equipo__categoria', 'equipo__entrenador')
        .all()
        .order_by('id')
    )

    if query:
        text_query = (
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query) |
            Q(run__icontains=query) |
            Q(equipo__nombre__icontains=query) |
            Q(equipo__categoria__nombre__icontains=query)
        )

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

    paginator = Paginator(jugadores_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': query,
    }
    return render(request, "jugadores/visualizacion.html", context)

def editar_jugador(request, jugador_id):
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
    jugador = get_object_or_404(Jugador, id=jugador_id)
    jugador.activo = True
    jugador.save(update_fields=["activo"])
    messages.success(request, f'Jugador "{jugador.nombre} {jugador.apellido}" habilitado correctamente.')

    next_url = request.GET.get("next")
    if next_url:
        return redirect(unquote(next_url))
    return redirect("visualizacion_jugadores")  # <- lista de jugadores, NO usuarios