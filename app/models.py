from django.db import models
import statistics,math

class Carta(models.Model):
    data = models.JSONField(default=dict)
    media = models.JSONField(default=0)
    dp = models.JSONField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    dp_geral = models.FloatField(default=0)
    x1 = models.FloatField(default=0)
    x0= models.FloatField(default=0)
    lse = models.FloatField(default=0)
    lie = models.FloatField(default=0)
    cp = models.FloatField(default=0)
    cpk = models.FloatField(default=0)
    probabilidade = models.JSONField(default=dict)
    alertas = models.JSONField(default=dict)
    regra = models.CharField(max_length=255, default="", blank=True)

    @property
    def is_capaz(self):
        if self.lse > 0 and self.lie > 0 and self.dp_geral > 0:
            # Curto prazo: Sem pontos na Regra 1 (fora de controle)
            curto_prazo_ok = True
            if isinstance(self.alertas, dict):
                regra_1 = self.alertas.get("regra_1_fora_controle", [])
                if len(regra_1) > 0:
                    curto_prazo_ok = False
            
            # Longo prazo: PPM < 990
            media_central = getattr(self, 'media_geral', getattr(self, 'lc_i', None))
            if media_central is not None:
                try:
                    curva_normal = statistics.NormalDist(mu=media_central, sigma=self.dp_geral)
                    prob_dentro = curva_normal.cdf(self.lse) - curva_normal.cdf(self.lie)
                    ppm = (1 - prob_dentro) * 1_000_000
                    longo_prazo_ok = ppm < 990
                    return curto_prazo_ok and longo_prazo_ok
                except Exception:
                    pass
                    
            # Fallback caso dê erro no PPM
            return self.cp >= 1.0 and self.cpk >= 1.0
        return None

    class Meta:
        abstract = True
    
    def aplicar_regras_western_electric(lista_medias, media_central, lsc):
                # 1. Descobrindo o tamanho das Zonas (1 sigma do gráfico)
                sigma = (lsc - media_central) / 3
                acima=0
                abaixo=0
                limite_1s = sigma       # Fronteira da Zona C para a Zona B
                limite_2s = 2 * sigma   # Fronteira da Zona B para a Zona A
                limite_3s = 3 * sigma   # Limites de Controle (LSC / LIC)

                # 2. Dicionário para guardar as amostras que dispararam alertas
                alertas = {
                "regra_1_fora_controle": [], # 1 ponto além de 3 sigmas
                "regra_2_alerta_zona_a": [], # 2 de 3 pontos além de 2 sigmas (mesmo lado)
                "regra_3_tendencia": [],     # 4 de 5 pontos além de 1 sigma (mesmo lado)
                "regra_4_deslocamento": []   # 8 pontos consecutivos do mesmo lado da média
                }

                # 3. Varrendo os pontos um por um
                for i in range(len(lista_medias)):
                    amostra_atual = i + 1 # Para salvar no relatório como Amostra 1, 2, 3...
                    valor = lista_medias[i]

                # --- REGRA 1: 1 ponto além da Zona A (> 3 sigmas) ---
                    if abs(valor - media_central) > limite_3s:
                        alertas["regra_1_fora_controle"].append(amostra_atual)

                    # --- REGRA 2: 2 de 3 pontos consecutivos > 2 sigmas (mesmo lado) ---
                    if i >= 2:
                        janela = [lista_medias[i], lista_medias[i-1], lista_medias[i-2]]
                        acima = sum(1 for p in janela if p > media_central + limite_2s)
                        abaixo = sum(1 for p in janela if p < media_central - limite_2s)
                    if acima >= 2 or abaixo >= 2:
                        # Evita duplicar o alerta se o ponto já estourou a Regra 1
                        if amostra_atual not in alertas["regra_1_fora_controle"]:
                            alertas["regra_2_alerta_zona_a"].append(amostra_atual)

                        # --- REGRA 3: 4 de 5 pontos consecutivos > 1 sigma (mesmo lado) ---
                    if i >= 4:
                        janela = [lista_medias[i], lista_medias[i-1], lista_medias[i-2], lista_medias[i-3], lista_medias[i-4]]
                        acima = sum(1 for p in janela if p > media_central + limite_1s)
                        abaixo = sum(1 for p in janela if p < media_central - limite_1s)
                    if acima >= 4 or abaixo >= 4:
                        if amostra_atual not in alertas["regra_1_fora_controle"] and amostra_atual not in alertas["regra_2_alerta_zona_a"]:
                            alertas["regra_3_tendencia"].append(amostra_atual)

        # --- REGRA 4: 8 pontos consecutivos do mesmo lado da Linha Central ---
                    if i >= 7:
                        janela = lista_medias[i-7 : i+1] # Pega o atual e os 7 anteriores
                        todos_acima = all(p > media_central for p in janela)
                        todos_abaixo = all(p < media_central for p in janela)
                        if todos_acima or todos_abaixo:
                            alertas["regra_4_deslocamento"].append(amostra_atual)

                return alertas
            
 
    def dados (self, *args, **kwargs):
        calcular_media = {}
        calcular_dp = {}
        for chave, lista_numeros in self.data.items():
            if isinstance(lista_numeros,list) and len(lista_numeros)>1:
                
                calcular_media[chave] = round(statistics.mean(lista_numeros),3)
                calcular_dp[chave] = round(statistics.stdev(lista_numeros),3)
                

            elif isinstance(lista_numeros,list) and len(lista_numeros)==1:
                calcular_media[chave] = lista_numeros[0]
                calcular_dp[chave] = 0.0
        amostra = []
        for valores in self.data.values():
            amostra += valores
        self.dp_geral = round(statistics.stdev(amostra),3)
        self.media =calcular_media
        self.dp = calcular_dp
       


    def save(self, *args, **kwargs):
        self.dados()
        super().save(*args, **kwargs)

