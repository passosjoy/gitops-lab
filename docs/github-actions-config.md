# Configuração do GitHub Actions (Secrets e Variables)

Configure em: **Repository → Settings → Secrets and variables → Actions**.

> **Importante:** valores sensíveis (chaves privadas, tokens, senhas) vão em **Secrets**. Valores não sensíveis/reutilizáveis (região, shape, flags) podem ir em **Variables** (`vars`). Nunca commite `terraform.tfvars` com dados reais nem chaves no repositório.

## 1) Pipeline de Infra — Terraform OCI (`deploy-infra.yml` / `ci-cd.yml`)

Autenticação OCI via **API Key** (usuário OCI com permissões no compartment/tenancy).

| Nome | Tipo | Obrigatório (deploy real) | Exemplo / Observação |
|---|---|---:|---|
| `OCI_TENANCY_OCID` | Secret | Sim | `ocid1.tenancy.oc1..aaaa...` |
| `OCI_USER_OCID` | Secret | Sim | `ocid1.user.oc1..aaaa...` |
| `OCI_FINGERPRINT` | Secret | Sim | `aa:bb:cc:...` |
| `OCI_PRIVATE_KEY` | Secret | Sim | Conteúdo PEM da chave privada da API key OCI (incluindo `BEGIN/END`) |
| `OCI_REGION` | Secret ou Variable | Sim | `sa-saopaulo-1` (ajuste sua região) |
| `TF_VAR_PARENT_COMPARTMENT_OCID` | Secret/Var | Recomendado | Compartment pai (muitas vezes = tenancy). Se vazio, workflow usa tenancy. |
| `TF_VAR_SSH_PUBLIC_KEY` | Secret/Var | Sim (compute/OKE) | `ssh-ed25519 AAAA...` |
| `TF_VAR_ADMIN_CIDR` | Secret/Var | Recomendado | `SEU_IP_PUBLICO/32` (SSH/k3s API). Evite `0.0.0.0/0`. |
| `TF_VAR_BUDGET_ALERT_EMAIL` | Secret/Var | Recomendado | E-mail para alertas OCI/budget |
| `TF_VAR_ADB_ADMIN_PASSWORD` | Secret | Só se `create_adb=true` | Senha forte (12+ chars). App do lab usa **PostgreSQL**, então normalmente `create_adb=false`. |

### Variáveis opcionais (Terraform) — `vars`

| Variable | Default no workflow | Uso |
|---|---|---|
| `TF_VAR_CREATE_ADB` | `false` | ADB Oracle (opcional; app atual usa Postgres) |
| `TF_VAR_CREATE_COMPUTE` | `true` | VM OCI para app/compose/k3s |
| `TF_VAR_CREATE_OKE` | `false` | Cluster OKE (use com créditos trial: 4.500h compute / OCIR 500 GB) |
| `TF_VAR_BOOTSTRAP_K3S` | `true` | Instala Docker/k3s na VM |
| `TF_VAR_ASSIGN_PUBLIC_IP` | `true` | IP público na VM (lab/SSH) |
| `TF_VAR_COMPUTE_SHAPE` | `VM.Standard.A1.Flex` | Always Free A1 (4 OCPU/24 GB total tenancy) |
| `TF_VAR_COMPUTE_OCPUS` | `4` | OCPUs VM |
| `TF_VAR_COMPUTE_MEMORY_GBS` | `24` | Memória VM |
| `TF_VAR_OKE_NODE_SHAPE` | `VM.Standard.A1.Flex` | Nós OKE (A1 flex onde disponível) |
| `TF_VAR_OKE_NODE_OCPUS` | `2` | OCPUs por nó OKE |
| `TF_VAR_OKE_NODE_MEMORY_GBS` | `12` | Memória por nó OKE |
| `TF_VAR_OKE_NODE_COUNT` | `2` | Nós no pool |
| `TF_VAR_OKE_KUBERNETES_VERSION` | (vazio) | Versão K8s OKE; vazio = seleção automática |

## 2) Deploy da aplicação (`deploy-oci.yml` / `ci-cd.yml`)

| Nome | Tipo | Obrigatório | Observação |
|---|---|---:|---|
| `OCI_HOST` | Secret/Var | Sim (deploy SSH) | IP público da VM (`terraform output compute_public_ip`) ou host com acesso ao cluster |
| `OCI_SSH_USER` | Secret/Var | Não | Default `opc` |
| `OCI_SSH_PRIVATE_KEY` | Secret | Sim (deploy SSH) | Chave privada correspondente à `TF_VAR_SSH_PUBLIC_KEY` |
| `GHCR_PULL_TOKEN` | Secret | Só se GHCR privado | PAT com `read:packages` |

> **Runners GitHub hospedados + SSH:** IPs variáveis; se `admin_cidr` no Terraform for restrito, o SSH do runner pode falhar. Soluções: self-hosted runner na VCN, OCI DevOps, ou liberar CIDRs dos runners (menos seguro) / ajustar processo.

## 3) DORA / Notificações (callback `retorno.yml`)

| Nome | Tipo | Uso |
|---|---|---|
| `PUSHGATEWAY_URL` | **Variable** (`vars`) | Endpoint do Prometheus Pushgateway acessível do runner (para lead time DORA) |
| `SLACK_WEBHOOK_URL` | **Secret** | Fallback Slack do callback (Argo Rollouts Notifications também pode enviar Slack direto) |

## 4) Environment recomendado (aprovação para `apply`)

Crie **Settings → Environments → `oci-infra`** e adicione *required reviewers* para aprovar `terraform apply`. O workflow `deploy-infra.yml` usa esse environment quando a ação é `apply`.

## 5) Como colocar no GitHub (UI)

1. Abra o repositório no GitHub.
2. **Settings** → **Secrets and variables** → **Actions**.
3. Aba **Secrets** → *New repository secret* (para `OCI_PRIVATE_KEY`, `OCI_SSH_PRIVATE_KEY`, tokens etc.).
4. Aba **Variables** → *New repository variable* (para flags `TF_VAR_*`, `OCI_REGION`, `OCI_HOST` se não sensível no seu contexto, `PUSHGATEWAY_URL`).
5. Rode o pipeline **CI/CD Sequencial** via *Actions → workflow_dispatch*: `terraform_action=plan` primeiro; depois `apply` com environment aprovado; depois `deploy_app=true`.

## 6) Exemplo com GitHub CLI (`gh`) — sem valores reais

```bash
# Autentique: gh auth login
gh secret set OCI_TENANCY_OCID --body 'ocid1.tenancy.oc1..REDACTED'
gh secret set OCI_USER_OCID --body 'ocid1.user.oc1..REDACTED'
gh secret set OCI_FINGERPRINT --body 'aa:bb:cc:dd:ee:ff:...'
gh secret set OCI_PRIVATE_KEY < ~/.oci/oci_api_key.pem
gh variable set OCI_REGION --body 'sa-saopaulo-1'
gh variable set TF_VAR_CREATE_OKE --body 'true'   # se usar trial OKE
gh variable set TF_VAR_CREATE_COMPUTE --body 'true'
```

> Substitua os placeholders. Não cole segredos em chats/issues.
