import json
from django.test import TestCase, Client
from django.urls import reverse
from django.template.loader import render_to_string
from app.models import Media_Amplitude


# ---------------------------------------------------------------------------
# Issue #1 — Adicionar tabela de dados brutos ao RelatorioXr
# Testa via interface pública: POST /gerar-carta/ e renderização do template
# ---------------------------------------------------------------------------

DADOS_XR = {
    "A1": [10.1, 10.3, 9.8, 10.0, 10.2],
    "A2": [9.9, 10.5, 10.1, 9.7, 10.3],
    "A3": [10.2, 10.0, 10.4, 10.1, 9.9],
}

PAYLOAD_XR = {
    "chart": "Xr",
    "measurements": DADOS_XR,
    "especificacoes": {"LSE": 11.0, "LIE": 9.0},
    "intervalo_probabilidade": {"x1": 10.5, "x0": 9.5},
}


class RelatorioXrTabelaDadosBrutosTest(TestCase):
    """
    Ciclo 1 — Tracer bullet: a rota POST /gerar-carta/ com dados Xr
    retorna uma resposta HTTP 200 com content-type application/pdf.
    """

    def test_gerar_carta_xr_retorna_pdf(self):
        client = Client()
        response = client.post(
            "/carta/gerar-carta/",
            data=json.dumps(PAYLOAD_XR),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    """
    Ciclo 2 — O HTML renderizado pelo template RelatorioXr inclui
    os dados brutos de cada amostra (chaves de carta.data).
    """

    def test_template_xr_contem_dados_brutos(self):
        carta = Media_Amplitude.objects.create(
            data=DADOS_XR,
            lse=11.0,
            lie=9.0,
            x1=10.5,
            x0=9.5,
        )
        html = render_to_string(
            "front/relatorios/RelatorioXr.html",
            {
                "carta": carta,
                "graficox": "",
                "graficor": "",
                "dados_tabela": carta.data.items(),
            },
        )
        # Cada chave de amostra deve aparecer na tabela
        for chave in DADOS_XR:
            self.assertIn(chave, html, f"Chave '{chave}' não encontrada no HTML do RelatorioXr")
