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
        from punchlist.models import PunchItem
        from soldagem.models import EPS, JuntaSolda, Soldador
        PunchItem.objects.filter(projeto__codigo=CODIGO).delete()
        JuntaSolda.objects.filter(projeto__codigo=CODIGO).delete()
        Soldador.objects.filter(funcionario__matricula__startswith=PREFIXO).delete()
        EPS.objects.filter(codigo__startswith=PREFIXO).delete()
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
        if usuario is None:  # banco vazio (instância de demonstração): cria o visitante, sem senha
            usuario = get_user_model().objects.create(username="visitante", first_name="Visitante", is_superuser=True)
            usuario.set_unusable_password()
            usuario.save()

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
        juntas = self._soldagem(projeto, areas, pessoas["DEMO-SOL"], hoje, usuario)
        punch = self._punch(projeto, areas, disciplinas, hoje, usuario)
        self.stdout.write(self.style.SUCCESS(
            f"Projeto {CODIGO} criado: {len(areas)} áreas, {len(crono)} atividades planejadas, {rdcs} RDCs, "
            f"{juntas} juntas de solda, {punch} pendências no punch list. "
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
            ("B102", 5, "nao_conformidade", "media", "aberta", "Ultrassom reprovou 2,5 m de solda na junta B102-C05 (falta de fusão).",
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

    def _soldagem(self, projeto, areas, time_solda, hoje, usuario):
        """Juntas por bloco soldadas nos dias de RDC de solda, com END, reprovações e reparos."""
        from soldagem.models import EPS, JuntaSolda, ResultadoEND, Soldador, StatusJunta
        from soldagem.services import registrar_execucao, registrar_resultado_end

        fcaw = EPS.objects.create(codigo="DEMO-EPS-FCAW-01", processo="FCAW", material="Aço naval AH36",
                                  espessura="6 a 25 mm", posicoes="1G a 4G", consumivel="E71T-1C")
        EPS.objects.create(codigo="DEMO-EPS-SMAW-02", processo="SMAW", material="Aço naval AH36",
                           espessura="6 a 20 mm", posicoes="1G a 4G", consumivel="E7018")
        soldadores = []
        for i, pessoa in enumerate(time_solda[1:]):
            validade = hoje + timedelta(days=10) if i == 3 else hoje + timedelta(days=180 + 30 * i)
            soldadores.append(Soldador.objects.create(
                funcionario=pessoa, sinete=f"S-{101 + i}", processos="FCAW, SMAW", posicoes="1G a 4G",
                certificado=f"CQ-{2026}-{311 + i}", validade_qualificacao=validade))
        # S-102 erra mais (aparece acima da meta de reparo)
        chance = {"B101": 0.05, "B102": 0.45, "B201": 0.06, "B202": 0.08, "B301": 0.05}
        locais = ["costura do fundo", "costura do costado", "antepara transversal", "longitudinal do convés",
                  "reforço do duplo-fundo", "caverna"]
        total = 0
        for bloco in ("B101", "B102", "B201", "B202", "B301"):
            area = areas[bloco]
            dias = list(RDC.objects.filter(projeto=projeto, area_local=area, disciplina__codigo="DEMO-SOL")
                        .order_by("data").values_list("data", flat=True))
            juntas = []
            for n in range(1, 11):
                filete = n in (4, 8)
                juntas.append(JuntaSolda.objects.create(
                    projeto=projeto, area_local=area, codigo=f"{bloco}-C{n:02d}",
                    descricao=f"{locais[n % len(locais)]}, caverna {20 + n * 2}",
                    tipo="filete" if filete else "topo", comprimento_m=Decimal(str(random.choice([6, 8, 9.5, 12, 14]))),
                    espessura_mm=Decimal(random.choice(["10", "12.5", "14", "16"])), eps=fcaw,
                    metodo_end="VS" if filete else random.choice(["UT", "UT", "RX"])))
            total += len(juntas)
            fila = list(juntas)
            for dia in dias:
                if not fila:
                    break
                junta = fila[0]
                junta.refresh_from_db()
                restante = junta.comprimento_m - junta.metros_soldados
                metros = min(restante, Decimal(str(round(random.uniform(4, 7), 1))))
                s = random.choice(soldadores[:3]) if bloco != "B102" else random.choice([soldadores[1], soldadores[1], soldadores[2]])
                registrar_execucao(junta, soldador=s, data=dia, metros=metros, usuario=usuario)
                junta.refresh_from_db()
                if junta.status == StatusJunta.AGUARDANDO_END:
                    fila.pop(0)
            if bloco == "B101" and dias:
                # bloco concluído no demo: termina o que sobrou no último dia de solda
                for junta in fila:
                    junta.refresh_from_db()
                    resto = junta.comprimento_m - junta.metros_soldados
                    if resto > 0:
                        registrar_execucao(junta, soldador=soldadores[0], data=dias[-1], metros=resto, usuario=usuario)

            # Ensaios: resultado 1 a 2 dias depois; os das últimas 48 h ficam pendentes
            for junta in juntas:
                for _ in range(3):
                    junta.refresh_from_db()
                    pend = junta.inspecoes.filter(resultado=ResultadoEND.PENDENTE).first()
                    if not pend:
                        break
                    data_ensaio = pend.solicitado_em + timedelta(days=random.choice([1, 2]))
                    if data_ensaio >= hoje - timedelta(days=1) and junta.codigo != "B202-C03":
                        break  # ainda na fila (B202-C03 fica pendente há dias: alerta)
                    if junta.codigo == "B202-C03":
                        break
                    reprova = pend.ciclo == 1 and (junta.codigo == "B102-C05" or (
                        pend.metodo != "VS" and random.random() < chance[bloco]))
                    if junta.codigo == "B102-C05":
                        reprova = pend.ciclo == 1
                    registrar_resultado_end(
                        pend, resultado=ResultadoEND.REPROVADO if reprova else ResultadoEND.APROVADO, data=data_ensaio,
                        metros_reprovados=Decimal(str(random.choice([1.5, 2.5, 3.5]))) if reprova else 0,
                        defeito=random.choice(["falta_fusao", "porosidade", "inclusao_escoria"]) if reprova else "",
                        inspetor="Inspetor N2 (fictício)", relatorio=f"{pend.metodo}-{junta.codigo}-{pend.ciclo}",
                        usuario=usuario)
                    if not reprova:
                        break
                    data_reparo = data_ensaio + timedelta(days=1)
                    if data_reparo >= hoje - timedelta(days=1) or junta.codigo == "B102-C05":
                        break  # reprovada aguardando reparo
                    registrar_execucao(junta, soldador=random.choice(soldadores[:3]), data=data_reparo,
                                       metros=Decimal("2.0"), reparo=True, usuario=usuario)
        return total

    def _punch(self, projeto, areas, disciplinas, hoje, usuario):
        """Pendências típicas de bloco naval em várias situações (A/B/C, vencidas, em verificação, fechadas)."""
        from datetime import timedelta as td
        from punchlist.models import PunchItem
        from punchlist.services import abrir_item, iniciar_item, resolver_item, verificar_item

        empresa = Empresa.objects.filter(nome__startswith="DEMO Estaleiro").first()
        pintura = Empresa.objects.filter(nome__startswith="DEMO Pinturas").first()
        d = disciplinas
        # (bloco, compartimento, disciplina, cat, origem, descrição, empresa, dias atrás, prazo em dias, situação final)
        casos = [
            ("B101", "Duplo-fundo, tanque 1BB", "DEMO-EST", "C", "interna", "Rebarba de corte na borda do agulheiro.", empresa, 30, 10, "fechada"),
            ("B101", "Convés principal", "DEMO-PIN", "B", "fiscal", "Retoque de pintura na região da solda C-07.", pintura, 25, 10, "fechada"),
            ("B101", "Antepara 34", "DEMO-SOL", "B", "interna", "Mordedura na solda de filete do reforço vertical.", empresa, 22, 7, "fechada"),
            ("B102", "Costado BE, caverna 28", "DEMO-SOL", "A", "classe", "Reparo da junta B102-C05 reprovada no ultrassom (falta de fusão, 2,5 m).", empresa, 6, 4, "aberta"),
            ("B102", "Duplo-fundo", "DEMO-EST", "B", "interna", "Agulheiro de passagem fora de cota (desvio de 12 mm).", empresa, 9, 7, "andamento"),
            ("B102", "Antepara 30", "DEMO-TUB", "B", "comissionamento", "Falta suporte do spool TUB-B102-04.", empresa, 4, 10, "verificacao"),
            ("B102", "Convés", "DEMO-PIN", "C", "fiscal", "Marcação de tinta ilegível na identificação do bloco.", pintura, 3, 15, "aberta"),
            ("B201", "Praça de máquinas, nível 2", "DEMO-ELE", "B", "interna", "Bandeja de cabos sem aterramento no trecho 3.", empresa, 8, 5, "verificacao"),
            ("B201", "Praça de máquinas", "DEMO-EST", "C", "interna", "Olhais de içamento ainda não removidos.", empresa, 5, 20, "aberta"),
            ("B201", "Tanque 2BE", "DEMO-PIN", "B", "classe", "Espessura de película abaixo do especificado em 3 pontos.", pintura, 12, 6, "recusada"),
            ("B202", "Costado BB", "DEMO-EST", "A", "interna", "Abertura provisória para passagem de material sem fechamento (aguardando chapa de 12,5 mm).", empresa, 15, 5, "aberta"),
            ("B202", "Antepara 40", "DEMO-SOL", "A", "fiscal", "Junta B202-C03 sem resultado de END; não liberar edificação.", empresa, 10, 3, "aberta"),
            ("B202", "Duplo-fundo", "DEMO-TUB", "B", "comissionamento", "Teste hidrostático do trecho de lastro pendente.", empresa, 7, 4, "aberta"),
            ("B202", "Convés", "DEMO-EST", "C", "seguranca", "Guarda-corpo provisório com fixação improvisada.", empresa, 2, 3, "aberta"),
            ("B301", "Convés principal", "DEMO-EST", "B", "interna", "Desalinhamento de 4 mm na costura transversal.", empresa, 4, 10, "aberta"),
            ("B301", "Superestrutura", "DEMO-ELE", "C", "interna", "Furos de passagem de cabos sem bucha de proteção.", empresa, 1, 20, "aberta"),
        ]
        for bloco, comp, disc, cat, origem, desc, emp, atras, prazo, final in casos:
            item = abrir_item(projeto=projeto, area_local=areas[bloco], descricao=desc, categoria=cat, usuario=usuario,
                              compartimento=comp, disciplina=d[disc], origem=origem, responsavel_empresa=emp,
                              responsavel="Encarregado " + d[disc].nome.split()[0].lower(),
                              prazo=hoje - timedelta(days=atras) + timedelta(days=prazo))
            aberta_em = timezone.now() - timedelta(days=atras)
            if final in ("andamento", "verificacao", "fechada", "recusada"):
                iniciar_item(item)
            if final in ("verificacao", "fechada", "recusada"):
                resolver_item(item, nota="Corrigido conforme procedimento.", usuario=usuario)
            if final == "fechada":
                verificar_item(item, aprovado=True, nota="Conferido no local.", usuario=usuario)
            if final == "recusada":
                verificar_item(item, aprovado=False, nota="Ainda abaixo de 250 µm em 1 ponto; refazer.", usuario=usuario)
            # datas no passado só depois das transições (o save() delas regravaria created_at)
            datas = {"created_at": aberta_em}
            if final == "fechada":
                fechada = aberta_em + timedelta(days=random.randint(2, 6))
                datas.update(fechada_em=fechada, resolvida_em=fechada - td(days=1))
            elif final in ("verificacao", "recusada"):
                datas["resolvida_em"] = timezone.now() - td(days=1)
            PunchItem.objects.filter(pk=item.pk).update(**datas)
        return len(casos)
