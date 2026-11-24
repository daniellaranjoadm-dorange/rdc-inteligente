from django import forms
from django.utils import timezone

from cadastros.models import AreaLocal, Funcionario, Projeto
from soldagem.models import EPS, DefeitoSolda, JuntaSolda, Passe, ResultadoEND, Soldador

DATA = {"type": "date"}


class _Estilo:
    def _estilizar(self):
        for field in self.fields.values():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "form-select")
            else:
                w.attrs.setdefault("class", "form-control")


class SoldadorForm(_Estilo, forms.ModelForm):
    class Meta:
        model = Soldador
        fields = ("funcionario", "sinete", "processos", "posicoes", "certificado", "validade_qualificacao", "ativo")
        widgets = {"validade_qualificacao": forms.DateInput(attrs=DATA, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["funcionario"].queryset = Funcionario.objects.filter(ativo=True).select_related("funcao").order_by("nome")
        self._estilizar()


class EPSForm(_Estilo, forms.ModelForm):
    class Meta:
        model = EPS
        fields = ("codigo", "processo", "material", "espessura", "posicoes", "consumivel", "ativo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estilizar()


class JuntaForm(_Estilo, forms.ModelForm):
    class Meta:
        model = JuntaSolda
        fields = ("projeto", "area_local", "codigo", "descricao", "tipo", "comprimento_m", "espessura_mm", "eps", "metodo_end")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["projeto"].queryset = Projeto.objects.filter(ativo=True).order_by("nome")
        self.fields["area_local"].queryset = AreaLocal.objects.filter(ativo=True).select_related("projeto").order_by("codigo")
        self.fields["eps"].queryset = EPS.objects.filter(ativo=True)
        self._estilizar()

    def clean(self):
        dados = super().clean()
        projeto, area = dados.get("projeto"), dados.get("area_local")
        if projeto and area and area.projeto_id != projeto.pk:
            self.add_error("area_local", "Este bloco/área é de outro projeto.")
        comp = dados.get("comprimento_m")
        if comp is not None and comp <= 0:
            self.add_error("comprimento_m", "Informe o comprimento da junta.")
        return dados


class ExecucaoForm(_Estilo, forms.Form):
    soldador = forms.ModelChoiceField(queryset=Soldador.objects.none(), label="Soldador (sinete)")
    data = forms.DateField(widget=forms.DateInput(attrs=DATA, format="%Y-%m-%d"), initial=timezone.localdate)
    metros = forms.DecimalField(label="Metros soldados", min_value=0.01, max_digits=8, decimal_places=2)
    passe = forms.ChoiceField(choices=Passe.choices, initial=Passe.COMPLETO)
    observacao = forms.CharField(label="Observação", required=False, max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["soldador"].queryset = Soldador.objects.filter(ativo=True).select_related("funcionario")
        self._estilizar()


class ResultadoENDForm(_Estilo, forms.Form):
    resultado = forms.ChoiceField(choices=[(ResultadoEND.APROVADO, "Aprovado"), (ResultadoEND.REPROVADO, "Reprovado")])
    data = forms.DateField(label="Ensaiado em", widget=forms.DateInput(attrs=DATA, format="%Y-%m-%d"), initial=timezone.localdate)
    metros_reprovados = forms.DecimalField(label="Metros reprovados", required=False, min_value=0, max_digits=8, decimal_places=2)
    defeito = forms.ChoiceField(choices=[("", "—")] + list(DefeitoSolda.choices), required=False)
    inspetor = forms.CharField(required=False, max_length=120)
    relatorio = forms.CharField(label="Nº do relatório", required=False, max_length=60)
    observacao = forms.CharField(label="Observação", required=False, max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._estilizar()
