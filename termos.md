# Glossário de Termos - GitOps Lab

## 1. GitOps & CI/CD

| Termo | Significado | Explicação |
|---|---|---|
| **GitOps** | Operações baseadas em Git | Modelo onde o Git é a *única fonte da verdade*. O estado desejado do cluster fica versionado e é aplicado automaticamente por um agente (ex: Argo CD). |
| **Push-based** | CI empurra para o cluster | O GitHub Actions faz `kubectl apply`, `helm upgrade` ou algo similar direto no Kubernetes. Mais comum em CI/CD tradicional. |
| **Pull-based** | Agente puxa do Git | O Argo CD/Argo Rollouts fica "observando" o repositório e puxa as mudanças para aplicá-las no cluster. É o modelo GitOps puro. |
| **Build & Push** | Construir e publicar imagem | Etapa onde o Dockerfile é buildado, a imagem recebe uma tag (geralmente o `SHA` do commit) e é enviada para um *Container Registry* (GHCR, ECR, Docker Hub). |
| **Container Registry** | Repositório de imagens | Local onde ficam as imagens Docker prontas para serem baixadas pelos nós do Kubernetes. Ex.: `ghcr.io`, `registry.hub.docker.com`. |
| **repository_dispatch** | Webhook do GitHub Actions | Permite que ferramentas externas (como Argo Rollouts) disparem um workflow no GitHub via API. Usado aqui para o *callback* pós-rollout. |

## 2. Argo CD, Argo Rollouts & Progressive Delivery

| Termo | Significado | Explicação |
|---|---|---|
| **Argo CD** | GitOps Controller | Ferramenta responsável por sincronizar os manifests do Git com o cluster Kubernetes. Garante que o cluster esteja exatamente no estado definido no repositório. |
| **Argo Rollouts** | Progressive Delivery Controller | Extensão do Kubernetes para fazer deploys graduais. Suporta **Canary**, **Blue/Green**, pausas, análises automáticas e rollback. |
| **Application (Argo CD)** | Recurso CRD | Define a ligação entre repositório Git, caminho (`path`), branch (`targetRevision`), cluster e namespace de destino. Fica no namespace `argocd`. |
| **Rollout** | Substituto do Deployment | Ao invés de um `Deployment` comum, usamos um `Rollout`. Ele controla a troca gradual de versões, tráfego e validações com `AnalysisTemplate`. |
| **Canary** | Deploy gradual | A nova versão recebe uma pequena porcentagem de tráfego (ex: 10%, 50%) e, se passar nas análises, vai aumentando até 100%. |
| **Blue/Green** | Duas versões em paralelo | Mantém a versão **Blue** (ativa) e cria a **Green** (preview). Após validação, todo o tráfego é trocado de uma vez com `promote`. Permite rollback rápido. |
| **AnalysisTemplate** | Modelo de validação | Define quais métricas serão consultadas (Prometheus, Datadog, etc) e quais condições precisam ser atendidas para aprovar ou abortar o rollout. |
| **AnalysisRun** | Execução da análise | Instância gerada pelo Argo Rollouts ao rodar um `AnalysisTemplate`. Mostra o resultado de cada consulta e se passou/falhou. |
| **Promote / Abort / Retry** | Ações manuais | `promote` avança o rollout manualmente. `abort` interrompe e volta para a versão estável. `retry` tenta retomar caso tenha pausado. |

## 3. Service Mesh com Istio

| Termo | Significado | Explicação |
|---|---|---|
| **Service Mesh** | Malha de serviços | Camada dedicada para gerenciar tráfego, segurança, observabilidade e resiliência entre microserviços, sem alterar o código da aplicação. |
| **Istio** | Implementação de Service Mesh | Um dos mais usados. Adiciona proxies `Envoy` aos pods para controlar e monitorar todo o tráfego entre serviços. |
| **Sidecar (Envoy)** | Proxy injetado | Container `istio-proxy` adicionado ao pod via injeção automática. Ele intercepta todo o tráfego de entrada/saída da aplicação. |
| **VirtualService** | Regras de roteamento | Define como o tráfego deve ser dividido. No nosso lab, é usado pelo Argo Rollouts para dividir entre `stable` e `canary` por peso. |
| **DestinationRule** | Configuração de destino | Complementa o `VirtualService`. Define *subsets* (grupos de pods por versão/label), balanceamento e políticas de conexão. |
| **mTLS** | Criptografia mútua | Garante que todo tráfego entre serviços dentro da malha seja criptografado e autenticado. Muito recomendado em ambientes mais restritivos. |
| **istio-injection** | Injeção de sidecar | Ao adicionar a label `istio-injection: enabled` no namespace, o Istio injeta o sidecar automaticamente em todos os novos pods. |

