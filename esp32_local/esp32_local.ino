#include <WiFi.h>
#include <WebServer.h>
#include <WiFiManager.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// =========================================================================
// CONFIGURAÇÃO DE HARDWARE
// =========================================================================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

const int pinoLed = 2;
const int pinoSpeaker = 23;
const int pinoAudio = 34;

const int LIMIAR_AMPLITUDE = 8;
const unsigned long JANELA_TEMPO = 30000; // 30 segundos

// =========================================================================
// VARIÁVEIS COMPARTILHADAS (volatile — acessadas por ambos os cores)
// =========================================================================
volatile int contadorPicos = 0;
volatile bool alarmeAtivo = false;

// Ring buffer — histórico das últimas 10 janelas
const int MAX_HISTORICO = 10;
volatile int historicoPicos[MAX_HISTORICO];
volatile int idxHistorico = 0;
volatile int totalHistorico = 0;

// =========================================================================
// SERVIDOR WEB (porta 80)
// =========================================================================
WebServer server(80);

// =========================================================================
// PÁGINA HTML (armazenada na Flash via PROGMEM)
// =========================================================================
const char PAGINA_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SPC Monitor Local</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: #0D1117;
      color: #E6EDF3;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 16px;
    }

    /* Header */
    .header {
      text-align: center;
      margin-bottom: 32px;
    }
    .header h1 {
      font-size: 1.6rem;
      font-weight: 700;
      background: linear-gradient(135deg, #58A6FF, #BC8CFF);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .header p {
      font-size: 0.8rem;
      color: #8B949E;
      margin-top: 4px;
    }

    /* Cards */
    .card {
      background: #161B22;
      border: 1px solid #30363D;
      border-radius: 16px;
      padding: 24px;
      width: 100%;
      max-width: 420px;
      margin-bottom: 16px;
      transition: border-color 0.3s ease;
    }
    .card:hover {
      border-color: #58A6FF44;
    }
    .card-label {
      font-size: 0.75rem;
      font-weight: 600;
      color: #8B949E;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      margin-bottom: 12px;
    }

    /* Picos atuais */
    .picos-valor {
      font-size: 4.5rem;
      font-weight: 900;
      text-align: center;
      line-height: 1;
      background: linear-gradient(180deg, #E6EDF3, #8B949E);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      transition: transform 0.2s ease;
    }
    .picos-valor.pulse {
      transform: scale(1.08);
    }

    /* Gráfico de barras */
    .chart-container {
      display: flex;
      align-items: flex-end;
      justify-content: center;
      gap: 6px;
      height: 100px;
      padding-top: 8px;
    }
    .bar-wrapper {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      flex: 1;
      max-width: 32px;
    }
    .bar {
      width: 100%;
      min-height: 4px;
      border-radius: 4px 4px 2px 2px;
      background: linear-gradient(180deg, #58A6FF, #1F6FEB);
      transition: height 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    .bar-label {
      font-size: 0.6rem;
      color: #8B949E;
      font-weight: 600;
    }
    .no-data {
      color: #30363D;
      font-size: 0.8rem;
      text-align: center;
      padding: 30px 0;
    }

    /* Botão de alerta */
    .alert-btn {
      width: 100%;
      padding: 16px;
      border: 2px solid #30363D;
      border-radius: 12px;
      font-family: 'Inter', sans-serif;
      font-size: 1rem;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      background: #161B22;
      color: #3FB950;
    }
    .alert-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
    }
    .alert-btn:active {
      transform: translateY(0);
    }
    .alert-btn.ativo {
      background: linear-gradient(135deg, #DA3633, #F85149);
      border-color: #F8514966;
      color: #FFFFFF;
      animation: glow-pulse 1.5s ease-in-out infinite;
    }
    @keyframes glow-pulse {
      0%, 100% { box-shadow: 0 0 8px #F8514933; }
      50% { box-shadow: 0 0 24px #F8514966; }
    }
    .alert-btn.loading {
      opacity: 0.6;
      pointer-events: none;
    }

    /* Status de conexão */
    .status-bar {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      margin-top: 20px;
      font-size: 0.75rem;
      color: #8B949E;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #3FB950;
      animation: blink 2s ease-in-out infinite;
    }
    .status-dot.offline {
      background: #F85149;
      animation: none;
    }
    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
  </style>
</head>
<body>

  <div class="header">
    <h1>&#128266; SPC Monitor Local</h1>
    <p>Monitoramento de ru&iacute;do em tempo real</p>
  </div>

  <!-- Card: Picos Atuais -->
  <div class="card">
    <div class="card-label">Picos na janela atual</div>
    <div class="picos-valor" id="picos-valor">--</div>
  </div>

  <!-- Card: Histórico -->
  <div class="card">
    <div class="card-label">Hist&oacute;rico (&uacute;ltimas 10 janelas)</div>
    <div class="chart-container" id="chart">
      <div class="no-data">Aguardando dados...</div>
    </div>
  </div>

  <!-- Card: Botão Alerta -->
  <div class="card">
    <button class="alert-btn" id="alert-btn" onclick="toggleAlerta()">
      <span id="alert-icon">&#128276;</span>
      <span id="alert-text">ATIVAR ALERTA</span>
    </button>
  </div>

  <!-- Status -->
  <div class="status-bar">
    <div class="status-dot" id="status-dot"></div>
    <span id="status-text">Conectado ao ESP32</span>
  </div>

  <script>
    let alarmeAtual = false;
    let ultimoPicos = -1;

    // --- Polling a cada 2 segundos ---
    async function fetchData() {
      try {
        const res = await fetch('/api/data');
        const data = await res.json();

        // Atualiza picos
        const el = document.getElementById('picos-valor');
        if (data.picos !== ultimoPicos) {
          el.textContent = data.picos;
          el.classList.add('pulse');
          setTimeout(() => el.classList.remove('pulse'), 200);
          ultimoPicos = data.picos;
        }

        // Atualiza histórico (gráfico de barras)
        const chart = document.getElementById('chart');
        const hist = data.historico;
        if (hist.length === 0) {
          chart.innerHTML = '<div class="no-data">Aguardando dados...</div>';
        } else {
          const maxVal = Math.max(...hist, 1);
          chart.innerHTML = hist.map(v => {
            const h = Math.max(4, (v / maxVal) * 90);
            return '<div class="bar-wrapper">' +
              '<div class="bar" style="height:' + h + 'px"></div>' +
              '<div class="bar-label">' + v + '</div>' +
            '</div>';
          }).join('');
        }

        // Atualiza botão
        alarmeAtual = data.alarme;
        atualizarBotao();

        // Status: online
        document.getElementById('status-dot').classList.remove('offline');
        document.getElementById('status-text').textContent = 'Conectado ao ESP32';

      } catch (e) {
        document.getElementById('status-dot').classList.add('offline');
        document.getElementById('status-text').textContent = 'Sem conexão com ESP32';
      }
    }

    function atualizarBotao() {
      const btn = document.getElementById('alert-btn');
      const icon = document.getElementById('alert-icon');
      const text = document.getElementById('alert-text');
      if (alarmeAtual) {
        btn.classList.add('ativo');
        icon.innerHTML = '&#128680;';
        text.textContent = 'DESATIVAR ALERTA';
      } else {
        btn.classList.remove('ativo');
        icon.innerHTML = '&#128276;';
        text.textContent = 'ATIVAR ALERTA';
      }
    }

    async function toggleAlerta() {
      const btn = document.getElementById('alert-btn');
      btn.classList.add('loading');
      try {
        await fetch('/api/alert', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ativo: !alarmeAtual })
        });
        alarmeAtual = !alarmeAtual;
        atualizarBotao();
      } catch (e) {
        console.error('Erro ao toggle alerta:', e);
      }
      btn.classList.remove('loading');
    }

    // Inicia polling
    fetchData();
    setInterval(fetchData, 2000);
  </script>

</body>
</html>
)rawliteral";

// =========================================================================
// FUNÇÕES DO DISPLAY OLED (só usado no setup)
// =========================================================================
void oledMensagem(String linha1, String linha2, String linha3) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  display.setCursor(0, 5);
  display.println(linha1);

  display.setCursor(0, 25);
  display.println(linha2);

  if (linha3.length() > 0) {
    display.setCursor(0, 45);
    display.println(linha3);
  }

  display.display();
}

void oledURL(String ip) {
  display.clearDisplay();

  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(10, 5);
  display.println("Wi-Fi OK!");

  display.setCursor(0, 25);
  display.println("Acesse no browser:");

  display.setTextSize(1);
  display.setCursor(0, 48);
  display.print("http://");
  display.println(ip);

  display.display();
}

// =========================================================================
// HANDLERS DOS ENDPOINTS
// =========================================================================

// Helper: adiciona headers CORS em toda resposta de API
void sendCORS() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

// OPTIONS preflight (browser envia antes de POST com JSON)
void handleOptions() {
  sendCORS();
  server.send(204);
}

// GET / → Página HTML
void handleRoot() {
  server.send_P(200, "text/html", PAGINA_HTML);
}

// GET /api/data → JSON com picos, alarme e histórico
void handleGetData() {
  sendCORS();

  StaticJsonDocument<512> doc;
  doc["picos"] = (int)contadorPicos;
  doc["alarme"] = (bool)alarmeAtivo;

  JsonArray hist = doc.createNestedArray("historico");

  // Monta o array na ordem cronológica (mais antigo → mais recente)
  if (totalHistorico > 0) {
    int count = (totalHistorico < MAX_HISTORICO) ? totalHistorico : MAX_HISTORICO;
    int start = (totalHistorico < MAX_HISTORICO) ? 0 : idxHistorico;
    for (int i = 0; i < count; i++) {
      int idx = (start + i) % MAX_HISTORICO;
      hist.add((int)historicoPicos[idx]);
    }
  }

  char buffer[512];
  serializeJson(doc, buffer);
  server.send(200, "application/json", buffer);
}

// POST /api/alert → Toggle do alarme
void handlePostAlert() {
  sendCORS();

  if (server.hasArg("plain")) {
    StaticJsonDocument<64> doc;
    DeserializationError error = deserializeJson(doc, server.arg("plain"));

    if (!error && doc.containsKey("ativo")) {
      alarmeAtivo = doc["ativo"].as<bool>();
    }
  }

  // Responde com o estado atual
  StaticJsonDocument<32> resp;
  resp["alarme"] = (bool)alarmeAtivo;
  char buffer[64];
  serializeJson(resp, buffer);
  server.send(200, "application/json", buffer);
}

// =========================================================================
// TASK DO WEBSERVER (Roda no Core 0)
// =========================================================================
void taskWebServerCode(void * pvParameters) {
  for (;;) {
    server.handleClient();
    vTaskDelay(10 / portTICK_PERIOD_MS);
  }
}

// =========================================================================
// SETUP
// =========================================================================
void setup() {
  Serial.begin(115200);

  // Pinos
  pinMode(pinoLed, OUTPUT);
  pinMode(pinoSpeaker, OUTPUT);
  analogSetPinAttenuation(pinoAudio, ADC_0db);
  digitalWrite(pinoLed, LOW);
  noTone(pinoSpeaker);

  // Inicializar ring buffer
  for (int i = 0; i < MAX_HISTORICO; i++) {
    historicoPicos[i] = 0;
  }

  // Display OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Falha ao iniciar SSD1306"));
    for (;;);
  }

  // Estado 1: Aguardando Wi-Fi
  oledMensagem(
    "   Wi-Fi",
    "Conecte na rede:",
    "SPC_Monitor_WiFi"
  );

  // WiFiManager
  WiFiManager wm;
  wm.setConnectTimeout(10);
  wm.setConfigPortalTimeout(180);
  bool res = wm.autoConnect("SPC_Monitor_WiFi");

  if (!res) {
    // Estado 3: Falha
    oledMensagem(
      "  Wi-Fi Falhou",
      "  Reiniciando...",
      ""
    );
    Serial.println("Falha ao conectar no Wi-Fi. Reiniciando...");
    delay(2000);
    ESP.restart();
  }

  // Wi-Fi conectado!
  String ip = WiFi.localIP().toString();
  Serial.println("\nWi-Fi Conectado!");
  Serial.println("IP: " + ip);
  Serial.println("Acesse: http://" + ip);

  // Estado 2: Mostra URL (permanece fixo)
  oledURL(ip);

  // Registrar rotas do WebServer
  server.on("/", HTTP_GET, handleRoot);
  server.on("/api/data", HTTP_GET, handleGetData);
  server.on("/api/data", HTTP_OPTIONS, handleOptions);
  server.on("/api/alert", HTTP_POST, handlePostAlert);
  server.on("/api/alert", HTTP_OPTIONS, handleOptions);
  server.begin();
  Serial.println("Servidor HTTP iniciado na porta 80");

  // Criar Task do WebServer no Core 0
  xTaskCreatePinnedToCore(
    taskWebServerCode,
    "TaskWebServer",
    10000,
    NULL,
    1,
    NULL,
    0  // Core 0
  );
}

