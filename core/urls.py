from django.urls import path
from .views import home_login

urlpatterns = [
    path('', home_login, name='home'),
]