class Media_Amplitude(Carta):
            media_geral = models.FloatField(default=0)
            amplitude = models.JSONField(default=dict)
            media_amplitude = models.FloatField(default=0)
            lsc_media = models.FloatField(default=0)
            lsc_amp = models.FloatField(default=0)
            lic_media = models.FloatField(default=0)
            lic_amp = models.FloatField(default=0)
            # Constantes para n=10
            a2 = 0.308
            d4 = 1.777
            d3 = 0.223
            

            def dados(self, *args, **kwargs):

                super().dados()
                calcular_amplitude = {}
                for chave, lista_numeros in self.data.items():
                        if isinstance(lista_numeros,list) and len(lista_numeros)>1:
                            calcular_amplitude[chave] = round(max(lista_numeros)-min(lista_numeros),3)
                        elif isinstance(lista_numeros,list) and len(lista_numeros)==1:
                            calcular_amplitude[chave] = 0
                
                self.media_geral = round(statistics.mean(list(self.media.values())),3)
                self.amplitude = calcular_amplitude
                self.media_amplitude = round(statistics.mean(list(self.amplitude.values())),3)
                
                # Issue #5: limites baseados em r_bar e constantes
                self.lic_media = round( self.media_geral - self.a2*self.media_amplitude, 3)
                self.lsc_media = round( self.media_geral + self.a2*self.media_amplitude, 3)
                self.lic_amp = round( self.media_amplitude*self.d3, 3)
                self.lsc_amp = round( self.media_amplitude*self.d4, 3)
                # Issue #6: LIE e LSE calculados dinamicamente
                self.lie = round(0.99 * self.lic_media, 3)
                self.lse = round(1.2 * self.lsc_media, 3)
                
                if self.dp_geral > 0:
                    self.cp = round(((self.lse-self.lie)/(6*self.dp_geral)),3)
                    cpk_superior = (self.lse - self.media_geral) / (3 * self.dp_geral)
                    cpk_inferior = (self.media_geral - self.lie) / (3 * self.dp_geral)
                    self.cpk = round(min(cpk_superior, cpk_inferior),3)

                    curva_normal = statistics.NormalDist(mu=self.media_geral, sigma=self.dp_geral)
                    
                    # Issue #6: Probabilidade deslocada
                    mu_deslocada = self.media_geral + (1 * self.dp_geral)
                    curva_deslocada = statistics.NormalDist(mu=mu_deslocada, sigma=self.dp_geral)
                    margem_deslocada = (curva_deslocada.cdf(self.lse) - curva_deslocada.cdf(self.lie)) * 100
                    
                    # Issue #6: Valor X para 95%
                    valor_x_95 = curva_normal.inv_cdf(0.95)
                    
                    intervalo = (curva_normal.cdf(self.x1) - curva_normal.cdf(self.x0))*100
                    prob_menor_x1 = curva_normal.cdf(self.x1) * 100
                    prob_maior_x0 = (1 - curva_normal.cdf(self.x0)) * 100
                    
                    self.probabilidade= {
                        "menor_x1": round(prob_menor_x1, 3),
                        "maior_x0": round(prob_maior_x0, 3),
                        "intervalo": round(intervalo, 3),
                        "margem_deslocada": round(margem_deslocada, 3),
                        "valor_x_95": round(valor_x_95, 3)
                    }
                
                lista_das_medias = list(self.media.values()) 

                alertas_we = Carta.aplicar_regras_western_electric(
                lista_medias = lista_das_medias, 
                media_central = self.media_geral, 
                lsc = self.lsc_media
                )
                print(alertas_we)
                self.alertas = alertas_we
