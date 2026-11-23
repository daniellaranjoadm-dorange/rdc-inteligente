from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cadastros.models import AreaLocal, Disciplina, Projeto

User = get_user_model()


class EstruturaNavalModeloTests(TestCase):
    def setUp(self):
        self.projeto = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="Transpetro")

    def test_resumo_naval_junta_so_o_que_foi_preenchido(self):
        area = AreaLocal.objects.create(projeto=self.projeto, codigo="D02P", descricao="Bloco D02P")
        self.assertEqual(area.resumo_naval, "")

        area.tipo, area.casco, area.etapa = "bloco", "Handymax 01", "edificacao"
        self.assertEqual(area.resumo_naval, "Bloco · Handymax 01 · Edificação no dique / carreira")

        area.casco = ""
        self.assertEqual(area.resumo_naval, "Bloco · Edificação no dique / carreira")

    def test_disciplinas_navais_padrao_foram_incluidas(self):
        nomes = set(Disciplina.objects.values_list("nome", flat=True))
        for nome in ["Solda", "Pintura e tratamento de superfície", "Outfitting / acabamento", "Andaime", "Controle de qualidade"]:
            self.assertIn(nome, nomes)


class EstruturaNavalTelasTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin_area", "a@example.com", "x")
        self.client.force_login(self.user)
        self.projeto = Projeto.objects.create(codigo="HMX", nome="Handymax", cliente="Transpetro")
        self.area = AreaLocal.objects.create(projeto=self.projeto, codigo="D02P", descricao="Bloco D02P")

    def test_lista_de_areas_mostra_colunas_navais_e_editar(self):
        response = self.client.get(reverse("area-list"))
        self.assertContains(response, "Casco / navio")
        self.assertContains(response, reverse("area-update", args=[self.area.pk]))

    def test_edita_area_com_tipo_casco_e_etapa(self):
        response = self.client.post(
            reverse("area-update", args=[self.area.pk]),
            {
                "projeto": self.projeto.pk, "codigo": "D02P", "descricao": "Bloco D02P",
                "tipo": "bloco", "casco": "Handymax 01", "etapa": "montagem_bloco", "ativo": "on",
            },
        )
        self.assertRedirects(response, reverse("area-list"))
        self.area.refresh_from_db()
        self.assertEqual((self.area.tipo, self.area.casco, self.area.etapa), ("bloco", "Handymax 01", "montagem_bloco"))

    def test_salvar_cadastro_volta_para_a_lista_sem_erro(self):
        # Antes o redirecionamento ia para a rota inexistente "dashboard" (erro 500).
        response = self.client.post(
            reverse("projeto-create"), {"codigo": "G7K", "nome": "Gaseiros 7k", "cliente": "Transpetro", "ativo": "on"}
        )
        self.assertRedirects(response, reverse("projeto-list"))
        self.assertTrue(Projeto.objects.filter(codigo="G7K").exists())

    def test_cria_area_ja_com_estrutura_naval(self):
        response = self.client.post(
            reverse("area-create"),
            {"projeto": self.projeto.pk, "codigo": "DQ1", "descricao": "Dique seco 1", "tipo": "dique", "etapa": "edificacao", "ativo": "on"},
        )
        self.assertRedirects(response, reverse("area-list"))
        self.assertEqual(AreaLocal.objects.get(codigo="DQ1").get_tipo_display(), "Dique / carreira")
