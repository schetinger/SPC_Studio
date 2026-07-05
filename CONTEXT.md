# Context & Glossary

Este documento serve como mapa mental para o funcionamento da plataforma SPC Studio.

## Domínio Arquitetural

1. **Motor Estatístico / Relatórios:**
   - O *core business* do sistema, escrito em Python/Django.
   - Responsável por receber lotes de amostras, calcular limites de controle estatístico (LC, LSC, LIC) e avaliar "Regras de Controle" (ex: Western Electric).
   - Suporta Cartas de Controle: **P** (Fração Defeituosa), **X-R**, **I-MR**, **U**, entre outras.
   - Gera relatórios estáticos exportáveis (PDF).

2. **Ingestão de Sinais / IoT:**
   - API REST (Polling) projetada para receber dados contínuos de hardware físico (ex: sensores).
   - *Agnóstico de hardware*: A API apenas espera um JSON contendo os dados brutos e avalia as violações de controle no back-end.
   - Mantém estado rápido (ex: alarme ativado) utilizando um Cache em memória (Redis).

## Key Architectural Decisions (ADRs informais)

- **HTTP Polling vs WebSockets**: Devido a timeouts silenciosos e limitações de conexões longas no deploy (Render/Cloudflare), substituímos Websockets por Polling simples usando `fetch` (Frontend) e `HTTPClient` assíncrono com FreeRTOS (ESP32).
- **Cache como Source of Truth**: Usamos o `django.core.cache` configurado com Redis para persistir de forma atômica e super rápida a intenção do usuário (ex: botão de Ligar Alarme) e a leitura dos sensores na janela de tempo atual.

## Glossary

**Sensor Endpoint (Ex: ESP32)**: Cliente "burro" que apenas mede o mundo real, bate no endpoint `/api/esp/picos/` enviando a quantidade coletada numa janela, e periodicamente faz GET em `/api/esp/status/` para saber se deve tocar o alarme localmente.
**Monitoramento Web**: Cliente Frontend que bate a cada N segundos em `/api/browser/sync/` para pegar o log de picos atualizado e renderizar no Chart.js animadamente, além de refletir a conexão do sensor físico.
