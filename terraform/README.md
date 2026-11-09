# Terraform — OCI (Always Free / OKE Trial) para o GitOps Lab

Provisiona infraestrutura na **Oracle Cloud (OCI)** para rodar o laboratório:

- **VM Always Free**: `VM.Standard.A1.Flex` (Ampere) — até **4 OCPU / 24 GB RAM** no total da tenancy (compute + Docker/Compose/k3s opcional).
- **OKE (trial/créditos)**: cluster OKE com node pool **A1.Flex onde disponível** (`create_oke=true`), adequado para a stack GitOps completa (Argo CD/Rollouts/Istio/observabilidade). O usuário indicou créditos trial: **até 4.500h compute OKE** e **500 GB OCIR** — monitore consumo e desative após testes; pós-trial, prefira VM Always Free + `compose`.

## O que este Terraform cria

| Recurso | Arquivo | Observação |
|---|---|---|
| Compartment + IAM (grupo/policies/dynamic group) | `iam.tf` | Escopo de laboratório |
| VCN, subnets (public/app/db), IGW/NAT/Service GW, NSGs, flow logs | `network.tf` | App pode receber IP público no lab (`assign_public_ip=true`) |
| Compute A1.Flex + cloud-init (Docker/k3s) + Bastion | `compute.tf`, `templates/cloud-init.yaml` | Bootstrap para deploy por pipeline |
| **OKE + node pool A1.Flex** | `oke.tf` | `create_oke=true`; requer créditos/quotas/shape disponível na região |
| Object Storage + Vault/KMS | `storage.tf` | Bucket privado, versionado |
| Notificação (ONS) + alarme | `observability.tf` | Alarme de CPU do ADB só quando `create_adb=true` |
| Autonomous Database (Oracle) | `database.tf` | **Opcional** (`create_adb=false` por padrão) |

## Importante: banco da aplicação

A aplicação Flask deste repositório usa **PostgreSQL** (`psycopg` / `postgresql+psycopg://`). O **ADB** é Oracle — **não é compatível** diretamente com o driver atual.

- **Padrão recomendado no lab:** `create_adb = false` e executar **PostgreSQL** no próprio compute/cluster (ex.: `deploy/oci/docker-compose.yml` ou manifesto Kubernetes em `gitops-lab-argo-istio/manifests/oci/`).
- Se optar por ADB (`create_adb = true`), será necessário adaptar a aplicação/driver e configuração (fora do padrão atual).

## Pré-requisitos

1. OCI CLI/config (`~/.oci/config`) ou variáveis de autenticação do provider.
2. Terraform >= 1.6.
3. Chave SSH pública.
4. Defina `admin_cidr` como seu IP/32 (não use `0.0.0.0/0` fora de teste).

## Uso

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# edite terraform.tfvars (tenancy_ocid, parent_compartment_ocid, ssh_public_key, admin_cidr, etc.)

terraform init
terraform plan
terraform apply
```

Saídas úteis:

```bash
terraform output compute_public_ip
terraform output ssh_command
```

## Pipeline de infra (GitHub Actions)

Pipeline dedicado: `.github/workflows/deploy-infra.yml` (nome **03 - Deploy Infra (Terraform OCI)**), também integrado na sequência `.github/workflows/ci-cd.yml`.

- Executa sempre: `terraform fmt -check`, `init -backend=false`, `validate`.
- Com credenciais OCI configuradas: `terraform plan` (e `apply` quando `terraform_action=apply`).
- `apply` usa o **Environment `oci-infra`** para aprovação (configure em *Settings → Environments*).
- Sem credenciais OCI: o workflow **não aplica** infra real; registra aviso e resumo (deploy bloqueado até configuração).

### Variáveis/secrets no GitHub

Configuração completa (nomes exatos, Secrets vs Variables, `gh` CLI): **`docs/github-actions-config.md`**.

Mínimo para `plan/apply` real:
- Secrets: `OCI_TENANCY_OCID`, `OCI_USER_OCID`, `OCI_FINGERPRINT`, `OCI_PRIVATE_KEY`
- Secret/Var: `OCI_REGION` (ex.: `sa-saopaulo-1`), `TF_VAR_SSH_PUBLIC_KEY`, `TF_VAR_ADMIN_CIDR`, `TF_VAR_PARENT_COMPARTMENT_OCID`
- Vars para OKE/trial: `TF_VAR_CREATE_OKE=true`, `TF_VAR_OKE_NODE_SHAPE=VM.Standard.A1.Flex`, `TF_VAR_OKE_NODE_*` (ajuste quotas/região)
- Vars para VM Always Free: `TF_VAR_CREATE_COMPUTE=true`, `TF_VAR_COMPUTE_SHAPE=VM.Standard.A1.Flex`, `TF_VAR_COMPUTE_OCPUS=4`, `TF_VAR_COMPUTE_MEMORY_GBS=24`

> O agente/ambiente local **não pode** criar secrets no seu GitHub nem rodar `terraform apply` na sua tenancy; adicione as variáveis no GitHub e execute o workflow `workflow_dispatch`.

### Notas de segurança

- Restrinja `admin_cidr` e revise NSGs (`network.tf`). O lab abre 80/443/5000 publicamente para acesso rápido — ajuste para produção.
- `terraform.tfvars` contém dados sensíveis: **não commitar** (já deve estar no `.gitignore`).
- Prefira state remoto (OCI Resource Manager ou backend S3-compatível do Object Storage) para times/ambientes compartilhados.
- Budget/Cost: variáveis de budget existem no exemplo; adicione recurso `oci_budget_budget` se desejar enforcement via Terraform (requer permissões/estrutura específicas da tenancy).

## Always Free (referência)

- **Compute:** VM.Standard.A1.Flex (Ampere), até **4 OCPU / 24 GB RAM** no total.
- **ADB (opcional):** Always Free com limites próprios; este lab não depende dele por padrão.
- Capacidade A1 pode variar por região/AD; se `terraform apply` falhar por capacidade, tente outro AD/região ou reduza temporariamente `compute_ocpus/memory_in_gbs`.
