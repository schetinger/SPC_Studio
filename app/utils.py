from io import BytesIO
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse
import io

def renderizar_formula_latex(formula_latex):
    """
    Renderiza uma fórmula em LaTeX usando o matplotlib e retorna a imagem em formato base64.
    """
    fig = plt.figure(figsize=(0.1, 0.1))
    fig.patch.set_visible(False)
    
    # Renderiza o texto com fonte grande — bbox_inches='tight' recorta ao redor
    fig.text(0.5, 0.5, f"${formula_latex}$", size=18, ha='center', va='center')
    
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', pad_inches=0.05, transparent=True)
    plt.close(fig)
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def gerar_grafico_da_carta(dados_brutos):
    # 1. Cria uma "tela" em branco para o gráfico
    plt.figure(figsize=(8, 6))
    # 2. Prepara os dados do seu JSON para o Seaborn entender
    # Ele gosta de duas listas: uma com os números e outra com os nomes (eixos X e Y)
    valores = []
    nomes_das_listas = []
    for chave, lista_numeros in (dados_brutos or {}).items():
        for numero in lista_numeros:
            valores.append(numero)
            nomes_das_listas.append(f"Lista {chave}")       
    # 3. Pede pro Seaborn desenhar o Boxplot
    sns.boxplot(x=nomes_das_listas, y=valores)
    # Dá um título bacana
    plt.title("Distribuição das Listas (Amplitude e Concentração)")
    plt.ylabel("Valores")
    plt.xlabel("Listas da Carta")
    # 4. Salva o gráfico na memória RAM (em vez de salvar no HD)
    # Isso é perfeito para injetar direto em um gerador de PDF depois!
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    # Fecha o gráfico para liberar a memória do servidor
    plt.close() 
    # Volta o "ponteiro" do buffer para o começo e retorna os dados da imagem
    buffer.seek(0)
    return buffer

def calcular_probabilidade_binomial(n, k, p, acumulada=False):
    import math
    if not acumulada:
        return math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
    else:
        return sum(math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k, n + 1))

