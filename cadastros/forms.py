from django import forms

from cadastros.models import AreaLocal, Disciplina, Empresa, Equipe, Funcao, Funcionario, Projeto


class BaseBootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            classes = widget.attrs.get("class", "")
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs["class"] = f"{classes} form-check-input".strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple, forms.DateInput, forms.DateTimeInput, forms.TimeInput, forms.TextInput, forms.NumberInput, forms.EmailInput, forms.URLInput, forms.PasswordInput, forms.Textarea)):
                widget.attrs["class"] = f"{classes} form-control".strip()
            else:
                widget.attrs["class"] = f"{classes} form-control".strip()


class ProjetoForm(BaseBootstrapModelForm):
    class Meta:
        model = Projeto
        fields = ["codigo", "nome", "cliente", "ativo"]


class DisciplinaForm(BaseBootstrapModelForm):
    class Meta:
        model = Disciplina
        fields = ["codigo", "nome", "ativo"]


class AreaLocalForm(BaseBootstrapModelForm):
    class Meta:
        model = AreaLocal
        fields = ["projeto", "codigo", "descricao", "disciplina_padrao", "ativo"]


class EmpresaForm(BaseBootstrapModelForm):
    class Meta:
        model = Empresa
        fields = ["nome", "cnpj", "ativa", "cadastro_pendente", "observacoes"]


class FuncaoForm(BaseBootstrapModelForm):
    class Meta:
        model = Funcao
        fields = ["codigo", "nome", "ativa"]


class FuncionarioForm(BaseBootstrapModelForm):
    class Meta:
        model = Funcionario
        fields = ["matricula", "nome", "cpf", "rg", "funcao", "empresa", "ativo"]


class EquipeForm(BaseBootstrapModelForm):
    class Meta:
        model = Equipe
        fields = ["codigo", "nome", "disciplina", "encarregado", "empresa", "ativa"]


