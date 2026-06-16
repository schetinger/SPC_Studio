# SPC Studio | Controle Estatístico de Processo Automatizado

![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)
![Django](https://img.shields.io/badge/Django-API-092E20?style=for-the-badge&logo=django)
![Status](https://img.shields.io/badge/Status-Stable-success?style=for-the-badge)

A ferramenta definitiva e *open-source* para engenheiros da qualidade gerarem relatórios avançados de **Controle Estatístico de Processo (CEP/SPC)**. Através de uma interface web estilo IDE (ou chamadas diretas via API REST), você envia seus dados amostrais e nós devolvemos um relatório PDF de nível executivo.

---

## 🎨 A Interface (IDE Estatístico)

<img width="1914" height="954" alt="image" src="https://github.com/user-attachments/assets/fc5583e9-5e73-4d11-9cfe-9d701a317959" />


Desenvolvemos um front-end focado em alta produtividade. Um layout dividido em *Dark Mode* que permite a entrada de arquivos JSON à esquerda e o **Preview instantâneo e dinâmico** do PDF gerado à direita. Nenhuma configuração extra: colou, gerou.

<img width="1914" height="941" alt="image" src="https://github.com/user-attachments/assets/1217a648-3f9c-4dfd-90ac-e08828bd6235" />

---

## 🚀 Principais Funcionalidades

O SPC Studio foi construído sobre uma arquitetura TDD estrita e aplica os cálculos estatísticos clássicos da qualidade industrial sem margem para erro:

- ✅ **Cartas de Controle para Variáveis (Contínuas):** Suporte total para as tradicionais Cartas **Xr** (Média e Amplitude) e Cartas **IMR** (Valores Individuais e Amplitude Móvel).
- ✅ **Cartas de Controle por Atributos:** Suporte para Cartas **p** (proporção) e Cartas **u** (taxa de defeitos).
- 🏆 **Certificados Automáticos de Capacidade (Cp e Cpk):** Para variáveis contínuas, se os limites (LSE/LIE) forem fornecidos, o sistema emite um selo atestando se o processo é *Capaz* (Cp e Cpk ≥ 1.0) ou *Reprovado*.
- 🚨 **Motor de Regras Western Electric:** O motor estatístico detecta automaticamente anomalias no processo e gera alertas visuais no PDF para as 4 regras clássicas (Pontos fora de controle, tendências, deslocamentos e alertas de Zona A).
- ⚡ **Geração Instantânea em PDF:** Arquivos padronizados e vetorizados, prontos para anexo em auditorias (ISO 9001).

---

## 🛠️ Como Rodar Localmente

Certifique-se de ter o Python 3.12+ instalado.

1. **Clone o Repositório:**
   ```bash
   git clone https://github.com/schetinger/Topicos-eletronica.git
   cd Topicos-eletronica/cep
   ```

2. **Crie o Ambiente Virtual e instale as dependências:**
   *(O projeto usa bibliotecas padrão como Django e django-cors-headers)*
   ```bash
   python -m venv env
   source env/bin/activate  # ou env\Scripts\activate no Windows
   pip install django django-cors-headers djangorestframework
   ```

3. **Inicie o Servidor:**
   ```bash
   python manage.py runserver
   ```
4. **Acesse o SPC Studio:**
   Abra `http://localhost:8000/` no seu navegador para usar a interface gráfica.

---

## 📡 Documentação da API

Você pode consumir nosso motor estatístico por fora da nossa interface gráfica enviando requisições REST. 

**Endpoint:** `POST /carta/gerar-carta/`

**Exemplo de Payload (Carta Xr):**
```json
{
    "chart": "Xr",
    "measurements": {
        "A1": [10.1, 10.3, 9.8, 10.0],
        "A2": [9.9, 10.5, 10.1, 9.7]
    },
    "especificacoes": {
        "LSE": 11.0, 
        "LIE": 9.0
    },
    "intervalo_probabilidade": {
        "x1": 10.5, 
        "x0": 9.5
    }
}
```

O endpoint responderá com **HTTP 200 OK** e o `Content-Type: application/pdf`, retornando o binário puro do relatório pronto para visualização/download.

---

## 🧠 Arquitetura e Decisões de Negócio

Este projeto é desenvolvido com **Agents Autônomos** focados em evolução de arquitetura. Mantemos a documentação de domínio extremamente próxima do código.

- Quer entender a terminologia estatística que usamos nas classes? Leia o [CONTEXT.md](CONTEXT.md) e o [GLOSSARY.md](GLOSSARY.md).
- Quer saber por que escolhemos determinadas tecnologias? Veja a pasta `docs/adr/`.
- Quer contribuir usando nossas skills de IA? Confira o `AGENTS.md`.
