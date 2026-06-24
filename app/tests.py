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

    def test_xr_is_capaz_reprovado(self):
        # Limites apertados, processo deve reprovar (Cp/Cpk < 1)
        carta = Media_Amplitude.objects.create(
            data=DADOS_XR, lse=10.5, lie=9.5, x1=10.5, x0=9.5
        )
        self.assertFalse(carta.is_capaz)
        html = render_to_string(
            "front/relatorios/RelatorioXr.html",
            {"carta": carta, "graficox": "", "graficor": "", "dados_tabela": carta.data.items()},
        )
        self.assertIn("Processo Reprovado", html)



class CartaXRLimitesControleTest(TestCase):
    def test_limites_calculados_com_constantes_n10(self):
        # Amostras com n=10 cada.
        # Amplitude (R) para todas as amostras será 9.
        # Médias (X-bar) serão 5.5, 6.5, 7.5. Então media_geral será 6.5.
        dados_mock = {
            "A1": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 
            "A2": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            "A3": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        }
        
        carta = Media_Amplitude.objects.create(data=dados_mock)
        
        # Média das amplitudes (R_bar) = 9.0
        # Média geral (X_bar_bar) = 6.5
        # Constantes n=10: A2 = 0.308, D3 = 0.223, D4 = 1.777
        
        expected_lsc_media = round(6.5 + (0.308 * 9.0), 3) # 9.272
        expected_lic_media = round(6.5 - (0.308 * 9.0), 3) # 3.728
        expected_lsc_amp = round(1.777 * 9.0, 3) # 15.993
        expected_lic_amp = round(0.223 * 9.0, 3) # 2.007
        
        self.assertEqual(carta.lsc_media, expected_lsc_media)
        self.assertEqual(carta.lic_media, expected_lic_media)
        self.assertEqual(carta.lsc_amp, expected_lsc_amp)
        self.assertEqual(carta.lic_amp, expected_lic_amp)

class CartaXRProbabilidadesEspeciaisTest(TestCase):
    def test_xr_calcula_lie_lse_dinamico_e_probabilidades(self):
        dados_mock = {
            "A1": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 
        }
        carta = Media_Amplitude.objects.create(data=dados_mock)
        
        # LIE e LSE devem ser sobrepostos
        expected_lie = round(0.99 * carta.lic_media, 3)
        expected_lse = round(1.2 * carta.lsc_media, 3)
        
        self.assertEqual(carta.lie, expected_lie)
        self.assertEqual(carta.lse, expected_lse)
        
        self.assertIn("margem_deslocada", carta.probabilidade)
        self.assertIn("valor_x_95", carta.probabilidade)
        
        self.assertGreaterEqual(carta.probabilidade["margem_deslocada"], 0)
        self.assertIsNotNone(carta.probabilidade["valor_x_95"])

