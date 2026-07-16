#include <WiFi.h>
#include <WiFiManager.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <driver/i2s.h>
#include <math.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

const char* api_base_url = "https://spc-studio.onrender.com"; 

const int pinoLed = 2;       
const int pinoSpeaker = 23;   

// Pinos I2S (INMP441)
#define I2S_WS 15
#define I2S_SCK 14
#define I2S_SD 32

#define I2S_PORT I2S_NUM_0
#define SAMPLE_RATE 16000
#define SAMPLES_PER_BUFFER 512

const unsigned long JANELA_TEMPO = 30000; 

// Variáveis voláteis (compartilhadas entre as Tasks)
volatile float energiaAcumulada = 0;
volatile int contadorAmostras = 0;
volatile float picoMaximo_dB = -999.0;
volatile float ultimoLeq = 0.0;
volatile bool alarmeAtivo = false;
volatile bool mudouStatusAlarme = false;

// Offset para aproximar dBFS de dB SPL.
// INMP441 tem sensibilidade de -26 dBFS para 94 dB SPL. Portanto, 0 dBFS = 120 dB SPL.
const float OFFSET_DB = 120.0; 

WiFiClientSecure client;

// Variáveis para o gráfico em tempo real
#define GRAPH_WIDTH 128
uint8_t graph_data[GRAPH_WIDTH];
unsigned long ultimoUpdateGrafico = 0;
float dbspl_atual = 0.0;

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

void atualizarGraficoRealTime(float db) {
  // Move os dados para a esquerda
  for (int i = 0; i < GRAPH_WIDTH - 1; i++) {
    graph_data[i] = graph_data[i + 1];
  }
  
  // Mapeia o dB (ex: 30 a 100 dB) para a altura do gráfico (0 a 30 pixels na base da tela)
  int y = map((int)db, 30, 110, 0, 30);
  if (y < 0) y = 0;
  if (y > 30) y = 30;
  
  graph_data[GRAPH_WIDTH - 1] = y;

  display.clearDisplay();
  
  // Desenha os textos
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.print("Tempo Real:");
  display.setTextSize(2);
  display.setCursor(70, 0);
  display.print((int)db);
  display.print("dB");
  
  // Desenha o Max do ciclo
  display.setTextSize(1);
  display.setCursor(0, 15);
  display.print("Max(30s): ");
  float mx = (picoMaximo_dB > 0) ? picoMaximo_dB : 0;
  display.print(mx, 1);
  display.print("dB");

  // Desenha a linha do gráfico
  for (int i = 0; i < GRAPH_WIDTH - 1; i++) {
    // 63 é a base da tela, subtraímos y para ir pra cima
    display.drawLine(i, 63 - graph_data[i], i + 1, 63 - graph_data[i + 1], SSD1306_WHITE);
  }
  
  display.display();
}

