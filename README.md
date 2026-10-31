# Laboratório Completo: GitOps com Argo Rollouts, Istio, Argo CD, GitHub Actions e Datadog

> Do iniciante ao avançado. Focado em **Progressive Delivery** (Canary e Blue/Green), **Service Mesh com Istio**, **GitOps com Argo CD**, **automação com GitHub Actions** e **observabilidade com Datadog**.

## Índice

- [1. Objetivo](#1-objetivo)
- [2. Conceitos Fundamentais](#2-conceitos-fundamentais)
  - [2.1 O que é GitOps?](#21-o-que-é-gitops)
  - [2.2 Service Mesh e Istio](#22-service-mesh-e-istio)
  - [2.3 Argo CD vs Argo Rollouts](#23-argo-cd-vs-argo-rollouts)
  - [2.4 Progressive Delivery](#24-progressive-delivery)
- [3. Estratégias de Deploy: Comparação](#3-estratégias-de-deploy-comparação)
- [4. Arquitetura do Laboratório](#4-arquitetura-do-laboratório)
- [5. Estratégia de Branches, Ambientes e Proteções](#5-estratégia-de-branches-ambientes-e-proteções)
  - [5.1 Mapeamento Branch x Ambiente](#51-mapeamento-branch-x-ambiente)
  - [5.2 Proteção de Branches (Branch Protection Rules)](#52-proteção-de-branches-branch-protection-rules)
  - [5.3 Proteção do Repositório (Regras Gerais)](#53-proteção-do-repositório-regras-gerais)
  - [5.4 Recomendações para GitHub Rulesets](#54-recomendações-para-github-rulesets)
- [6. Integração com GitHub Actions](#6-integração-com-github-actions)
  - [6.1 Por que usar `repository_dispatch`?](#61-por-que-usar-repository_dispatch)
  - [6.2 Workflow de Callback](#62-workflow-de-callback)
  - [6.3 Conectando Argo Rollouts ao GitHub Actions](#63-conectando-argo-rollouts-ao-github-actions)
  - [6.4 Segredos Necessários](#64-segredos-necessários)
- [7. Pré-requisitos](#7-pré-requisitos)
- [8. Estrutura do Repositório](#8-estrutura-do-repositório)
- [9. Passo a Passo: Do Zero ao Avançado](#9-passo-a-passo-do-zero-ao-avançado)
  - [Etapa 1: Instalar Argo CD](#etapa-1-instalar-argo-cd)
  - [Etapa 2: Instalar Argo Rollouts](#etapa-2-instalar-argo-rollouts)
  - [Etapa 3: Instalar e Configurar Istio](#etapa-3-instalar-e-configurar-istio)
  - [Etapa 4: Preparar Namespace e Injeção Sidecar](#etapa-4-preparar-namespace-e-injeção-sidecar)
  - [Etapa 5: Configurar Argo CD Application](#etapa-5-configurar-argo-cd-application)
  - [Etapa 6: Habilitar Notificações Argo Rollouts + GitHub](#etapa-6-habilitar-notificações-argo-rollouts--github)
  - [Etapa 7: Integrar com Datadog (Observabilidade)](#etapa-7-integrar-com-datadog-observabilidade)
  - [Etapa 8: Aplicar Manifestos do Laboratório](#etapa-8-aplicar-manifestos-do-laboratório)
- [10. Executando os Deploys Progressivos](#10-executando-os-deploys-progressivos)
  - [10.1 Canary com Argo Rollouts + Istio](#101-canary-com-argo-rollouts--istio)
  - [10.2 Blue/Green com Argo Rollouts + Istio](#102-bluegreen-com-argo-rollouts--istio)
- [11. Validação, Rollback e Troubleshooting](#11-validação-rollback-e-troubleshooting)
- [12. Checklist de Segurança (Repo + Branch + Deploy)](#12-checklist-de-segurança-repo--branch--deploy)
- [13. Dicas para Evoluir o Laboratório](#13-dicas-para-evoluir-o-laboratório)
- [14. Referências](#14-referências)

## 1. Objetivo

Este laboratório tem como objetivo ensinar, na prática, como implementar um fluxo **GitOps** com **Progressive Delivery** utilizando:

- **[Argo CD](https://argo-cd.readthedocs.io/)** - Sincronização Git -> Cluster Kubernetes.
- **[Argo Rollouts](https://argo-rollouts.readthedocs.io/)** - Estratégias avançadas de deploy (Canary, Blue/Green, análise e promoção automatizada/manual).
- **[Istio](https://istio.io/latest/docs/)** - Service Mesh para roteamento inteligente de tráfego, observabilidade e resiliência.
- **[GitHub Actions](https://docs.github.com/pt/actions)** - Automação, callbacks de rollout e integração com o fluxo GitOps.
- **[Datadog](https://docs.datadoghq.com/)** - Métricas, APM, logs e validação de saúde da aplicação durante o progressive delivery.

A ideia é ir **do conceito ao deploy real**, entendendo o "porquê" de cada etapa.

## 2. Conceitos Fundamentais

### 2.1 O que é GitOps?

**GitOps** é uma abordagem operacional onde o **estado desejado** da sua infraestrutura e aplicações é versionado em um repositório Git. Um agente (ex: Argo CD) monitora esse repositório e garante que o cluster esteja sempre em conformidade com o que está declarado no Git.

**Princípios chave:**

- **Declarativo**: Tudo é descrito como código (YAML).
- **Versionado e imutável**: Histórico, auditoria e rollbacks via Git.
- **Automatizado**: Sincronização contínua entre Git e cluster.
- **Reconciliado**: O operador corrige drift (diferenças) entre estado desejado e atual.

### 2.2 Service Mesh e Istio

**Service Mesh** é uma camada de infraestrutura dedicada para gerenciar comunicação service-to-service de forma confiável, segura e observável, sem alterar o código da aplicação.

**Istio** é um dos service meshes mais utilizados. Ele funciona com um **data plane** (Envoy sidecars injetados nos pods) e um **control plane** (istiod) responsável por roteamento, políticas, mTLS, telemetria, etc.

**Principais conceitos no laboratório:**

| Conceito | Explicação |
|---|---|
| **Sidecar (Envoy)** | Proxy injetado em cada pod. Intercepta todo o tráfego de entrada/saída da aplicação. |
| **VirtualService** | Define regras de roteamento HTTP/TCP com base em peso, headers, URI etc. Fundamental para dividir tráfego entre versões (Canary). |
| **DestinationRule** | Define **subsets** (grupos) de pods com base em labels. Usado para distinguir `stable` x `canary`. |
| **Gateway** | Configura como o tráfego externo entra no mesh (Ingress Gateway). |
| **ServiceEntry** | Permite comunicação com serviços externos fora do cluster. |
| **mTLS** | Criptografia automática entre serviços dentro do mesh (segurança por padrão). |

> **Por que usar Istio com Argo Rollouts?** Porque o Argo Rollouts precisa **controlar o peso do tráfego** entre as revisões. Com Istio, conseguimos fazer isso de forma granular via `VirtualService`/`DestinationRule`, sem depender apenas do balanceamento do Service do Kubernetes.

### 2.3 Argo CD vs Argo Rollouts

| Ferramenta | Função | Quando usar |
|---|---|---|
| **Argo CD** | GitOps Controller. Sincroniza manifests (Deployments, Services, ConfigMaps) do Git para o cluster. | Gerenciar o **estado desejado** geral da aplicação e dos manifests. |
| **Argo Rollouts** | Progressive Delivery Controller. Substitui/estende o `Deployment` com estratégias `Canary` e `Blue/Green`, com **pausas, análises e promoção**. | Controlar **como** a nova versão vai receber tráfego com segurança e rollback automatizado. |

**Imagem mental:** Argo CD "publica" o `Rollout` no cluster. Argo Rollouts "orquestra" a transição entre versões com base em regras, tempo e métricas.

### 2.4 Progressive Delivery

Diferente de um "deploy tudo ou nada", **Progressive Delivery** permite expor a nova versão para um pequeno percentual de usuários, validar com métricas/observabilidade e aumentar gradualmente, ou promover/descartar com segurança.

## 3. Estratégias de Deploy: Comparação

| Estratégia | Descrição | Tempo de exposição | Risco | Rollback | Observações |
|---|---|---|---|---|---|
| **Recreate** | Derruba todos os pods antigos e sobe os novos. Downtime esperado. | 0% -> 100% instantâneo | **Alto** | Lento (redeploy versão anterior) | Simples, mas não recomendado para produção. |
| **RollingUpdate (nativo K8s)** | Substitui pods gradualmente, mantendo disponibilidade. | Gradual via `maxUnavailable`/`maxSurge` | Médio | Relativamente rápido, mas menos controlado | Padrão do Kubernetes. Ótimo para maioria dos casos simples. |
| **Canary** | Direciona uma **pequena fatia de tráfego** (ex: 5%, 20%, 50%) para a nova versão. Monitora e aumenta aos poucos. | Controlado por pesos (`setWeight`) | **Baixo** | Rápido (voltar pesos para 0 ou abortar) | Ideal com métricas + Service Mesh (Istio). Muito usado em produção. |
| **Blue/Green** | Cria ambiente **Green** (nova versão) em paralelo. Mantém **Blue** (atual) ativo. Após validação, **troca** todo o tráfego de uma vez para Green. | 0% -> 100% na promoção | Baixo (se validado antes) | Extremamente rápido (voltar para Blue) | Ótimo quando você quer **validação completa** antes de expor a todos. Consome mais recursos temporariamente. |
| **A/B Testing** | Direciona tráfego com base em **regras de negócio** (headers, cookies, geolocalização, etc). | Baseado em critério | Baixo | Rápido | Mais voltado a **experimentação/feature flagging** do que apenas "deploy". |
| **Shadow (Mirroring)** | Replica o tráfego real para a nova versão **sem responder ao usuário**. Apenas observa. | 0% visível ao usuário | **Mínimo** | Imediato | Excelente para **validação de carga/latência/erros** sem impacto. |

> **Neste laboratório focaremos em Canary e Blue/Green com Argo Rollouts + Istio.**

## 4. Arquitetura do Laboratório

```text
┌─────────────────┐   Git Push/PR   ┌─────────────────────┐
│ Desenvolvedor   │ ──────────────► │ GitHub Repository    │
└─────────────────┘                 │ (manifests + app)    │
                                    └──────────┬──────────┘
                                               │ (sync)
                                               ▼
                                        ┌─────────────┐
                                        │   Argo CD    │  (GitOps)
                                        └─────┬───────┘
                                              │ Aplica Rollouts/VS/DR
                                              ▼
                                        ┌─────────────────────────────────────────┐
                                        │                Kubernetes                │
                                        │  ┌─────────────┐   ┌──────────────────┐  │
                                        │  │ Argo Rollouts│   │ Istio Service Mesh│  │
                                        │  │ Controller   │   │ (istiod + Envoy) │  │
                                        │  └─────────────┘   └──────────────────┘  │
                                        │           │                    │        │
                                        │           ▼                    ▼        │
                                        │      Rollout(Canary/BlueGreen) <-> VS/DR │
                                        └─────────────┬───────────────────────────┘
                                                      │ Métricas/Traces/Logs
                                                      ▼
                                                   ┌────────┐
                                                   │ Datadog │ (Observabilidade + Analysis)
                                                   └────────┘
                                                      │ eventos
                                                      ▼
                                                ┌─────────────────┐
                                                │ GitHub Actions   │ (repository_dispatch)
                                                │ retorno-rollout  │ (notificações/integração)
                                                └─────────────────┘
```

## 5. Estratégia de Branches, Ambientes e Proteções

### 5.1 Mapeamento Branch x Ambiente

Para manter **isolamento, rastreabilidade e segurança**, adote este mapeamento:

| Branch | Ambiente | Propósito | Regras |
|---|---|---|---|
| `develop` | **DEV** | Integração contínua de features. Deploy automático/sincronizado para cluster DEV. | PR obrigatório. Testes básicos. Ideal para validação rápida. |
| `release/*` ou `homolog` | **HML/HOMOLOG** | Pré-produção. Valida integração end-to-end, performance e regras de negócio. | PR obrigatório + revisão. Usado para validação com stakeholders. |
| `main` (ou `master`) | **PROD** | Produção. Única fonte confiável para releases aprovados. | **Altamente protegido**. Mínimo 2 aprovações, checks obrigatórios, sem force push. |
| `feature/*` | **Local/PR Preview** | Desenvolvimento isolado. Nunca direto em `develop/main`. | Criar via PR para `develop`. |

**Fluxo sugerido:** `feature/nova-funcionalidade` → `develop` (DEV) → `release/v1.x` ou `homolog` (HML) → `main` (PROD)

### 5.2 Proteção de Branches (Branch Protection Rules)

Acesse: `Settings > Branches > Branch protection rules > Add rule`

Configure por branch crítico:

| Configuração | `develop` | `homolog/release/*` | `main` | Justificativa |
|---|---|---|---|---|
| **Require a pull request before merging** | ✅ | ✅ | ✅ | Evita pushes diretos. |
| **Require approvals** | 1 | 1-2 | **2** | Revisão por pares. |
| **Dismiss stale pull request approvals when new commits are pushed** | ✅ | ✅ | ✅ | Garante revisão com código atualizado. |
| **Require review from Code Owners** | Opcional | Recomendado | **Altamente recomendado** | Obriga revisão de responsáveis técnicos. |
| **Require status checks to pass before merging** | ✅ | ✅ | ✅ | Garante CI (lint, build, testes) ok. |
| **Require branches to be up to date before merging** | ✅ | ✅ | ✅ | Evita merge com código desatualizado. |
| **Require conversation resolution** | ✅ | ✅ | ✅ | Exige resolução de comentários. |
| **Require signed commits** | Opcional | Opcional | **Recomendado** | Maior rastreabilidade/autenticidade. |
| **Require linear history** | Opcional | Opcional | Recomendado | Histórico mais limpo. |
| **Do not allow bypassing the above settings** | Opcional | ✅ | **✅** | Impede bypass mesmo por admins (em times maduros). |
| **Restrict who can push to matching branches** | ❌ (via PR) | Restrito | **Restrito** | Ninguém deve commitar direto em `main`. |
| **Allow force pushes** | ❌ | ❌ | **❌** | Nunca permitir em branches protegidas. |
| **Allow deletions** | ❌ | ❌ | **❌** | Evita deleção acidental. |

### 5.3 Proteção do Repositório (Regras Gerais)

Em `Settings > General`:

- **Default branch**: manter `main` como branch padrão.
- **Require contributors to sign off on web-based commits**: avaliar conforme política da empresa.
- **Disable forking**: apenas se repositório for estritamente interno.
- **Rules for pull requests**: seguir seção 5.2.

Em `Settings > Security`:

- **Dependabot alerts**: Ativar.
- **Dependabot security updates**: Ativar.
- **Secret scanning**: Ativar (GitHub Advanced Security ou nativo conforme plano).
- **Push protection**: **Ativar** (bloqueia commit com secrets expostos).

### 5.4 Recomendações para GitHub Rulesets

Se seu repositório tiver acesso a **Rulesets** (`Settings > Rules > Rulesets`), prefira usá-los ao invés (ou em conjunto) com Branch Protection Rules. Vantagens:

- Regras por **grupos de branches** (`refs/heads/main`, `refs/heads/develop`, `refs/heads/release/**`).
- Aplicação mais granular por **equipe/role**.
- Melhor controle para organizações.
- Suporte a **bypass lists** bem definidos.

**Regras mínimas para PROD (`main`):**

- `Restrict creations`, `Restrict updates`, `Restrict deletions`
- `Require pull request` (min approvals, dismiss stale, require review)
- `Require status checks` (CI/GitOps validation)
- `Block force pushes`

## 6. Integração com GitHub Actions

### 6.1 Por que usar `repository_dispatch`?

O `repository_dispatch` permite **disparar workflows remotamente** via API do GitHub. É perfeito para integrar **Argo Rollouts** com **GitHub Actions**:

- Ao finalizar um step, pausar para análise ou promover/abortar um `Rollout`.
- Notificar times via PR/Issue/Slack/Teams.
- Registrar histórico de promoção/rollback.
- Acionar jobs de validação pós-deploy.

### 6.2 Workflow de Callback

O arquivo `.github/workflows/retorno-rollout.yml` já foi criado/atualizado neste repositório. Ele escuta os eventos:

```yaml
on:
  repository_dispatch:
    types: [rollout-completed, rollout-aborted, rollout-paused]
```

Ele recebe `client_payload` com informações como `sha`, `rollout`, `namespace`. Isso permite rastrear **qual commit** gerou aquele rollout.

### 6.3 Conectando Argo Rollouts ao GitHub Actions

Existem duas abordagens comuns:

#### A) Argo Rollouts Notifications (recomendada neste lab)

O Argo Rollouts possui o módulo **Notifications**. Você pode configurar para enviar eventos via **webhook** para a API do GitHub `repository_dispatch`.

Exemplo conceitual (configurar via `ConfigMap`/`Secret`):

- **Trigger**: `on-rollout-completed`, `on-rollout-aborted`, `on-analysis-run-failed`
- **Template**: Monta JSON com `event_type` e `client_payload`
- **Service**: Webhook apontando para `https://api.github.com/repos/<ORG>/<REPO>/dispatches` com `Authorization: Bearer <GITHUB_TOKEN>`

#### B) CI/CD via GitHub Actions chamando `kubectl argo rollouts`

Você também pode orquestrar com GitHub Actions usando `kubectl` + plugin `argo-rollouts` e promover/abortar manualmente com gates.

**Neste laboratório, utilizaremos a abordagem A (Notifications) + B (visão prática via CLI) para fins didáticos.**

### 6.4 Segredos Necessários

Crie os seguintes **Secrets** no GitHub (`Settings > Secrets and variables > Actions`):

| Secret | Obrigatório | Descrição |
|---|---|---|
| `GITHUB_TOKEN` | Sim (padrão) | Já disponível. Usado para `repository_dispatch`. |
| `ARGOCD_AUTH_TOKEN` / `KUBE_CONFIG` | Opcional | Caso queira promover via GitHub Actions diretamente. |
| `DATADOG_API_KEY` / `DATADOG_APP_KEY` | Sim (se usar Analysis com Datadog) | Usados pelo Argo Rollouts AnalysisTemplate/provider Datadog. |
| `GH_PAT` | Opcional | Caso precise de permissões mais amplas para dispatch entre repos. |

> **Nunca commitar secrets no repositório. Use apenas Secrets/External Secrets/Vault.**

## 7. Pré-requisitos

Antes de iniciar, garanta que você possui:

| Componente | Versão Sugerida | Notas |
|---|---|---|
| **Kubernetes Cluster** | 1.28+ | Pode ser local (Kind/Minikube/K3d) ou remoto. |
| **kubectl** | Compatível com cluster | Configurado com acesso ao cluster. |
| **Helm** | 3.x | Para instalação facilitada. |
| **istioctl** | 1.22+ | Para gerenciar Istio. |
| **Argo CD CLI** (`argocd`) | Última estável | Opcional, mas prático. |
| **Argo Rollouts Plugin** | Última estável | `kubectl argo rollouts` para inspecionar/promover/abortar. |
| **Git** | 2.x | Para versionar e commitar. |
| **Conta GitHub** | Com permissão para editar Actions/Settings | Necessário para proteções e workflows. |
| **Conta Datadog** | Com API/App Keys | Necessário para `AnalysisTemplate` com Datadog. |

## 8. Estrutura do Repositório

Após a geração, sua estrutura ficará similar a esta:

```text
gitops/
├── .github/
│   └── workflows/
│       └── retorno-rollout.yml        # Callback GitHub Actions
├── .opencode/
│   └── skills/
│       └── gitops-lab-generator/      # Skill para gerar laboratórios
├── gitops-lab-argo-istio/
│   ├── argocd/
│   │   └── application.yaml          # ArgoCD Application
│   ├── manifests/
│   │   ├── analysis/
│   │   │   └── analysistemplate-datadog.yaml
│   │   ├── app/                      # Services, ConfigMaps, etc (app já orquestrada c/ Datadog)
│   │   ├── istio/
│   │   │   └── virtualservice-destinationrule.yaml
│   │   └── rollouts/
│   │       ├── bluegreen/
│   │       │   └── rollout-bluegreen.yaml
│   │       └── canary/
│   │           └── rollout-canary.yaml
│   └── docs/                         # Espaço para anotações futuras
└── README.md                         # Este arquivo
```

> A sua aplicação já foi copiada/orquestrada com **Datadog**. Coloque os manifestos da aplicação em `gitops-lab-argo-istio/manifests/app/` (Deployment base, Service, ServiceAccount, etc). Os `Rollout` irão **gerenciar as revisões** (muitas vezes substituindo/estendendo a lógica do Deployment para Progressive Delivery).

## 9. Passo a Passo: Do Zero ao Avançado

### Etapa 1: Instalar Argo CD

```bash
# Criar namespace
kubectl create namespace argocd

# Instalar Argo CD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Aguardar pods ficarem prontos
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

# Expor UI (para lab local)
kubectl port-forward svc/argocd-server -n argocd 8080:443 &
```

**Obter senha inicial:**

```bash
# Linux/Mac
argocd admin initial-password -n argocd

# Ou via kubectl
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d && echo
```

Acesse: [https://localhost:8080](https://localhost:8080) (usuário: `admin`)

### Etapa 2: Instalar Argo Rollouts

```bash
# Criar namespace
kubectl create namespace argo-rollouts

# Instalar controller + CRDs
kubectl apply -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# Instalar plugin kubectl (opcional mas MUITO recomendado)
# Linux
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-linux-amd64
chmod +x kubectl-argo-rollouts-linux-amd64
sudo mv kubectl-argo-rollouts-linux-amd64 /usr/local/bin/kubectl-argo-rollouts

# Verificar
kubectl argo rollouts version
```

### Etapa 3: Instalar e Configurar Istio

```bash
# Download istioctl (ajuste versão conforme necessário)
curl -L https://istio.io/downloadIstio | sh -
cd istio-*/
export PATH=$PWD/bin:$PATH
istioctl version

# Instalar perfil demo (ideal para laboratório)
istioctl install --set profile=demo -y

# Verificar
kubectl get pods -n istio-system
```

**Conceitos prontos no cluster:** `istiod`, `istio-ingressgateway`, `istio-egressgateway`.

### Etapa 4: Preparar Namespace e Injeção Sidecar

```bash
# Criar namespace do laboratório
kubectl create namespace gitops-lab

# Habilitar injeção automática de sidecar Envoy
kubectl label namespace gitops-lab istio-injection=enabled

# Verificar label
kubectl get namespace gitops-lab --show-labels
```

> Com `istio-injection=enabled`, todo pod criado nesse namespace receberá o **sidecar Envoy** automaticamente.

### Etapa 5: Configurar Argo CD Application

Edite `gitops-lab-argo-istio/argocd/application.yaml` e ajuste:

```yaml
source:
  repoURL: https://github.com/SEU-USUARIO/SEU-REPO.git  # <-- ALTERAR
  targetRevision: main                                # ou develop/homolog conforme ambiente
  path: gitops-lab-argo-istio/manifests              # sincroniza todos manifests
```

Aplique a Application no Argo CD:

```bash
kubectl apply -f gitops-lab-argo-istio/argocd/application.yaml
```

No UI do Argo CD você verá a app `gitops-lab-app`. Com `automated: { prune: true, selfHeal: true }`, qualquer alteração commitada no Git será reconciliada automaticamente.

### Etapa 6: Habilitar Notificações Argo Rollouts + GitHub

O Argo Rollouts Notifications precisa ser configurado. Existem 2 caminhos:

#### Opção A: Instalar via manifests oficiais (recomendado)

```bash
# Aplicar notificações (se não vierem com install padrão, verificar docs)
kubectl apply -n argo-rollouts -f https://raw.githubusercontent.com/argoproj/argo-rollouts/master/manifests/notifications-install.yaml
```

#### Opção B: Configurar ConfigMap + Secret

Crie um Secret com o token para GitHub:

```bash
# Gere um PAT (classic) com scope "repo" ou use GITHUB_TOKEN com cuidado
kubectl create secret generic github-token \
  --from-literal=token=ghp_SEU_PERSONAL_ACCESS_TOKEN \
  -n argo-rollouts
```

Crie/edite `argo-rollouts-notification-configmap` com:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: argo-rollouts-notification-configmap
  namespace: argo-rollouts
data:
  service.webhook.github: |
    url: https://api.github.com
    headers:
    - name: Authorization
      value: Bearer $github-token
    - name: Accept
      value: application/vnd.github+json
  template.github-dispatch: |
    webhook:
      github:
        method: POST
        path: /repos/SEU-USUARIO/SEU-REPO/dispatches
        body: |
          {
            "event_type": "{{.rollout.metadata.annotations.notifications.argoproj.io/github-event-type}}",
            "client_payload": {
              "rollout": "{{.rollout.metadata.name}}",
              "namespace": "{{.rollout.metadata.namespace}}",
              "sha": "{{.rollout.metadata.annotations.github-sha}}",
              "status": "{{.rollout.status.phase}}"
            }
          }
  trigger.on-rollout-completed: |
    - when: rollout.status.phase == 'Healthy'
      send: [github-dispatch]
      oncePer: rollout.status.observedGeneration
  trigger.on-rollout-aborted: |
    - when: rollout.status.phase == 'Degraded'
      send: [github-dispatch]
      oncePer: rollout.status.observedGeneration
```

Adicione anotações ao seu `Rollout` para disparar:

```yaml
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-rollout-completed.github: "rollout-completed"
    notifications.argoproj.io/subscribe.on-rollout-aborted.github: "rollout-aborted"
```

> Ajuste `event_type` para bater com os tipos definidos no `.github/workflows/retorno-rollout.yml` (`rollout-completed`, `rollout-aborted`, `rollout-paused`).

### Etapa 7: Integrar com Datadog (Observabilidade)

Como sua aplicação já está orquestrada com **Datadog**, garanta:

1. **Datadog Agent** instalado no cluster (DaemonSet) com APM habilitado.
2. **Labels/annotations** corretas nos pods (ex: `tags.datadoghq.com/service`, `tags.datadoghq.com/env`, `tags.datadoghq.com/version`).
3. **APM Tracing** habilitado na aplicação.
4. **Logs** sendo coletados (pode usar `ad.datadoghq.com/*` annotations).
5. **API Key + APP Key** criados no Datadog (`Organization Settings > API Keys / Application Keys`).

Edite `manifests/analysis/analysistemplate-datadog.yaml` com sua query real. Exemplo genérico:

```yaml
query: |
  (sum:trace.servlet.request.hits{service:{{args.service-name}},env:lab} - 
   sum:trace.servlet.request.errors{service:{{args.service-name}},env:lab}) /
  sum:trace.servlet.request.hits{service:{{args.service-name}},env:lab} * 100
```

**Importante:** O provider `datadog` no Argo Rollouts Analysis precisa ter acesso às credenciais. Configure `secret`/env para o controller ou siga a documentação oficial conforme sua versão.

**Métricas úteis para análise:** `error rate`, `p50/p90/p99 latency`, `apdex`, `request rate`, `5xx`.

### Etapa 8: Aplicar Manifestos do Laboratório

Antes de aplicar, **revise e ajuste** os arquivos:

- `manifests/app/` - Coloque seus manifests reais da aplicação (Services, etc). Garanta que o Service baterá com o que o Rollout espera.
- `manifests/istio/virtualservice-destinationrule.yaml` - Ajuste `hosts`, `gateways`, `subsets` e labels para casar com seu `Rollout`.
- `manifests/rollouts/canary/rollout-canary.yaml` - Ajuste `image`, `replicas`, `steps`, `analysis`.
- `manifests/rollouts/bluegreen/rollout-bluegreen.yaml` - Ajuste `activeService`, `previewService`, gates.

Aplicação via Argo CD (recomendado):

```bash
# Commit e push
git add .
git commit -m "feat: adiciona laboratório GitOps Argo Rollouts + Istio + Datadog"
git push origin main
```

Argo CD irá sincronizar automaticamente. Acompanhe pelo UI ou CLI:

```bash
argocd app get gitops-lab-app
argocd app sync gitops-lab-app
```

## 10. Executando os Deploys Progressivos

### 10.1 Canary com Argo Rollouts + Istio

**Cenário:** Lançar `v2.0.0` com exposição gradual, validando com `AnalysisTemplate` (Datadog) a cada etapa.

#### Passo 1: Atualizar imagem

Edite `gitops-lab-argo-istio/manifests/rollouts/canary/rollout-canary.yaml`:

```yaml
containers:
  - name: web
    image: ghcr.io/seu-org/minha-aplicacao:v2.0.0  # <-- nova versão
```

Commit e push:

```bash
git add manifests/rollouts/canary/rollout-canary.yaml
git commit -m "deploy: canary v2.0.0"
git push origin main
```

Argo CD sincroniza e o **Argo Rollouts** inicia o Canary.

#### Passo 2: Acompanhar o rollout

```bash
# Ver status em tempo real
kubectl argo rollouts get rollout app-canary -n gitops-lab --watch

# Ver detalhes
kubectl argo rollouts describe rollout app-canary -n gitops-lab

# Dashboard (opcional)
kubectl argo rollouts dashboard
```

#### Passo 3: Entendendo os passos

Com a configuração atual:

1. `setWeight: 5` -> 5% do tráfego para canary
2. `pause: 2m` -> Aguarda tempo para análise/observação
3. `analysis` -> Executa query Datadog. Se falhar (abaixo do threshold) ou exceder `failureLimit` -> **aborta** e volta 100% para stable
4. `setWeight: 20` -> Aumenta gradualmente
5. Continua até `setWeight: 100` e finaliza como **Healthy**

#### Passo 4: Promover ou Abortar manualmente

```bash
# Promover próximo step manualmente (se pause sem duração ou em modo manual)
kubectl argo rollouts promote app-canary -n gitops-lab

# Abortar e fazer rollback para versão estável
kubectl argo rollouts abort app-canary -n gitops-lab

# Retomar após correção (raro em fluxo automático)
kubectl argo rollouts retry rollout app-canary -n gitops-lab

# Ver histórico de revisões
kubectl argo rollouts history rollout app-canary -n gitops-lab
```

**Validação com Istio:** Os pesos são aplicados no `VirtualService`. Você verá o tráfego sendo dividido entre `stable` e `canary` conforme os steps.

### 10.2 Blue/Green com Argo Rollouts + Istio

**Cenário:** Criar versão **Preview (Green)**, validar com análise, e **trocar** todo o tráfego para ela com um clique (`promote`).

#### Passo 1: Atualizar imagem Blue/Green

Edite `gitops-lab-argo-istio/manifests/rollouts/bluegreen/rollout-bluegreen.yaml`:

```yaml
containers:
  - name: web
    image: ghcr.io/seu-org/minha-aplicacao:v2.0.0
```

Commit e push:

```bash
git add manifests/rollouts/bluegreen/rollout-bluegreen.yaml
git commit -m "deploy: bluegreen v2.0.0"
git push origin main
```

#### Passo 2: Entendendo o fluxo

Com `autoPromotionEnabled: false`:

1. **Argo Rollouts** cria o ReplicaSet **Preview** (Green) com a nova imagem.
2. Executa **`prePromotionAnalysis`** (validação antes de trocar tráfego).
3. Fica em **Paused** aguardando promoção manual.
4. Ao promover, todo o tráfego vai para **Green** (`preview` passa a ser `active`).
5. Após promoção, roda **`postPromotionAnalysis`** (validação pós-troca).
6. Com `scaleDownDelaySeconds: 30`, o **Blue** antigo é escalado para 0 após delay (mantido por segurança para rollback rápido).

#### Passo 3: Promover ou Fazer Rollback

```bash
# Acompanhar
kubectl argo rollouts get rollout app-bluegreen -n gitops-lab --watch

# Validar preview (testar diretamente via service preview antes de promover)
kubectl get svc app-preview -n gitops-lab

# PROMOVER: trocar tráfego Blue -> Green
kubectl argo rollouts promote app-bluegreen -n gitops-lab

# ABORTAR: descartar Green e manter Blue
kubectl argo rollouts abort app-bluegreen -n gitops-lab
```

**Dica prática:** Teste o `app-preview` internamente (port-forward/curl via pod teste) antes de promover. É uma das grandes vantagens do Blue/Green.

## 11. Validação, Rollback e Troubleshooting

### Comandos Úteis

```bash
# Ver todos os rollouts
kubectl get rollouts -n gitops-lab

# Ver ReplicaSets gerenciados
kubectl get rs -n gitops-lab

# Ver VirtualService/DestinationRule
kubectl get vs,dr -n gitops-lab

# Logs do Argo Rollouts controller
kubectl logs -n argo-rollouts -l app.kubernetes.io/name=argo-rollouts -f

# Logs do Argo CD
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller -f

# Logs do Istiod
kubectl logs -n istio-system -l app=istiod -f

# Ver análises em execução
kubectl get analysisrun -n gitops-lab
```

### Troubleshooting Comum

| Problema | Possível Causa | Solução |
|---|---|---|
| **Rollout travado em "Progressing"** | Falta `VirtualService`/`DestinationRule` ou labels errados | Verificar `trafficRouting.istio`, subsets e labels dos pods. |
| **Analysis falha sempre** | Query Datadog errada, chaves ausentes ou serviço sem tráfego | Testar query no Datadog. Garantir que há hits/erros no intervalo. Ver logs do analysisrun. |
| **Sidecar não injetado** | Namespace sem label `istio-injection=enabled` | `kubectl label ns gitops-lab istio-injection=enabled` e recriar pods. |
| **Argo CD fora de sync** | Caminho errado ou repo privado sem credenciais | Verificar `repoURL`, `path` e credenciais em `Settings > Repositories`. |
| **GitHub Actions não dispara** | Erro na config de notificações/webhook ou token inválido | Validar `ConfigMap`, Secret `github-token`, permissões do PAT e logs do controller. |
| **Tráfego não divide** | Istio não roteando ou Gateway/hosts incorretos | Conferir `VirtualService.http.route.weight`, `DestinationRule.subsets`. Testar via `curl` com headers/hosts. |

### Rollback Rápido

**Canary:** `kubectl argo rollouts abort <rollout> -n gitops-lab` (volta todo tráfego para stable imediatamente)

**Blue/Green:** `kubectl argo rollouts abort <rollout> -n gitops-lab` (mantém Blue ativo)

**GitOps puro:** Reverter o commit no Git (`git revert`) -> Argo CD sincroniza e Argo Rollouts aplica estado anterior.

## 12. Checklist de Segurança (Repo + Branch + Deploy)

### Repositório GitHub

- [ ] **Branch protection** configurado em `main`, `develop`, `homolog/release/*`
- [ ] **Require PR reviews** com número mínimo de aprovações
- [ ] **Status checks obrigatórios** (CI/lint/test/validate manifests)
- [ ] **Force push e delete desabilitados** em branches protegidas
- [ ] **Secret scanning + Push protection** ativos
- [ ] **Dependabot alerts/updates** ativos
- [ ] **CODEOWNERS** criado (`.github/CODEOWNERS`) para arquivos críticos (`manifests/`, `argocd/`)
- [ ] **Sem secrets hardcoded** (usar GitHub Secrets/Sealed Secrets/External Secrets)

### Kubernetes/Cluster

- [ ] **RBAC mínimo** para Argo CD/Argo Rollouts
- [ ] **Namespaces isolados** por ambiente
- [ ] **Istio mTLS** habilitado (avaliar `STRICT` vs `PERMISSIVE` conforme maturidade)
- [ ] **NetworkPolicies** considerados (restrição entre namespaces)
- [ ] **Resource Requests/Limits** em todos os containers
- [ ] **Probes** (`readiness/liveness/startup`) configurados
- [ ] **ImagePullPolicy** adequado + imagens de registry confiável

### GitOps/Progressive Delivery

- [ ] **Análises com métricas reais** (Datadog/Prometheus) antes de aumentar peso
- [ ] **`failureLimit`** definido para abortar automaticamente
- [ ] **`autoPromotionEnabled: false`** em PROD para Blue/Green (promover com critério)
- [ ] **Pausas com tempo suficiente** para coleta de métricas
- [ ] **Rollback testado** em ambiente DEV/HML
- [ ] **Histórico/versionamento** via Git (tudo auditável)
- [ ] **Notificações integradas** com GitHub Actions para visibilidade

## 13. Dicas para Evoluir o Laboratório

| Evolução | Descrição | Prioridade |
|---|---|---|
| **Prometheus + Analysis** | Trocar/substituir por `AnalysisTemplate` com Prometheus (complementar ao Datadog) | Alta |
| **Flagger** | Comparar Flagger vs Argo Rollouts para entender trade-offs | Média-Alta |
| **Sealed Secrets / External Secrets** | Gerenciar secrets sem expor no Git | **Alta (produção)** |
| **Kustomize/Helm** | Tornar manifests reutilizáveis por ambiente (overlays `dev/hml/prod`) | Alta |
| **Slack/Teams Notifications** | Enviar status de rollout para canal de engenharia | Média |
| **OpenTelemetry** | Padronizar traces e correlacionar com Datadog | Média-Alta |
| **Chaos Engineering** | Testar resiliência com Litmus/ChaosMesh durante Canary | Avançado |
| **Policy as Code** | Validar manifests com OPA Conftest/Kyverno | Avançado |

## 14. Referências

- [Argo CD Documentation](https://argo-cd.readthedocs.io/)
- [Argo Rollouts Documentation](https://argo-rollouts.readthedocs.io/)
- [Istio Documentation](https://istio.io/latest/docs/)
- [Istio Traffic Management](https://istio.io/latest/docs/concepts/traffic-management/)
- [GitHub Actions - repository_dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [GitHub Docs - Branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Datadog APM](https://docs.datadoghq.com/tracing/)
- [CNCF GitOps Principles](https://opengitops.dev/)
- [Progressive Delivery](https://www.weave.works/blog/what-is-progressive-delivery-all-about)

---

**Autor:** Laboratório GitOps Argo + Istio + Datadog  
**Foco:** Aprendizado prático do básico ao avançado com ênfase em **segurança, observabilidade e governança Git**  
**Status:** Pronto para execução no cluster configurado.
