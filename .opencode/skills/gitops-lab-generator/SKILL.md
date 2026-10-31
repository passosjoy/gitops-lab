# Skill: Gerador de Laboratório GitOps (Argo Rollouts + Istio)

## Descrição
Use esta skill sempre que o usuário solicitar a criação de um laboratório de engenharia de plataforma ou ambiente de testes focado em estratégias de deploy avançadas (Canary, Blue-Green) utilizando **Argo Rollouts**, roteamento de tráfego com **Istio** e automação de retornos/notificações via GitHub Actions.

## Instruções de Execução
Quando ativada, a skill deve estruturar o ambiente criando:
1. Manifestos Kubernetes para o Argo Rollout com `AnalysisTemplate` (para métricas de rollback automático).
2. Configurações de tráfego do Istio (`VirtualService` e `DestinationRule`).
3. O script utilitário em Python (`generate_lab.py`) para provisionar a árvore de diretórios automaticamente no workspace.

## Diretrizes Técnicas
- **Rolling vs Canary:** Garanta que a estratégia do Rollout defina claramente os passos de incremento de tráfego (`steps: setWeight`) e os tempos de pausa (`pause: { duration }`).
- **Resiliência:** Sempre inclua ganchos de notificação (`argo-rollouts-notification-configmap`) se o escopo envolver feedback para pipelines.