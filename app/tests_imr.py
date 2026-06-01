import json
from django.test import TestCase, Client
from django.urls import reverse
from django.template.loader import render_to_string
from app.models import imr

# ---------------------------------------------------------------------------
# Issue #2 — Cp, Cpk, probabilidades e alertas Western Electric ao IMR
# ---------------------------------------------------------------------------

DADOS_IMR = {
    "M1": [10.1],
    "M2": [10.3],
    "M3": [9.8],
    "M4": [10.0],
    "M5": [10.2],
    "M6": [9.9],
    "M7": [10.5],
    "M8": [10.1],
}

PAYLOAD_IMR = {
    "chart": "IMR",
    "measurements": DADOS_IMR,
    "especificacoes": {"LSE": 11.0, "LIE": 9.0},
    "intervalo_probabilidade": {"x1": 10.5, "x0": 9.5},
}


class RelatorioIMRCpCpkTest(TestCase):
    """Ciclo 1 — imr salvo com lse/lie calcula cp e cpk não-nulos."""

    def test_imr_calcula_cp_cpk(self):
        carta = imr.objects.create(
            data=DADOS_IMR, lse=11.0, lie=9.0, x1=10.5, x0=9.5
        )
        self.assertGreater(carta.cp, 0, "cp deve ser maior que 0")
        self.assertGreater(carta.cpk, 0, "cpk deve ser maior que 0")


class RelatorioIMRProbabilidadeTest(TestCase):
    """Ciclo 2 — imr salvo calcula probabilidade com as 3 chaves esperadas."""

    def test_imr_calcula_probabilidade(self):
        carta = imr.objects.create(
            data=DADOS_IMR, lse=11.0, lie=9.0, x1=10.5, x0=9.5
        )
        self.assertIn("menor_x1", carta.probabilidade)
        self.assertIn("maior_x0", carta.probabilidade)
        self.assertIn("intervalo", carta.probabilidade)


class RelatorioIMRAletasWETest(TestCase):
    """Ciclo 3 — imr salvo popula alertas com as 4 regras Western Electric."""

    def test_imr_popula_alertas_western_electric(self):
        carta = imr.objects.create(
            data=DADOS_IMR, lse=11.0, lie=9.0, x1=10.5, x0=9.5
        )
        self.assertIn("regra_1_fora_controle", carta.alertas)
        self.assertIn("regra_2_alerta_zona_a", carta.alertas)
        self.assertIn("regra_3_tendencia", carta.alertas)
        self.assertIn("regra_4_deslocamento", carta.alertas)


class RelatorioIMREndpointTest(TestCase):
    """Ciclo 4 — POST /carta/gerar-carta/ com IMR e lse/lie retorna PDF 200."""

    def test_gerar_carta_imr_retorna_pdf(self):
        response = self.client.post(
            "/carta/gerar-carta/",
            data=json.dumps(PAYLOAD_IMR),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")


class RelatorioIMRTemplateTest(TestCase):
    """Ciclo 5 — HTML do template IMR contém Cp, Cpk e bloco de alertas."""

    def test_template_imr_contem_cp_cpk_e_alertas(self):
        carta = imr.objects.create(
            data=DADOS_IMR, lse=11.0, lie=9.0, x1=10.5, x0=9.5
        )
        html = render_to_string(
            "front/relatorios/RelatorioIMR.html",
            {
                "carta": carta,
                "grafico_i": "",
                "grafico_mr": "",
                "dados_tabela": carta.data.items(),
            },
        )
        self.assertIn("Cp", html, "Cp não encontrado no HTML do RelatorioIMR")
        self.assertIn("Cpk", html, "Cpk não encontrado no HTML do RelatorioIMR")
        self.assertIn("Alerta", html, "Bloco de alertas não encontrado no HTML do RelatorioIMR")
