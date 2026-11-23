"""Cria um projeto de DEMONSTRAÇÃO (fictício) de construção naval para ver o sistema funcionando.

PSV 4500 (navio de apoio offshore), dois cascos, cinco blocos, seis disciplinas, cronograma com
HH orçado e cerca de dois meses de RDCs com equipe, atividades, apontamentos, paralisações,
equipamentos e ocorrências. Tudo marcado como DEMO e removível com --remover.

Uso:
    python manage.py criar_projeto_demo
    python manage.py criar_projeto_demo --remover
"""
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from cadastros.models import AreaLocal, Disciplina, Empresa, Equipe, Funcao, Funcionario, Projeto
from core.choices import StatusRDCChoices, TurnoChoices
from planejamento.models import AtividadeCronograma
from rdc.models import (
    RDC, CalendarioPlanejamento, PerfilOperacionalUsuario, RDCApontamento, RDCAtividade, RDCEquipamento, RDCFuncionario,
    RDCOcorrencia, RDCParalisacao,
)

CODIGO = "DEMO-PSV"
PREFIXO = "DEMO-"

DISCIPLINAS = [
    ("DEMO-EST", "Estrutura / caldeiraria", "Montador", "Caldeireiro"),
    ("DEMO-SOL", "Solda", "Soldador", "Soldador"),
    ("DEMO-TUB", "Tubulação", "Encanador", "Encanador"),
    ("DEMO-PIN", "Pintura e tratamento", "Pintor", "Jatista"),
    ("DEMO-ELE", "Elétrica", "Eletricista", "Eletricista"),
]

NOMES = [
    "Adriano Lopes", "Bruno Siqueira", "Carlos Menezes", "Diego Farias", "Edson Prates", "Fábio Nunes",
    "Gilson Rocha", "Hugo Barreto", "Igor Cardoso", "Jair Moura", "Kleber Dias", "Luan Batista",
    "Marcos Teixeira", "Nilton Paiva", "Otávio Ramos", "Paulo Vieira", "Renato Alves", "Sérgio Lima",
    "Tiago Freitas", "Ulisses Souza", "Valter Pires", "Wagner Costa", "Yuri Matos", "Zeca Andrade",
    "André Pacheco", "Cícero Gomes", "Davi Rezende", "Emerson Leal", "Flávio Torres", "Gustavo Mendes",
]

# (codigo, casco, toneladas de aço, dias atrás em que começou, ritmo: 1.0 = no prazo)
BLOCOS = [
    ("B101", "Casco 101", 85, 70, 1.06),
    ("B102", "Casco 101", 110, 60, 0.82),
    ("B201", "Casco 101", 95, 46, 0.98),
    ("B202", "Casco 102", 120, 40, 0.68),
    ("B301", "Casco 102", 70, 20, 1.00),
]

# (sufixo, descrição, disciplina, unidade, escopo por tonelada, início (dias após o bloco), duração, HH por unidade)
ATIVIDADES = [
    ("FAB", "Fabricação de painéis e reforços", "DEMO-EST", "t", 1.0, 0, 20, 14),
    ("MON", "Montagem e edificação do bloco", "DEMO-EST", "t", 1.0, 12, 25, 18),
    ("SOL", "Solda de costuras e reforços", "DEMO-SOL", "m", 9.0, 15, 28, 1.6),
    ("TUB", "Pré-outfitting de tubulação (spools)", "DEMO-TUB", "UN", 0.45, 25, 20, 22),
    ("ELE", "Bandejamento e passagem de cabos", "DEMO-ELE", "m", 3.0, 33, 18, 0.9),
    ("PIN", "Jateamento e pintura de fundo", "DEMO-PIN", "m²", 11.0, 40, 15, 0.6),
]

CLIMAS = ["Ensolarado", "Ensolarado", "Nublado", "Parcialmente nublado", "Chuva fraca"]


def _dias_uteis(inicio, fim):
    d, dias = inicio, []
    while d <= fim:
        if d.weekday() < 6:
            dias.append(d)
        d += timedelta(days=1)
    return dias


