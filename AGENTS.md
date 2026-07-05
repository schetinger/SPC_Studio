# Agent Rules

As diretrizes para agentes atuando neste projeto:

## Regra de Ouro do Contexto
- Sempre leia `CONTEXT.md` para entender a arquitetura (Motor de Relatórios + API IoT de Ingestão via Polling) antes de propor qualquer mudança.
- O propósito do sistema se encontra em `MISSION.md`.

## Backend (Django)
- **REST + Polling**: Não use WebSockets nem Channels. Toda a comunicação realtime é baseada em polling na API (com endpoints HTTP).
- O `django.core.cache` via Redis é nossa "Single Source of Truth" para estados ultrarrápidos (ex: Alarme IoT ativado) que vivem entre requests.
- Se for criar endpoints novos, prefira Views simples decoradas com `@csrf_exempt` em vez do peso do DRF (`djangorestframework`), a menos que o usuário exija.
- Use sempre Test-Driven Development (via `/tdd`) antes de codar as views.

## Frontend & Estética
- O UI é gerado no backend via templates (`app/templates/front/`).
- Não usar Tailwind ou frameworks JS. O estilo é **Vanilla CSS**.
- **Aesthetic First**: Preserve o esquema de cores premium Dark Mode (#0D1117 de fundo), bordas sutis e tipografia moderna (Inter / JetBrains Mono).
- Use `fetch` com async/await e `setInterval` para o polling do monitoramento.

## Firmware IoT (ESP32)
- Quando mexer no código do microcontrolador (em C++), use FreeRTOS para não bloquear a leitura de sinais analógicos (`analogRead`) durante as requisições lentas de HTTPClient.
