## What to build
Atualizar os relatórios das cartas XR e IMR (backend e templates HTML) para recalcular e exibir as novas exigências de probabilidade e capacidade do processo. As alterações envolvem tanto o `models.py` (cálculo) quanto o `RelatorioXr.html` e `RelatorioIMR.html` (exibição).

## Acceptance criteria
- [ ] Modificar `is_capaz` no `models.py` para retornar um dicionário indicando as avaliações de curto e longo prazo.
- [ ] Exibir o motivo de curto prazo (geralmente relacionado à Regra 1).
- [ ] Exibir o motivo de reprovação a longo prazo com a frase exata estipulada no plano: `Longo prazo: ppm obtido < ppm requerido onde o pmm requerido é 990`.
- [ ] Injetar o cálculo da probabilidade binomial na renderização (n=50, k=45, p=probabilidade da peça dentro dos limites LSE/LIE).
- [ ] Exibir a margem de sucesso simulando um deslocamento de +1 sigma na média.
- [ ] Remover exibição das variáveis obsoletas relacionadas a intervalo de probabilidade (`x0`, `x1`, `menor_x1`, etc).

## Blocked by
None - can start immediately
