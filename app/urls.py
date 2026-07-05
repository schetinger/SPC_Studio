from django.urls import path
from app.views import pagina_inicial, pagina_monitoramento, api_browser_sync, api_esp_picos, api_esp_status, api_browser_comando
from . import views
urlpatterns = [
    path('',pagina_inicial, name='home'),
    path('monitoramento/', pagina_monitoramento, name='monitoramento'),
    path('gerar-carta/',views.GeradorCEP.as_view()),
    
    # API REST
    path('api/browser/sync/', api_browser_sync, name='api_browser_sync'),
    path('api/esp/picos/', api_esp_picos, name='api_esp_picos'),
    path('api/esp/status/', api_esp_status, name='api_esp_status'),
    path('api/browser/comando/', api_browser_comando, name='api_browser_comando'),
]