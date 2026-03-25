from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from core.models import ImportJob
from core.services.import_funcionarios import ImportFuncionariosCSVService


class ImportFuncionariosView(View):
    template_name = "core/import_funcionarios.html"

    def get(self, request):
        return render(request, self.template_name)

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

        messages.success(request, f"Importação finalizada com status: {job.get_status_display()}")

        return redirect("import-funcionarios")
