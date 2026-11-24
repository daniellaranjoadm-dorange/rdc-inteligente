from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cadastros.models import AreaLocal, Disciplina, Projeto
from planejamento.models import AtividadeCronograma
from punchlist.services import abrir_item, cancelar_item
from rdc.models import RDC, RDCAtividade, RDCOcorrencia
from rdc.services.bloco_service import liberacao_blocos

User = get_user_model()


class LiberacaoBlocoTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_bl", "a@example.com", "x")
        self.projeto = Projeto.objects.create(codigo="P1", nome="PSV", cliente="T")
        self.disc = Disciplina.objects.create(codigo="EST-BL", nome="Estrutura")
        self.bloco = AreaLocal.objects.create(projeto=self.projeto, codigo="B1", descricao="Bloco 1")
        self.vazio = AreaLocal.objects.create(projeto=self.projeto, codigo="B9", descricao="Sem dados")
        self.hoje = timezone.localdate()
        self.ativ = AtividadeCronograma.objects.create(
            projeto=self.projeto, area_local=self.bloco, disciplina=self.disc, codigo_atividade="MON",
            descr_atividade="Montagem", qtd_escopo=Decimal("10"), unidade="t",
            data_inicio=self.hoje - timedelta(days=20), data_fim=self.hoje - timedelta(days=5), status_planejado="P")
        self.rdc = RDC.objects.create(projeto=self.projeto, area_local=self.bloco, disciplina=self.disc,
                                      data=self.hoje - timedelta(days=10), turno="manha", criado_por=self.admin,
                                      status="fechado")
        RDCAtividade.objects.create(rdc=self.rdc, atividade_cronograma=self.ativ, codigo_atividade="MON",
                                    descr_atividade="Montagem", qtd_executada=Decimal("10"))

    def _bloco(self):
        return {b["area"].codigo: b for b in liberacao_blocos(projeto_id=self.projeto.pk, hoje=self.hoje)}

    def test_bloco_completo_e_liberado_e_bloco_sem_dados_nao_aparece(self):
        blocos = self._bloco()
        self.assertNotIn("B9", blocos)
        b = blocos["B1"]
        self.assertTrue(b["liberado"])
        criterios = {c["chave"]: c["ok"] for c in b["criterios"]}
        self.assertTrue(criterios["avanco"])
        self.assertIsNone(criterios["solda"])  # sem juntas: não se aplica, não bloqueia
        self.assertTrue(criterios["rdc"])

    def test_pendencia_a_ocorrencia_grave_e_rdc_aberto_bloqueiam(self):
        item = abrir_item(projeto=self.projeto, area_local=self.bloco, descricao="Abertura sem fechar", categoria="A")
        RDCOcorrencia.objects.create(rdc=self.rdc, tipo="quase_acidente", gravidade="alta", descricao="x")
        RDC.objects.create(projeto=self.projeto, area_local=self.bloco, disciplina=self.disc,
                           data=self.hoje - timedelta(days=1), turno="manha", criado_por=self.admin, status="em_revisao")
        b = self._bloco()["B1"]
        self.assertFalse(b["liberado"])
        self.assertEqual({c["chave"] for c in b["pendencias"]}, {"punch", "seguranca", "rdc"})
        cancelar_item(item, motivo="duplicada")
        self.assertNotIn("punch", {c["chave"] for c in self._bloco()["B1"]["pendencias"]})

    def test_avanco_incompleto_bloqueia(self):
        RDCAtividade.objects.update(qtd_executada=Decimal("6"))
        b = self._bloco()["B1"]
        self.assertFalse(b["liberado"])
        self.assertEqual([c["chave"] for c in b["pendencias"]], ["avanco"])

    def test_telas(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("rdc-blocos"))
        self.assertContains(r, "Blocos e liberação para edificação")
        self.assertContains(r, reverse("rdc-bloco", args=[self.bloco.pk]))
        d = self.client.get(reverse("rdc-bloco", args=[self.bloco.pk]))
        self.assertContains(d, "Bloco liberado para subir.")
        self.assertContains(d, "Avanço físico concluído")
        self.assertEqual(self.client.get(reverse("rdc-bloco", args=[self.vazio.pk])).status_code, 200)

    def test_demo_tem_blocos_liberados_e_bloqueados(self):
        call_command("criar_projeto_demo", stdout=StringIO())
        demo = Projeto.objects.get(codigo="DEMO-PSV")
        blocos = {b["area"].codigo: b for b in liberacao_blocos(projeto_id=demo.pk)}
        self.assertTrue(blocos["B101"]["liberado"], blocos["B101"]["pendencias"])
        self.assertFalse(blocos["B202"]["liberado"])
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("rdc-bloco", args=[blocos["B202"]["area"].pk])).status_code, 200)
