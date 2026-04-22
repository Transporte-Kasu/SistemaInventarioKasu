from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def perfil(request):
    return render(request, 'usuarios/perfil.html')
