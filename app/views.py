from app.models import Media_Amplitude,imr,p,u
from rest_framework import status
from rest_framework.views import APIView
from django.http import HttpResponse
from .utils import GerarRelatorioXr,GerarRelatorioIMR,GerarRelatorioU,GerarRelatorioP,grafico_u
from rest_framework.response import Response
from django.shortcuts import render



def pagina_inicial(request):
    # Isso vai renderizar o seu HTML de teste
    return render(request, 'front/index.html')


def pagina_monitoramento(request):
    return render(request, 'front/monitoramento.html')


class CartaGraficoIMR(APIView):
        def get(self, request,carta_id):
            try:
                carta = imr.objects.get(id=carta_id)
            except imr.DoesNotExist:
                return HttpResponse("carta nao encontrada", status=404)
            
            dados_brutos = carta
            buffer_imagem = grafico_u(dados_brutos)
            return HttpResponse(buffer_imagem.getvalue(),content_type="image/png")

class GeradorCEP(APIView):
    def post (self,request,*args, **kwargs):
        data_lower = {str(k).lower(): v for k, v in request.data.items()}
        
        tipo_carta = data_lower.get("carta", data_lower.get("chart", ""))
        dados_medicao = data_lower.get("amostras", data_lower.get("measurements", {}))

        if not tipo_carta or not dados_medicao:
            return Response(
                {"erro": "Você precisa enviar o tipo ('carta') e os dados ('amostras')."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        tipo_carta_lower = str(tipo_carta).lower()

        try:
            if tipo_carta_lower == "xr":
                print("aqui ta passando")
                nova_carta = Media_Amplitude.objects.create(data=dados_medicao)
                print ("criou a carta")
                return GerarRelatorioXr(nova_carta)

            elif tipo_carta_lower in ["imr", "mri"]:
                nova_carta = imr.objects.create(data=dados_medicao)
                return GerarRelatorioIMR(nova_carta)
            
            elif tipo_carta_lower == "u":
                nova_carta = u.objects.create(data=dados_medicao, regra=data_lower.get("defeituosos", ""))
                return GerarRelatorioU(nova_carta)
            
            elif tipo_carta_lower == "p":
                nova_carta = p.objects.create(data=dados_medicao, regra=data_lower.get("defeituosos", ""))
                return GerarRelatorioP(nova_carta)
            else:
                return Response(
                    {"erro": f"O tipo de carta '{tipo_carta}' não é suportado."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {
                    "mensagem": f"Carta {tipo_carta} gerada com sucesso!",
                    "id_carta": nova_carta.id,
                    "tipo de carta": tipo_carta,
                }, 
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response(
                {"erro_interno": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    
from django.http import JsonResponse
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
import time

from app.models import LeituraBarulho
from app.services import AcumuladorBarulho

# Instância global do acumulador (igual era no EspConsumer)
acumulador = AcumuladorBarulho()

def api_browser_sync(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    # Check ESP online status
    esp_last_seen = cache.get("esp_last_seen")
    import time
    esp_online = False
    if esp_last_seen:
        if time.time() - esp_last_seen < 10:
            esp_online = True

    # Check alarm status
    led_ligado = cache.get("comando_alerta", False)

    # Fetch history
    leituras = LeituraBarulho.objects.order_by('-timestamp')[:25]
    historico = []
    for l in reversed(leituras):
        historico.append({
            "timestamp": timezone.localtime(l.timestamp).strftime("%H:%M"),
            "p": round(l.p, 6),
            "lc": round(l.lc, 6),
            "lsc": round(l.lsc, 6),
            "lic": 0,
            "total_picos": l.total_picos,
            "fora_controle": l.fora_controle,
        })

    return JsonResponse({
        "tipo": "estado_inicial",
        "historico": historico,
        "led_ligado": led_ligado,
        "esp_online": esp_online,
        "enviosCiclo": len(acumulador._buffer),
    })

@csrf_exempt
def api_esp_picos(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    # Marcar ESP como online
    cache.set("esp_last_seen", time.time(), timeout=None)

    try:
        data = json.loads(request.body)
        if "picos" in data:
            picos = data["picos"]
            # Processar os picos usando a mesma lógica que estava no consumer
            nova_leitura = acumulador.receber_envio(picos)
            
            # Se completou um subgrupo, salvar no banco (receber_envio já cria no banco)
            # Então não precisamos recriar. O websocket precisa saber, mas não tem websocket.
            # O get do browser_sync vai pegar do banco!

            return JsonResponse({"ack": True})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    return JsonResponse({"error": "Missing picos"}, status=400)

@csrf_exempt
def api_esp_status(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    # Marcar ESP como online
    cache.set("esp_last_seen", time.time(), timeout=None)
    
    # Buscar status do alarme
    led_ligado = cache.get("comando_alerta", False)
    
    return JsonResponse({"comando_alerta": led_ligado})

@csrf_exempt
def api_browser_comando(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        comando = data.get("comando")
        
        if comando == "ligar_alerta":
            # Salvar no redis que o alarme está ligado, expirando em 30s (ou o tempo que quiser)
            cache.set("comando_alerta", True, timeout=None)
            return JsonResponse({"ack": True, "led_ligado": True})
        
        elif comando == "desligar_alerta":
            cache.set("comando_alerta", False, timeout=None)
            return JsonResponse({"ack": True, "led_ligado": False})
            
    except json.JSONDecodeError:
        pass
        
    return JsonResponse({"error": "Invalid command"}, status=400)
