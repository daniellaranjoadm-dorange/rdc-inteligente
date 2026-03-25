from django.views.generic import TemplateView

from core.dashboard_services import HomeDashboardService


class DashboardView(TemplateView):
    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(HomeDashboardService().build())
        return context

from django.shortcuts import render

def handler403(request, exception=None):
    return render(request, "errors/403.html", status=403)


