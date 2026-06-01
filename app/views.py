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
        tipo_carta = request.data.get("chart")
        dados_medicao = request.data.get("measurements")
        especificacoes = request.data.get("especificacoes", {})
        intervalo_probabilidade = request.data.get("intervalo_probabilidade", {})

        if not tipo_carta or not dados_medicao:
            return Response(
                {"erro": "Você precisa enviar o tipo ('chart') e os dados ('measurements')."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if tipo_carta == "Xr":
                nova_carta = Media_Amplitude.objects.create(data=dados_medicao,
                                                            lse=especificacoes.get('LSE'),
                                                            lie=especificacoes.get('LIE'),
                                                            x1=intervalo_probabilidade.get('x1'),
                                                            x0=intervalo_probabilidade.get('x0'))
                return GerarRelatorioXr(nova_carta)

            elif tipo_carta == "IMR":
                nova_carta = imr.objects.create(
                    data=dados_medicao,
                    lse=especificacoes.get('LSE', 0),
                    lie=especificacoes.get('LIE', 0),
                    x1=intervalo_probabilidade.get('x1', 0),
                    x0=intervalo_probabilidade.get('x0', 0)
                )
                return GerarRelatorioIMR(nova_carta)
            
            elif tipo_carta =="u":
                nova_carta = u.objects.create(data=dados_medicao)
                return GerarRelatorioU(nova_carta)
            
            elif tipo_carta == "p":
                nova_carta = p.objects.create(data=dados_medicao)
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

    