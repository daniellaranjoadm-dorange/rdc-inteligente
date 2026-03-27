from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login

def home_login(request):
    if request.user.is_authenticated:
        return redirect("/m/")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("/m/")
        else:
            return render(request, "login.html", {
                "error": "Usuário ou senha inválidos"
            })

    return render(request, "login.html")
