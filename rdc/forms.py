from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum

from core.choices import StatusValidacaoChoices, TurnoChoices
from rdc.models import RDC, RDCAtividade, RDCApontamento, RDCFuncionario, RDCValidacao


DEFAULT_HORA_NORMAL = Decimal("8.00")
DEFAULT_HORA_EXTRA = Decimal("0.00")


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css = field.widget.attrs.get("class", "")
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = f"{css} form-check-input".strip()
            else:
                field.widget.attrs["class"] = f"{css} form-control".strip()
                field.widget.attrs.setdefault("autocomplete", "off")
            field.widget.attrs.setdefault("data-field-name", name)

    def _make_field_readonly(self, name):
        if name in self.fields:
            self.fields[name].widget.attrs["readonly"] = True
            self.fields[name].widget.attrs["tabindex"] = "-1"

    def _mark_field_autofill(self, name):
        if name in self.fields:
            css = self.fields[name].widget.attrs.get("class", "")
            self.fields[name].widget.attrs["class"] = f"{css} autofill-target".strip()


class RDCMontagemForm(BootstrapFormMixin, forms.Form):
    projeto = forms.ModelChoiceField(queryset=None)
    area_local = forms.ModelChoiceField(queryset=None, label="Área/local")
    disciplina = forms.ModelChoiceField(queryset=None)
    data = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    turno = forms.ChoiceField(choices=TurnoChoices.CHOICES)
    equipe = forms.ModelChoiceField(queryset=None, required=False)

    def __init__(self, *args, **kwargs):
        contexto = kwargs.pop("contexto_guiado", None) or {}
        from cadastros.models import AreaLocal, Disciplina, Equipe, Projeto

        super().__init__(*args, **kwargs)

        self.fields["projeto"].queryset = Projeto.objects.filter(ativo=True).order_by("codigo")
        self.fields["area_local"].queryset = AreaLocal.objects.filter(ativo=True).order_by("descricao")
        self.fields["disciplina"].queryset = Disciplina.objects.filter(ativo=True).order_by("nome")
        self.fields["equipe"].queryset = Equipe.objects.filter(ativa=True).order_by("nome")
        self.fields["equipe"].help_text = "Opcional. Ajuda a priorizar alocAção e programAção semanal."

        projeto = contexto.get("projeto")
        disciplina = contexto.get("disciplina")
        area_local = contexto.get("area_local")
        equipe = contexto.get("equipe")
        data = contexto.get("data")
        turno = contexto.get("turno")

        if projeto:
            self.fields["projeto"].initial = projeto.pk
            self.fields["area_local"].queryset = self.fields["area_local"].queryset.filter(projeto=projeto)

        if disciplina:
            self.fields["disciplina"].initial = disciplina.pk
            if hasattr(Equipe, "disciplina_id"):
                self.fields["equipe"].queryset = self.fields["equipe"].queryset.filter(disciplina=disciplina)

        if area_local:
            self.fields["area_local"].initial = area_local.pk
        if equipe:
            self.fields["equipe"].initial = equipe.pk
        if data:
            self.fields["data"].initial = data
        if turno:
            self.fields["turno"].initial = turno

    def clean(self):
        cleaned = super().clean()
        projeto = cleaned.get("projeto")
        area_local = cleaned.get("area_local")
        disciplina = cleaned.get("disciplina")
        equipe = cleaned.get("equipe")

        if projeto and area_local and getattr(area_local, "projeto_id", None) != projeto.id:
            self.add_error("area_local", "A área selecionada não pertence ao projeto informado.")

        if (
            equipe
            and disciplina
            and getattr(equipe, "disciplina_id", None)
            and equipe.disciplina_id != disciplina.id
        ):
            self.add_error("equipe", "A equipe selecionada não pertence Ã  disciplina informada.")

        return cleaned


class RDCForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RDC
        fields = [
            "projeto",
            "area_local",
            "disciplina",
            "data",
            "turno",
            "supervisor",
            "dia_semana",
            "condicao_area",
            "clima_manha",
            "clima_tarde",
            "clima_noite",
            "horario_inicio",
            "horario_fim",
            "observacoes",
            "status",
        ]
        widgets = {
            "data": forms.DateInput(attrs={"type": "date"}),
            "horario_inicio": forms.TimeInput(attrs={"type": "time"}),
            "horario_fim": forms.TimeInput(attrs={"type": "time"}),
            "observacoes": forms.Textarea(attrs={"rows": 6}),
        }


class RDCAtividadeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RDCAtividade
        exclude = ["rdc"]

    def __init__(self, *args, **kwargs):
        self.rdc = kwargs.pop("rdc", None)
        super().__init__(*args, **kwargs)

        if "atividade_cronograma" in self.fields:
            qs = self.fields["atividade_cronograma"].queryset
            if self.rdc is not None:
                qs = qs.filter(
                    projeto=self.rdc.projeto,
                    area_local=self.rdc.area_local,
                    disciplina=self.rdc.disciplina,
                    data_inicio__lte=self.rdc.data,
                    data_fim__gte=self.rdc.data,
                )
            self.fields["atividade_cronograma"].queryset = qs.order_by(
                "codigo_atividade",
                "descr_atividade",
            )
            self.fields["atividade_cronograma"].help_text = (
                "Pesquise por código, descrição ou subatividade."
            )

        for field_name in [
            "codigo_atividade",
            "descr_atividade",
            "codigo_subatividade",
            "descr_subatividade",
            "qtd_escopo",
        ]:
            self._mark_field_autofill(field_name)

    def clean(self):
        cleaned = super().clean()
        atividade = cleaned.get("atividade_cronograma")

        if atividade:
            cleaned["codigo_atividade"] = atividade.codigo_atividade or cleaned.get("codigo_atividade")
            cleaned["descr_atividade"] = atividade.descr_atividade or cleaned.get("descr_atividade")
            cleaned["codigo_subatividade"] = atividade.codigo_subatividade or cleaned.get("codigo_subatividade")
            cleaned["descr_subatividade"] = atividade.descr_subatividade or cleaned.get("descr_subatividade")

            if hasattr(atividade, "qtd_escopo"):
                cleaned["qtd_escopo"] = atividade.qtd_escopo

            if "origem" in self.fields and not cleaned.get("origem"):
                try:
                    cleaned["origem"] = type(self.instance)._meta.get_field("origem").default
                except Exception:
                    pass

            if "obrigatoria" in self.fields and cleaned.get("obrigatoria") in (None, ""):
                cleaned["obrigatoria"] = True

            if "ativa_no_dia" in self.fields and cleaned.get("ativa_no_dia") in (None, ""):
                cleaned["ativa_no_dia"] = True

        codigo = (cleaned.get("codigo_atividade") or "").strip()
        descricao = (cleaned.get("descr_atividade") or "").strip()

        if not codigo and not descricao:
            raise ValidationError(
                "Informe a atividade do cronograma ou preencha ao menos código/descrição."
            )

        if self.rdc is not None:
            qs = RDCAtividade.objects.filter(
                rdc=self.rdc,
                codigo_atividade=codigo,
                codigo_subatividade=(cleaned.get("codigo_subatividade") or "").strip(),
                origem=cleaned.get("origem") or "",
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise ValidationError(
                    "Já existe uma atividade com este código/subatividade/origem neste RDC."
                )

        return cleaned


class RDCFuncionarioForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RDCFuncionario
        exclude = ["rdc"]

    def __init__(self, *args, **kwargs):
        self.rdc = kwargs.pop("rdc", None)
        super().__init__(*args, **kwargs)

        if "funcionario" in self.fields:
            qs = self.fields["funcionario"].queryset
            try:
                from alocacao.models import FuncionarioProjeto

                if self.rdc is not None:
                    alocados = FuncionarioProjeto.objects.filter(
                        projeto=self.rdc.projeto,
                        disciplina=self.rdc.disciplina,
                        ativo=True,
                        data_inicio__lte=self.rdc.data,
                    ).filter(Q(data_fim__isnull=True) | Q(data_fim__gte=self.rdc.data))
                    ids = alocados.values_list("funcionario_id", flat=True).distinct()
                    # melhora importante: manter busca ampla, mas priorizar/permitir não alocados
                    if ids:
                        qs = qs.filter(Q(id__in=ids) | Q(ativo=True))
                    else:
                        qs = qs.filter(ativo=True)
            except Exception:
                qs = qs.filter(ativo=True)

            self.fields["funcionario"].queryset = qs.order_by("nome")
            self.fields["funcionario"].help_text = (
                "Pesquise por matrícula ou nome. O sistema completa função, equipe, HH e catraca. "
                "Se faltar equipe, alocAção ou catraca, o sistema avisa e mantém a informAção visível."
            )

        if "matricula" in self.fields:
            self.fields["matricula"].widget.attrs.update(
                {"autocomplete": "off", "inputmode": "numeric", "placeholder": "Digite ou selecione para preencher"}
            )
            self.fields["matricula"].help_text = "Ao escolher o funcionário, a matrícula é preenchida automaticamente."

        for decimal_field in ["hora_normal", "hora_extra", "hh_total"]:
            if decimal_field in self.fields:
                self.fields[decimal_field].widget.attrs.setdefault("step", "0.01")

        for field_name in [
            "matricula",
            "nome",
            "funcao",
            "equipe",
            "presente_catraca",
            "elegivel",
            "motivo_bloqueio",
            "hh_total",
            "hora_normal",
            "hora_extra",
        ]:
            self._mark_field_autofill(field_name)

        for readonly_field in ["nome", "funcao", "presente_catraca", "elegivel", "motivo_bloqueio", "hh_total"]:
            self._make_field_readonly(readonly_field)

        if "nome" in self.fields:
            self.fields["nome"].help_text = "Preenchido automaticamente a partir do cadastro do funcionário."
        if "equipe" in self.fields:
            self.fields["equipe"].help_text = (
                "Tentativa de preenchimento automático pela alocAção ativa. "
                "Se ficar vazio, selecione manualmente e revise a alocAção do funcionário."
            )
        if "funcao" in self.fields:
            self.fields["funcao"].help_text = "Preenchida automaticamente pelo cadastro do funcionário."
        if "presente_catraca" in self.fields:
            self.fields["presente_catraca"].help_text = "Informado automaticamente pela catraca do dia."
        if "elegivel" in self.fields:
            self.fields["elegivel"].help_text = "Definido automaticamente. Sem catraca no dia, o funcionário fica não elegível."
        if "motivo_bloqueio" in self.fields:
            self.fields["motivo_bloqueio"].help_text = "Motivo automático quando houver ausência de catraca ou pendência de contexto."

        if "liberado_sem_catraca" in self.fields:
            self.fields["liberado_sem_catraca"].label = "Liberar manualmente sem catraca"
            self.fields["liberado_sem_catraca"].help_text = (
                "Use somente quando o funcionário realmente trabalhou no dia, mas não apareceu na catraca."
            )
        if "justificativa_liberacao" in self.fields:
            self.fields["justificativa_liberacao"].label = "Justificativa da liberAção"
            self.fields["justificativa_liberacao"].widget = forms.Textarea(attrs={"rows": 3})
            self.fields["justificativa_liberacao"].help_text = "Obrigatória quando houver liberAção manual sem catraca."
        if "liberado_por" in self.fields:
            self.fields["liberado_por"].disabled = True
            self.fields["liberado_por"].required = False
            self.fields["liberado_por"].help_text = "Preenchido automaticamente ao salvar a liberAção manual."
        if "liberado_em" in self.fields:
            self.fields["liberado_em"].disabled = True
            self.fields["liberado_em"].required = False
            self.fields["liberado_em"].help_text = "Preenchido automaticamente ao salvar a liberAção manual."

    def _resolve_funcionario_context(self, funcionario):
        ctx = {
            "matricula": funcionario.matricula or "",
            "nome": funcionario.nome or "",
            "funcao": getattr(funcionario, "funcao", None),
            "equipe": None,
            "presente_catraca": False,
            "elegivel": True,
            "motivo_bloqueio": "",
            "hora_normal": DEFAULT_HORA_NORMAL,
            "hora_extra": DEFAULT_HORA_EXTRA,
            "hh_total": DEFAULT_HORA_NORMAL + DEFAULT_HORA_EXTRA,
            "alertas": [],
        }

        try:
            from alocacao.models import FuncionarioProjeto

            if self.rdc is not None:
                aloc = (
                    FuncionarioProjeto.objects.select_related("equipe")
                    .filter(
                        funcionario=funcionario,
                        projeto=self.rdc.projeto,
                        disciplina=self.rdc.disciplina,
                        ativo=True,
                        data_inicio__lte=self.rdc.data,
                    )
                    .filter(Q(data_fim__isnull=True) | Q(data_fim__gte=self.rdc.data))
                    .order_by("-data_inicio")
                    .first()
                )
                if aloc:
                    ctx["equipe"] = getattr(aloc, "equipe", None)
                else:
                    ctx["alertas"].append("Sem alocAção ativa para o projeto/disciplina/data do RDC.")
        except Exception:
            ctx["alertas"].append("Não foi possível consultar a alocAção do funcionário.")

        try:
            from acesso.models import RegistroCatraca

            if self.rdc is not None and funcionario.matricula:
                presente = RegistroCatraca.objects.filter(
                    matricula=funcionario.matricula,
                    data=self.rdc.data,
                    presente=True,
                ).exists()
                ctx["presente_catraca"] = presente
                if not presente:
                    ctx["elegivel"] = False
                    ctx["alertas"].append("Sem catraca no dia.")
        except Exception:
            ctx["alertas"].append("Não foi possível validar a catraca do dia.")

        if not ctx["elegivel"]:
            ctx["motivo_bloqueio"] = " ; ".join(ctx["alertas"]) or "Sem catraca no dia."
        elif ctx["alertas"]:
            ctx["motivo_bloqueio"] = " ; ".join(ctx["alertas"])

        return ctx

    def clean(self):
        cleaned = super().clean()
        funcionario = cleaned.get("funcionario")

        if funcionario:
            autofill = self._resolve_funcionario_context(funcionario)
            cleaned["matricula"] = autofill["matricula"] or cleaned.get("matricula")
            cleaned["nome"] = autofill["nome"] or cleaned.get("nome")

            if "funcao" in self.fields and not cleaned.get("funcao"):
                cleaned["funcao"] = autofill["funcao"]

            if "equipe" in self.fields and not cleaned.get("equipe") and autofill["equipe"] is not None:
                cleaned["equipe"] = autofill["equipe"]

            if "hora_normal" in self.fields and cleaned.get("hora_normal") in (None, ""):
                cleaned["hora_normal"] = autofill["hora_normal"]
            if "hora_extra" in self.fields and cleaned.get("hora_extra") in (None, ""):
                cleaned["hora_extra"] = autofill["hora_extra"]

            if "presente_catraca" in self.fields:
                cleaned["presente_catraca"] = bool(autofill["presente_catraca"])

            if "elegivel" in self.fields:
                cleaned["elegivel"] = bool(autofill["elegivel"])

            if "motivo_bloqueio" in self.fields and not cleaned.get("motivo_bloqueio"):
                cleaned["motivo_bloqueio"] = autofill["motivo_bloqueio"]

        hora_normal = cleaned.get("hora_normal")
        hora_extra = cleaned.get("hora_extra")
        hora_normal = DEFAULT_HORA_NORMAL if hora_normal in (None, "") else hora_normal
        hora_extra = DEFAULT_HORA_EXTRA if hora_extra in (None, "") else hora_extra

        if hora_normal < 0 or hora_extra < 0:
            raise ValidationError("Hora normal e hora extra não podem ser negativas.")

        cleaned["hora_normal"] = hora_normal
        cleaned["hora_extra"] = hora_extra

        if "hh_total" in self.fields:
            cleaned["hh_total"] = hora_normal + hora_extra

        presente_catraca = bool(cleaned.get("presente_catraca"))
        liberado_sem_catraca = bool(cleaned.get("liberado_sem_catraca"))
        justificativa_liberacao = (cleaned.get("justificativa_liberacao") or "").strip()

        if presente_catraca:
            cleaned["liberado_sem_catraca"] = False
            cleaned["justificativa_liberacao"] = ""
            if "elegivel" in self.fields:
                cleaned["elegivel"] = True
            cleaned["motivo_bloqueio"] = ""
        else:
            if liberado_sem_catraca:
                if not justificativa_liberacao:
                    raise ValidationError({
                        "justificativa_liberacao": "Informe a justificativa da liberAção manual."
                    })
                if "elegivel" in self.fields:
                    cleaned["elegivel"] = True
                cleaned["motivo_bloqueio"] = "Sem catraca no dia €” liberado manualmente."
                cleaned["justificativa_liberacao"] = justificativa_liberacao
            else:
                if "elegivel" in self.fields:
                    cleaned["elegivel"] = False
                cleaned["motivo_bloqueio"] = "Sem catraca no dia."
                cleaned["justificativa_liberacao"] = ""

        matricula = (cleaned.get("matricula") or "").strip()
        nome = (cleaned.get("nome") or "").strip()

        if not matricula and not nome:
            raise ValidationError("Selecione um funcionário ou informe matrícula/nome.")

        if self.rdc is not None and funcionario:
            qs = RDCFuncionario.objects.filter(rdc=self.rdc, funcionario=funcionario)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise ValidationError("Este funcionário já foi incluído neste RDC.")

        return cleaned


class RDCApontamentoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RDCApontamento
        exclude = ["rdc"]

    def __init__(self, *args, **kwargs):
        self.rdc = kwargs.pop("rdc", None)
        super().__init__(*args, **kwargs)

        if self.rdc is not None:
            if "rdc_funcionario" in self.fields:
                self.fields["rdc_funcionario"].queryset = self.rdc.funcionarios.all().order_by("nome")
                self.fields["rdc_funcionario"].help_text = (
                    "Somente funcionários incluídos neste RDC. "
                    "Funcionários não elegíveis exibem bloqueio no lançamento."
                )

            if "rdc_atividade" in self.fields:
                self.fields["rdc_atividade"].queryset = self.rdc.atividades.all().order_by(
                    "codigo_atividade",
                    "descr_atividade",
                )

        if "horas" in self.fields:
            self.fields["horas"].widget.attrs.setdefault("step", "0.25")

    def clean(self):
        cleaned = super().clean()
        funcionario = cleaned.get("rdc_funcionario")
        atividade = cleaned.get("rdc_atividade")
        horas = cleaned.get("horas")

        if horas is not None and horas <= 0:
            raise ValidationError("As horas do apontamento devem ser maiores que zero.")

        if horas is not None and horas > Decimal("24.00"):
            raise ValidationError("As horas do apontamento não podem ser maiores que 24.")

        if funcionario and atividade and self.rdc is not None:
            qs = RDCApontamento.objects.filter(
                rdc=self.rdc,
                rdc_funcionario=funcionario,
                rdc_atividade=atividade,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise ValidationError("Já existe apontamento para este funcionário nesta atividade.")

            if getattr(funcionario, "elegivel", True) is False:
                detalhe = (getattr(funcionario, "motivo_bloqueio", "") or "").strip()
                raise ValidationError(
                    "Não é permitido apontar horas para funcionário bloqueado ou não elegível."
                    + (f" Motivo: {detalhe}" if detalhe else "")
                )

            if getattr(atividade, "ativa_no_dia", True) is False:
                raise ValidationError("Não é permitido apontar horas para atividade inativa no dia.")

            limite = (
                (getattr(funcionario, "hora_normal", Decimal("0.00")) or Decimal("0.00"))
                + (getattr(funcionario, "hora_extra", Decimal("0.00")) or Decimal("0.00"))
            )

            ja_apontado = RDCApontamento.objects.filter(
                rdc=self.rdc,
                rdc_funcionario=funcionario,
            )
            if self.instance.pk:
                ja_apontado = ja_apontado.exclude(pk=self.instance.pk)

            total_existente = ja_apontado.aggregate(total=Sum("horas")).get("total") or Decimal("0.00")
            total_final = total_existente + (horas or Decimal("0.00"))

            if limite and total_final > limite:
                raise ValidationError(
                    f"O total de horas do funcionário excede o limite diário ({limite})."
                )

        return cleaned


class RDCValidacaoForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = RDCValidacao
        exclude = ["rdc"]
        widgets = {
            "mensagem": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        if "status" in self.fields and not cleaned.get("status"):
            cleaned["status"] = StatusValidacaoChoices.ALERTA
        return cleaned


class RDCApontamentoRapidoForm(RDCApontamentoForm):
    salvar_continuar = forms.BooleanField(required=False, label="Salvar e continuar")

    class Meta(RDCApontamentoForm.Meta):
        fields = ["rdc_funcionario", "rdc_atividade", "horas", "observacao"]


class RDCApontamentoLoteRapidoForm(BootstrapFormMixin, forms.Form):
    rdc_atividade = forms.ModelChoiceField(queryset=RDCAtividade.objects.none(), label="Atividade")
    funcionarios = forms.ModelMultipleChoiceField(
        queryset=RDCFuncionario.objects.none(),
        label="Funcionários",
        widget=forms.SelectMultiple(attrs={"size": 8}),
    )
    horas = forms.DecimalField(max_digits=6, decimal_places=2, min_value=Decimal("0.25"), label="Horas")
    observacao = forms.CharField(required=False, label="ObservAção", widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        self.rdc = kwargs.pop("rdc", None)
        super().__init__(*args, **kwargs)
        if self.rdc is not None:
            self.fields["rdc_atividade"].queryset = self.rdc.atividades.filter(ativa_no_dia=True).order_by("codigo_atividade", "descr_atividade")
            if not self.fields["rdc_atividade"].queryset.exists():
                self.fields["rdc_atividade"].queryset = self.rdc.atividades.all().order_by("codigo_atividade", "descr_atividade")
            self.fields["funcionarios"].queryset = self.rdc.funcionarios.filter(elegivel=True).order_by("nome")
        self.fields["horas"].widget.attrs.setdefault("step", "0.25")

    def clean(self):
        cleaned = super().clean()
        atividade = cleaned.get("rdc_atividade")
        funcionarios = cleaned.get("funcionarios")
        horas = cleaned.get("horas")

        if atividade and getattr(atividade, "ativa_no_dia", True) is False:
            raise ValidationError("Não é permitido apontar horas para atividade inativa no dia.")
        if horas is not None and horas > Decimal("24.00"):
            raise ValidationError("As horas do apontamento não podem ser maiores que 24.")
        if not funcionarios:
            raise ValidationError("Selecione pelo menos um funcionário para o lançamento em lote.")

        if self.rdc is not None and horas is not None:
            for funcionario in funcionarios:
                if getattr(funcionario, "elegivel", True) is False:
                    detalhe = (getattr(funcionario, "motivo_bloqueio", "") or "").strip()
                    raise ValidationError(
                        "Não é permitido apontar horas para funcionário bloqueado ou não elegível."
                        + (f" Motivo: {detalhe}" if detalhe else "")
                    )
                limite = ((getattr(funcionario, "hora_normal", Decimal("0.00")) or Decimal("0.00"))
                          + (getattr(funcionario, "hora_extra", Decimal("0.00")) or Decimal("0.00")))
                total_existente = RDCApontamento.objects.filter(rdc=self.rdc, rdc_funcionario=funcionario).aggregate(total=Sum("horas")).get("total") or Decimal("0.00")
                total_final = total_existente + horas
                if limite and total_final > limite:
                    raise ValidationError(
                        f"{funcionario.nome}: o total apontado ({total_final}) ultrapassa o limite disponível ({limite})."
                    )
        return cleaned


class RDCWorkflowActionForm(BootstrapFormMixin, forms.Form):
    acao = forms.ChoiceField(
        choices=[
            ("enviar_revisao", "Enviar para revisão"),
            ("aprovar", "Aprovar"),
            ("devolver", "Devolver para rascunho"),
            ("fechar", "Fechar RDC"),
            ("reabrir", "Reabrir RDC"),
        ],
        widget=forms.HiddenInput,
    )
    observacao = forms.CharField(required=False, label="ObservAção", widget=forms.Textarea(attrs={"rows": 3}))
    forcar = forms.BooleanField(required=False, label="Permitir Ação mesmo com bloqueios")