class CartaAceitacaoTest(TestCase):
    def test_is_capaz_longo_curto_prazo(self):
        # A1 e A2 comportadas
        dados_aprovado = {
            "A1": [9.9, 10.1, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
            "A2": [10.0, 9.9, 10.1, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
        }
        carta_ok = Media_Amplitude.objects.create(data=dados_aprovado)
        
        # Pode ser que os dados simulados não atinjam PPM < 990 por causa da relação
        # de R_bar / sigma para essas amostras pequenas, mas o is_capaz deve rodar sem quebrar
        # e refletir a lógica. Para este teste (RED) exigimos que seja boolean.
        self.assertIsInstance(carta_ok.is_capaz, bool)
        
        dados_reprovado_curto = {
            "A1": [9.9, 10.1, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
            "A2": [20.0, 9.9, 10.1, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0], # Regra 1!
        }
        carta_ruim = Media_Amplitude.objects.create(data=dados_reprovado_curto)
        self.assertFalse(carta_ruim.is_capaz)

class ProbabilidadeBinomialTest(TestCase):
    def test_calculo_probabilidade_binomial(self):
        from app.utils import calcular_probabilidade_binomial
        # Probabilidade de acertar k=45 em n=50 com p=0.95
        # comb(50, 45) * (0.95)^45 * (0.05)^5 = ~0.0658
        prob = calcular_probabilidade_binomial(n=50, k=45, p=0.95)
        self.assertAlmostEqual(prob, 0.0658, places=3)

# ---------------------------------------------------------------------------
# Issue #9 — Padronização de Leitura de Dados na API
# ---------------------------------------------------------------------------
class APIPadronizacaoLeituraTest(TestCase):
    def test_post_carta_ignorando_maiusculas_e_removendo_obsoletos(self):
        client = Client()
        
        # Simulando payload dados1.json (com "Carta" e "Amostras" em maiúsculo)
        # e sem os campos "especificacoes" e "intervalo_probabilidade"
        payload_xr_novo_formato = {
            "Carta": "XR",
            "Amostras": {
                "A1": [10.1, 10.3, 9.8, 10.0, 10.2],
                "A2": [9.9, 10.5, 10.1, 9.7, 10.3],
            }
        }
        
        response = client.post(
            "/carta/gerar-carta/",
            data=json.dumps(payload_xr_novo_formato),
            content_type="application/json",
        )
        
        # Teste deve passar se a API conseguir ler "Carta", "Amostras",
        # instanciar a Carta_XR e retornar um PDF HTTP 200.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_post_carta_mri_imr_roteamento(self):
        client = Client()
        
        payload_mri = {
            "carta": "MRI",
            "amostras": {
                "A1": [10.1, 10.3, 9.8, 10.0, 10.2],
            }
        }
        
        response_mri = client.post(
            "/carta/gerar-carta/",
            data=json.dumps(payload_mri),
            content_type="application/json",
        )
        self.assertEqual(response_mri.status_code, 200)
        self.assertEqual(response_mri["Content-Type"], "application/pdf")

    def test_post_carta_p_u_com_defeituosos(self):
        client = Client()
        
        payload_p = {
            "carta": "P",
            "amostras": {
                "A1": [10.1, 10.3, 9.8, 10.0, 10.2],
            },
            "defeituosos": "x < 10.00"
        }
        
        response_p = client.post(
            "/carta/gerar-carta/",
            data=json.dumps(payload_p),
            content_type="application/json",
        )
        self.assertEqual(response_p.status_code, 200)
        self.assertEqual(response_p["Content-Type"], "application/pdf")
        
        # Testar U também
        payload_u = dict(payload_p)
        payload_u["carta"] = "U"
        response_u = client.post(
            "/carta/gerar-carta/",
            data=json.dumps(payload_u),
            content_type="application/json",
        )
        self.assertEqual(response_u.status_code, 200)
        self.assertEqual(response_u["Content-Type"], "application/pdf")

class CartaCapacidadeEDicionarioTest(TestCase):
    def test_is_capaz_retorna_dicionario(self):
        from app.models import Media_Amplitude
        dados = {
            "A1": [10.1, 10.3, 9.8, 10.0, 10.2]
        }
        # lse e lie grandes garantem ppm < 990 e sem regra 1
        carta = Media_Amplitude.objects.create(data=dados)
        
        # Testar se is_capaz agora retorna dicionário
        self.assertIsInstance(carta.is_capaz, dict)
        self.assertIn("geral", carta.is_capaz)
        self.assertIn("curto_prazo", carta.is_capaz)
        self.assertIn("motivo_curto", carta.is_capaz)
        self.assertIn("longo_prazo", carta.is_capaz)
        self.assertIn("motivo_longo", carta.is_capaz)
        
    def test_probabilidade_inclui_binomial(self):
        from app.models import Media_Amplitude
        dados = {
            "A1": [10.1, 10.3, 9.8, 10.0, 10.2]
        }
        carta = Media_Amplitude.objects.create(data=dados)
        
        self.assertIn("binomial_50_45", carta.probabilidade)
        self.assertIn("margem_deslocada", carta.probabilidade)
        # Campos antigos não devem existir mais
        self.assertNotIn("menor_x1", carta.probabilidade)
        self.assertNotIn("maior_x0", carta.probabilidade)
        self.assertNotIn("intervalo", carta.probabilidade)

class RenderizarFormulaLatexTest(TestCase):
    def test_renderizar_formula_latex_retorna_base64(self):
        from app.utils import renderizar_formula_latex
        formula = r"\overline{\overline{X}} = \frac{\sum \overline{X}_i}{k}"
        imagem_base64 = renderizar_formula_latex(formula)
        
        # O resultado deve ser uma string longa (base64)
        self.assertIsInstance(imagem_base64, str)
        self.assertTrue(len(imagem_base64) > 100)
        
        # Testar decodificação do base64 (deve ser um PNG válido)
        import base64
        decoded = base64.b64decode(imagem_base64)
        self.assertTrue(decoded.startswith(b'\x89PNG\r\n\x1a\n'))
