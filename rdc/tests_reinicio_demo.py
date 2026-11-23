import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from cadastros.models import AreaLocal, Disciplina, Projeto
from planejamento.models import AtividadeCronograma
from rdc.models import RDC, RDCOcorrencia, RDCParalisacao
from rdc.services.avanco_service import montar_avanco

User = get_user_model()


class ReiniciarDadosTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin_rz", "a@example.com", "x")
        projeto = Projeto.objects.create(codigo="FAKE", nome="Fictício", cliente="T")
        disc = Disciplina.objects.create(codigo="X", nome="X")
        area = AreaLocal.objects.create(projeto=projeto, codigo="A", descricao="A")
        RDC.objects.create(projeto=projeto, area_local=area, disciplina=disc, data="2026-11-02", turno="manha",
                           criado_por=self.admin)

    def test_sem_confirmar_nao_apaga(self):
        saida = StringIO()
        call_command("reiniciar_dados", stdout=saida)
        self.assertIn("--confirmar", saida.getvalue())
        self.assertEqual(RDC.objects.count(), 1)

    def test_confirmar_faz_backup_apaga_e_mantem_usuarios(self):
        with tempfile.TemporaryDirectory() as pasta, mock.patch.dict("os.environ", {"BACKUP_DIR": pasta}):
            call_command("reiniciar_dados", "--confirmar", stdout=StringIO())
            arquivos = list(Path(pasta).glob("rdc_antes_reinicio_*.json"))
            self.assertEqual(len(arquivos), 1)
            dados = json.loads(arquivos[0].read_text(encoding="utf-8"))
            self.assertTrue(any(o["model"] == "rdc.rdc" for o in dados))
        self.assertFalse(RDC.objects.exists())
        self.assertFalse(Projeto.objects.exists())
        self.assertTrue(User.objects.filter(username="admin_rz").exists())


class ProjetoDemoTests(TestCase):
    def setUp(self):
        User.objects.create_superuser("admin_demo", "a@example.com", "x")

    def test_cria_dados_navais_coerentes_e_remove(self):
        call_command("criar_projeto_demo", stdout=StringIO())
        projeto = Projeto.objects.get(codigo="DEMO-PSV")
        self.assertEqual(AtividadeCronograma.objects.filter(projeto=projeto).count(), 30)
        self.assertGreater(RDC.objects.filter(projeto=projeto).count(), 100)
        self.assertTrue(RDCParalisacao.objects.filter(rdc__projeto=projeto, motivo="falta_material").exists())
        self.assertEqual(RDCOcorrencia.objects.filter(rdc__projeto=projeto).count(), 3)
        from rdc.models import CalendarioPlanejamento, PerfilOperacionalUsuario
        self.assertTrue(CalendarioPlanejamento.objects.filter(projeto=projeto, data=timezone.localdate()).exists())
        self.assertTrue(PerfilOperacionalUsuario.objects.filter(user__username="admin_demo").exists())

        avanco = montar_avanco(timezone.localdate(), projeto_id=projeto.pk)
        blocos = {l["codigo"]: l for l in avanco["por_area"]}
        self.assertEqual(blocos["B202"]["situacao"], "atrasado")
        self.assertGreater(blocos["B101"]["realizado"], blocos["B202"]["realizado"])

        call_command("criar_projeto_demo", stdout=StringIO())  # rodar de novo recria sem duplicar
        self.assertEqual(Projeto.objects.filter(codigo="DEMO-PSV").count(), 1)

        call_command("criar_projeto_demo", "--remover", stdout=StringIO())
        self.assertFalse(Projeto.objects.filter(codigo="DEMO-PSV").exists())
        self.assertFalse(Disciplina.objects.filter(codigo__startswith="DEMO-").exists())
