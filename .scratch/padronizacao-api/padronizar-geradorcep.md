# Padronizar API GeradorCEP para consumo do novo schema JSON

Labels: `ready-for-agent`

## Parent
Nenhum

## What to build
Implementar a padronização no endpoint `GeradorCEP.post` em `views.py` para suportar nativamente a estrutura JSON fornecida (`dados1.json`, `dados2.json`, `dados3.json`):
- Tratar case-insensitivity nas chaves (aceitar `Amostras` ou `amostras`).
- Mapear `Carta` em vez de `chart` e `Amostras`/`amostras` em vez de `measurements`.
- Extrair o valor `Defeituosos` (quando existir) e passar como `regra` para a criação das cartas P e U.
- Remover chamadas de variáveis obsoletas (`especificacoes` e `intervalo_probabilidade`).
- Suportar valores de cartas como `XR`, `MRI`/`IMR`, `P`, `U`.

## Acceptance criteria
- [ ] O backend consegue ler chaves ignorando letras maiúsculas/minúsculas.
- [ ] `dados1.json` (Carta XR) é consumido e roteado para `Media_Amplitude.objects.create()`.
- [ ] `dados2.json` (Carta MRI) é consumido e roteado para `imr.objects.create()`.
- [ ] `dados3.json` (Carta P) é consumido e os "Defeituosos" são enviados como argumento `regra` para `p.objects.create(data=..., regra=...)`.
- [ ] Se houver Carta "U" com o mesmo schema do `dados3.json`, os "Defeituosos" também vão para `u.objects.create(data=..., regra=...)`.
- [ ] Nenhum erro ocorre devido à falta de `especificacoes` ou `intervalo_probabilidade`.

## Blocked by
None - can start immediately
