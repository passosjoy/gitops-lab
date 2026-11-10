# Laboratório Completo: GitOps com Argo Rollouts, Istio, Argo CD, GitHub Actions e Observabilidade Open Source

> Do iniciante ao avançado. Focado em **Progressive Delivery** (Canary e Blue/Green), **Service Mesh com Istio**, **GitOps com Argo CD**, **automação com GitHub Actions** e **observabilidade self-hosted com Prometheus, Grafana, Tempo e OpenTelemetry**.

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
  - [Etapa 7: Observabilidade com Prometheus, Grafana, Tempo e OpenTelemetry](#etapa-7-observabilidade-com-prometheus-grafana-tempo-e-opentelemetry)
  - [Etapa 8: Aplicar Manifestos do Laboratório](#etapa-8-aplicar-manifestos-do-laboratório)
- [10. Executando os Deploys Progressivos](#10-executando-os-deploys-progressivos)
  - [10.1 Canary com Argo Rollouts + Istio](#101-canary-com-argo-rollouts--istio)
  - [10.2 Blue/Green com Argo Rollouts + Istio](#102-bluegreen-com-argo-rollouts--istio)
- [11. Validação, Rollback e Troubleshooting](#11-validação-rollback-e-troubleshooting)
- [12. Checklist de Segurança (Repo + Branch + Deploy)](#12-checklist-de-segurança-repo--branch--deploy)
- [13. Notificações, DORA Metrics e Policy as Code](#13-notificações-dora-metrics-e-policy-as-code)
- [14. Deploy na OCI (Always Free) com Terraform e Pipelines](#14-deploy-na-oci-always-free-com-terraform-e-pipelines)
- [15. Dicas para Evoluir o Laboratório](#15-dicas-para-evoluir-o-laboratório)
- [16. Referências](#16-referências)

## 1. Objetivo

Este laboratório tem como objetivo ensinar, na prática, como implementar um fluxo **GitOps** com **Progressive Delivery** utilizando:

- **[Argo CD](https://argo-cd.readthedocs.io/)** - Sincronização Git -> Cluster Kubernetes.
- **[Argo Rollouts](https://argo-rollouts.readthedocs.io/)** - Estratégias avançadas de deploy (Canary, Blue/Green, análise e promoção automatizada/manual).
- **[Istio](https://istio.io/latest/docs/)** - Service Mesh para roteamento inteligente de tráfego, observabilidade e resiliência.
- **[GitHub Actions](https://docs.github.com/pt/actions)** - Automação, callbacks de rollout e integração com o fluxo GitOps.
- **[OpenTelemetry](https://opentelemetry.io/)** - Instrumentação padronizada de traces e correlação com logs.
- **[Prometheus](https://prometheus.io/)** + **[Grafana](https://grafana.com/)** - Métricas, alertas e dashboards self-hosted, sem custo por host.
- **[Grafana Tempo](https://grafana.com/oss/tempo/)** - Backend de traces compatível com OTLP.
- **[Argo Rollouts Analysis](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)** - Validação automática do canary com queries Prometheus.

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
                                                      │ /metrics + OTLP
                                                      ▼
                                        ┌────────────────────────────────┐
                                        │  Observability (namespace)      │
                                        │   Prometheus ◄── Pushgateway    │
                                        │   Grafana    ◄── Tempo          │
                                        │   OTel Collector ──► Tempo      │
                                        └───────────────┬────────────────┘
                                                        │ AnalysisTemplate
                                                        ▼
                                                ┌─────────────────┐
                                                │  Argo Rollouts  │  (rollback automático)
                                                └────────┬────────┘
                                                         │ eventos
                                                         ▼
                                                ┌─────────────────┐
                                                │ Slack / Teams   │
                                                │ GitHub Actions  │  (DORA lead time)
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

O arquivo `.github/workflows/retorno.yml` já foi criado/atualizado neste repositório. Ele escuta os eventos:

```yaml
on:
  repository_dispatch:
    types: [rollout-completed, rollout-aborted]
```

Ele recebe `client_payload` com informações como `sha`, `rollout`, `namespace`. Isso permite rastrear **qual commit** gerou aquele rollout e calcular o **Lead Time for Changes** (commit -> rollout concluído), publicado no Pushgateway.

### 6.3 Conectando Argo Rollouts ao GitHub Actions

Existem duas abordagens comuns:

#### A) Argo Rollouts Notifications (recomendada neste lab)

O Argo Rollouts possui o módulo **Notifications**. Neste repositório ele está configurado em `gitops-lab-argo-istio/manifests/notifications/argo-rollouts-notifications.yaml` para enviar eventos ao **Slack**.

- **Trigger**: `on-rollout-completed`, `on-rollout-aborted`
- **Template**: mensagem com rollout, namespace, phase e imagem
- **Service**: `service.slack` com token lido do Secret `argo-rollouts-notification-secret`

O mesmo módulo pode enviar para **Teams** via `service.webhook` ou para a API do GitHub (`repository_dispatch`). O workflow `.github/workflows/retorno.yml` continua sendo o ponto de integração com CI e com o Pushgateway de DORA metrics.

#### B) CI/CD via GitHub Actions chamando `kubectl argo rollouts`

Você também pode orquestrar com GitHub Actions usando `kubectl` + plugin `argo-rollouts` e promover/abortar manualmente com gates.

**Neste laboratório, utilizaremos a abordagem A (Notifications) + B (visão prática via CLI) para fins didáticos.**

### 6.4 Segredos Necessários

Crie os seguintes **Secrets** no GitHub (`Settings > Secrets and variables > Actions`):

| Secret / Variable | Obrigatório | Descrição |
|---|---|---|
| `GITHUB_TOKEN` | Sim (padrão) | Já disponível. Usado para `repository_dispatch`. |
| `ARGOCD_AUTH_TOKEN` / `KUBE_CONFIG` | Opcional | Caso queira promover via GitHub Actions diretamente. |
| `SLACK_WEBHOOK_URL` (Secret) | Opcional | Fallback de notificação no workflow. O canal principal é o Argo Rollouts Notifications. |
| `PUSHGATEWAY_URL` (Variable) | Opcional | URL pública do Pushgateway para publicar o Lead Time. Ex.: `https://pushgateway.example.com`. |
| `GH_PAT` | Opcional | Caso precise de permissões mais amplas para dispatch entre repos. |

No **cluster**, crie os Secrets (nunca no Git):

| Secret Kubernetes | Namespace | Uso |
|---|---|---|
| `grafana-admin` (`admin-user`, `admin-password`) | `observability` | Login do Grafana. |
| `argo-rollouts-notification-secret` (`slack-token`) | `argo-rollouts` | Token do Slack Bot usado pelo Notifications. |

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
| **Conta SaaS de observabilidade** | Não necessária | A stack é self-hosted: Prometheus, Grafana, Tempo e OTel Collector rodam no cluster. |

## 8. Estrutura do Repositório

Após a geração, sua estrutura ficará similar a esta:

```text
gitops/
├── .github/
│   └── workflows/
│       ├── policy-check.yaml          # Kyverno + Conftest no CI
│       └── retorno.yml                # Callback + DORA lead time
├── .opencode/
│   └── skills/                        # Skill de SRE/DevOps sênior (operação, observabilidade, troubleshooting)        
│       ├── SKILL.md
│       └── references/                # Kubernetes, Lambda, observabilidade, infra/GitOps, playbooks
├── gitops-lab-argo-istio/
│   ├── argocd/                        # Argo CD Application (crie/ajuste)
│   ├── manifests/
│   │   ├── analysis/
│   │   │   └── analysistemplate-prometheus.yaml
│   │   ├── app/
│   │   │   └── src/                   # Código Flask + Dockerfile
│   │   ├── istio/
│   │   │   └── virtualservice.yaml
│   │   ├── notifications/
│   │   │   └── argo-rollouts-notifications.yaml
│   │   ├── observability/
│   │   │   ├── grafana-dashboard-dora.yaml
│   │   │   ├── otel-collector.yaml
│   │   │   ├── prometheus-rules-dora.yaml
│   │   │   ├── scrape-configs.yaml
│   │   │   └── tempo.yaml
│   │   └── rollouts/
│   │       └── rollout.yaml
│   └── values/
│       └── kube-prometheus-stack-values.yaml
├── policy/
│   ├── conftest/
│   │   └── kubernetes.rego
│   └── kyverno/
│       ├── disallow-latest-tag.yaml
│       ├── disallow-privileged.yaml
│       ├── require-labels.yaml
│       └── require-resources.yaml
└── termos.md                          # Termos e conceitos importantes
└── README.md                          # Este arquivo

```

> A aplicação em `manifests/app/src/` expõe métricas em `/metrics` e envia traces via OTLP. Os manifestos base (Deployment/Service/ConfigMap da aplicação) podem ser adicionados em `manifests/app/`; o `Rollout` é quem **gerencia as revisões** e o tráfego.

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

#### Opção B: ConfigMap + Secret do repositório

O arquivo `gitops-lab-argo-istio/manifests/notifications/argo-rollouts-notifications.yaml` já contém o `ConfigMap` completo com **Slack** e **GitHub `repository_dispatch`**. Falta apenas criar o Secret com os tokens (nunca commitar):

```bash
kubectl -n argo-rollouts create secret generic argo-rollouts-notification-secret \
  --from-literal=slack-token="$SLACK_BOT_TOKEN" \
  --from-literal=github-token="$GH_PAT" \
  --dry-run=client -o yaml | kubectl apply -f -
```

Aplique o `ConfigMap` e ajuste `SEU-USUARIO/SEU-REPO` nos templates `github-*`:

```bash
kubectl apply -f gitops-lab-argo-istio/manifests/notifications/argo-rollouts-notifications.yaml
```

O `ConfigMap` define:

- `service.slack` e `service.webhook.github` (tokens lidos de `$slack-token` / `$github-token`);
- templates `rollout-completed`, `rollout-aborted`, `github-completed`, `github-aborted`;
- triggers separados por serviço (`on-rollout-completed-slack`, `on-rollout-aborted-slack`, `on-rollout-completed-github`, `on-rollout-aborted-github`).

O `Rollout` então se inscreve nos triggers por anotação:

```yaml
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-rollout-completed-slack.slack: sre-rollouts
    notifications.argoproj.io/subscribe.on-rollout-aborted-slack.slack: sre-rollouts
    notifications.argoproj.io/subscribe.on-rollout-completed-github.github: dora
    notifications.argoproj.io/subscribe.on-rollout-aborted-github.github: dora
    github-sha: "0000000000000000000000000000000000000000"  # preenchido pelo CI
```

> A anotação `github-sha` é o que permite ao workflow `.github/workflows/retorno.yml` calcular o **Lead Time for Changes** (commit → rollout concluído). Sem ela o evento chega, mas o lead time é ignorado.

### Etapa 7: Observabilidade com Prometheus, Grafana, Tempo e OpenTelemetry

A stack é **self-hosted** e não depende de nenhum SaaS. Componentes:

| Componente | Papel |
|---|---|
| OpenTelemetry SDK | Instrumenta a aplicação (traces + correlação de logs). |
| OTel Collector | Recebe OTLP e encaminha para o Tempo. |
| Prometheus + Operator | Coleta métricas via `PodMonitor`/`ServiceMonitor` e avalia regras DORA. |
| Pushgateway | Recebe o lead time publicado pelo GitHub Actions. |
| Tempo | Armazena traces. |
| Grafana | Dashboards (DORA, latência, erros) e datasource Tempo. |
| Alertmanager | Roteia alertas (ex.: `RolloutDegraded`). |

#### Passo 1: Instalar a stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -

kubectl -n observability create secret generic grafana-admin \
  --from-literal=admin-user=admin \
  --from-literal=admin-password="$GRAFANA_ADMIN_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -n observability \
  --values gitops-lab-argo-istio/values/kube-prometheus-stack-values.yaml
```

#### Passo 2: Aplicar Tempo, Collector, scrape configs, regras e dashboard

```bash
kubectl apply -f gitops-lab-argo-istio/manifests/observability/
```

Isso cria `tempo`, `otel-collector`, `PodMonitor`/`ServiceMonitor` (app, Collector, Argo CD, Argo Rollouts), `PrometheusRule` de DORA e o dashboard `DORA Metrics - GitOps Lab` (provisionado automaticamente pelo sidecar do Grafana).

#### Passo 3: Instrumentação da aplicação

A aplicação em `manifests/app/src/` já está pronta:

- `observability.py` configura o SDK OTel (OTLP HTTP), JSON logs com `trace_id`/`span_id` e métricas `prometheus_client` em modo multiprocess;
- `index.py` usa `@traced("...")` e `tracer.start_as_current_span(...)` no lugar do `ddtrace`;
- `/metrics` expõe `oficina_http_requests_total`, `oficina_http_requests_good_total`, `oficina_http_request_duration_milliseconds_bucket` e `oficina_http_errors_total`, todas com label `service`.

Variáveis relevantes no `Rollout`:

```yaml
env:
  - name: OTEL_SERVICE_NAME
    value: oficina-lanternagem-do-rasta
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: http://otel-collector.observability.svc.cluster.local:4318
  - name: PROMETHEUS_MULTIPROC_DIR
    value: /tmp/prometheus-multiproc
```

#### Passo 4: Análise automática do canary

O `manifests/analysis/analysistemplate-prometheus.yaml` consulta o Prometheus diretamente:

```yaml
provider:
  prometheus:
    address: http://kube-prometheus-stack-prometheus.observability.svc.cluster.local:9090
    query: |
      sum(rate(oficina_http_requests_good_total{service="{{args.service-name}}"}[2m]))
      /
      clamp_min(sum(rate(oficina_http_requests_total{service="{{args.service-name}}"}[2m])), 0.0001)
```

O `Rollout` referencia o template com `analysis.templates[].templateName: app-success-rate` e `startingStep: 1`.

#### Passo 5: Acessar Grafana

```bash
kubectl -n observability port-forward svc/kube-prometheus-stack-grafana 3000:80
# http://localhost:3000  (admin / $GRAFANA_ADMIN_PASSWORD)
```

Dashboards esperados: **DORA Metrics - GitOps Lab**, **Kubernetes / Compute Resources**, e o datasource **Tempo** para abrir traces a partir dos logs (via `trace_id`).

**Métricas úteis para análise:** `error rate`, `p50/p95/p99 latency`, `request rate`, `5xx` e as séries `dora:*` (Deployment Frequency, Change Failure Rate, Lead Time, MTTR).

### Etapa 8: Aplicar Manifestos do Laboratório

Antes de aplicar, **revise e ajuste** os arquivos:

- `manifests/rollouts/rollout.yaml` — ajuste `image`, `replicas`, `steps`, `analysis` e a anotação `github-sha`.
- `manifests/istio/virtualservice.yaml` — ajuste `hosts`, `gateways` e o nome da rota (`primary` deve casar com `strategy.canary.trafficRouting.istio.virtualService.routes`).
- `manifests/analysis/analysistemplate-prometheus.yaml` — ajuste `service-name` e os thresholds (99% de sucesso, p95 < 500 ms).
- `manifests/observability/` — scrape configs e regras DORA.
- `values/kube-prometheus-stack-values.yaml` — retenção, recursos e Pushgateway.

Aplicação via Argo CD (recomendado):

```bash
# Commit e push
git add .
git commit -m "feat: GitOps com Argo Rollouts + Istio + observabilidade open source"
git push origin main
```

Argo CD irá sincronizar automaticamente. Acompanhe pelo UI ou CLI:

```bash
argocd app get gitops-lab-app
argocd app sync gitops-lab-app
```

## 10. Executando os Deploys Progressivos

### 10.1 Canary com Argo Rollouts + Istio

**Cenário:** Lançar `v2.0.0` com exposição gradual, validando com `AnalysisTemplate` (Prometheus) a cada etapa.

#### Passo 1: Atualizar imagem

Edite `gitops-lab-argo-istio/manifests/rollouts/canary/rollout-canary.yaml`:

```yaml
containers:
  - name: web
    image: ghcr.io/seu-org/oficina-lanternagem:v2.0.0  # <-- nova versão
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
3. `analysis` -> Executa query Prometheus. Se falhar (abaixo do threshold) ou exceder `failureLimit` -> **aborta** e volta 100% para stable
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
    image: ghcr.io/seu-org/oficina-lanternagem:v2.0.0
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
| **Analysis falha sempre** | Query Prometheus errada, Prometheus inacessível ou serviço sem tráfego | Testar a query no Prometheus/Grafana. Garantir `/metrics` disponível e `PodMonitor` aplicado. Ver `kubectl describe analysisrun -n gitops-lab`. |
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

- [ ] **Análises com métricas reais** (Prometheus) antes de aumentar peso
- [ ] **`failureLimit`** definido para abortar automaticamente
- [ ] **`autoPromotionEnabled: false`** em PROD para Blue/Green (promover com critério)
- [ ] **Pausas com tempo suficiente** para coleta de métricas
- [ ] **Rollback testado** em ambiente DEV/HML
- [ ] **Histórico/versionamento** via Git (tudo auditável)
- [ ] **Notificações integradas** com GitHub Actions para visibilidade

## 13. Notificações, DORA Metrics e Policy as Code

### 13.1 Notificações (Slack/Teams + GitHub)

- **Argo Rollouts Notifications**: `gitops-lab-argo-istio/manifests/notifications/argo-rollouts-notifications.yaml` configura `service.slack` e `service.webhook.github` (tokens via Secret `argo-rollouts-notification-secret` em `argo-rollouts`, nunca no Git).
- **Triggers**: rollout `Healthy`/`Degraded` envia mensagem ao Slack e dispara `repository_dispatch` (`rollout-completed`/`rollout-aborted`) para o GitHub.
- **Callback CI**: `.github/workflows/retorno.yml` registra o evento e publica o *Lead Time for Changes* no Pushgateway (quando `PUSHGATEWAY_URL` e `github-sha` estão disponíveis). Teams pode ser integrado via webhook/Teams connector no mesmo padrão do Slack.

Anote o SHA no Rollout (pipeline/kustomize): `metadata.annotations.github-sha: <commit>`.

### 13.2 DORA Metrics (Prometheus + Grafana)

| Métrica | Fonte | Implementação |
|---|---|---|
| **Deployment Frequency** | Argo CD | `argocd_app_sync_total{phase="Succeeded"}` |
| **Change Failure Rate** | Argo CD | falhas/erros sobre total de syncs (24h) |
| **Lead Time for Changes** | GitHub Actions + Pushgateway | `dora_lead_time_seconds` publicado por `retorno.yml`; Prometheus calcula p50/p90 |
| **MTTR** | Argo Rollouts | tempo em `rollout_info{phase="Degraded"}` / incidentes (aproximação em `prometheus-rules-dora.yaml`) |

- Regras: `gitops-lab-argo-istio/manifests/observability/prometheus-rules-dora.yaml`
- Dashboard: `gitops-lab-argo-istio/manifests/observability/grafana-dashboard-dora.yaml` (Grafana sidecar)
- Scrape de Argo CD/Rollouts/App: `gitops-lab-argo-istio/manifests/observability/scrape-configs.yaml`

### 13.3 Policy as Code (Kyverno + OPA/Conftest)

- **Kyverno** (`policy/kyverno/`): `disallow-latest-tag`, `require-labels`, `require-resources`, `disallow-privileged` (Rollouts no namespace `gitops-lab`).
- **Conftest/Rego** (`policy/conftest/kubernetes.rego`): validações equivalentes via OPA.
- **CI**: `.github/workflows/policy-check.yaml` executa `kyverno-cli` e `conftest` em PR/push nos manifests/policies.

## 14. Deploy na OCI com Terraform e Pipelines (sequencial)

### 14.1 Opções de execução

| Opção | Quando usar | Observação |
|---|---|---|
| **VM OCI Always Free** (A1.Flex **4 OCPU / 24 GB**, total tenancy) | Pós-trial ou custo zero | Terraform `create_compute=true`; deploy rápido via `docker compose` (`deploy/oci/docker-compose.yml`). k3s+Istio+stack completa em nó único é possível, mas pesado. |
| **OKE (trial/créditos)** | Stack GitOps completa (Argo CD/Rollouts/Istio/observabilidade) | Até **4.500h compute OKE** e **500 GB OCIR** no trial (conforme informado). Terraform suporta `create_oke=true` com node pool **A1.Flex onde disponível**. Monitore consumo; após trial, volte ao Always Free/ajuste. |
| **GHCR ou OCIR** | Registry de imagem | GHCR já configurado (`ghcr.io/<owner>/<repo>/app:<sha>`). OCIR pode ser adicionado; requer secrets de OCIR no workflow de build. |

### 14.2 Pipeline CI/CD sequencial (principal)

Workflow: `.github/workflows/ci-cd.yml` (manual `workflow_dispatch` e `push` em `main`).

Ordem **sequencial**:
1. **01 Policy Check** — `.github/workflows/policy-check.yaml` (Kyverno CLI + Conftest/OPA). **Mantido/necessário**: gate shift-left antes de build/deploy; evita promover manifests inválidos.
2. **02 Build & Push** — `.github/workflows/build-and-push.yml` (imagem GHCR). Depende do policy.
3. **03 Deploy Infra** — `.github/workflows/deploy-infra.yml` (Terraform `fmt/init/validate` sempre; `plan/apply` quando credenciais OCI existem). Roda em `workflow_dispatch`; `apply` usa Environment `oci-infra` (aprovação recomendada).
4. **04 Deploy App** — `.github/workflows/deploy-oci.yml` (SSH na VM OCI: `compose` ou `k8s` básico). Roda só quando `deploy_app=true` no dispatch e destino SSH está configurado.

**`retorno.yml` (Callback DORA)** — `.github/workflows/retorno.yml` é **mantido/necessário**, mas **não entra na sequência de deploy**: é disparado por **`repository_dispatch`** do Argo Rollouts Notifications quando o rollout completa/aborta no cluster (evento assíncrono de runtime). Ele publica **Lead Time for Changes** no Pushgateway (DORA) e atua como fallback Slack. O canal principal de notificação continua sendo o Argo Rollouts Notifications.

### 14.3 Configuração no GitHub (variáveis/secrets)

Veja o mapeamento completo em **`docs/github-actions-config.md`**.

Resumo mínimo para deploy real:
- **Infra (Terraform OCI API key):** `OCI_TENANCY_OCID`, `OCI_USER_OCID`, `OCI_FINGERPRINT`, `OCI_PRIVATE_KEY`, `OCI_REGION`, `TF_VAR_SSH_PUBLIC_KEY`, `TF_VAR_ADMIN_CIDR`, `TF_VAR_PARENT_COMPARTMENT_OCID` (secrets/vars conforme sensibilidade).
- **Flags (vars):** `TF_VAR_CREATE_OKE`, `TF_VAR_CREATE_COMPUTE`, `TF_VAR_COMPUTE_*`, `TF_VAR_OKE_*` etc.
- **Deploy app (SSH):** `OCI_HOST`, `OCI_SSH_PRIVATE_KEY`, opcional `OCI_SSH_USER`, `GHCR_PULL_TOKEN`.
- **DORA/callback:** `PUSHGATEWAY_URL` (var), `SLACK_WEBHOOK_URL` (secret).

> Neste workspace não é possível configurar secrets do seu repositório GitHub nem executar deploy real contra sua tenancy OCI; os workflows foram preparados para **validar** (Terraform fmt/init/validate) e **pular com aviso** quando credenciais/destino não existem.

### 14.4 Processo de deploy do laboratório (ponta a ponta)

1. **Código/manifest alterado** → PR/push aciona policy/build conforme paths (ou pipeline sequencial no dispatch).
2. **Policy Check** valida manifests com Kyverno e Conftest (OPA). Falha = bloqueia sequência.
3. **Build & Push** gera imagem `ghcr.io/<owner>/<repo>/app:<sha>` e publica no GHCR.
4. **Deploy Infra (Terraform)** provisiona/atualiza OCI (compartment, VCN/NSGs, VM A1 Always Free e/ou OKE com A1 flex, storage, observabilidade OCI, etc.). **Ordem lógica no pipeline:** infra após build da imagem e antes do deploy da aplicação (para haver alvo pronto quando a app é implantada). *Observação: o cluster/VM precisa existir e estar acessível; `apply` é manual/aprovado.*
5. **Deploy App**:
   - **Modo `compose` (VM OCI):** copia `deploy/oci/*` via SSH e executa `docker compose` com a nova imagem (app + Postgres + OTel). Caminho mais simples no Always Free.
   - **Modo `k8s` (básico via SSH):** aplica manifests base no host com `kubectl` (ex.: k3s). **GitOps completo (recomendado com OKE/Argo CD):** a pipeline de build atualiza a tag no Git/manifest (ou Image Updater) e o **Argo CD** sincroniza; o **Argo Rollouts** faz canary/análise via Istio/Prometheus.
6. **Progressive delivery (cluster):** Argo Rollouts promove/aborta; em sucesso/falha envia Slack e `repository_dispatch` ao GitHub.
7. **Callback DORA:** `retorno.yml` recebe o dispatch, calcula lead time (commit → rollout concluído) e publica no Pushgateway para Prometheus/Grafana.

### 14.5 “Redmine” e passos manuais

- **Redmine:** não foi encontrado artefato/configuração "redmine" neste repositório (busca por `*redmine*`). Nenhuma etapa de Redmine foi removida; se a referência for a um sistema externo, ela permanece **manual/fora do repo**.
- **Automatizado pelas pipelines (quando configuradas):** validação de policies, build/push de imagem, Terraform fmt/init/validate/plan/apply, deploy compose/SSH da app, callback DORA.
- **Ainda manual (não removido, pois depende de credenciais/ambiente real):** configurar credenciais OCI e **Secrets/Variables no GitHub**; criar/ajustar `terraform.tfvars` local (sem commitar) se rodar Terraform fora do Actions; substituir placeholders `SEU-USUARIO/SEU-REPO`/repoURL; criar Secrets Kubernetes (`app-secret`, tokens de notificação Argo Rollouts, etc.); instalar stack completa no cluster quando usar OKE/k3s GitOps (Argo CD/Rollouts/Istio/Prometheus/Grafana/Tempo) — pode ser automatizado depois com Helm/Terraform adicional; configurar DNS/TLS/ingress externo; ajustar `admin_cidr`/acesso SSH para runners (self-hosted runner/OCI DevOps recomendado); revisão de segurança antes de produção.

## 15. Dicas para Evoluir o Laboratório

| Evolução | Descrição | Prioridade |
|---|---|---|
| **Prometheus + Analysis** | Já implementado em `manifests/analysis/analysistemplate-prometheus.yaml` com validação automática de canary | Alta |
| **Flagger** | Comparar Flagger vs Argo Rollouts para entender trade-offs | Média-Alta |
| **Sealed Secrets / External Secrets** | Gerenciar secrets sem expor no Git | **Alta (produção)** |
| **Kustomize/Helm** | Tornar manifests reutilizáveis por ambiente (overlays `dev/hml/prod`) | Alta |
| **Slack/Teams Notifications** | Enviar status de rollout para canal de engenharia | Média |
| **OpenTelemetry** | Já implementado: SDK, Collector, envio OTLP para Tempo, correlação de logs com `trace_id`/`span_id` | Média-Alta |
| **Chaos Engineering** | Testar resiliência com Litmus/ChaosMesh durante Canary | Avançado |
| **Policy as Code** | Validar manifests com OPA Conftest/Kyverno | Avançado |

## 16. Referências

- [Argo CD Documentation](https://argo-cd.readthedocs.io/)
- [Argo Rollouts Documentation](https://argo-rollouts.readthedocs.io/)
- [Istio Documentation](https://istio.io/latest/docs/)
- [Istio Traffic Management](https://istio.io/latest/docs/concepts/traffic-management/)
- [GitHub Actions - repository_dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event)
- [GitHub Docs - Branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Grafana Tempo](https://grafana.com/docs/tempo/)
- [OpenTelemetry](https://opentelemetry.io/docs/)
- [Argo Rollouts Analysis](https://argo-rollouts.readthedocs.io/en/stable/features/analysis/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)

---

**Autor:** Laboratório GitOps Argo + Istio + Prometheus/Grafana/Tempo/OpenTelemetry  
**Foco:** Aprendizado prático do básico ao avançado com ênfase em **segurança, observabilidade self-hosted e governança Git**  
**Status:** Pronto para execução no cluster configurado.