// =========================================================================
// LOOP (Roda no Core 1 — Sensor + Alarme)
// =========================================================================
unsigned long tempoInicial = 0;

void loop() {
  // Inicializa o tempo na primeira iteração
  if (tempoInicial == 0) {
    tempoInicial = millis();
  }

  // --- Controle do alarme (LED + Speaker) ---
  if (alarmeAtivo) {
    digitalWrite(pinoLed, HIGH);
    if (millis() % 600 < 300) {
      tone(pinoSpeaker, 800);
    } else {
      tone(pinoSpeaker, 500);
    }
  } else {
    digitalWrite(pinoLed, LOW);
    noTone(pinoSpeaker);
  }

  // --- Leitura do microfone (janela de 50ms) ---
  int maximo = 0;
  int minimo = 4095;
  unsigned long inicioAmostra = millis();

  while (millis() - inicioAmostra < 50) {
    int leitura = analogRead(pinoAudio);
    if (leitura < 4095 && leitura > 0) {
      if (leitura > maximo) maximo = leitura;
      if (leitura < minimo) minimo = leitura;
    }
  }

  int amplitude = maximo - minimo;

  if (amplitude > LIMIAR_AMPLITUDE) {
    contadorPicos++;
  }

  // --- Ring buffer: salva e reseta a cada 30 segundos ---
  if (millis() - tempoInicial >= JANELA_TEMPO) {
    historicoPicos[idxHistorico] = contadorPicos;
    idxHistorico = (idxHistorico + 1) % MAX_HISTORICO;
    if (totalHistorico < MAX_HISTORICO) totalHistorico++;

    Serial.printf("Janela encerrada — picos: %d | historico[%d/%d]\n",
                  contadorPicos, totalHistorico,  MAX_HISTORICO);

    contadorPicos = 0;
    tempoInicial = millis();
  }
}
