from django import forms

from core.choices import TipoImportacaoChoices
from importacoes.models import ImportacaoArquivo


class ImportacaoArquivoForm(forms.ModelForm):
    class Meta:
        model = ImportacaoArquivo
        fields = ["tipo", "arquivo", "observacoes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css} form-control".strip()
        self.fields["tipo"].choices = TipoImportacaoChoices.CHOICES


