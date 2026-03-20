from django.urls import path

from accounts.views import UsuarioLoginView, UsuarioLogoutView

urlpatterns = [
    path("login/", UsuarioLoginView.as_view(), name="login"),
    path("logout/", UsuarioLogoutView.as_view(), name="logout"),
]
