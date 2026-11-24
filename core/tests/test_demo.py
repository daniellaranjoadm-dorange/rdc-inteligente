from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from cadastros.models import AreaLocal, Projeto
from punchlist.models import PunchItem

User = get_user_model()


@override_settings(DEMO_MODE=True)
class InstanciaDemoTests(TestCase):
    def test_entra_sem_senha_ve_tudo_e_nao_grava_nada(self):
        call_command("criar_projeto_demo", stdout=StringIO())  # banco vazio: cria o visitante
        r = self.client.get("/demo/entrar/")
        self.assertRedirects(r, "/rdc/blocos/", fetch_redirect_response=False)
        visitante = User.objects.get(username="visitante")
        self.assertFalse(visitante.has_usable_password())

        pagina = self.client.get("/rdc/blocos/")
        self.assertContains(pagina, "Demonstração com dados fictícios")
        self.assertContains(pagina, "B101")

        area = AreaLocal.objects.filter(projeto__codigo="DEMO-PSV").first()
        antes = PunchItem.objects.count()
        r = self.client.post("/punch/nova/", {"projeto": area.projeto_id, "area_local": area.pk, "categoria": "A",
                                              "origem": "interna", "descricao": "tentativa"},
                             HTTP_REFERER="/punch/nova/", follow=True)
        self.assertContains(r, "somente leitura")
        self.assertEqual(PunchItem.objects.count(), antes)

        self.assertRedirects(self.client.get("/admin/"), "/rdc/blocos/", fetch_redirect_response=False)
        self.assertEqual(self.client.post("/api/mobile/sync/", {}).status_code, 403)

    def test_login_mostra_botao_da_demonstracao(self):
        self.assertContains(self.client.get("/accounts/login/"), "Entrar na demonstração sem senha")


class InstanciaPrincipalTests(TestCase):
    def test_entrada_sem_senha_nao_existe_fora_da_demo(self):
        self.assertEqual(self.client.get("/demo/entrar/").status_code, 404)
        self.assertNotContains(self.client.get("/accounts/login/"), "Entrar na demonstração")

    @override_settings(DEMO_URL="https://rdc-inteligente-demo.onrender.com")
    def test_endereco_fixo_leva_a_demo(self):
        r = self.client.get("/demo/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "https://rdc-inteligente-demo.onrender.com/demo/entrar/")

    @override_settings(DEMO_URL="")
    def test_sem_demo_configurada_mostra_aviso(self):
        r = self.client.get("/demo/")
        self.assertEqual(r.status_code, 503)
        self.assertContains(r, "sendo preparada", status_code=503)

    def test_gravacao_normal_continua_funcionando(self):
        admin = User.objects.create_superuser("adm_demo_off", "a@example.com", "x")
        projeto = Projeto.objects.create(codigo="P", nome="P", cliente="C")
        area = AreaLocal.objects.create(projeto=projeto, codigo="B1", descricao="B1")
        self.client.force_login(admin)
        self.client.post("/punch/nova/", {"projeto": projeto.pk, "area_local": area.pk, "categoria": "A",
                                          "origem": "interna", "descricao": "real"})
        self.assertEqual(PunchItem.objects.count(), 1)
