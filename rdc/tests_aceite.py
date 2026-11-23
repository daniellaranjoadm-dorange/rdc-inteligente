import base64
import shutil
import tempfile
from datetime import date, timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageDraw

from accounts.models import PerfilAcesso
from cadastros.models import AreaLocal, Disciplina, Projeto
from core.choices import TurnoChoices
from rdc.models import RDC, RDCAceite, RDCLinkAceite
from rdc.services.aceite_service import criar_link, hash_do_retrato, retrato_rdc

User = get_user_model()
MEDIA_TESTE = tempfile.mkdtemp(prefix="rdc_aceite_teste_")


def _assinatura(em_branco=False):
    img = Image.new("RGBA", (600, 200), (0, 0, 0, 0))
    if not em_branco:
        d = ImageDraw.Draw(img)
        d.line([(40, 150), (160, 60), (280, 140), (420, 50), (560, 130)], fill=(20, 33, 48, 255), width=5)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


@override_settings(MEDIA_ROOT=MEDIA_TESTE)
class AceiteFiscalTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TESTE, ignore_errors=True)

    def setUp(self):
        self.sup = User.objects.create_user("sup_ac", password="x")
        PerfilAcesso.objects.create(user=self.sup, role="supervisor")
        projeto = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="Transpetro")
        disc = Disciplina.objects.create(codigo="EST-A", nome="Estrutura A")
        area = AreaLocal.objects.create(projeto=projeto, codigo="D02P", descricao="Bloco D02P")
        self.rdc = RDC.objects.create(projeto=projeto, area_local=area, disciplina=disc, data=date(2026, 11, 23),
                                      turno=TurnoChoices.MANHA, criado_por=self.sup)
        self.link = criar_link(self.rdc, usuario=self.sup, destinatario="Fiscal Transpetro")
        self.url = reverse("aceite-publico", kwargs={"token": self.link.token})

    def _dados(self, **extra):
        dados = {"decisao": "aprovado", "nome": "João Fiscal", "cargo": "Fiscal", "empresa": "Transpetro",
                 "observacao": "", "declaro": "on", "assinatura": _assinatura()}
        dados.update(extra)
        return dados

    def test_supervisor_gera_link_pela_tela(self):
        self.client.force_login(self.sup)
        r = self.client.post(reverse("rdc-aceite-gerar-link", kwargs={"pk": self.rdc.pk}), {"destinatario": "Eng. Ana"})
        self.assertEqual(r.status_code, 302)
        novo = RDCLinkAceite.objects.get(destinatario="Eng. Ana")
        self.assertTrue(novo.ativo)
        self.assertGreaterEqual(len(novo.token), 40)
        detalhe = self.client.get(reverse("rdc-detail", kwargs={"pk": self.rdc.pk}))
        self.assertContains(detalhe, novo.token)

    def test_fiscal_abre_sem_login(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "RDC #%d" % self.rdc.pk)
        self.assertContains(r, 'name="robots" content="noindex')

    def test_aceite_valido_grava_assinatura_retrato_e_usa_o_link(self):
        r = self.client.post(self.url, self._dados())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Obrigado")
        aceite = RDCAceite.objects.get()
        self.assertEqual(aceite.decisao, "aprovado")
        self.assertEqual(aceite.hash_retrato, hash_do_retrato(retrato_rdc(self.rdc)))
        self.assertTrue(aceite.assinatura.name.endswith(".png"))
        self.link.refresh_from_db()
        self.assertEqual(self.link.situacao, "usado")

    def test_link_nao_serve_duas_vezes(self):
        self.client.post(self.url, self._dados())
        r = self.client.post(self.url, self._dados(nome="Outra Pessoa"))
        self.assertEqual(r.status_code, 410)
        self.assertEqual(RDCAceite.objects.count(), 1)
        self.assertEqual(self.client.get(self.url).status_code, 410)

    def test_assinatura_em_branco_e_recusada(self):
        r = self.client.post(self.url, self._dados(assinatura=_assinatura(em_branco=True)))
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "em branco", status_code=400)
        self.assertFalse(RDCAceite.objects.exists())

    def test_sem_assinatura_e_recusado(self):
        r = self.client.post(self.url, self._dados(assinatura=""))
        self.assertEqual(r.status_code, 400)
        self.assertFalse(RDCAceite.objects.exists())

    def test_ressalva_exige_observacao(self):
        r = self.client.post(self.url, self._dados(decisao="ressalvas", observacao=""))
        self.assertEqual(r.status_code, 400)
        r = self.client.post(self.url, self._dados(decisao="ressalvas", observacao="Faltou foto do anel 2"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(RDCAceite.objects.get().decisao, "ressalvas")

    def test_link_expirado_ou_revogado_nao_abre(self):
        self.link.expira_em = timezone.now() - timedelta(minutes=1)
        self.link.save()
        self.assertEqual(self.client.get(self.url).status_code, 410)

        outro = criar_link(self.rdc, usuario=self.sup)
        self.client.force_login(self.sup)
        self.client.post(reverse("rdc-aceite-revogar-link", kwargs={"pk": self.rdc.pk, "link_id": outro.pk}))
        self.client.logout()
        self.assertEqual(self.client.get(reverse("aceite-publico", kwargs={"token": outro.token})).status_code, 410)

    def test_token_inexistente_da_404(self):
        self.assertEqual(self.client.get(reverse("aceite-publico", kwargs={"token": "nao-existe"})).status_code, 404)

    def test_comprovante_pdf_exige_login(self):
        self.client.post(self.url, self._dados())
        aceite = RDCAceite.objects.get()
        url = reverse("rdc-aceite-comprovante", kwargs={"pk": self.rdc.pk, "aceite_id": aceite.pk})
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.sup)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_detalhe_mostra_aceite_recebido(self):
        self.client.post(self.url, self._dados(decisao="reprovado", observacao="HH divergente"))
        self.client.force_login(self.sup)
        r = self.client.get(reverse("rdc-detail", kwargs={"pk": self.rdc.pk}))
        self.assertContains(r, "Reprovado por João Fiscal")


class AceiteCsrfTests(TestCase):
    """O navegador real manda Origin no POST; a pagina nao pode fazer o Origin virar 'null'."""

    def test_pagina_nao_usa_politica_que_anula_a_origem(self):
        sup = User.objects.create_user("sup_csrf", password="x")
        projeto = Projeto.objects.create(codigo="HMC", nome="Handymax C", cliente="Transpetro")
        disc = Disciplina.objects.create(codigo="EST-C", nome="Estrutura C")
        area = AreaLocal.objects.create(projeto=projeto, codigo="D03P", descricao="Bloco D03P")
        rdc = RDC.objects.create(projeto=projeto, area_local=area, disciplina=disc, data=date(2026, 11, 24),
                                 turno=TurnoChoices.MANHA, criado_por=sup)
        link = criar_link(rdc, usuario=sup)
        r = self.client.get(reverse("aceite-publico", kwargs={"token": link.token}))
        self.assertNotContains(r, 'content="no-referrer"')
        self.assertContains(r, 'name="referrer" content="same-origin"')

    @override_settings(MEDIA_ROOT=MEDIA_TESTE)
    def test_post_com_origem_do_proprio_site_e_aceito_com_csrf_ativo(self):
        from django.test import Client
        sup = User.objects.create_user("sup_csrf2", password="x")
        projeto = Projeto.objects.create(codigo="HMD", nome="Handymax D", cliente="Transpetro")
        disc = Disciplina.objects.create(codigo="EST-D", nome="Estrutura D")
        area = AreaLocal.objects.create(projeto=projeto, codigo="D04P", descricao="Bloco D04P")
        rdc = RDC.objects.create(projeto=projeto, area_local=area, disciplina=disc, data=date(2026, 11, 25),
                                 turno=TurnoChoices.MANHA, criado_por=sup)
        link = criar_link(rdc, usuario=sup)
        url = reverse("aceite-publico", kwargs={"token": link.token})
        c = Client(enforce_csrf_checks=True)
        c.get(url)
        token = c.cookies["csrftoken"].value
        dados = {"decisao": "aprovado", "nome": "Fiscal", "declaro": "on", "assinatura": _assinatura(),
                 "csrfmiddlewaretoken": token}
        r = c.post(url, dados, HTTP_ORIGIN="http://testserver")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(RDCAceite.objects.filter(rdc=rdc).count(), 1)
