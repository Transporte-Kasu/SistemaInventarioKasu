from django import forms
from .models import Equipo


class EquipoForm(forms.ModelForm):
    class Meta:
        model = Equipo
        fields = [
            'usuario', 'tipo', 'marca', 'modelo', 'numero_serie', 'estado',
            'mac_address', 'telefono_interno', 'monitores_cantidad', 'monitores_marca',
            'ubicacion', 'foto', 'fecha_adquisicion', 'notas',
        ]
        widgets = {
            'usuario': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del custodio'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'modelo': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_serie': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de serie del fabricante'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'mac_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XX:XX:XX:XX:XX:XX'}),
            'telefono_interno': forms.TextInput(attrs={'class': 'form-control'}),
            'monitores_cantidad': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'monitores_marca': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Área o departamento'}),
            'foto': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'fecha_adquisicion': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
