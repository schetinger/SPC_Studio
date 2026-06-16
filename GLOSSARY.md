# Agent Skills Glossary

Terminologia usada neste workspace de ensino sobre o sistema de agent skills (mattpocock/skills) aplicado ao projeto CEP.

## Terms

**Skill**:
Um arquivo `SKILL.md` (com recursos opcionais) que instrui um agente a executar um workflow especializado — como criar issues, rodar TDD, ou revisar código. O agente lê as instruções e as segue literalmente.
_Avoid_: plugin, comando, ferramenta genérica

**Spec**:
Uma descrição formal e suficientemente detalhada do comportamento esperado de uma feature — geralmente uma issue no GitHub com critérios de aceite claros. É o insumo que habilita um agente a trabalhar de forma autônoma.
_Avoid_: história do usuário, tarefa, ticket vago

**Skill invocation**:
O ato de chamar uma skill num agente usando um slash command (ex: `/tdd`) ou mencionando seu nome. O agente lê o `SKILL.md` e executa o processo descrito.
_Avoid_: rodar o comando, executar a skill

**Zone of proximal development**:
O escopo mínimo de aprendizado que está um passo acima do que o usuário já sabe — desafiador o suficiente para crescer, mas não tão vasto que paralise.

**Issue tracker**:
O lugar onde as specs (issues) vivem. Neste projeto: GitHub Issues do repositório `schetinger/Topicos-eletronica`.