class p(Carta):
    n = 10
    lc = models.FloatField(default=0)
    lsc = models.FloatField(default=0)
    lic = models.FloatField(default=0)
    taxa = models.JSONField(default=dict)

    def dados(self):
        import operator
        ops = {"<": operator.lt, ">": operator.gt, "<=": operator.le, ">=": operator.ge, "==": operator.eq, "!=": operator.ne}
        
        op_func = None
        val_regra = None
        
        if self.regra:
            partes = self.regra.strip().split()
            if len(partes) == 3 and partes[0].lower() == 'x':
                op_func = ops.get(partes[1])
                try:
                    val_regra = float(partes[2])
                except ValueError:
                    pass

        calcular_taxas = {}
        calcular_lc = 0
        tamanho = 0
        super().dados()
        
        for i, valores in self.data.items():
            falhas = 0
            if op_func and val_regra is not None:
                for v in valores:
                    if op_func(v, val_regra):
                        falhas += 1
            else:
                falhas = valores[0]
                
            calcular_lc += falhas
            tamanho += self.n
            calcular_taxas[i] = round(falhas / self.n, 3)
            
        self.lc = calcular_lc / tamanho
        
        def desvio(p, n):
           return math.sqrt((p*(1-p))/n)
  
        if (self.lc - 3*desvio(self.lc, self.n) > 0): 
             self.lic = round(self.lc - 3*desvio(self.lc, self.n), 3)
        else: 
             self.lic = 0
             
        self.lsc = round(self.lc + 3*desvio(self.lc, self.n), 3)
        self.taxa = calcular_taxas
        
        lista_das_taxas = list(self.taxa.values())
        if lista_das_taxas:
            self.alertas = Carta.aplicar_regras_western_electric(
                lista_medias=lista_das_taxas,
                media_central=self.lc,
                lsc=self.lsc
            )
class u(Carta):
    n = 10
    lc = models.FloatField(default=0)
    lic = models.FloatField(default=0)
    lsc = models.FloatField(default=0)
    taxa = models.JSONField(default=dict)

    def dados(self):
        import operator
        ops = {"<": operator.lt, ">": operator.gt, "<=": operator.le, ">=": operator.ge, "==": operator.eq, "!=": operator.ne}
        
        op_func = None
        val_regra = None
        
        if self.regra:
            partes = self.regra.strip().split()
            if len(partes) == 3 and partes[0].lower() == 'x':
                op_func = ops.get(partes[1])
                try:
                    val_regra = float(partes[2])
                except ValueError:
                    pass

        calcular_taxas = {}
        calcular_lc = 0
        tamanho = 0
        super().dados()
        
        for i, valores in self.data.items():
            falhas = 0
            if op_func and val_regra is not None:
                for v in valores:
                    if op_func(v, val_regra):
                        falhas += 1
            else:
                falhas = valores[0]
                
            calcular_lc += falhas
            calcular_taxas[i] = round(falhas / self.n, 3)
            tamanho += self.n
            
        self.lc = calcular_lc / tamanho
        
        def desvio(u, n):
           return math.sqrt(u/n)
           
        if (self.lc - 3*desvio(self.lc, self.n) > 0): 
             self.lic = round(self.lc - 3*desvio(self.lc, self.n), 3)
        else: 
             self.lic = 0
             
        self.lsc = round(self.lc + 3*desvio(self.lc, self.n), 3)
        self.taxa = calcular_taxas

        lista_das_taxas = list(self.taxa.values())
        if lista_das_taxas:
            self.alertas = Carta.aplicar_regras_western_electric(
                lista_medias=lista_das_taxas,
                media_central=self.lc,
                lsc=self.lsc
            )
