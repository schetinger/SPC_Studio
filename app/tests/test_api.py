from django.test import TestCase, Client, override_settings
from django.urls import reverse
import json

@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
class ApiTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_browser_sync_estado_inicial(self):
        client = Client()
        response = client.get('/api/browser/sync/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['tipo'], 'estado_inicial')
        self.assertFalse(data['led_ligado'])
        self.assertFalse(data['esp_online'])
        self.assertIsInstance(data['historico'], list)

    def test_esp_envia_ruido(self):
        # 1. ESP sends leq and lmax 10 times to complete a point
        for i in range(10):
            response = self.client.post('/api/esp/picos/', json.dumps({"leq": 65.0, "lmax": 80.0}), content_type="application/json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['ack'], True)

        # 2. Browser fetches sync and sees the new reading
        sync_resp = self.client.get('/api/browser/sync/')
        data = sync_resp.json()
        self.assertEqual(len(data['historico']), 1)
        self.assertEqual(data['historico'][0]['leq'], 65.0)
        self.assertEqual(data['historico'][0]['lmax'], 80.0)
        
        # 3. ESP should be marked online
        self.assertTrue(data['esp_online'])

    def test_esp_status_alarme(self):
        response = self.client.get('/api/esp/status/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['comando_alerta'])

    def test_browser_liga_desliga_alarme(self):
        # Ligar alarme
        resp = self.client.post('/api/browser/comando/', json.dumps({"comando": "ligar_alerta"}), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        # Verificar se o ESP32 vê ligado
        esp_resp = self.client.get('/api/esp/status/')
        self.assertTrue(esp_resp.json()['comando_alerta'])

        # Desligar alarme
        resp2 = self.client.post('/api/browser/comando/', json.dumps({"comando": "desligar_alerta"}), content_type="application/json")
        self.assertEqual(resp2.status_code, 200)

        # Verificar se o ESP32 vê desligado
        esp_resp2 = self.client.get('/api/esp/status/')
        self.assertFalse(esp_resp2.json()['comando_alerta'])

