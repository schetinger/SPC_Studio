#include <WiFi.h>
#include <WiFiManager.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

const char* api_base_url = "https://spc-studio.onrender.com"; 

const int pinoLed = 2;       
const int pinoSpeaker = 23;   
const int pinoAudio = 34;

const int LIMIAR_AMPLITUDE = 8; 
const unsigned long JANELA_TEMPO = 30000; 

// Variáveis voláteis (compartilhadas entre as Tasks)
volatile int contadorPicos = 0;
volatile bool alarmeAtivo = false;
volatile bool mudouStatusAlarme = false;
volatile bool limpouContador = false;

int ultimoPicoMostrado = -1; 

WiFiClientSecure client;

void atualizarTela(String status, String detalhe, bool alerta) {
  display.clearDisplay();
  if (alerta) {
    display.setTextSize(2);
    display.setTextColor(SSD1306_BLACK, SSD1306_WHITE); 
    display.setCursor(10, 5);
    display.println("POR FAVOR");
    display.setCursor(16, 25);
    display.println("ABAIXE O");
    display.setCursor(28, 45);
    display.println("VOLUME");
  } else {
    display.setTextSize(2);
    display.setTextColor(SSD1306_WHITE); 
    display.setCursor(0, 10);
    display.println(status);
    display.setTextSize(1);
    display.setCursor(0, 40);
    display.println(detalhe);
  }
  display.display();
}

// =========================================================================
// TASK DA REDE (Roda no Core 0)
// =========================================================================
void taskRedeCode(void * pvParameters) {
  unsigned long ultimoStatusGet = millis();
  unsigned long tempoInicial = millis();
  
  for(;;) {
    // --- Obter Status do Alarme a cada 1 Segundo ---
    if (millis() - ultimoStatusGet >= 1000) {
      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String url = String(api_base_url) + "/api/esp/status/";
        http.begin(client, url);
        
        int httpCode = http.GET();
        if (httpCode > 0 && httpCode == HTTP_CODE_OK) {
          String payload = http.getString();
          StaticJsonDocument<256> doc;
          DeserializationError error = deserializeJson(doc, payload);
          if (!error && doc.containsKey("comando_alerta")) {
            bool ligar_tudo = doc["comando_alerta"].as<bool>();
            if (ligar_tudo != alarmeAtivo) {
              alarmeAtivo = ligar_tudo;
              mudouStatusAlarme = true;
            }
          }
        }
        http.end();
      }
      ultimoStatusGet = millis();
    }

    // --- Envio de Picos a cada 30 Segundos ---
    if (millis() - tempoInicial >= JANELA_TEMPO) {
      // 1. Coleta e zera rapidamente para não perder contagem no outro núcleo
      int picosParaEnviar = contadorPicos;
      contadorPicos = 0; 
      limpouContador = true;

      // 2. Faz o envio (pode demorar alguns segundos, não vai travar o sensor!)
      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String url = String(api_base_url) + "/api/esp/picos/";
        http.begin(client, url);
        http.addHeader("Content-Type", "application/json");

        StaticJsonDocument<64> doc;
        doc["picos"] = picosParaEnviar; 
        char jsonString[64];
        serializeJson(doc, jsonString);
        
        int httpCode = http.POST(jsonString);
        if (httpCode > 0) {
          Serial.printf("Dados enviados. Resposta: %d\n", httpCode);
          Serial.println("Picos enviados: " + String(picosParaEnviar));
        } else {
          Serial.printf("[HTTP] POST falhou, erro: %s\n", http.errorToString(httpCode).c_str());
        }
        http.end();
      } else {
        Serial.println("Não foi possível enviar dados: Wi-Fi desconectado.");
      }
      
      tempoInicial = millis();
    }

    // Aguarda 50ms para não consumir 100% da CPU do Core 0 e permitir tarefas do sistema (Wi-Fi)
    vTaskDelay(50 / portTICK_PERIOD_MS); 
  }
}
// =========================================================================


void setup() {
  Serial.begin(115200);
  pinMode(pinoLed, OUTPUT);
  pinMode(pinoSpeaker, OUTPUT);
  analogSetPinAttenuation(pinoAudio, ADC_0db); 
  digitalWrite(pinoLed, LOW);
  noTone(pinoSpeaker);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Falha ao iniciar SSD1306"));
    for(;;); 
  }

  atualizarTela("  Wi-Fi   ", "Ligue no Wi-Fi:\nSPC_Monitor_WiFi\nAcesse 192.168.4.1", false);
  WiFiManager wm;
  wm.setConnectTimeout(10); 
  wm.setConfigPortalTimeout(180); 
  bool res = wm.autoConnect("SPC_Monitor_WiFi");

  if(!res) {
    Serial.println("Falha ao conectar no Wi-Fi. Reiniciando...");
    ESP.restart();
  } 

  Serial.println("\nWi-Fi Conectado!");
  atualizarTela(" Wi-Fi OK ", "IP:\n" + WiFi.localIP().toString(), false);
  delay(2000); 

  // Configurar cliente HTTPS para ignorar verificação de certificado
  client.setInsecure();
  
  // Criar a Task de rede no Core 0 (O loop() padrão roda no Core 1)
  xTaskCreatePinnedToCore(
    taskRedeCode,   // Função que a task vai rodar
    "TaskRede",     // Nome da task
    10000,          // Tamanho da pilha em words
    NULL,           // Parâmetros (nenhum)
    1,              // Prioridade
    NULL,           // Handle (não precisamos)
    0               // Roda no Core 0
  );

  atualizarTela(" Monitor ", "Aguardando som...", false);
}

void loop() {
  // --- Atualizações do Display com base nas flags da Task de Rede ---
  if (mudouStatusAlarme) {
    mudouStatusAlarme = false;
    if (alarmeAtivo) {
      Serial.println(">>> ALERTA RECEBIDO: LIGANDO TUDO <<<");
      digitalWrite(pinoLed, HIGH);
      atualizarTela("", "", true); 
    } else {
      Serial.println(">>> ALERTA DESLIGADO: DESLIGANDO TUDO <<<");
      digitalWrite(pinoLed, LOW);
      noTone(pinoSpeaker);
      ultimoPicoMostrado = contadorPicos; // Força desenhar o zero
      atualizarTela(" Ambiente ", "Monitorando picos:\n" + String(contadorPicos), false);
    }
  }

  if (limpouContador) {
    limpouContador = false;
    ultimoPicoMostrado = 0;
    if (!alarmeAtivo) {
      atualizarTela(" Ambiente ", "Monitorando picos:\n0", false);
    }
  }

  // --- Comportamento do alarme sonoro ---
  if (alarmeAtivo) {
    if (millis() % 600 < 300) {
      tone(pinoSpeaker, 800); 
    } else {
      tone(pinoSpeaker, 500); 
    }
  }

  // --- Leitura contínua do microfone (50ms para achar picos) ---
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
    contadorPicos++; // Acessa variável volátil
    if (!alarmeAtivo && contadorPicos != ultimoPicoMostrado) {
      atualizarTela(" Ambiente ", "Monitorando picos:\n" + String(contadorPicos), false);
      ultimoPicoMostrado = contadorPicos; 
    }
  }
}
