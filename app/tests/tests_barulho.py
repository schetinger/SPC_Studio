from django.test import TestCase
from app.models import LeituraBarulho
from app.services import AcumuladorBarulho


class LeituraBarulhoModelTest(TestCase):
    """Testes do model LeituraBarulho — cada instância é um ponto de 5 min na carta p."""

    def test_criar_leitura_calcula_p_automaticamente(self):
        """Ao criar uma leitura com total_picos e n, o campo p deve ser calculado."""
        leitura = LeituraBarulho.objects.create(total_picos=12, n=6000)
        self.assertAlmostEqual(leitura.p, 12 / 6000, places=6)

    def test_leitura_sem_picos_tem_p_zero(self):
        """Sem picos de barulho, p deve ser 0."""
        leitura = LeituraBarulho.objects.create(total_picos=0, n=6000)
        self.assertEqual(leitura.p, 0.0)


class AcumuladorBarulhoTest(TestCase):
    """Testes da lógica de acumulação: 10 envios → 1 ponto na carta p."""

    def setUp(self):
        self.acumulador = AcumuladorBarulho()

    def test_envio_unico_nao_gera_ponto(self):
        """Um envio sozinho não deve gerar ponto — precisa de 10."""
        resultado = self.acumulador.receber_envio(picos=5)
        self.assertIsNone(resultado)

    def test_dez_envios_gera_ponto(self):
        """Após 10 envios, deve gerar uma LeituraBarulho no banco."""
        for i in range(9):
            resultado = self.acumulador.receber_envio(picos=3)
            self.assertIsNone(resultado)

        # O 10º envio deve gerar o ponto
        resultado = self.acumulador.receber_envio(picos=3)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.total_picos, 30)  # 3 × 10
        self.assertEqual(resultado.n, 6000)
        self.assertAlmostEqual(resultado.p, 30 / 6000, places=6)

    def test_buffer_reseta_apos_gerar_ponto(self):
        """Após gerar um ponto, o buffer deve resetar e começar novo ciclo."""
        # Primeiro ciclo
        for _ in range(10):
            self.acumulador.receber_envio(picos=5)

        # Segundo ciclo — começa do zero
        for i in range(9):
            resultado = self.acumulador.receber_envio(picos=7)
            self.assertIsNone(resultado)

        resultado = self.acumulador.receber_envio(picos=7)
        self.assertIsNotNone(resultado)
        self.assertEqual(resultado.total_picos, 70)  # 7 × 10

    def test_lc_lsc_lic_calculados_com_historico(self):
        """LC/LSC/LIC devem ser calculados usando o histórico de leituras."""
        # Gerar 3 pontos com picos diferentes
        picos_por_ciclo = [10, 20, 30]
        for picos in picos_por_ciclo:
            for _ in range(10):
                resultado = self.acumulador.receber_envio(picos=picos)

        # O último ponto deve ter LC/LSC/LIC calculados
        leitura = LeituraBarulho.objects.last()
        self.assertGreater(leitura.lc, 0)
        self.assertGreater(leitura.lsc, leitura.lc)
        self.assertGreaterEqual(leitura.lic, 0)


class RegrasWesternElectricBarulhoTest(TestCase):
    """Testes das regras WE aplicadas à carta p de barulho em tempo real."""

    def test_ponto_extremo_dispara_fora_controle(self):
        """Um ponto com picos muito acima da média deve disparar fora_controle."""
        acumulador = AcumuladorBarulho()

        # Gerar 5 pontos com picos normais (estáveis)
        for _ in range(5):
            for _ in range(10):
                acumulador.receber_envio(picos=3)

        # Agora enviar um ponto com picos absurdamente altos
        for _ in range(10):
            resultado = acumulador.receber_envio(picos=500)

        # Este ponto deve estar fora de controle (regra 1: > 3σ)
        self.assertTrue(resultado.fora_controle)

    def test_pontos_normais_nao_dispara_fora_controle(self):
        """Com poucos pontos (menos de 2), fora_controle deve ser False."""
        acumulador = AcumuladorBarulho()

        # Gerar apenas 1 ponto — sem histórico suficiente pra WE
        for _ in range(10):
            resultado = acumulador.receber_envio(picos=10)

        # Com 1 só ponto, não tem como aplicar WE
        self.assertFalse(resultado.fora_controle)


class EspConsumerTest(TestCase):
    """Testes do consumer WebSocket do ESP32."""

    def test_esp_envia_dados_e_gera_ponto(self):
        """ESP enviando 10 mensagens de picos deve gerar um ponto no banco."""
        from channels.testing import WebsocketCommunicator
        from cep.asgi import application
        import asyncio

        async def _test():
            # Resetar acumulador pra teste limpo
            from app.consumers import EspConsumer
            EspConsumer._acumulador = None

            communicator = WebsocketCommunicator(application, "/ws/esp/")
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            # Enviar 10 mensagens de picos
            for _ in range(10):
                await communicator.send_json_to({"picos": 5})

            # Aguardar processamento
            await asyncio.sleep(0.5)

            await communicator.disconnect()

            # Verificar que uma LeituraBarulho foi criada
            count = await database_sync_to_async(LeituraBarulho.objects.count)()
            self.assertEqual(count, 1)

            leitura = await database_sync_to_async(LeituraBarulho.objects.first)()
            self.assertEqual(leitura.total_picos, 50)

        from channels.db import database_sync_to_async
        asyncio.get_event_loop().run_until_complete(_test())


class MonitorConsumerTest(TestCase):
    """Testes do consumer WebSocket do browser."""

    def test_monitor_recebe_estado_inicial_ao_conectar(self):
        """Ao conectar, o monitor deve receber o estado inicial com histórico."""
        from channels.testing import WebsocketCommunicator
        from cep.asgi import application
        import asyncio

        async def _test():
            communicator = WebsocketCommunicator(application, "/ws/monitor/")
            connected, _ = await communicator.connect()
            self.assertTrue(connected)

            # Deve receber estado inicial
            response = await communicator.receive_json_from(timeout=2)
            self.assertEqual(response["tipo"], "estado_inicial")
            self.assertIn("historico", response)
            self.assertIn("led_ligado", response)

            await communicator.disconnect()

        asyncio.get_event_loop().run_until_complete(_test())

