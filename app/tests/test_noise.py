from django.test import TestCase
from app.models import LeituraRuido

class LeituraRuidoModelTest(TestCase):
    """Testes do model LeituraRuido para o gráfico I-MR."""

    def test_criar_leitura_salva_leq_e_lmax(self):
        """Ao criar uma leitura, ela deve armazenar leq e lmax corretamente."""
        leitura = LeituraRuido.objects.create(leq=65.5, lmax=80.2)
        self.assertEqual(leitura.leq, 65.5)
        self.assertEqual(leitura.lmax, 80.2)
        
    def test_primeira_leitura_calcula_limites_basicos(self):
        """A primeira leitura não tem histórico para MR, então MR deve ser 0 e limites dependem só dela."""
        leitura = LeituraRuido.objects.create(leq=70.0, lmax=85.0)
        self.assertEqual(leitura.mr, 0.0)
        self.assertEqual(leitura.lc_i, 70.0)
        self.assertEqual(leitura.lsc_i, 70.0) # Sem variabilidade (MR=0), limites = média
        self.assertEqual(leitura.lic_i, 70.0)

    def test_calculo_mr_e_limites_com_historico(self):
        """A segunda leitura em diante deve calcular o Moving Range (MR) e os limites I-MR."""
        leitura1 = LeituraRuido.objects.create(leq=60.0, lmax=75.0)
        leitura2 = LeituraRuido.objects.create(leq=70.0, lmax=80.0)
        
        # MR = abs(70.0 - 60.0) = 10.0
        self.assertEqual(leitura2.mr, 10.0)
        
        # Média de Leq = (60.0 + 70.0) / 2 = 65.0
        self.assertEqual(leitura2.lc_i, 65.0)
        
        # Média de MR = 10.0 / 1 (já que MR da primeira é 0 e não conta, ou a média de MR é só dos MRs válidos)
        self.assertEqual(leitura2.am_media, 10.0)
        
        # E2 = 2.66 (para I-MR)
        # LSC_I = LC_I + E2 * am_media = 65.0 + (2.66 * 10.0) = 91.6
        self.assertAlmostEqual(leitura2.lsc_i, 91.6, places=1)
        
        # LIC_I = LC_I - E2 * am_media = 65.0 - (2.66 * 10.0) = 38.4
        self.assertAlmostEqual(leitura2.lic_i, 38.4, places=1)

class AcumuladorRuidoTest(TestCase):
    """Testes da lógica de acumulação para o Gráfico I-MR: 10 envios de 30s → 1 ponto de 5 min."""

    def test_envio_unico_nao_gera_ponto(self):
        """Um único envio de leq e lmax não deve gerar um ponto de I-MR."""
        from app.services import AcumuladorRuido
        acumulador = AcumuladorRuido()
        resultado = acumulador.receber_envio(leq=60.0, lmax=70.0)
        self.assertIsNone(resultado)
        
    def test_dez_envios_gera_ponto_com_medias(self):
        """Após 10 envios, deve gerar uma LeituraRuido com a média do leq e o pico do lmax."""
        from app.services import AcumuladorRuido
        acumulador = AcumuladorRuido()
        
        for _ in range(9):
            resultado = acumulador.receber_envio(leq=60.0, lmax=75.0)
            self.assertIsNone(resultado)
            
        # O décimo envio deve gerar o ponto
        resultado = acumulador.receber_envio(leq=70.0, lmax=90.0) # Lmax = 90
        
        self.assertIsNotNone(resultado)
        # O Leq médio de nove 60 e um 70 é 61.0
        self.assertEqual(resultado.leq, 61.0)
        # O Lmax deve ser o maior entre todos os recebidos (90.0)
        self.assertEqual(resultado.lmax, 90.0)
        
        # O buffer do acumulador deve ter sido resetado
        self.assertEqual(len(acumulador._buffer_leq), 0)
        self.assertEqual(len(acumulador._buffer_lmax), 0)

