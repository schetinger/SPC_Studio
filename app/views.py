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

    