void i2s_init() {
  const i2s_config_t i2s_config = {
    .mode = i2s_mode_t(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = SAMPLES_PER_BUFFER,
    .use_apll = false
  };

  const i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  i2s_start(I2S_PORT);
}

// =========================================================================
// TASK DA REDE (Roda no Core 0)
// =========================================================================
void taskRedeCode(void * pvParameters) {
  unsigned long ultimoStatusGet = millis();
  unsigned long tempoInicial = millis();
  
  HTTPClient httpStatus;
  bool httpStatusInit = false;
  
  for(;;) {
    // --- Obter Status do Alarme a cada 1 Segundo ---
    if (millis() - ultimoStatusGet >= 1000) {
      if (WiFi.status() == WL_CONNECTED) {
        if (!httpStatusInit) {
          httpStatus.setReuse(true);
          httpStatus.begin(client, String(api_base_url) + "/api/esp/status/");
          httpStatusInit = true;
        }
        
        int httpCode = httpStatus.GET();
        if (httpCode > 0 && httpCode == HTTP_CODE_OK) {
          String payload = httpStatus.getString();
          StaticJsonDocument<256> doc;
          DeserializationError error = deserializeJson(doc, payload);
          if (!error && doc.containsKey("comando_alerta")) {
            bool ligar_tudo = doc["comando_alerta"].as<bool>();
            if (ligar_tudo != alarmeAtivo) {
              alarmeAtivo = ligar_tudo;
              mudouStatusAlarme = true;
            }
          }
        } else if (httpCode < 0) {
          Serial.printf("[HTTP] GET falhou, erro: %s\n", httpStatus.errorToString(httpCode).c_str());
          httpStatus.end();
          httpStatusInit = false;
        }
      }
      ultimoStatusGet = millis();
    }

    // --- Envio de Picos a cada 30 Segundos ---
    if (millis() - tempoInicial >= JANELA_TEMPO) {
      // 1. Calcular Leq e Lmax e zerar
      float lmaxEnvio = picoMaximo_dB;
      float energiaMedia = 0;
      if (contadorAmostras > 0) {
          energiaMedia = energiaAcumulada / contadorAmostras;
      }
      
      float leqEnvio = 0;
      if (energiaMedia > 0) {
          float rms = sqrt(energiaMedia);
          if (rms < 1e-9) rms = 1e-9;
          float dbfs = 20.0 * log10(rms); 
          leqEnvio = dbfs + OFFSET_DB;
      }
      if (leqEnvio < 0) leqEnvio = 0;
      if (lmaxEnvio < 0) lmaxEnvio = 0;
      
      ultimoLeq = leqEnvio;
      
      // Reseta acumuladores garantindo exclusao mutua (rudimentar)
      energiaAcumulada = 0;
      contadorAmostras = 0;
      picoMaximo_dB = -999.0;
      
      // Mostrar na tela apenas se alarme desligado (agora a maior parte é em tempo real)
      if (!alarmeAtivo) {
        // atualizarTela(" Ambiente ", "Ruido (30s):\nLeq: " + String(leqEnvio, 1) + "dB\nMax: " + String(lmaxEnvio, 1) + "dB", false);
      }

      // 2. Faz o envio
      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String url = String(api_base_url) + "/api/esp/picos/";
        http.begin(client, url);
        http.addHeader("Content-Type", "application/json");

        StaticJsonDocument<128> doc;
        doc["leq"] = leqEnvio; 
        doc["lmax"] = lmaxEnvio;
        char jsonString[128];
        serializeJson(doc, jsonString);
        
        int httpCode = http.POST(jsonString);
        if (httpCode > 0) {
          Serial.printf("Dados enviados. Resposta: %d\n", httpCode);
          Serial.println("Leq: " + String(leqEnvio) + " Lmax: " + String(lmaxEnvio));
        } else {
          Serial.printf("[HTTP] POST falhou, erro: %s\n", http.errorToString(httpCode).c_str());
        }
        http.end();
      } else {
        Serial.println("Não foi possível enviar dados: Wi-Fi desconectado.");
      }
      
      tempoInicial = millis();
    }

    vTaskDelay(50 / portTICK_PERIOD_MS); 
  }
}
// =========================================================================

void setup() {
  Serial.begin(115200);
  pinMode(pinoLed, OUTPUT);
  pinMode(pinoSpeaker, OUTPUT);
  digitalWrite(pinoLed, LOW);
  noTone(pinoSpeaker);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("Falha ao iniciar SSD1306"));
    for(;;); 
  }

  i2s_init();

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

  client.setInsecure();
  
  xTaskCreatePinnedToCore(
    taskRedeCode,
    "TaskRede",
    10000,
    NULL,
    1,
    NULL,
    0
  );

  // Inicializa o array do gráfico com 0
  for (int i = 0; i < GRAPH_WIDTH; i++) {
    graph_data[i] = 0;
  }
  
  atualizarTela(" Monitor ", "Aguardando som...", false);
}

void loop() {
  // --- Atualizações do Display ---
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
      // Volta pro gráfico automaticamente no loop
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

  // --- Leitura contínua do microfone I2S (Core 1) ---
  int32_t samples[SAMPLES_PER_BUFFER];
  size_t bytes_read = 0;
  
  i2s_read(I2S_PORT, &samples, sizeof(samples), &bytes_read, portMAX_DELAY);
  
  int samples_read = bytes_read / sizeof(int32_t);
  
  if (samples_read > 0) {
    // 1. Calcular a média (DC Offset)
    float sum = 0;
    for (int i = 0; i < samples_read; i++) {
        // O valor do INMP441 é left-justified. Podemos pegar o valor float dividindo por 2^31
        sum += ((float)samples[i] / 2147483648.0f);
    }
    float mean = sum / samples_read;
    
    // 2. Calcular a energia AC (variância) removendo o DC offset
    float sum_squares = 0;
    for (int i = 0; i < samples_read; i++) {
        float sample = ((float)samples[i] / 2147483648.0f) - mean;
        sum_squares += (sample * sample);
    }
    
    float mean_square = sum_squares / samples_read;
    
    // Acumula para o Leq global (30s)
    energiaAcumulada += mean_square;
    contadorAmostras++;
    
    // Lmax desta pequena amostra (RMS)
    if (mean_square > 0) {
        float rms = sqrt(mean_square);
        if (rms < 1e-9) rms = 1e-9;
        float dbfs = 20.0 * log10(rms);
        float dbspl = dbfs + OFFSET_DB;
        
        if (dbspl > picoMaximo_dB) {
            picoMaximo_dB = dbspl;
        }
        dbspl_atual = dbspl;
    }
  }

  // --- Atualiza o Gráfico no OLED (sem travar o I2S) ---
  if (!alarmeAtivo && millis() - ultimoUpdateGrafico > 100) {
      atualizarGraficoRealTime(dbspl_atual);
      ultimoUpdateGrafico = millis();
  }
}
