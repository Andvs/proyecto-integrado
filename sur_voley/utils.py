
from io import BytesIO
import os
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa

def render_to_pdf(template_src, context_dict=None):
    if context_dict is None:
        context_dict = {}

    template = get_template(template_src)
    html = template.render(context_dict)

    result = BytesIO()
    pdf = pisa.CreatePDF(
        html.encode("UTF-8"),
        dest=result,
        link_callback=link_callback,   # 👈 importante
        encoding="UTF-8",
    )

    if not pdf.err:
        return result.getvalue()
    return None

def link_callback(uri, rel):
    """
    Convierte rutas estáticas (staticfiles) y media en rutas absolutas del sistema.
    Esto permite que xhtml2pdf encuentre imágenes y CSS.
    """

    static_url = settings.STATIC_URL
    static_root = settings.STATIC_ROOT

    media_url = getattr(settings, "MEDIA_URL", "")
    media_root = getattr(settings, "MEDIA_ROOT", "")

    if uri.startswith(static_url):  # ej: /static/...
        # En desarrollo los archivos están en BASE_DIR/static
        # o en STATIC_ROOT si has hecho collectstatic
        base_static = static_root or os.path.join(settings.BASE_DIR, "static")
        path = os.path.join(base_static, uri.replace(static_url, ""))
        return path

    if media_url and uri.startswith(media_url):  # /media/...
        path = os.path.join(media_root, uri.replace(media_url, ""))
        return path

    # http://, https://, file:// ...
    return uri