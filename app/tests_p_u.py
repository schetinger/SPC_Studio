import json
from django.test import TestCase
from django.template.loader import render_to_string
from app.models import p, u

# ---------------------------------------------------------------------------
# Issue #3 — Adicionar alertas Western Electric aos relatórios p e u
# ---------------------------------------------------------------------------

DADOS_P = {
    "A1": [2],
    "A2": [3],
    "A3": [1],
    "A4": [5],
    "A5": [2],
    "A6": [1],
    "A7": [4],
    "A8": [20] # 20/20 = 1.0, garante ponto fora de controle para disparar Regra 1
}

class CartaP_UTest(TestCase):
    """Ciclo 1 e 2 — model p e u populam alertas WE após salvos."""

    def test_p_popula_alertas(self):
        carta = p.objects.create(data=DADOS_P)
        self.assertIn("regra_1_fora_controle", carta.alertas)
        self.assertIn("regra_2_alerta_zona_a", carta.alertas)
        self.assertIn("regra_3_tendencia", carta.alertas)
        self.assertIn("regra_4_deslocamento", carta.alertas)

    def test_u_popula_alertas(self):
        carta = u.objects.create(data=DADOS_P)
        self.assertIn("regra_1_fora_controle", carta.alertas)
        self.assertIn("regra_2_alerta_zona_a", carta.alertas)
        self.assertIn("regra_3_tendencia", carta.alertas)
        self.assertIn("regra_4_deslocamento", carta.alertas)

    """Ciclo 3 e 4 — template HTML de p e u contém bloco de alertas WE."""

    def test_template_p_contem_alertas(self):
        carta = p.objects.create(data=DADOS_P)
        html = render_to_string(
            "front/relatorios/RelatorioP.html", 
            {"carta": carta, "grafico": "", "dados_tabela": carta.data.items()}
        )
        self.assertIn("Alerta", html)

    def test_template_u_contem_alertas(self):
        carta = u.objects.create(data=DADOS_P)
        html = render_to_string(
            "front/relatorios/RelatorioU.html", 
            {"carta": carta, "grafico": "", "dados_tabela": carta.data.items()}
        )
        self.assertIn("Alerta", html)

class CartaP_U_ValidacaoTest(TestCase):
    def test_p_u_extrai_taxas_com_regra_e_n10(self):
        # Amostras com 10 medições cada
        dados_mock = {
            "A1": [50.1, 48.5, 49.2, 51.0, 48.0, 50.0, 50.0, 50.0, 50.0, 50.0], # 2 valores < 49.00
            "A2": [48.1, 48.2, 48.3, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0, 50.0], # 3 valores < 49.00
        }
        
        # Testando P
        carta_p = p.objects.create(data=dados_mock, regra="x < 49.00")
        
        self.assertEqual(carta_p.n, 10)
        self.assertEqual(carta_p.taxa["A1"], 0.2)
        self.assertEqual(carta_p.taxa["A2"], 0.3)
        self.assertEqual(carta_p.lc, 0.25)

        # Testando U
        carta_u = u.objects.create(data=dados_mock, regra="x < 49.00")
        
        self.assertEqual(carta_u.n, 10)
        self.assertEqual(carta_u.taxa["A1"], 0.2)
        self.assertEqual(carta_u.taxa["A2"], 0.3)
        self.assertEqual(carta_u.lc, 0.25)
