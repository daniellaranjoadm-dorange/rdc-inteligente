import shutil
import tempfile
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from cadastros.models import AreaLocal, Projeto
from punchlist.models import PunchItem, Status
from punchlist.services import (
    abrir_item, alertas_punch, cancelar_item, montar_painel_punch, resolver_item, verificar_item,
)

User = get_user_model()
MEDIA = tempfile.mkdtemp()


def _foto(nome="f.jpg"):
    buf = BytesIO()
    Image.new("RGB", (64, 48), (200, 90, 30)).save(buf, format="JPEG")
    return SimpleUploadedFile(nome, buf.getvalue(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT=MEDIA)
class PunchTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_superuser("admin_pl", "a@example.com", "x")
        self.operador = User.objects.create_user("op_pl", "o@example.com", "x")
        self.projeto = Projeto.objects.create(codigo="P1", nome="PSV", cliente="T")
        self.b1 = AreaLocal.objects.create(projeto=self.projeto, codigo="B1", descricao="Bloco 1")
        self.b2 = AreaLocal.objects.create(projeto=self.projeto, codigo="B2", descricao="Bloco 2")

    def _abrir(self, area=None, cat="B", **kw):
        return abrir_item(projeto=self.projeto, area_local=area or self.b1, descricao="Pendência", categoria=cat,
                          usuario=self.admin, **kw)

    def test_numeracao_por_projeto_e_codigo(self):
        a, b = self._abrir(), self._abrir()
        self.assertEqual((a.codigo, b.codigo), ("PL-0001", "PL-0002"))

    def test_ciclo_resolver_recusar_resolver_aceitar(self):
        item = self._abrir(cat="A")
        with self.assertRaises(ValidationError):  # sem nota nem foto
            resolver_item(item, nota="", usuario=self.operador)
        resolver_item(item, nota="Feito", usuario=self.operador)
        with self.assertRaises(ValidationError):  # recusar exige motivo
            verificar_item(item, aprovado=False, nota="")
        verificar_item(item, aprovado=False, nota="Ainda solto", usuario=self.admin)
        item.refresh_from_db()
        self.assertEqual((item.status, item.reaberturas), (Status.EM_ANDAMENTO, 1))
        resolver_item(item, nota="Refeito", usuario=self.operador)
        verificar_item(item, aprovado=True, usuario=self.admin)
        item.refresh_from_db()
        self.assertEqual(item.status, Status.FECHADA)
        self.assertIsNotNone(item.fechada_em)
        with self.assertRaises(ValidationError):
            cancelar_item(item, motivo="x")

    def test_bloco_bloqueado_por_categoria_a_e_vencidas(self):
        hoje = timezone.localdate()
        self._abrir(area=self.b1, cat="A")
        self._abrir(area=self.b2, cat="C", prazo=hoje - timedelta(days=1))
        painel = montar_painel_punch()
        blocos = {l["area"].codigo: l for l in painel["por_bloco"]}
        self.assertFalse(blocos["B1"]["liberado"])
        self.assertTrue(blocos["B2"]["liberado"])
        self.assertEqual((painel["totais"]["categoria_a"], painel["totais"]["vencidas"]), (1, 1))
        tipos = [a["tipo"] for a in alertas_punch(hoje)]
        self.assertEqual(tipos[:2], ["punch_categoria_a", "punch_vencida"])

    def test_area_de_outro_projeto_recusada(self):
        outro = Projeto.objects.create(codigo="P2", nome="Outro", cliente="T")
        with self.assertRaises(ValidationError):
            abrir_item(projeto=outro, area_local=self.b1, descricao="x", categoria="B")

    def test_tela_abrir_com_foto_ver_foto_e_csv(self):
        self.client.force_login(self.operador)
        r = self.client.post(reverse("punch-create"), {
            "projeto": self.projeto.pk, "area_local": self.b1.pk, "categoria": "A", "origem": "interna",
            "descricao": "Guarda-corpo solto", "fotos": [_foto("a.jpg"), _foto("b.jpg")],
        })
        item = PunchItem.objects.get()
        self.assertRedirects(r, reverse("punch-detail", args=[item.pk]), fetch_redirect_response=False)
        self.assertEqual(item.fotos.count(), 2)
        foto = item.fotos.first()
        self.assertEqual(self.client.get(reverse("punch-foto-mini", args=[foto.pk])).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("punch-foto", args=[foto.pk])).status_code, 302)  # exige login
        self.client.force_login(self.operador)

        detalhe = self.client.get(reverse("punch-detail", args=[item.pk]))
        self.assertContains(detalhe, "Marcar como resolvida")
        self.assertNotContains(detalhe, "Verificação do CQ")
        self.client.post(reverse("punch-acao", args=[item.pk, "resolver"]), {"nota": "Refixado", "fotos": [_foto()]})
        item.refresh_from_db()
        self.assertEqual(item.status, Status.AGUARDANDO_VERIFICACAO)
        self.assertEqual(self.client.post(reverse("punch-acao", args=[item.pk, "verificar"]),
                                          {"decisao": "aceitar"}).status_code, 403)  # operador nao verifica

        self.client.force_login(self.admin)
        self.client.post(reverse("punch-acao", args=[item.pk, "verificar"]), {"decisao": "aceitar", "nota": "ok"})
        item.refresh_from_db()
        self.assertEqual(item.status, Status.FECHADA)
        painel = self.client.get(reverse("punch-painel") + "?situacao=todas")
        self.assertContains(painel, "PL-0001")
        csv = self.client.get(reverse("punch-painel") + "?situacao=todas&formato=csv")
        self.assertIn("Guarda-corpo solto", csv.content.decode("utf-8"))

    def test_paginas_abrem_e_editar(self):
        item = self._abrir()
        self.client.force_login(self.admin)
        for url in (reverse("punch-painel"), reverse("punch-create") + f"?area={self.b1.pk}",
                    reverse("punch-detail", args=[item.pk]), reverse("punch-update", args=[item.pk])):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        r = self.client.post(reverse("punch-update", args=[item.pk]), {
            "categoria": "A", "origem": "fiscal", "descricao": "Editada", "responsavel": "Fulano"})
        self.assertRedirects(r, reverse("punch-detail", args=[item.pk]), fetch_redirect_response=False)
        item.refresh_from_db()
        self.assertEqual((item.categoria, item.descricao), ("A", "Editada"))
