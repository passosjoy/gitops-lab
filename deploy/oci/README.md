# Deploy no OCI (Always Free) — compute único

Este diretório suporta o deploy da aplicação em uma **VM OCI Always Free** (A1.Flex 4 OCPU / 24 GB) via **pipelines GitHub Actions** (sem scripts manuais como fluxo principal).

## Modo `compose` (recomendado para deploy rápido da imagem)

- `docker-compose.yml`: `postgres` + `otel-collector` + `app` (imagem do GHCR).
- `.env.example`: modelo de variáveis. No primeiro deploy o pipeline cria `/opt/gitops-lab/deploy/.env` com segredos gerados para laboratório — **revise/rotacione**.

Pré-requisitos na VM (o `terraform/templates/cloud-init.yaml` instala): Docker + Compose plugin, firewall, opcional k3s.

## Pipelines

1. **`.github/workflows/build-and-push.yml`** — build da imagem (`gitops-lab-argo-istio/manifests/app/src`) e push para GHCR:
   - `ghcr.io/<owner>/<repo>/app:<sha>`
2. **`.github/workflows/deploy-oci.yml`** — SSH na VM (`OCI_HOST`) e `docker compose pull/up`.

### Secrets (GitHub Actions)

| Secret | Descrição |
|---|---|
| `OCI_HOST` | IP público da VM (`terraform output compute_public_ip`) |
| `OCI_SSH_USER` | `opc` (padrão) |
| `OCI_SSH_PRIVATE_KEY` | Chave privada SSH autorizada na instância |
| `GHCR_PULL_TOKEN` (opcional) | PAT `read:packages` se a imagem GHCR for privada |

> Garanta que o NSG/Terraform permita SSH a partir de quem executa o deploy. `admin_cidr` deve incluir seu IP; runners hospedados do GitHub têm IPs variáveis — para produção, use **self-hosted runner** na VCN, **OCI DevOps**, ou Bastion/ação específica.

## Modo `k8s`

Requer `bootstrap_k3s=true` e manifests aplicados (namespace, `app-secret`, Postgres, app/Rollout). O pipeline oferece um modo básico; para **GitOps completo** (Argo CD + Argo Rollouts + Istio + observabilidade), instale a stack no k3s e aponte o Argo CD para este repositório.