## 4. Observabilidade, OpenTelemetry & DORA Metrics

| Termo | Significado | Explicação |
|---|---|---|
| **Observabilidade** | Capacidade de entender o sistema | Permite responder "por que isso está acontecendo?" através de **métricas**, **logs** e **traces**. |
| **Prometheus** | Coleta e consulta de métricas | Banco de séries temporais. Coleta métricas via HTTP (`/metrics`), armazena e permite consultas com **PromQL**. |
| **Grafana** | Visualização de dados | Cria dashboards interativos a partir do Prometheus, Tempo e outras fontes. No lab temos o dashboard **DORA Metrics - GitOps Lab**. |
| **OpenTelemetry (OTel)** | Padrão de instrumentação | Framework vendor-neutral para gerar **traces**, **métricas** e **logs**. Evita ficar preso a um único provedor (como era o caso do Datadog). |
| **OTel Collector** | Agregador de telemetria | Recebe dados no formato OTLP, processa e encaminha para backends como **Grafana Tempo**. Centraliza a coleta. |
| **Grafana Tempo** | Armazenamento de traces | Backend leve e eficiente para armazenar *distributed traces*. Permite seguir uma requisição do início ao fim entre serviços. |
| **trace_id / span_id** | Identificadores de rastreio | Usados para correlacionar **logs** com **traces**. Permite clicar num log e ir direto para o trace correspondente no Grafana. |
| **Pushgateway** | Coleta de métricas pontuais | Diferente do Prometheus (que faz *pull*), o Pushgateway recebe métricas enviadas via `push` (ex: do GitHub Actions) para depois serem raspadas. |
| **DORA Metrics** | Métricas de performance DevOps | Criadas pelo Google DORA. Medem velocidade e estabilidade das entregas com base em dados reais. |

### As 4 Métricas DORA

| Métrica | Nome Completo | Explicação | Objetivo |
|---|---|---|---|
| **DF** | *Deployment Frequency* | Frequência de deploys bem-sucedidos para o ambiente. | Medir **agilidade**. Quanto mais frequente e confiável, melhor. |
| **LT** | *Lead Time for Changes* | Tempo entre o **commit** no Git e o deploy ficar **Healthy**. | Medir **velocidade** da entrega. Quanto menor, mais eficiente o fluxo. |
| **CFR** | *Change Failure Rate* | % de deploys/syncs que falharam ou causaram instabilidade. | Medir **qualidade**. Ideal manter o mais baixo possível. |
| **MTTR** | *Mean Time to Restore* | Tempo médio para recuperar o serviço após ficar em estado `Degraded`. | Medir **resiliência**. Times elite se recuperam muito rápido. |

## 5. Policy as Code, Segurança & Governança

| Termo | Significado | Explicação |
|---|---|---|
| **Policy as Code (PaC)** | Políticas como código | Regras de segurança/governança escritas em arquivos versionados no Git. Podem ser validadas no CI (*shift-left*) e/ou aplicadas no cluster. |
| **Kyverno** | Admission Controller nativo ao Kubernetes | Motor de políticas escrito em **YAML**. Valida, muta ou gera recursos na hora da submissão. Muito prático pra quem já trabalha com manifests Kubernetes. |
| **OPA (Open Policy Agent)** | Motor de políticas genérico | Mais versátil. Utiliza a linguagem **Rego** para escrever regras. Muito usado fora e dentro do Kubernetes. |
| **Conftest** | CLI para testar manifests com OPA | Roda localmente ou no CI validando arquivos YAML/JSON contra políticas Rego. Ótimo para *shift-left*. |
| **Admission Controller** | Validador na API do Kubernetes | Intercepta requisições `CREATE/UPDATE/DELETE` antes que sejam persistidas no etcd. Se a política reprovar com `Enforce`, a requisição é **bloqueada**. |
| **Shift-left** | Validar o mais cedo possível | Em vez de só bloquear no cluster, validamos os manifests já no **Pull Request** (via CI). Assim evitamos erros antes mesmo do merge. |
| **RBAC** | *Role-Based Access Control* | Controle de permissões no Kubernetes. Define quem pode fazer o quê em quais recursos/namespaces. |
| **Least Privilege** | Princípio do menor privilégio | Dar apenas as permissões estritamente necessárias para cada componente (Argo CD, Argo Rollouts, CI, etc). |
| **Secret** | Dado sensível | Usado para armazenar tokens, senhas e chaves. **Nunca** deve ir commitado no Git. No lab usamos `Secrets` do Kubernetes. |
| **PAT vs GitHub App** | Formas de autenticar com GitHub | **PAT (Personal Access Token)**: mais simples para repo pessoal. **GitHub App**: mais seguro e recomendado para **Organizações**, com permissões granulares e rotação facilitada. |

