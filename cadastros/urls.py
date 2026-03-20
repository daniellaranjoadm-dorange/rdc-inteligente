from django.urls import path

from cadastros.views import (
    AreaLocalCreateView, AreaLocalListView, DisciplinaCreateView, DisciplinaListView, EmpresaCreateView, EmpresaListView,
    EquipeCreateView, EquipeListView, FuncaoCreateView, FuncaoListView, FuncionarioCreateView, FuncionarioListView,
    ProjetoCreateView, ProjetoListView,
)

urlpatterns = [
    path("projetos/", ProjetoListView.as_view(), name="projeto-list"),
    path("projetos/novo/", ProjetoCreateView.as_view(), name="projeto-create"),
    path("disciplinas/", DisciplinaListView.as_view(), name="disciplina-list"),
    path("disciplinas/nova/", DisciplinaCreateView.as_view(), name="disciplina-create"),
    path("areas/", AreaLocalListView.as_view(), name="area-list"),
    path("areas/nova/", AreaLocalCreateView.as_view(), name="area-create"),
    path("empresas/", EmpresaListView.as_view(), name="empresa-list"),
    path("empresas/nova/", EmpresaCreateView.as_view(), name="empresa-create"),
    path("funcoes/", FuncaoListView.as_view(), name="funcao-list"),
    path("funcoes/nova/", FuncaoCreateView.as_view(), name="funcao-create"),
    path("funcionarios/", FuncionarioListView.as_view(), name="funcionario-list"),
    path("funcionarios/novo/", FuncionarioCreateView.as_view(), name="funcionario-create"),
    path("equipes/", EquipeListView.as_view(), name="equipe-list"),
    path("equipes/nova/", EquipeCreateView.as_view(), name="equipe-create"),
]