def grafico_media(carta):
    plt.figure(figsize=(9, 5))
    lista_media = list(carta.media.values())
    
    if len(lista_media) > 0:
        eixo_x = range(1, len(lista_media) + 1)
        
        # Linha com pontos conectados
        plt.plot(eixo_x, lista_media, marker='o', markersize=5, color='#2874A6', 
                 linestyle='-', linewidth=1.5, label='Média da Amostra', zorder=5)
        
        # Limites e Linha Central
        plt.axhline(y=carta.lsc_media, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LSC ({carta.lsc_media:.2f})')
        plt.axhline(y=carta.media_geral, color='#27AE60', linestyle='-', linewidth=2, label=f'Média Geral ({carta.media_geral:.2f})')
        plt.axhline(y=carta.lic_media, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LIC ({carta.lic_media:.2f})')

        plt.xticks(eixo_x) # Força números inteiros no eixo X

    # Perfumaria
    plt.title("Carta de Controle X-Barra (Médias)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Amostra", fontsize=11, labelpad=10)
    plt.ylabel("Média", fontsize=11, labelpad=10)
    
    plt.legend(loc='best')
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()

    # Salvando em alta resolução
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150)
    plt.close()
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')
def grafico_amplitude(carta):
    plt.figure(figsize=(9, 5))
    lista_amplitude = list(carta.amplitude.values())
    
    if len(lista_amplitude) > 0:
        eixo_x = range(1, len(lista_amplitude) + 1)
        
        # Linha com pontos conectados
        plt.plot(eixo_x, lista_amplitude, marker='o', markersize=5, color='#2874A6', 
                 linestyle='-', linewidth=1.5, label='Amplitude da Amostra', zorder=5)
        
        # Limites e Linha Central
        plt.axhline(y=carta.lsc_amp, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LSC ({carta.lsc_amp:.2f})')
        plt.axhline(y=carta.media_amplitude, color='#27AE60', linestyle='-', linewidth=2, label=f'Média ({carta.media_amplitude:.2f})')
        plt.axhline(y=carta.lic_amp, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LIC ({carta.lic_amp:.2f})')

        plt.xticks(eixo_x) # Força números inteiros no eixo X

    # Perfumaria
    plt.title("Carta de Controle R (Amplitudes)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Amostra", fontsize=11, labelpad=10)
    plt.ylabel("Amplitude", fontsize=11, labelpad=10)
    
    plt.legend(loc='best')
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()

    # Salvando em alta resolução
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150)
    plt.close()
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def grafico_i(carta):
    # Proporção mais "widescreen" (9x5) fica muito melhor e mais legível em PDFs
    plt.figure(figsize=(9, 5)) 
    
    # 1. Puxamos os valores
    valores_brutos = list(carta.data.values())
    
    if len(valores_brutos) > 0:
        # Prevenção: Se os dados vierem como [[15.0], [15.2]], extraímos só o número
        if isinstance(valores_brutos[0], list):
            lista_1 = [item[0] for item in valores_brutos]
        else:
            lista_1 = valores_brutos
            
        eixo_x = range(1, len(lista_1) + 1)
        
        # 3. Desenhando LINHAS e PONTOS JUNTOS (A mágica acontece aqui!)
        # marker='o' faz a bolinha, markersize controla o tamanho da bolinha
        plt.plot(eixo_x, lista_1, marker='o', markersize=5, color='#2874A6', 
                 linestyle='-', linewidth=1.5, label='Valor Individual', zorder=5)
        
        # 4. LINHAS HORIZONTAIS (Padrão da Indústria)
        # Limite Superior (Vermelho Tracejado)
        plt.axhline(y=carta.lsc_i, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LSC ({carta.lsc_i:.2f})')
        # Linha Central / Média (Verde Sólido)
        plt.axhline(y=carta.lc_i, color='#27AE60', linestyle='-', linewidth=2, label=f'Média ({carta.lc_i:.2f})')
        # Limite Inferior (Vermelho Tracejado)
        plt.axhline(y=carta.lic_i, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LIC ({carta.lic_i:.2f})')

    # 5. Perfumaria Nível PRO
    plt.title("Carta de Controle I-MR (Valores Individuais)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Amostra", fontsize=11, labelpad=10)
    plt.ylabel("Valor Medido", fontsize=11, labelpad=10)
    
    # Força o eixo X a mostrar apenas números inteiros (1, 2, 3...) em vez de 1.5, 2.5
    plt.xticks(eixo_x)
    
    # Organiza a legenda e coloca a grade de fundo mais suave para não poluir
    plt.legend(loc='best') 
    plt.grid(True, linestyle='--', alpha=0.4) 
    
    # Garante que as bordas não fiquem cortadas na hora de salvar
    plt.tight_layout()

    # 6. Salva na memória com alta qualidade (dpi=150) e devolve para a View
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150) 
    plt.close()
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')
def grafico_mr(carta):
    plt.figure(figsize=(9, 5))
    lista_mr = list(carta.amplitude_movel.values())
    
    if len(lista_mr) > 0:
        eixo_x = range(1, len(lista_mr) + 1)
        
        # Linha com pontos conectados
        plt.plot(eixo_x, lista_mr, marker='o', markersize=5, color='#2874A6', 
                 linestyle='-', linewidth=1.5, label='Amplitude Móvel (MR)', zorder=5)
        
        # Limites e Linha Central
        plt.axhline(y=carta.lsc_mr, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LSC ({carta.lsc_mr:.2f})')
        plt.axhline(y=carta.lc_mr, color='#27AE60', linestyle='-', linewidth=2, label=f'Média ({carta.lc_mr:.2f})')
        plt.axhline(y=carta.lic_mr, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LIC ({carta.lic_mr:.2f})')

        plt.xticks(eixo_x)

    # Perfumaria
    plt.title("Carta de Controle I-MR (Amplitude Móvel)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Amostra", fontsize=11, labelpad=10)
    plt.ylabel("Amplitude Móvel", fontsize=11, labelpad=10)
    
    plt.legend(loc='best')
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()

    # Salvando em alta resolução
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150)
    plt.close()
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def grafico_u(carta):
    plt.figure(figsize=(9, 5))
    lista_taxa = list(carta.taxa.values())
    
    if len(lista_taxa) > 0:
        eixo_x = range(1, len(lista_taxa) + 1)
        
        # Linha com pontos conectados
        plt.plot(eixo_x, lista_taxa, marker='o', markersize=5, color='#2874A6', 
                 linestyle='-', linewidth=1.5, label='Taxa da Amostra', zorder=5)
        
        # Limites e Linha Central
        plt.axhline(y=carta.lsc, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LSC ({carta.lsc:.2f})')
        plt.axhline(y=carta.lc, color='#27AE60', linestyle='-', linewidth=2, label=f'Média ({carta.lc:.2f})')
        plt.axhline(y=carta.lic, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LIC ({carta.lic:.2f})')

        plt.xticks(eixo_x)

    # Perfumaria
    plt.title("Carta de Controle (Taxa/Proporção)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Amostra", fontsize=11, labelpad=10)
    plt.ylabel("Valor da Taxa", fontsize=11, labelpad=10)
    
    plt.legend(loc='best')
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()

    # Salvando em alta resolução
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150)
    plt.close()
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def grafico_p(carta):
    plt.figure(figsize=(9, 5))
    lista_p = list(carta.taxa.values())
    
    if len(lista_p) > 0:
        eixo_x = range(1, len(lista_p) + 1)
        
        # Linha com pontos conectados
        plt.plot(eixo_x, lista_p, marker='o', markersize=5, color='#2874A6', 
                 linestyle='-', linewidth=1.5, label='Proporção da Amostra', zorder=5)
        
        # Limites e Linha Central
        plt.axhline(y=carta.lsc, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LSC ({carta.lsc:.4f})')
        plt.axhline(y=carta.lc, color='#27AE60', linestyle='-', linewidth=2, label=f'Média ({carta.lc:.4f})')
        plt.axhline(y=carta.lic, color='#E74C3C', linestyle='--', linewidth=1.5, label=f'LIC ({carta.lic:.4f})')

        plt.xticks(eixo_x)

    # Perfumaria
    plt.title("Carta de Controle p (Proporção de Defeituosos)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Amostra", fontsize=11, labelpad=10)
    plt.ylabel("Proporção (p)", fontsize=11, labelpad=10)
    
    plt.legend(loc='best')
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.tight_layout()

    # Salvando em alta resolução
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150)
    plt.close()
    
    return base64.b64encode(buffer.getvalue()).decode('utf-8')







def GerarRelatorioXr(carta):
    
    formulas = {
        'media_medias': renderizar_formula_latex(r"\overline{\overline{X}} = \dfrac{\sum \overline{X}_i}{k}"),
        'amplitude_media': renderizar_formula_latex(r"\overline{R} = \dfrac{\sum R_i}{k}"),
        'lsc_x': renderizar_formula_latex(r"LSC_X = \overline{\overline{X}} + A_2 \overline{R}"),
        'lic_x': renderizar_formula_latex(r"LIC_X = \overline{\overline{X}} - A_2 \overline{R}"),
        'lsc_r': renderizar_formula_latex(r"LSC_R = D_4 \overline{R}"),
        'lic_r': renderizar_formula_latex(r"LIC_R = D_3 \overline{R}")
    }

    context = {
            'carta': carta,
            'graficox': grafico_media(carta),
            'graficor':grafico_amplitude(carta),
            'dados_tabela': carta.data.items(),
            'formulas': formulas
        }
    template = get_template('front/relatorios/RelatorioXr.html')
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")),result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        #response['Content-Disposition'] = f'attachment; filename="relatorio_{carta.id}.pdf"'
        response['Content-Disposition'] = f'inline; filename="relatorio_{carta.id}.pdf"'
        return response
    
    return None

def GerarRelatorioIMR(carta):
    
    formulas = {
        'media_indiv': renderizar_formula_latex(r"\overline{X} = \dfrac{\sum X_i}{k}"),
        'amplitude_movel_media': renderizar_formula_latex(r"\overline{MR} = \dfrac{\sum MR_i}{k-1}"),
        'lsc_i': renderizar_formula_latex(r"LSC_I = \overline{X} + E_2 \overline{MR}"),
        'lic_i': renderizar_formula_latex(r"LIC_I = \overline{X} - E_2 \overline{MR}"),
        'lsc_mr': renderizar_formula_latex(r"LSC_{MR} = D_4 \overline{MR}"),
        'lic_mr': renderizar_formula_latex(r"LIC_{MR} = D_3 \overline{MR}")
    }

    context = {
            'carta': carta,
            'grafico_i': grafico_i(carta),
            'grafico_mr':grafico_mr(carta),
            'dados_tabela': carta.data.items(),
            'formulas': formulas
        }
    template = get_template('front/relatorios/RelatorioIMR.html')
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")),result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        #response['Content-Disposition'] = f'attachment; filename="relatorio_{carta.id}.pdf"'
        response['Content-Disposition'] = f'inline; filename="relatorio_{carta.id}.pdf"'
        return response
    
    return None

def GerarRelatorioU(carta):
    
    formulas = {
        'taxa_media': renderizar_formula_latex(r"\bar{u} = \dfrac{\sum \mathrm{defeitos}}{\sum n_i}"),
        'lsc_u': renderizar_formula_latex(r"LSC_U = \bar{u} + 3\sqrt{\dfrac{\bar{u}}{n}}"),
        'lic_u': renderizar_formula_latex(r"LIC_U = \bar{u} - 3\sqrt{\dfrac{\bar{u}}{n}}")
    }

    context = {
            'carta': carta,
            'grafico': grafico_u(carta),
            'dados_tabela': carta.data.items(),
            'formulas': formulas
        }
    template = get_template('front/relatorios/RelatorioU.html')
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")),result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        #response['Content-Disposition'] = f'attachment; filename="relatorio_{carta.id}.pdf"'
        response['Content-Disposition'] = f'inline; filename="relatorio_{carta.id}.pdf"'
        return response
    
    return None

def GerarRelatorioP(carta):
    
    formulas = {
        'proporcao_media': renderizar_formula_latex(r"\bar{p} = \dfrac{\sum \mathrm{defeituosos}}{\sum n_i}"),
        'lsc_p': renderizar_formula_latex(r"LSC_P = \bar{p} + 3\sqrt{\dfrac{\bar{p}(1-\bar{p})}{n}}"),
        'lic_p': renderizar_formula_latex(r"LIC_P = \bar{p} - 3\sqrt{\dfrac{\bar{p}(1-\bar{p})}{n}}")
    }

    context = {
            'carta': carta,
            'grafico': grafico_p(carta),
            'dados_tabela': carta.data.items(),
            'formulas': formulas
        }
    template = get_template('front/relatorios/RelatorioP.html')
    html = template.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")),result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        #response['Content-Disposition'] = f'attachment; filename="relatorio_{carta.id}.pdf"'
        response['Content-Disposition'] = f'inline; filename="relatorio_{carta.id}.pdf"'
        return response
    
    return None
    


