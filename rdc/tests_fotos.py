import shutil
import tempfile
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import PerfilAcesso
from cadastros.models import AreaLocal, Disciplina, Projeto
from core.choices import TurnoChoices
from rdc.models import RDC, RDCFoto

User = get_user_model()
MEDIA_TESTE = tempfile.mkdtemp(prefix="rdc_fotos_teste_")


def _jpeg(largura=3000, altura=2000, orientacao=None, data_exif=None, cor=(200, 90, 20)):
    img = Image.new("RGB", (largura, altura), cor)
    exif = Image.Exif()
    if orientacao:
        exif[274] = orientacao  # Orientation
    if data_exif:
        exif[306] = data_exif  # DateTime
    buffer = BytesIO()
    img.save(buffer, format="JPEG", exif=exif.tobytes() if (orientacao or data_exif) else b"")
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=MEDIA_TESTE)
class FotosRDCTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TESTE, ignore_errors=True)

    def setUp(self):
        self.admin = User.objects.create_superuser("admin_ft", "a@example.com", "x")
        projeto = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="Transpetro")
        disciplina = Disciplina.objects.create(codigo="EST-F", nome="Estrutura F")
        area = AreaLocal.objects.create(projeto=projeto, codigo="D02P", descricao="Bloco D02P")
        self.rdc = RDC.objects.create(projeto=projeto, area_local=area, disciplina=disciplina,
                                      data=date(2026, 11, 23), turno=TurnoChoices.MANHA, criado_por=self.admin)
        self.client.force_login(self.admin)
        self.url_upload = reverse("rdc-foto-upload", kwargs={"pk": self.rdc.pk})

    def _enviar(self, *arquivos, **dados):
        payload = {"categoria": "avanco", "legenda": "Anel 3", **dados}
        payload["fotos"] = list(arquivos)
        return self.client.post(self.url_upload, payload)

    def test_reduz_corrige_rotacao_e_le_data_da_foto(self):
        # Foto "deitada" 3000x2000 com tag de rotacao 90 graus (Orientation=6) e data EXIF
        arquivo = SimpleUploadedFile("celular.jpg", _jpeg(orientacao=6, data_exif="2026:11:23 09:15:00"), "image/jpeg")
        response = self._enviar(arquivo)

        self.assertEqual(response.status_code, 302)
        foto = RDCFoto.objects.get()
        self.assertEqual((foto.largura, foto.altura), (1067, 1600))  # virou retrato e foi reduzida
        from django.utils import timezone
        self.assertEqual(timezone.localtime(foto.tirada_em).strftime("%d/%m/%Y %H:%M"), "23/11/2026 09:15")
        with Image.open(foto.miniatura.path) as mini:
            self.assertLessEqual(max(mini.size), 400)
        self.assertLess(foto.tamanho_bytes, 1_000_000)
        self.assertEqual(foto.criado_por, self.admin)

    def test_envia_varias_fotos_de_uma_vez(self):
        arquivos = [SimpleUploadedFile(f"f{i}.jpg", _jpeg(800, 600), "image/jpeg") for i in range(3)]
        self._enviar(*arquivos)
        self.assertEqual(RDCFoto.objects.filter(rdc=self.rdc).count(), 3)

    def test_recusa_arquivo_que_nao_e_imagem(self):
        falso = SimpleUploadedFile("planilha.jpg", b"isto nao e uma imagem", "image/jpeg")
        response = self._enviar(falso)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RDCFoto.objects.exists())

    def test_exige_ao_menos_uma_foto(self):
        response = self.client.post(self.url_upload, {"categoria": "geral"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Escolha ao menos uma foto")

    def test_foto_so_e_entregue_para_quem_esta_logado(self):
        self._enviar(SimpleUploadedFile("a.jpg", _jpeg(800, 600), "image/jpeg"))
        foto = RDCFoto.objects.get()
        url = reverse("rdc-foto-arquivo", kwargs={"pk": self.rdc.pk, "pk2": foto.pk})

        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/jpeg")
        self.assertIn("private", r["Cache-Control"])

        self.client.logout()
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_miniatura_de_outro_rdc_da_404(self):
        self._enviar(SimpleUploadedFile("a.jpg", _jpeg(800, 600), "image/jpeg"))
        foto = RDCFoto.objects.get()
        r = self.client.get(reverse("rdc-foto-miniatura", kwargs={"pk": self.rdc.pk + 999, "pk2": foto.pk}))
        self.assertEqual(r.status_code, 404)

    def test_excluir_apaga_os_arquivos(self):
        self._enviar(SimpleUploadedFile("a.jpg", _jpeg(800, 600), "image/jpeg"))
        foto = RDCFoto.objects.get()
        caminhos = [foto.imagem.path, foto.miniatura.path]
        self.client.post(reverse("rdc-foto-delete", kwargs={"pk": self.rdc.pk, "pk2": foto.pk}))
        self.assertFalse(RDCFoto.objects.exists())
        import os
        self.assertFalse(any(os.path.exists(c) for c in caminhos))

    def test_detalhe_mostra_aba_fotos_e_relatorio_pdf(self):
        self._enviar(SimpleUploadedFile("a.jpg", _jpeg(800, 600), "image/jpeg"))
        r = self.client.get(reverse("rdc-detail", kwargs={"pk": self.rdc.pk}))
        self.assertContains(r, 'id="fotos"')
        self.assertContains(r, "Relatório fotográfico (PDF)")

        pdf = self.client.get(reverse("rdc-relatorio-fotografico", kwargs={"pk": self.rdc.pk}))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertIn("attachment", pdf["Content-Disposition"])
        ver = self.client.get(reverse("rdc-relatorio-fotografico", kwargs={"pk": self.rdc.pk}), {"ver": "1"})
        self.assertIn("inline", ver["Content-Disposition"])

    def test_relatorio_sem_fotos_volta_para_a_aba(self):
        r = self.client.get(reverse("rdc-relatorio-fotografico", kwargs={"pk": self.rdc.pk}))
        self.assertEqual(r.status_code, 302)

    def test_supervisor_nao_envia_foto_em_rdc_fechado(self):
        sup = User.objects.create_user("sup_ft", password="x")
        PerfilAcesso.objects.create(user=sup, role="supervisor")
        self.rdc.status = "fechado"
        self.rdc.save()
        self.client.force_login(sup)
        self.assertEqual(self.client.get(self.url_upload).status_code, 403)
