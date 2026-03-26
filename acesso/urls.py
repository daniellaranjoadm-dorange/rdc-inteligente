from django.urls import path
from acesso.views import AcessoHomeView
urlpatterns = [path("", AcessoHomeView.as_view(), name="acesso-home")]


