from django.views.generic import TemplateView

from core.mixins import AuthenticatedTemplateMixin


class MobileHomeView(AuthenticatedTemplateMixin, TemplateView):
    """Inicio do app no celular. Exige login: sem isso a tela parecia logada sem estar."""

    template_name = "mobile_home.html"
