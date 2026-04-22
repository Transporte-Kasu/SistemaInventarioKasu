from django import forms
from .models import Ticket


class TicketCierreForm(forms.Form):
    notas_cierre = forms.CharField(
        label='Notas de resolución',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                     'placeholder': 'Describe cómo se resolvió el problema...'}),
        required=True,
    )


class TicketPublicoForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['nombre_solicitante', 'email_solicitante', 'categoria', 'descripcion', 'prioridad']
        widgets = {
            'nombre_solicitante': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Tu nombre completo',
                'autocomplete': 'name',
            }),
            'email_solicitante': forms.EmailInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'tu@correo.com',
                'autocomplete': 'email',
                'inputmode': 'email',
            }),
            'categoria': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe brevemente el problema...',
            }),
            'prioridad': forms.Select(attrs={'class': 'form-select form-select-lg'}),
        }
        labels = {
            'nombre_solicitante': 'Tu nombre',
            'email_solicitante': 'Tu correo',
            'categoria': '¿Qué tipo de problema es?',
            'descripcion': 'Describe el problema',
            'prioridad': 'Prioridad',
        }
