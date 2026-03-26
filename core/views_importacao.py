from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from core.models import ImportJob
from core.services.import_funcionarios import ImportFuncionariosCSVService


class ImportFuncionariosView(View):
    template_name = "core/import_funcionarios.html"

    def get_context_data(self):
        jobs = ImportJob.objects.filter(
            tipo=ImportJob.TIPO_FUNCIONARIOS,
        ).order_by("-criado_em")[:10]

        ultimo_job = jobs[0] if jobs else None

        return {
            "jobs": jobs,
            "ultimo_job": ultimo_job,
        }

    def get(self, request):
        return render(request, self.template_name, self.get_context_data())

    def post(self, request):
        arquivo = request.FILES.get("arquivo")

        if not arquivo:
            messages.error(request, "Selecione um arquivo.")
            return redirect("import-funcionarios")

        job = ImportJob.objects.create(
            tipo=ImportJob.TIPO_FUNCIONARIOS,
            arquivo=arquivo,
            nome_arquivo_original=arquivo.name,
            usuario=request.user if request.user.is_authenticated else None,
        )

        ImportFuncionariosCSVService(job).run()

        messages.success(
            request,
            f"Importação finalizada com status: {job.get_status_display()}",
        )

        context = self.get_context_data()
        context["ultimo_job"] = job
        return render(request, self.template_name, context)

