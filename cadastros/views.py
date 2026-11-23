from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

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
        context["editar_url_name"] = getattr(self, "editar_url_name", "")
        return context


class BaseCadastroCreateView(AuthenticatedTemplateMixin, CreateView):
    template_name = "cadastros/form.html"
    titulo = "Novo cadastro"
    # Rota da lista para onde voltar depois de salvar. Antes apontava para "dashboard",
    # que nao existe, e todo cadastro terminava em erro 500 depois de gravado.
    lista_url_name = None

    def get_success_url(self):
        return reverse_lazy(self.lista_url_name) if self.lista_url_name else "/m/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = self.titulo
        context["voltar_url"] = self.get_success_url()
        return context


class ProjetoListView(BaseCadastroListView):
    editar_url_name = "projeto-update"
    model = Projeto
    titulo = "Projetos"
    botao_novo_url = reverse_lazy("projeto-create")
    campos_busca = ("codigo", "nome", "cliente")


class ProjetoCreateView(BaseCadastroCreateView):
    lista_url_name = "projeto-list"
    model = Projeto
    form_class = ProjetoForm
    titulo = "Novo projeto"


class DisciplinaListView(BaseCadastroListView):
    editar_url_name = "disciplina-update"
    model = Disciplina
    titulo = "Disciplinas"
    botao_novo_url = reverse_lazy("disciplina-create")
    campos_busca = ("codigo", "nome")


class DisciplinaCreateView(BaseCadastroCreateView):
    lista_url_name = "disciplina-list"
    model = Disciplina
    form_class = DisciplinaForm
    titulo = "Nova disciplina"


class AreaLocalListView(BaseCadastroListView):
    model = AreaLocal
    template_name = "cadastros/areas_lista.html"
    titulo = "Áreas e blocos da obra"
    botao_novo_url = reverse_lazy("area-create")
    campos_busca = ("codigo", "descricao", "projeto__nome", "casco")

    def get_queryset(self):
        return super().get_queryset().select_related("projeto", "disciplina_padrao")


class AreaLocalCreateView(BaseCadastroCreateView):
    lista_url_name = "area-list"
    model = AreaLocal
    form_class = AreaLocalForm
    titulo = "Nova área/local"


class EmpresaListView(BaseCadastroListView):
    editar_url_name = "empresa-update"
    model = Empresa
    titulo = "Empresas"
    botao_novo_url = reverse_lazy("empresa-create")
    campos_busca = ("nome", "cnpj", "observacoes")


class EmpresaCreateView(BaseCadastroCreateView):
    lista_url_name = "empresa-list"
    model = Empresa
    form_class = EmpresaForm
    titulo = "Nova empresa"


class FuncaoListView(BaseCadastroListView):
    editar_url_name = "funcao-update"
    model = Funcao
    titulo = "Funções"
    botao_novo_url = reverse_lazy("funcao-create")
    campos_busca = ("codigo", "nome")


class FuncaoCreateView(BaseCadastroCreateView):
    lista_url_name = "funcao-list"
    model = Funcao
    form_class = FuncaoForm
    titulo = "Nova função"


class FuncionarioListView(BaseCadastroListView):
    editar_url_name = "funcionario-update"
    model = Funcionario
    titulo = "Funcionários"
    botao_novo_url = reverse_lazy("funcionario-create")
    campos_busca = ("matricula", "nome", "cpf", "rg", "empresa__nome", "funcao__nome")


class FuncionarioCreateView(BaseCadastroCreateView):
    lista_url_name = "funcionario-list"
    model = Funcionario
    form_class = FuncionarioForm
    titulo = "Novo funcionário"


class EquipeListView(BaseCadastroListView):
    editar_url_name = "equipe-update"
    model = Equipe
    titulo = "Equipes"
    botao_novo_url = reverse_lazy("equipe-create")
    campos_busca = ("codigo", "nome", "empresa__nome", "disciplina__nome")


class EquipeCreateView(BaseCadastroCreateView):
    lista_url_name = "equipe-list"
    model = Equipe
    form_class = EquipeForm
    titulo = "Nova equipe"






class AreaLocalUpdateView(AuthenticatedTemplateMixin, UpdateView):
    model = AreaLocal
    form_class = AreaLocalForm
    template_name = "cadastros/form.html"
    success_url = reverse_lazy("area-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = f"Editar área: {self.object.descricao}"
        context["voltar_url"] = self.success_url
        return context



class BaseCadastroUpdateView(AuthenticatedTemplateMixin, UpdateView):
    """Edicao generica de cadastro: volta para a lista ao salvar."""

    template_name = "cadastros/form.html"
    lista_url_name = None
    campo_titulo = "nome"

    def get_success_url(self):
        return reverse_lazy(self.lista_url_name)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nome = getattr(self.object, self.campo_titulo, "") or str(self.object)
        context["titulo"] = f"Editar {self.model._meta.verbose_name}: {nome}"
        context["voltar_url"] = self.get_success_url()
        return context


class ProjetoUpdateView(BaseCadastroUpdateView):
    model = Projeto
    form_class = ProjetoForm
    lista_url_name = "projeto-list"


class DisciplinaUpdateView(BaseCadastroUpdateView):
    model = Disciplina
    form_class = DisciplinaForm
    lista_url_name = "disciplina-list"


class EmpresaUpdateView(BaseCadastroUpdateView):
    model = Empresa
    form_class = EmpresaForm
    lista_url_name = "empresa-list"


class FuncaoUpdateView(BaseCadastroUpdateView):
    model = Funcao
    form_class = FuncaoForm
    lista_url_name = "funcao-list"


class FuncionarioUpdateView(BaseCadastroUpdateView):
    model = Funcionario
    form_class = FuncionarioForm
    lista_url_name = "funcionario-list"


class EquipeUpdateView(BaseCadastroUpdateView):
    model = Equipe
    form_class = EquipeForm
    lista_url_name = "equipe-list"
