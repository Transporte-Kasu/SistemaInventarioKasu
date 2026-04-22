from django import forms
from .models import BajaEquipo


class BajaSolicitudForm(forms.ModelForm):
    """Fase 1 — Solicitud inicial de baja."""

    class Meta:
        model = BajaEquipo
        fields = ['motivo', 'metodo_sanitizacion', 'observaciones']
        widgets = {
            'motivo': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'metodo_sanitizacion': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class BajaEjecucionForm(forms.ModelForm):
    """Fase 2 — Ejecución de formateo/desinfección."""

    class Meta:
        model = BajaEquipo
        fields = [
            'herramienta_utilizada',
            'numero_pasadas',
            'verificacion_borrado',
            'evidencia_foto',
            'observaciones',
        ]
        widgets = {
            'herramienta_utilizada': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_pasadas': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'verificacion_borrado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'evidencia_foto': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'observaciones': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }


class BajaDestruccionForm(forms.ModelForm):
    """Fase 3 — Destrucción física (opcional, solo si aplica)."""

    class Meta:
        model = BajaEquipo
        fields = ['evidencia_foto', 'observaciones']
        widgets = {
            'evidencia_foto': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'observaciones': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class BajaCierreForm(forms.ModelForm):
    """Fase 4 — Cierre y generación de acta."""

    class Meta:
        model = BajaEquipo
        fields = ['testigos', 'observaciones']
        widgets = {
            'testigos': forms.CheckboxSelectMultiple(),
            'observaciones': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }
