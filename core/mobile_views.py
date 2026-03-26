from django.views.generic import TemplateView

from core.mixins import AuthenticatedTemplateMixin


class MobileHomeView(AuthenticatedTemplateMixin, TemplateView):
    template_name = "mobile_home.html"
