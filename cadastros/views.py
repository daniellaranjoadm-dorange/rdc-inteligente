from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from cadastros.forms import AreaLocalForm, DisciplinaForm, EmpresaForm, EquipeForm, FuncaoForm, FuncionarioForm, ProjetoForm
from cadastros.models import AreaLocal, Disciplina, Empresa, Equipe, Funcao, Funcionario, Projeto
from core.mixins import AuthenticatedTemplateMixin


class BaseCadastroListView(AuthenticatedTemplateMixin, ListView):
    template_name = "cadastros/lista.html"
    paginate_by = 20
    context_object_name = "objetos"
    titulo = "Cadastros"

    def get_queryset(self):
        queryset = super().get_queryset()
        termo = self.request.GET.get("q", "").strip()
        if termo and hasattr(self, "campos_busca"):
            filtros = Q()
            for campo in self.campos_busca:
                filtros |= Q(**{f"{campo}__icontains": termo})
            queryset = queryset.filter(filtros)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo
        context["termo_busca"] = self.request.GET.get("q", "").strip()
        context["botao_novo_url"] = getattr(self, "botao_novo_url", "")
        return context


class BaseCadastroCreateView(AuthenticatedTemplateMixin, CreateView):
    template_name = "cadastros/form.html"
    success_url = reverse_lazy("dashboard")
    titulo = "Novo cadastro"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo
        return context


class ProjetoListView(BaseCadastroListView):
    model = Projeto
    titulo = "Projetos"
    botao_novo_url = reverse_lazy("projeto-create")
    campos_busca = ("codigo", "nome", "cliente")


class ProjetoCreateView(BaseCadastroCreateView):
    model = Projeto
    form_class = ProjetoForm
    titulo = "Novo projeto"


class DisciplinaListView(BaseCadastroListView):
    model = Disciplina
    titulo = "Disciplinas"
    botao_novo_url = reverse_lazy("disciplina-create")
    campos_busca = ("codigo", "nome")


class DisciplinaCreateView(BaseCadastroCreateView):
    model = Disciplina
    form_class = DisciplinaForm
    titulo = "Nova disciplina"


class AreaLocalListView(BaseCadastroListView):
    model = AreaLocal
    titulo = "Áreas/Locais"
    botao_novo_url = reverse_lazy("area-create")
    campos_busca = ("codigo", "descricao", "projeto__nome")


class AreaLocalCreateView(BaseCadastroCreateView):
    model = AreaLocal
    form_class = AreaLocalForm
    titulo = "Nova área/local"


class EmpresaListView(BaseCadastroListView):
    model = Empresa
    titulo = "Empresas"
    botao_novo_url = reverse_lazy("empresa-create")
    campos_busca = ("nome", "cnpj", "observacoes")


class EmpresaCreateView(BaseCadastroCreateView):
    model = Empresa
    form_class = EmpresaForm
    titulo = "Nova empresa"


class FuncaoListView(BaseCadastroListView):
    model = Funcao
    titulo = "FunçÃµes"
    botao_novo_url = reverse_lazy("funcao-create")
    campos_busca = ("codigo", "nome")


class FuncaoCreateView(BaseCadastroCreateView):
    model = Funcao
    form_class = FuncaoForm
    titulo = "Nova função"


class FuncionarioListView(BaseCadastroListView):
    model = Funcionario
    titulo = "Funcionários"
    botao_novo_url = reverse_lazy("funcionario-create")
    campos_busca = ("matricula", "nome", "cpf", "rg", "empresa__nome", "funcao__nome")


class FuncionarioCreateView(BaseCadastroCreateView):
    model = Funcionario
    form_class = FuncionarioForm
    titulo = "Novo funcionário"


class EquipeListView(BaseCadastroListView):
    model = Equipe
    titulo = "Equipes"
    botao_novo_url = reverse_lazy("equipe-create")
    campos_busca = ("codigo", "nome", "empresa__nome", "disciplina__nome")


class EquipeCreateView(BaseCadastroCreateView):
    model = Equipe
    form_class = EquipeForm
    titulo = "Nova equipe"