## 6. Cluster, Namespaces & Deploy

| Termo | Significado | Explicação |
|---|---|---|
| **Namespace** | Isolamento lógico | Divide recursos dentro do mesmo cluster. Ex.: `argocd`, `argo-rollouts`, `gitops-lab`, `observability`. |
| **in-cluster** | Conexão interna | Quando o Argo CD gerencia o próprio cluster onde está instalado, usa `https://kubernetes.default.svc`. Não precisa de kubeconfig externo. |
| **Cluster-wide RBAC** | Permissão em todo cluster | Necessário quando o Argo CD precisa criar recursos em **diferentes namespaces** (além do `argocd`). Feito com `ClusterRole` + `ClusterRoleBinding`. |
| **kind / k3d / minikube** | Clusters Kubernetes locais | Ótimos para lab. Com `kind load docker-image` você consegue usar imagens locais sem subir pro registry. |
| **EKS / GKE / AKS** | Clusters Kubernetes na cloud | Gerenciados por provedores. Como os nós não têm acesso ao seu Docker local, **obrigatoriamente** precisa ter imagem no registry e workflow `build-and-push`. |
| **Drift** | Diferença entre Git e Cluster | Quando alguém altera manualmente algo no cluster (`kubectl edit`). Com `selfHeal: true` no Argo CD, ele volta ao estado definido no Git. |
| **Prune** | Remoção de recursos órfãos | Com `prune: true`, se um recurso for removido do Git, o Argo CD também o remove do cluster. |
| **Rollback** | Voltar para versão anterior | Em GitOps, o jeito **auditável e correto** é fazer `git revert` do commit que mudou a imagem. Já `kubectl argo rollouts abort` é ótimo para **frear imediatamente** durante o canary. |

## 7. Workflows no Repositório

| Workflow | Função | Status |
|---|---|---|
| `.github/workflows/policy-check.yaml` | Valida os manifests com **Kyverno CLI** e **Conftest/OPA** (*Policy as Code*). Roda em Pull Requests. | Presente |
| `.github/workflows/retorno.yml` | *Callback* pós-rollout. Escuta o `repository_dispatch` vindo do Argo Rollouts (via *Notifications*) para registrar o status, publicar o *Lead Time for Changes* no Pushgateway e enviar um aviso no Slack. | Presente |
| `.github/workflows/build-and-push.yml` | Constrói o `Dockerfile` em `manifests/app/src/`, faz login no *Container Registry*, builda e realiza o *push* da imagem com a tag baseada no `SHA` do commit. | Ausente |

> **Importante:** O `retorno.yml` **não** faz deploy. Ele apenas responde ao evento `"rollout-completed"` ou `"rollout-aborted"`. Ou seja, trata-se de uma ação *pós-deploy*.

### 7.1 Por que isso acontece em um modelo GitOps?

Em um modelo **GitOps puro (*pull-based*)**, a lógica é invertida em relação ao CI tradicional (*push-based*):

1. **CI (GitHub Actions)** – Builda, testa, escaneia e publica a imagem no *Container Registry*. Em seguida, atualiza o repositório Git com a nova tag da imagem (commitando em `manifests/rollouts/rollout.yaml` ou `kustomization.yaml`).
2. **Git** – Torna-se a *única fonte da verdade* (*Single Source of Truth*).
3. **Argo CD / Argo Rollouts** – Ficam observando o repositório e *puxam* (*pull*) as mudanças para aplicá-las no cluster.
4. **Argo Rollouts** – Executa o *canary* ou *blue/green*, roda o `AnalysisTemplate` com Prometheus e, ao finalizar (`Healthy` ou `Degraded`), dispara um `repository_dispatch` para o GitHub.
5. **GitHub Actions (`retorno.yml`)** – Recebe esse *callback*, calcula e publica as *DORA Metrics*.

Ou seja: **Quem "faz" o deploy aqui é o Argo Rollouts lendo o Git, não o GitHub Actions.** Por isso não vemos um `kubectl apply` ou `argo rollouts promote` dentro de um workflow de deploy.

## 8. Diferenças entre rodar local ou na nuvem

A necessidade do `build-and-push` depende diretamente de onde the cluster está rodando.

