import math
from app.models import LeituraBarulho, Carta


class AcumuladorBarulho:
    """Acumula envios do ESP32 e gera pontos de carta p a cada 10 envios (5 min).

    Cada envio contém a quantidade de picos detectados em 30 segundos (n=600 medições).
    Após 10 envios, soma os picos (n=6000) e cria uma LeituraBarulho no banco.
    """

    ENVIOS_POR_PONTO = 10
    N_POR_ENVIO = 600
    JANELA = 25  # últimos 25 pontos para calcular LC/LSC/LIC

    def __init__(self):
        self._buffer = []

    def receber_envio(self, picos: int):
        """Recebe um envio do ESP com a contagem de picos.

        Returns:
            LeituraBarulho se gerou um ponto (10 envios acumulados), None caso contrário.
        """
        self._buffer.append(picos)

        if len(self._buffer) < self.ENVIOS_POR_PONTO:
            return None

        # Acumulou 10 envios — gerar ponto
        total_picos = sum(self._buffer)
        n = self.N_POR_ENVIO * self.ENVIOS_POR_PONTO
        self._buffer = []

        # Criar leitura (p é calculado automaticamente no save)
        leitura = LeituraBarulho(total_picos=total_picos, n=n)

        # Calcular LC/LSC/LIC usando histórico
        self._calcular_limites(leitura)

        leitura.save()
        return leitura

    def _calcular_limites(self, leitura_nova):
        """Calcula LC, LSC e LIC da carta p usando o histórico + o novo ponto."""
        # Buscar últimos pontos do banco
        historico = list(
            LeituraBarulho.objects.order_by('-timestamp')[:self.JANELA - 1]
            .values_list('total_picos', 'n')
        )

        # Incluir o ponto atual
        todos_picos = [leitura_nova.total_picos] + [h[0] for h in historico]
        todos_n = [leitura_nova.n] + [h[1] for h in historico]

        # LC = soma total de picos / soma total de n
        soma_picos = sum(todos_picos)
        soma_n = sum(todos_n)
        lc = soma_picos / soma_n if soma_n > 0 else 0

        # LSC e LIC da carta p: LC ± 3 * sqrt(LC * (1-LC) / n)
        n_medio = leitura_nova.n  # n é constante (6000)
        if lc > 0 and n_medio > 0:
            sigma = math.sqrt((lc * (1 - lc)) / n_medio)
            lsc = lc + 3 * sigma
            lic = max(0, lc - 3 * sigma)
        else:
            lsc = 0
            lic = 0

        leitura_nova.lc = round(lc, 6)
        leitura_nova.lsc = round(lsc, 6)
        leitura_nova.lic = round(lic, 6)

        # Calcular p do ponto atual pra aplicar regras WE
        p_atual = leitura_nova.total_picos / leitura_nova.n if leitura_nova.n > 0 else 0
        leitura_nova.p = p_atual

        # Aplicar regras Western Electric
        todos_p = [p_atual] + [tp / tn for tp, tn in zip(
            [h[0] for h in historico], [h[1] for h in historico]
        )]
        # Reverter pra ordem cronológica (mais antigo primeiro)
        todos_p.reverse()

        if len(todos_p) >= 2:
            alertas = Carta.aplicar_regras_western_electric(
                lista_medias=todos_p,
                media_central=lc,
                lsc=lsc
            )
            leitura_nova.alertas = alertas

            # fora_controle se qualquer regra disparou
            leitura_nova.fora_controle = any(
                len(v) > 0 for v in alertas.values()
            )
        else:
            leitura_nova.alertas = {}
            leitura_nova.fora_controle = False
