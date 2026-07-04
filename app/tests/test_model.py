import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cep.settings')
django.setup()

import json
from app.models import Media_Amplitude

with open('../data/dados1.json', 'r') as f:
    payload = json.load(f)

# Pega apenas a chave Amostras, ou converte o payload para minúsculo como na API
data_lower = {k.lower(): v for k, v in payload.items()}
amostras = data_lower.get("amostras", {})

try:
    obj = Media_Amplitude.objects.create(data=amostras)
    print("Sucesso! ID:", obj.id)
except Exception as e:
    import traceback
    traceback.print_exc()