- **Cluster local (`kind`, `minikube`, `k3d`)** – É possível pular o *push* para um registry remoto.
- **Cluster na nuvem (`EKS`, `GKE`, `AKS`)** – **Obrigatório** buildar, subir a imagem para um registry acessível e atualizar o manifesto com essa tag.

### 8.1 Precisa mesmo do workflow `build-and-push`?

Depende do ambiente. A chave é: **os nós do Kubernetes conseguem puxar essa imagem?**

| Cenário | Precisa de `build-and-push`? | Explicação |
|---|---|---|
| **100% local (`kind`/`minikube`/`k3d`)** | Geralmente **não** | Você consegue buildar localmente com `docker build`, carregar a imagem direto no cluster com `kind load docker-image ...` e apontar o `Rollout` para essa tag local. Os nós já enxergam essa imagem. |
| **Cluster remoto (Cloud - EKS/GKE/AKS)** | **Sim** | Os nós não têm acesso ao seu Docker local. A imagem precisa estar em um *Container Registry* acessível (GHCR, ECR, Docker Hub, etc.). Por isso, é necessário fazer `docker build`, `docker push` e commitar a nova tag no repositório Git. |
| **Usando registry público ou privado** | **Sim** | Mesmo em ambiente local, caso você opte por utilizar um registry (ex.: GHCR), será necessário autenticar e realizar the *push* da imagem. |

> O `retorno.yml` **não** substitui o `build-and-push`. Ele existe exclusivamente por conta do modelo GitOps.

### 8.2 Por que o workflow "estabelece" esses dados?

Porque, no GitOps, **quem altera o estado do cluster é the Argo CD/Argo Rollouts, and not the GitHub Actions**.

**Fluxo correto and realista:**

1. **CI (GitHub Actions)** – Builda, testa, escaneia a imagem and faz *push* para o registry com uma tag imutável (normalmente the `SHA` do commit).
2. **CI atualiza o Git** – Com um `git commit + push`, o workflow altera `gitops-lab-argo-istio/manifests/rollouts/rollout.yaml`, trocando `image: ...:<tag>` pela nova tag gerada.
3. **Argo CD** – Detecta essa alteração no Git and sincroniza com o cluster.
4. **Argo Rollouts** – Vê o `Rollout` modificado, inicia o *canary* or *blue/green* and executa o `AnalysisTemplate` com Prometheus.
5. **Argo Rollouts Notifications** – Ao ficar `Healthy` or `Degraded`, dispara um `repository_dispatch` para o GitHub.
6. **GitHub Actions (`retorno.yml`)** – Recebe esse evento, calcula o *Lead Time for Changes` (diferença entre o timestamp do commit e o momento em que o rollout ficou `Healthy`) and publica no Pushgateway para o painel DORA.

Perceba: **O GitHub Actions never executa `kubectl apply` neste fluxo.** Ele apenas atualiza the repositório Git e, depois, reage a um evento vindo do próprio cluster.

### 8.3 Argo CD: criar conta, conectar ao GitHub and ao cluster

#### Acessando o Argo CD

Ao instalar o Argo CD, já existe o usuário `admin` por padrão.

```bash
# Pegar a senha inicial
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Fazer port-forward para acessar localmente
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Acesse: https://localhost:8080
```

Para este laboratório, the usuário `admin` já é suficiente. Em produção, the ideal é criar usuários com RBAC próprio or integrar com SSO (Google, GitHub, etc.).

#### Conectando o Argo CD ao GitHub

O Argo CD precisa ter permissão para **ler** o repositório Git. Essa configuração é feita em `Settings > Repositories > Connect Repo`.

| Método | Quando usar | Observação |
|---|---|---|
| **HTTPS + Personal Access Token (PAT)** | Repositório pessoal / Laboratório | Mais simples. Crie um PAT with the escopo `repo` no GitHub. |
| **SSH Key + Deploy Key** | Geral (pessoal or time) | Gere um par de chaves, adicione a **chave pública** como *Deploy Key* no GitHub and a **chave privada** no Argo CD. |
| **GitHub App** | **Organizações** | Mais granular, permite limitar o acesso a repositórios específicos, facilita a rotação and evita the uso de PATs pessoais. É a abordagem mais recomendada for organizações. |

- **Repositório pessoal:** HTTPS + PAT já resolve tranquilamente.
- **Repositório em organização:** The ideal é utilizar **GitHub App** por questões de governança and segurança.

#### Conectando ao cluster

**The Argo CD já vem conectado ao próprio cluster onde foi instalado por padrão.**

- Ao instalar, ele adiciona automaticamente o cluster `in-cluster` com `server: https://kubernetes.default.svc`.
- Só será necessário adicionar um cluster externo caso queira sincronizar manifests para um cluster diferente.
- Essa conexão é feita via **ServiceAccount + RBAC** dentro do próprio cluster, não por um IP exposto na internet.

