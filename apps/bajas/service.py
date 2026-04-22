"""PDF acta generation for BajaEquipo using WeasyPrint."""
import io
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone


def generar_acta_baja(baja):
    """Renders the acta PDF for a BajaEquipo and saves it to baja.acta_pdf."""
    try:
        from weasyprint import HTML
    except ImportError:
        return None

    context = {
        'baja': baja,
        'fecha_impresion': timezone.now(),
        'BASE_DIR': str(settings.BASE_DIR),
    }
    html_string = render_to_string('bajas/pdf/acta_baja.html', context)
    pdf_bytes = HTML(
        string=html_string,
        base_url=str(settings.BASE_DIR),
    ).write_pdf()

    nombre = f'acta_baja_{baja.equipo.numero_serie or baja.pk}_{timezone.now().strftime("%Y%m%d")}.pdf'
    baja.acta_pdf.save(nombre, ContentFile(pdf_bytes), save=True)
    return baja.acta_pdf