class Command(BaseCommand):
    help = "Cria (ou remove, com --remover) um projeto naval de demonstração com dados fictícios."

    def add_arguments(self, parser):
        parser.add_argument("--remover", action="store_true")
        parser.add_argument("--semente", type=int, default=42)

    def handle(self, *args, **options):
        with transaction.atomic():
            self._remover()
            if options["remover"]:
                self.stdout.write(self.style.SUCCESS("Projeto de demonstração removido."))
                return
            random.seed(options["semente"])
            self._criar()

    # ------------------------------------------------------------------ remover
    def _remover(self):
        RDC.objects.filter(projeto__codigo=CODIGO).delete()
        PerfilOperacionalUsuario.objects.filter(funcionario__matricula__startswith=PREFIXO).delete()
        AtividadeCronograma.objects.filter(projeto__codigo=CODIGO).delete()
        Equipe.objects.filter(codigo__startswith=PREFIXO).delete()
        Funcionario.objects.filter(matricula__startswith=PREFIXO).delete()
        AreaLocal.objects.filter(projeto__codigo=CODIGO).delete()
        Projeto.objects.filter(codigo=CODIGO).delete()
        Funcao.objects.filter(codigo__startswith=PREFIXO).delete()
        Disciplina.objects.filter(codigo__startswith=PREFIXO).delete()
        Empresa.objects.filter(nome__startswith="DEMO ").delete()

    # ------------------------------------------------------------------ criar
    def _criar(self):
        hoje = timezone.localdate()
        usuario = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
        if usuario is None:
            usuario = get_user_model().objects.order_by("pk").first()

        projeto = Projeto.objects.create(codigo=CODIGO, nome="PSV 4500 · DEMONSTRAÇÃO", cliente="Armador Demonstração S.A.")
        estaleiro = Empresa.objects.create(nome="DEMO Estaleiro Atlântico (fictício)")
        terceira = Empresa.objects.create(nome="DEMO Pinturas Industriais (fictício)")

        disciplinas, funcoes, equipes, pessoas = {}, {}, {}, {}
        enc_funcao = Funcao.objects.create(codigo="DEMO-ENC", nome="Encarregado")
        nomes = iter(NOMES)
        n = 1
        for codigo, nome, f1, f2 in DISCIPLINAS:
            disc = Disciplina.objects.create(codigo=codigo, nome=nome)
            disciplinas[codigo] = disc
            for fn in {f1, f2}:
                if fn not in funcoes:
                    funcoes[fn] = Funcao.objects.create(codigo=f"DEMO-{fn[:6].upper()}", nome=fn)
            empresa = terceira if codigo == "DEMO-PIN" else estaleiro
            encarregado = Funcionario.objects.create(matricula=f"DEMO-{n:03d}", nome=next(nomes), funcao=enc_funcao, empresa=empresa)
            n += 1
            equipe = Equipe.objects.create(codigo=f"DEMO-{codigo[-3:]}", nome=f"Equipe {nome}", disciplina=disc,
                                           empresa=empresa, encarregado=encarregado)
            equipes[codigo] = equipe
            time_ = [encarregado]
            for i in range(5):
                time_.append(Funcionario.objects.create(
                    matricula=f"DEMO-{n:03d}", nome=next(nomes), funcao=funcoes[f1 if i % 2 == 0 else f2], empresa=empresa))
                n += 1
            pessoas[codigo] = time_

        # Perfil operacional (Novo RDC guiado / modo campo) para quem administra e ainda não tem
        admins = get_user_model().objects.filter(is_active=True).filter(
            Q(is_superuser=True) | Q(is_staff=True) | Q(perfil_acesso__role__in=["admin", "supervisor"])).distinct()
        for user in admins:
            if not PerfilOperacionalUsuario.objects.filter(user=user).exists():
                PerfilOperacionalUsuario.objects.create(
                    user=user, funcionario=pessoas["DEMO-EST"][0], projeto_padrao=projeto,
                    disciplina_padrao=disciplinas["DEMO-EST"], equipe_padrao=equipes["DEMO-EST"])

        areas = {}
        for codigo, casco, _t, _atras, _ritmo in BLOCOS:
            areas[codigo] = AreaLocal.objects.create(
                projeto=projeto, codigo=codigo, descricao=f"Bloco {codigo}", tipo="bloco", casco=casco,
                etapa="montagem_bloco", disciplina_padrao=disciplinas["DEMO-EST"])
        areas["DQ1"] = AreaLocal.objects.create(projeto=projeto, codigo="DQ1", descricao="Dique seco 1", tipo="dique",
                                                casco="Casco 101", etapa="edificacao")

        # Cronograma
        crono = []
        for codigo, _casco, toneladas, atras, ritmo in BLOCOS:
            inicio_bloco = hoje - timedelta(days=atras)
            for suf, desc, disc, unid, por_t, ini, dur, hh in ATIVIDADES:
                escopo = Decimal(str(round(toneladas * por_t)))
                crono.append((AtividadeCronograma.objects.create(
                    projeto=projeto, area_local=areas[codigo], disciplina=disciplinas[disc],
                    codigo_atividade=f"{suf}-{codigo}", descr_atividade=f"{desc} · {codigo}", qtd_escopo=escopo,
                    unidade=unid, data_inicio=inicio_bloco + timedelta(days=ini),
                    data_fim=inicio_bloco + timedelta(days=ini + dur), status_planejado="Planejada",
                    peso=(escopo * Decimal(str(hh))).quantize(Decimal("1"))), codigo, ritmo))

        # Execução diária -> RDCs
        feito = {a.pk: Decimal("0") for a, _, _ in crono}
        rdcs = 0
        for dia in _dias_uteis(min(a.data_inicio for a, _, _ in crono), hoje):
            frentes = {}
            for ativ, bloco, ritmo in crono:
                limite = ativ.data_fim + timedelta(days=12)  # atividade atrasada continua depois do fim
                if not (ativ.data_inicio <= dia <= limite) or feito[ativ.pk] >= ativ.qtd_escopo:
                    continue
                frentes.setdefault((bloco, ativ.disciplina.codigo), []).append((ativ, ritmo))
            for (bloco, disc), lista in sorted(frentes.items()):
                if dia == hoje and bloco not in ("B101", "B201"):
                    continue  # parte das frentes ainda sem RDC hoje -> aparece nos alertas
                self._rdc_do_dia(projeto, areas[bloco], disciplinas[disc], equipes[disc], pessoas[disc], dia, hoje,
                                 lista, feito, usuario)
                rdcs += 1

        self._ocorrencias(projeto, hoje, usuario)
        self._calendario(projeto, min(a.data_inicio for a, _, _ in crono) - timedelta(days=14), hoje + timedelta(days=150))
        self.stdout.write(self.style.SUCCESS(
            f"Projeto {CODIGO} criado: {len(areas)} áreas, {len(crono)} atividades planejadas, {rdcs} RDCs. "
            f"Abra /rdc/avanco/?projeto={projeto.pk}"))

    def _rdc_do_dia(self, projeto, area, disciplina, equipe, time_, dia, hoje, lista, feito, usuario):
        if dia == hoje:
            status = StatusRDCChoices.PRE_PREENCHIDO
        elif dia >= hoje - timedelta(days=2):
            status = StatusRDCChoices.EM_REVISAO
        else:
            status = StatusRDCChoices.FECHADO
        clima = random.choice(CLIMAS)
        rdc = RDC.objects.create(
            projeto=projeto, area_local=area, disciplina=disciplina, data=dia, turno=TurnoChoices.INTEGRAL,
            supervisor=time_[0], criado_por=usuario, status=status, clima_manha=clima, clima_tarde=random.choice(CLIMAS),
            condicao_area="Liberada", horario_inicio=time(7, 0), horario_fim=time(17, 0),
            fechado_em=timezone.make_aware(datetime.combine(dia, time(18, 0))) if status == StatusRDCChoices.FECHADO else None,
            fechado_por=usuario if status == StatusRDCChoices.FECHADO else None,
        )
        atividades = []
        for ativ, ritmo in lista:
            dias = max(len(_dias_uteis(ativ.data_inicio, ativ.data_fim)), 1)
            qtd = ativ.qtd_escopo / dias * Decimal(str(ritmo)) * Decimal(str(random.uniform(0.75, 1.2)))
            if clima == "Chuva fraca" and ativ.unidade == "m²":
                qtd = Decimal("0")
            qtd = min(qtd.quantize(Decimal("0.01")), ativ.qtd_escopo - feito[ativ.pk])
            feito[ativ.pk] += qtd
            atividades.append(RDCAtividade.objects.create(
                rdc=rdc, atividade_cronograma=ativ, codigo_atividade=ativ.codigo_atividade,
                descr_atividade=ativ.descr_atividade, qtd_escopo=ativ.qtd_escopo, qtd_executada=qtd))

        fechado = status == StatusRDCChoices.FECHADO
        escalados = [time_[0]] + random.sample(time_[1:], k=random.randint(3, 5))
        membros = []
        for pessoa in escalados:
            extra = Decimal("2.00") if random.random() < 0.15 else Decimal("0.00")
            membros.append(RDCFuncionario.objects.create(
                rdc=rdc, funcionario=pessoa, equipe=equipe, funcao=pessoa.funcao, matricula=pessoa.matricula,
                nome=pessoa.nome, hora_normal=Decimal("8.00"), hora_extra=extra, presente_catraca=True,
                confirmado_supervisor=fechado))
        RDCApontamento.objects.bulk_create([
            RDCApontamento(rdc=rdc, rdc_funcionario=m, rdc_atividade=atividades[i % len(atividades)], horas=m.hh_total)
            for i, m in enumerate(membros)
        ])

        disc = disciplina.codigo
        if disc in ("DEMO-EST", "DEMO-SOL"):
            RDCEquipamento.objects.create(
                rdc=rdc, tipo="portico" if disc == "DEMO-EST" else "maquina_solda",
                identificacao="PT-02" if disc == "DEMO-EST" else f"MS-{random.randint(10, 24)}",
                horas_trabalhadas=Decimal("7.00"), horas_paradas=Decimal("1.00") if random.random() < 0.2 else 0,
                motivo_parada="aguardando_frente" if random.random() < 0.2 else "", criado_por=usuario)

        sorteio = random.random()
        motivo = None
        if clima == "Chuva fraca" and disc in ("DEMO-PIN", "DEMO-SOL"):
            motivo, desc = "chuva", "Chuva no dique; trabalho externo suspenso."
        elif area.codigo == "B202" and sorteio < 0.35:
            motivo, desc = "falta_material", "Chapas de 12,5 mm do bloco B202 ainda não recebidas do fornecedor."
        elif disc == "DEMO-EST" and sorteio < 0.12:
            motivo, desc = "aguardando_icamento", "Pórtico ocupado com outro bloco."
        elif disc == "DEMO-SOL" and sorteio < 0.10:
            motivo, desc = "aguardando_inspecao", "Aguardando liberação do CQ (dimensional) para soldar."
        if motivo:
            RDCParalisacao.objects.create(
                rdc=rdc, motivo=motivo, inicio=time(13, 0), fim=time(15, 30) if motivo != "falta_material" else time(17, 0),
                pessoas_afetadas=len(membros), equipe=equipe, rdc_atividade=atividades[0], descricao=desc,
                criado_por=usuario)

    def _ocorrencias(self, projeto, hoje, usuario):
        def rdc_em(bloco, dias):
            return (RDC.objects.filter(projeto=projeto, area_local__codigo=bloco, data__lte=hoje - timedelta(days=dias))
                    .order_by("-data").first())

        casos = [
            ("B202", 2, "quase_acidente", "alta", "aberta", "Peça de 300 kg balançou durante içamento sem cabo-guia.",
             "Içamento suspenso e APR revisada."),
            ("B102", 5, "nao_conformidade", "media", "aberta", "Ultrassom reprovou 2 m de solda na costura C-14.",
             "Reparo programado; nova inspeção após reparo."),
            ("B101", 12, "condicao_insegura", "media", "encerrada", "Guarda-corpo provisório solto no nível 2.",
             "Guarda-corpo refixado e área inspecionada."),
        ]
        for bloco, dias, tipo, grav, status, desc, acao in casos:
            rdc = rdc_em(bloco, dias)
            if rdc:
                RDCOcorrencia.objects.create(
                    rdc=rdc, tipo=tipo, gravidade=grav, hora=time(10, 30), local=f"Bloco {bloco}", descricao=desc,
                    acao_imediata=acao, responsavel="Técnico de segurança (fictício)", status=status,
                    encerrada_em=timezone.now() if status == "encerrada" else None, criado_por=usuario)

    def _calendario(self, projeto, inicio, fim):
        """Semanas de planejamento sábado a sexta, como no calendário importado (código AASS)."""
        nomes = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        registros, d = [], inicio
        while d <= fim:
            jan1 = d.replace(month=1, day=1)
            primeiro_sabado = jan1 + timedelta(days=(5 - jan1.weekday()) % 7)
            if d < primeiro_sabado:
                ano_ref = d.year - 1
                jan1 = jan1.replace(year=ano_ref)
                primeiro_sabado = jan1 + timedelta(days=(5 - jan1.weekday()) % 7)
            semana = (d - primeiro_sabado).days // 7 + 1
            inicio_semana = primeiro_sabado + timedelta(weeks=semana - 1)
            codigo = f"{primeiro_sabado.year % 100:02d}{semana:02d}"
            registros.append(CalendarioPlanejamento(
                projeto=projeto, data=d, ano=d.year, mes=d.month, semana_codigo=codigo, semana_numero=semana,
                semana_label=f"SEM {codigo}", data_inicio_semana=inicio_semana,
                data_fim_semana=inicio_semana + timedelta(days=6), dia_semana=d.weekday(),
                dia_semana_nome=nomes[d.weekday()], eh_dia_util=d.weekday() < 5))
            d += timedelta(days=1)
        CalendarioPlanejamento.objects.bulk_create(registros)