### 8.4 É por namespace?

Sim and não. Depends of the componente analisado.

| Componente | Onde fica | Explicação |
|---|---|---|
| **Argo CD (controller, API, UI)** | Namespace `argocd` | É onde toda the instalação do Argo CD vive. |
| **Argo Rollouts Controller** | Namespace `argo-rollouts` | Instalado em um namespace separado do Argo CD. |
| **`Application` (CRD)** | Namespace `argocd` | O recurso `kind: Application` **must** estar no mesmo namespace onde the Argo CD foi instalado. |
| **Manifests aplicados (`Rollout`, `Service`, `VirtualService`, etc.)** | Namespace definido em `spec.destination.namespace` (ex.: `gitops-lab`) | É para esse namespace that the Argo CD irá criar and gerenciar the recursos. |
| **Namespaces por ambiente** | Recomendado (`gitops-llab-dev`, `gitops-lab-hml`, `gitops-lab-prod`) | Em um cenário real, é comum criar um `Application` por ambiente, apontando para the same repositório, but with *branches*, *paths* or *values* distintos. |

**Regra prática:** The Argo CD vive in seu próprio namespace (`argocd`), but consegue gerenciar recursos em **qualquer outro namespace** do cluster, desde that tenha as permissões corretas via *ClusterRoleBindings*.

The `syncOptions: - CreateNamespace=true` simply indica ao Argo CD: *"Caso o namespace de destino não exista, crie-o automáticamente."*

## 9. O que falta para ficar "realista"?

Em um cenário real, seria necessário adicionar um workflow for **buildar, subir a imagem and atualizar the manifesto**. Sem essa etapa, the fluxo GitOps não consegue iniciar sozinho ao alterar the código da aplicação.

### Example: `.github/workflows/build-and-push.yml`

```yaml
name: Build and Push App

on:
  push:
    branches: [main]
    paths:
      - 'manifests/app/src/**'
      - '.github/workflows/build-and-push.yml'

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: ./manifests/app/src
          push: true
          tags: ghcr.io/SEU-USUARIO/SEU-REPO/oficina-app:${{ github.sha }}

      - name: Update rollout image
        run: |
          sudo apt-get update && sudo apt-get install -y yq
          yq -i '.spec.template.spec.containers[0].image = "ghcr.io/SEU-USUARIO/SEU-REPO/oficina-app:${{ github.sha }}"' \
            gitops-lab-argo-istio/manifests/rollouts/rollout.yaml

      - name: Commit & push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add gitops-lab-argo-istio/manifests/rollouts/rollout.yaml
          git commit -m "chore: bump image to ${{ github.sha }}" || echo "Sem alterações"
          git push
```
### Fluxo completo com esse workflow
| Etapa	| Responsável |Ação |
|---|---|---|
| Build/Push | GitHub Actions | Builda a aplicação, gera uma imagem imutável com o SHA do commit e faz push para o Container Registry. |
| Update Manifest | GitHub Actions | Atualiza a imagem no Rollout e commita essa alteração de volta no repositório Git. |
| GitOps Sync | Argo CD | Detecta o novo commit e sincroniza o estado desejado com o cluster. |
| Progressive Delivery | Argo Rollouts | Executa canary ou blue/green, com validação automática via AnalysisTemplate (Prometheus). |
| Callback + DORA Metrics | Argo Rollouts Notifications + retorno.yml | Ao finalizar (Healthy ou Degraded), dispara o repository_dispatch. O retorno.yml calcula o Lead Time for Changes (commit da alteração → rollout Healthy) e publica no Pushgateway para visualização no Grafana. |

Resumindo
- Em cenário real: Falta a etapa build + push + update do manifesto. É ela que fecha o ciclo de CI dentro do modelo GitOps.
- O retorno.yml não é um workflow de deploy: Ele é um rollout callback, responsável por fechar o loop entre Argo Rollouts e GitHub para notificações e cálculo das DORA Metrics.
- O "deploy" aqui é GitOps: A mudança acontece via commit no Git, e não via kubectl apply disparado pelo GitHub Actions.
- Sobre rollback: Em GitOps, a forma auditável e recomendada é fazer git revert do commit que alterou a imagem/manifests. Já o kubectl argo rollouts abort é perfeito para frear o rollout imediatamente durante o canary, mas não substitui um rollback versionado via Git.