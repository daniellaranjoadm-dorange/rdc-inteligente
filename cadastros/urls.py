from django.urls import path

from cadastros.views import (
    AreaLocalCreateView, AreaLocalListView, AreaLocalUpdateView, DisciplinaCreateView, DisciplinaListView, EmpresaCreateView, EmpresaListView,
    EquipeCreateView, EquipeListView, FuncaoCreateView, FuncaoListView, FuncionarioCreateView, FuncionarioListView,
    ProjetoCreateView, ProjetoListView,
    DisciplinaUpdateView, EmpresaUpdateView, EquipeUpdateView, FuncaoUpdateView, FuncionarioUpdateView,
    ProjetoUpdateView,
)

urlpatterns = [
    path("projetos/", ProjetoListView.as_view(), name="projeto-list"),
    path("projetos/novo/", ProjetoCreateView.as_view(), name="projeto-create"),
    path("projetos/<int:pk>/editar/", ProjetoUpdateView.as_view(), name="projeto-update"),
    path("disciplinas/", DisciplinaListView.as_view(), name="disciplina-list"),
    path("disciplinas/nova/", DisciplinaCreateView.as_view(), name="disciplina-create"),
    path("disciplinas/<int:pk>/editar/", DisciplinaUpdateView.as_view(), name="disciplina-update"),
    path("areas/", AreaLocalListView.as_view(), name="area-list"),
    path("areas/nova/", AreaLocalCreateView.as_view(), name="area-create"),
    path("areas/<int:pk>/editar/", AreaLocalUpdateView.as_view(), name="area-update"),
    path("empresas/", EmpresaListView.as_view(), name="empresa-list"),
    path("empresas/nova/", EmpresaCreateView.as_view(), name="empresa-create"),
    path("empresas/<int:pk>/editar/", EmpresaUpdateView.as_view(), name="empresa-update"),
    path("funcoes/", FuncaoListView.as_view(), name="funcao-list"),
    path("funcoes/nova/", FuncaoCreateView.as_view(), name="funcao-create"),
    path("funcoes/<int:pk>/editar/", FuncaoUpdateView.as_view(), name="funcao-update"),
    path("funcionarios/", FuncionarioListView.as_view(), name="funcionario-list"),
    path("funcionarios/novo/", FuncionarioCreateView.as_view(), name="funcionario-create"),
    path("funcionarios/<int:pk>/editar/", FuncionarioUpdateView.as_view(), name="funcionario-update"),
    path("equipes/", EquipeListView.as_view(), name="equipe-list"),
    path("equipes/nova/", EquipeCreateView.as_view(), name="equipe-create"),
    path("equipes/<int:pk>/editar/", EquipeUpdateView.as_view(), name="equipe-update"),
]