class imr(Carta):
     
     amplitude_movel = models.JSONField(default=dict)
     lc_i = models.FloatField(default=0)
     lsc_i = models.FloatField(default=0)
     lic_i = models.FloatField(default=0)
     lc_mr = models.FloatField(default=0)
     lsc_mr = models.FloatField(default=0)
     lic_mr= models.FloatField(default=0)
     am_media = models.FloatField(default=0)
     e2 = 2.66
     d3 = 0
     d4 = 3.267
     def dados (self, *args, **kwargs):
        super().dados()
        calcular_amplitudem = {}
        valores = list(self.media.values())

        for i in range (1,len(valores)):
            mr_atual = round(abs(valores[i]-valores[i-1]))
            calcular_amplitudem[i-1]=mr_atual
        
        self.amplitude_movel = calcular_amplitudem
        self.lc_i = round(statistics.mean(list(self.media.values())),3)
        if len(self.amplitude_movel) > 0:
            self.am_media = statistics.mean(list(self.amplitude_movel.values()))
        else:
            self.am_media = 0
        self.lsc_i = round(self.lc_i +self.e2*self.am_media,3)
        self.lic_i = round(self.lc_i -self.e2*self.am_media,3)
        self.lic_mr = round(self.am_media*self.d3,3)
        self.lsc_mr = round(self.am_media*self.d4,3)
        self.lc_mr = self.am_media
        
        # Issue #6: LIE e LSE calculados dinamicamente
        self.lie = round(0.99 * self.lic_i, 3)
        self.lse = round(1.2 * self.lsc_i, 3)
        
        # Issue #2 e #6: Cp, Cpk e Probabilidades
        if self.dp_geral > 0:
            self.cp = round(((self.lse - self.lie) / (6 * self.dp_geral)), 3)
            cpk_superior = (self.lse - self.lc_i) / (3 * self.dp_geral)
            cpk_inferior = (self.lc_i - self.lie) / (3 * self.dp_geral)
            self.cpk = round(min(cpk_superior, cpk_inferior), 3)

            curva_normal = statistics.NormalDist(mu=self.lc_i, sigma=self.dp_geral)
            
            # Issue #6: Probabilidade deslocada
            mu_deslocada = self.lc_i + (1 * self.dp_geral)
            curva_deslocada = statistics.NormalDist(mu=mu_deslocada, sigma=self.dp_geral)
            margem_deslocada = (curva_deslocada.cdf(self.lse) - curva_deslocada.cdf(self.lie)) * 100
            
            # Issue #6: Valor X para 95%
            valor_x_95 = curva_normal.inv_cdf(0.95)
            
            intervalo = (curva_normal.cdf(self.x1) - curva_normal.cdf(self.x0)) * 100
            prob_menor_x1 = curva_normal.cdf(self.x1) * 100
            prob_maior_x0 = (1 - curva_normal.cdf(self.x0)) * 100
            
            self.probabilidade = {
                "menor_x1": round(prob_menor_x1, 3),
                "maior_x0": round(prob_maior_x0, 3),
                "intervalo": round(intervalo, 3),
                "margem_deslocada": round(margem_deslocada, 3),
                "valor_x_95": round(valor_x_95, 3)
            }
        
        # Issue #2: Alertas Western Electric
        lista_das_medias = list(self.media.values())
        if lista_das_medias:
            self.alertas = Carta.aplicar_regras_western_electric(
                lista_medias=lista_das_medias,
                media_central=self.lc_i,
                lsc=self.lsc_i
            )
    
    
