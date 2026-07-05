import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from app.services import AcumuladorBarulho
from app.models import LeituraBarulho


class EspConsumer(AsyncWebsocketConsumer):
    """Consumer para o ESP32: recebe dados de picos de barulho.
    
    O ESP envia {"picos": N} a cada 30 segundos.
    Após 10 envios (5 min), gera um ponto na carta p e notifica os browsers.
    """

    # Compartilhado entre todas as conexões ESP (class-level)
    _acumulador = None
    _timer_desligar = None
    _connected_esps = 0

    @classmethod
    def get_acumulador(cls):
        if cls._acumulador is None:
            cls._acumulador = AcumuladorBarulho()
        return cls._acumulador

    async def connect(self):
        EspConsumer._connected_esps += 1
        await self.channel_layer.group_add("esp_devices", self.channel_name)
        await self.accept()

        # Enviar estado atual do alerta para o ESP caso ele tenha acabado de reconectar
        if EspConsumer._timer_desligar is not None:
            await self.send(text_data=json.dumps({"comando_alerta": True}))

        # Notificar browsers que ESP conectou
        await self.channel_layer.group_send(
            "browser_monitors",
            {
                "type": "esp_status",
                "dados": {"tipo": "esp_status", "online": True}
            }
        )

    async def disconnect(self, close_code):
        EspConsumer._connected_esps = max(0, EspConsumer._connected_esps - 1)
        await self.channel_layer.group_discard("esp_devices", self.channel_name)

        # Notificar browsers que ESP desconectou
        await self.channel_layer.group_send(
            "browser_monitors",
            {
                "type": "esp_status",
                "dados": {"tipo": "esp_status", "online": False}
            }
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            
            # Ignorar pings de heartbeat (application-level)
            if "ping" in data:
                try:
                    await self.send(text_data=json.dumps({"pong": True}))
                except Exception:
                    pass
                return
                
            if "picos" not in data:
                return
                
            picos = data.get("picos", 0)
        except (json.JSONDecodeError, TypeError):
            return

        # Envia um ACK imediatamente para evitar que o Cloudflare derrube a conexão
        try:
            await self.send(text_data=json.dumps({"ack": True}))
        except Exception:
            pass

        # Processar envio no acumulador (sync por causa do ORM)
        resultado = await database_sync_to_async(
            self.get_acumulador().receber_envio
        )(picos=picos)

        if resultado is not None:
            # Gerou um ponto — buscar histórico e enviar pro browser
            historico = await self._buscar_historico()

            await self.channel_layer.group_send(
                "browser_monitors",
                {
                    "type": "novo_ponto",
                    "dados": {
                        "tipo": "novo_ponto",
                        "timestamp": resultado.timestamp.strftime("%H:%M"),
                        "p": round(resultado.p, 6),
                        "lc": round(resultado.lc, 6),
                        "lsc": round(resultado.lsc, 6),
                        "lic": round(resultado.lic, 6),
                        "fora_controle": resultado.fora_controle,
                        "alertas": resultado.alertas,
                        "historico": historico,
                    }
                }
            )

    async def comando_alerta(self, event):
        """Recebe comando de toggle do browser e envia pro ESP."""
        await self.send(text_data=json.dumps(event["dados"]))

    @database_sync_to_async
    def _buscar_historico(self):
        """Busca os últimos 25 pontos da carta p para o gráfico."""
        leituras = LeituraBarulho.objects.order_by('-timestamp')[:25]
        historico = []
        for l in reversed(leituras):
            historico.append({
                "timestamp": l.timestamp.strftime("%H:%M"),
                "p": round(l.p, 6),
                "total_picos": l.total_picos,
                "fora_controle": l.fora_controle,
            })
        return historico


class MonitorConsumer(AsyncWebsocketConsumer):
    """Consumer para o browser: exibe gráfico e controla LED/speaker."""

    async def connect(self):
        await self.channel_layer.group_add("browser_monitors", self.channel_name)
        await self.accept()

        # Enviar estado atual ao conectar
        historico = await self._buscar_historico_completo()
        await self.send(text_data=json.dumps({
            "tipo": "estado_inicial",
            "historico": historico,
            "led_ligado": EspConsumer._timer_desligar is not None,
            "esp_online": EspConsumer._connected_esps > 0,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("browser_monitors", self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            comando = data.get("comando")
        except (json.JSONDecodeError, TypeError):
            return

        if comando == "ligar_alerta":
            # Enviar comando pro ESP
            await self.channel_layer.group_send(
                "esp_devices",
                {
                    "type": "comando_alerta",
                    "dados": {"comando_alerta": True}
                }
            )

            # Notificar browsers
            await self.channel_layer.group_send(
                "browser_monitors",
                {
                    "type": "status_led",
                    "dados": {"tipo": "status_led", "ligado": True, "timer": 60}
                }
            )

            # Cancelar timer anterior se existir
            if EspConsumer._timer_desligar is not None:
                EspConsumer._timer_desligar.cancel()

            # Iniciar auto-desligamento de 1 minuto
            EspConsumer._timer_desligar = asyncio.create_task(
                self._auto_desligar()
            )

        elif comando == "desligar_alerta":
            await self._desligar()

    async def _auto_desligar(self):
        """Auto-desliga LED/speaker após 60 segundos."""
        try:
            await asyncio.sleep(60)
            await self._desligar()
        except asyncio.CancelledError:
            pass

    async def _desligar(self):
        """Desliga LED/speaker/display e notifica todos."""
        # Cancelar timer se existir
        if EspConsumer._timer_desligar is not None:
            EspConsumer._timer_desligar.cancel()
            EspConsumer._timer_desligar = None

        # Enviar comando pro ESP
        await self.channel_layer.group_send(
            "esp_devices",
            {
                "type": "comando_alerta",
                "dados": {"comando_alerta": False}
            }
        )

        # Notificar browsers
        await self.channel_layer.group_send(
            "browser_monitors",
            {
                "type": "status_led",
                "dados": {"tipo": "status_led", "ligado": False, "timer": 0}
            }
        )

    async def novo_ponto(self, event):
        """Envia novo ponto de carta p para o browser."""
        await self.send(text_data=json.dumps(event["dados"]))

    async def esp_status(self, event):
        """Envia status de conexão do ESP pro browser."""
        await self.send(text_data=json.dumps(event["dados"]))

    async def status_led(self, event):
        """Envia status do LED/speaker pro browser."""
        await self.send(text_data=json.dumps(event["dados"]))

    @database_sync_to_async
    def _buscar_historico_completo(self):
        """Busca os últimos 25 pontos com limites para estado inicial."""
        leituras = LeituraBarulho.objects.order_by('-timestamp')[:25]
        historico = []
        for l in reversed(leituras):
            historico.append({
                "timestamp": l.timestamp.strftime("%H:%M"),
                "p": round(l.p, 6),
                "lc": round(l.lc, 6),
                "lsc": round(l.lsc, 6),
                "lic": round(l.lic, 6),
                "total_picos": l.total_picos,
                "fora_controle": l.fora_controle,
            })
        return historico
