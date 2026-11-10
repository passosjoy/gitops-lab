# Infraestrutura, GitOps, CI/CD e operação

Este guia cobre o que sustenta o serviço: IaC, nuvem, entrega, segurança, capacidade,
continuidade e custo. A regra central é **mudança pequena, declarativa, revisada e reversível**.

---

## 1. IaC — modelo de operação

- O Git é a fonte da verdade. Console/CLI manual é exceção auditada, nunca rotina.
- **State remoto com lock** (Object Storage/S3 + lock, Terraform Cloud, Resource Manager).
  State local em laptop é incidente esperando acontecer.
- Um state por blast radius (por ambiente/conta/região), não um monstro global.
- `plan` é artefato de revisão: leia destroy/replace, não só "2 to add".
- Módulos versionados, inputs validados, outputs explícitos, sem `count` frágil.
- Tags obrigatórias: `owner`, `env`, `cost_center`, `managed_by`, `data_classification`.
- Segredos nunca em `.tfvars`/state sem cifra; use cofre e `sensitive = true`.
- Mudança de recurso com estado: prefira `moved`/`import` a destroy/create.
- Drift detectado é sinal de processo quebrado; reconcilie ou importe, não ignore.

Fluxo seguro:

```bash
terraform fmt -check -recursive
terraform init -backend=false        # validação sem backend quando aplicável
terraform validate
terraform plan -out=tfplan           # com credenciais e backend reais
# revise o plano: replacements, destroys, IAM, rede, dados
terraform show -json tfplan | jq '.resource_changes[] | select(.change.actions != ["no-op"])'
terraform apply tfplan               # após aprovação; nunca -auto-approve em prod
```

Nunca use `-target` como fluxo normal: cria state parcial e divergência. Use para emergência
com plano de reconciliação depois.

Diagnóstico comum:

| Sintoma | Causa | Ação |
|---|---|---|
| `Error acquiring the state lock` | execução anterior travou/CI concorrente | identificar lock ID, garantir que não há apply ativo, então destravar |
| `Provider produced inconsistent result` | bug/provider/atributo computado | atualizar provider, isolar recurso, abrir issue |
| `resource already exists` | criado fora do Terraform | `terraform import` + `plan` para alinhar |
| replace inesperado | atributo imutável mudou | avaliar `create_before_destroy`, `lifecycle`, estratégia de migração |
| drift constante | outro operador/console escrevendo | achar dono, desabilitar escrita manual, `ignore_changes` só com justificativa |
| credencial expirada | chave estática/rotação | migrar para OIDC/instance principal/workload identity |
| quota exceeded | limite da conta/região | aumentar quota ou redesenhar; não fragmentar sem controle |

Ferramentas de apoio: `tflint`, `checkov`, `tfsec`, `trivy config`, `conftest`, `infracost`,
`terraform-docs`, `atlantis`/`Spacelift`/`env0` para PR automation.

---

## 2. OCI — padrões do laboratório

O `terraform/` deste repo é uma referência de arquitetura segura para OCI.

**Identidade e acesso**

- Compartment dedicado por projeto/ambiente; `enable_delete` consciente.
- Grupo de operadores + policy escopada ao compartment (não `manage all-resources` na tenancy).
- Dynamic group para instance principals: `instance.compartment.id = '<ocid>'`.
- Prefira federação/SSO e chaves de curta duração; API key estática é dívida.
- Bastion + subnet privada em vez de SSH público. `admin_cidr` nunca `0.0.0.0/0` em produção.

**Rede**

- VCN com subnets separadas: pública (LB/bastion), aplicação privada, banco privado.
- NSG por workload (stateful, referência por NSG) em vez de security list ampla.
- IGW só para público; NAT para saída privada; **Service Gateway** para Object Storage
  sem passar pela internet.
- Route tables explícitas por subnet; documente o fluxo.
- Flow logs habilitados para auditoria e troubleshooting.
- OKE: endpoint público é conveniência de lab; em produção, endpoint privado + bastion/VPN.
- `node_pool_pod_network_option_details` com VCN-native pod networking exige planejamento de IP.

**Compute/OKE**

- `VM.Standard.A1.Flex` (Ampere/ARM) no Always Free; confirme disponibilidade por AD/região.
- Capacidade pode falhar por falta de shape; tenha fallback de AD/região ou reduza OCPU.
- OKE Basic é suficiente para lab; Enhanced adiciona recursos/custos.
- `ignore_changes` em imagem/versão de nó evita replace acidental, mas exige upgrade planejado.
- Cloud-init instala Docker/k3s/Helm no lab; em produção, prefira imagem imutável + bootstrap idempotente.
- Não abra 30000-32767 e 6443 para o mundo; restrinja ao admin CIDR.

**Dados e chaves**

- Object Storage privado, versionado, com lifecycle (archive/delete) e KMS.
- KMS vault/key com rotação e policy mínima; bucket e ADB usando a chave.
- ADB exige subnet privada, NSG, mTLS e senha forte; **não** é compatível com o driver
  Postgres da app deste repo — não ative `create_adb` esperando que funcione.
- Backups e restore testados; versionamento não substitui backup lógico.

**Observabilidade/custo**

- ONS topic + subscription para alarmes; alarme de CPU do ADB é exemplo, não cobertura completa.
- Budget + alerta de anomalia; tags de custo desde o dia 1.
- Monitore NAT, storage, OKE e nós ociosos — os maiores vilões de surpresa.

Comandos úteis:

```bash
oci iam compartment list --all
oci compute instance list --compartment-id <ocid> --output table
oci ce cluster create-kubeconfig --cluster-id <ocid> --file ~/.kube/config --region <region>
oci os object list --bucket-name <bucket> --namespace <ns>
oci logging log list --compartment-id <ocid>
```

Equivalentes AWS (para não misturar modelos): IAM role/IRSA, VPC com subnets privadas,
VPC endpoints, EKS com endpoint privado, RDS Multi-AZ, KMS, CloudTrail, Budgets.
O princípio é o mesmo: **segmentação, menor privilégio, auditoria e custo visível**.

---

## 3. GitOps com Argo CD

- App aponta para Git + path + revision; cluster/namespace explícitos.
- `automated: { prune: true, selfHeal: true }` é poderoso, mas exige revisão de prune.
- `CreateNamespace=true` e `PruneLast=true` ajudam em bootstrap; cuidado com ordem.
- Separe apps por ambiente e por blast radius; use app-of-apps ou ApplicationSet.
- `sync-wave` para dependência (CRD → operator → app); health checks customizados.
- `ignoreDifferences` só para campos realmente gerenciados por outro controller (HPA, webhook),
  com justificativa e escopo mínimo.
- Credenciais de repo: Deploy Key, PAT ou GitHub App; prefira App/SSO e rotação.
- Segredos: Sealed Secrets, External Secrets, Vault/SOPS; nunca plaintext no Git.
- Promoção: PR alterando imagem/tag no overlay do ambiente; não `kubectl set image`.
- Drift: investigue quem escreveu; `selfHeal` não é desculpa para ignorar processo.

```bash
argocd app list -o wide
argocd app get <app>
argocd app diff <app>
argocd app sync <app> --dry-run
argocd app history <app>
argocd app rollback <app> <id>
kubectl -n argocd get applicationsets,applications
```

Erros clássicos: path errado, branch inexistente, CRD ainda não instalada, RBAC do
Argo CD insuficiente, webhook mutando campo, recurso órfão com finalizer, secret ausente.

---

## 4. Progressive delivery

**Canary** (repo): pesos 10 → 50 → 100, pausas e `AnalysisTemplate` com Prometheus.
**Blue/Green**: preview validado, troca total, `scaleDownDelaySeconds` para rollback rápido.

Regras:

- A análise mede **impacto de usuário** (sucesso, latência, erro) e tem `failureLimit`.
- `startingStep` e `count × interval` devem cobrir tempo suficiente para o tráfego canary
  gerar amostra estatisticamente útil. Com pouco tráfego, a métrica fica vazia.
- `progressDeadlineSeconds` coerente com a soma dos passos.
- Tráfego real controlado por Istio/NGINX/Gateway; confirme o peso no proxy, não no YAML.
- Pause manual em produção para blue/green é padrão sadio (`autoPromotionEnabled: false`).
- Rollback: `abort` para o tráfego + `git revert` para o estado desejado.
- Teste o canary em DEV com falha injetada; rollback não testado não existe.
- Não faça canary de mudança de schema incompatível; use expand/contract.

```bash
kubectl argo rollouts get rollout <r> -n <ns> --watch
kubectl argo rollouts promote <r> -n <ns>
kubectl argo rollouts abort <r> -n <ns>
kubectl get analysisrun -n <ns>
kubectl describe analysisrun <ar> -n <ns>
```

---

## 5. CI/CD

Pipeline de referência (repo): **policy → build → infra → app**, com callback assíncrono
de DORA após o rollout.

Desenho correto:

1. **Validação**: lint, unit, contract, SAST, secret scan, policy (Kyverno/Conftest), IaC scan.
2. **Build**: reprodutível, cache, tag imutável por SHA, SBOM, assinatura, scan de imagem.
3. **Publicação**: registry com retenção e imutabilidade; nunca sobrescrever tag.
4. **Deploy**: GitOps (commit da tag) ou pipeline com aprovação; ambiente protegido.
5. **Verificação**: smoke test, SLI, análise de rollout; rollback automático se falhar.
6. **Feedback**: status no PR, notificação, métrica DORA, artefato auditável.

Práticas:

- **OIDC/federação** em vez de chave estática de nuvem no GitHub.
- `permissions` mínimas no workflow; pin de actions por SHA em ambiente sensível.
- `concurrency` para não sobrepor deploys; `environment` com required reviewers em prod.
- Segredos só em Secrets; nunca `echo` de credencial; mask adicional quando necessário.
- Cache não pode servir artefato de outra branch/compromisso.
- Build once, deploy many: a mesma imagem promovida DEV → HML → PROD.
- Migração de banco em job separado, compatível e observável.
- Pipeline que "pula com aviso" quando falta credencial é bom para lab, ruim para produção:
  em prod, falhe fechado.

Sinais de pipeline doente: deploy manual recorrente, tag `latest`, rollback por edição no
cluster, build lento sem cache, secrets em log, ausência de aprovação, deploy sem smoke test.

---

## 6. Segurança e supply chain

- **Menor privilégio** em IAM/RBAC/ServiceAccount; sem `cluster-admin` para workload.
- **NetworkPolicy** default-deny com allow explícito entre serviços e egress controlado.
- **mTLS STRICT** no mesh quando todos os clientes estão no mesh; migração via PERMISSIVE.
- **Pod Security Standards**: `restricted` para produção; non-root, sem privileged,
  capabilities drop ALL, readOnlyRootFilesystem quando possível.
- **Imagens**: base mínima/distroless, non-root, scan contínuo, assinatura (cosign) e admissão
  que rejeita imagem não assinada/vencida.
- **Segredos**: cofre, rotação, escopo, auditoria; secret em env é aceitável só com risco consciente.
- **Policy as Code**: Kyverno/OPA no CI e no admission; exceções com validade e dono.
- **Auditoria**: CloudTrail/OCI Audit, Kubernetes audit, Git history, logs de acesso.
- **Dados**: classificação, criptografia, retenção, mascaramento em logs e backups.
- **Cadeia de suprimentos**: lockfile, SBOM, proveniência, dependências atualizadas.
- **Resposta**: acesso de emergência documentado, rotação pós-incidente, evidências preservadas.

Checklist rápido de PR de infra:

- [ ] Muda rede/IAM/dados? blast radius declarado.
- [ ] `plan` anexado e revisado; nenhum destroy inesperado.
- [ ] Segredo não aparece no diff/state/log.
- [ ] Rollback possível e testado.
- [ ] Tags, limites, backup e monitoração incluídos.
- [ ] Policy e scan passando; exceção justificada.

---

## 7. Capacidade e performance

- Dimensione por **p95/p99 histórico + pico**, não por média.
- Headroom para falha de zona: N+1 no mínimo; para HA real, multi-AZ.
- Calcule **conexões de banco**: `réplicas × pool_size` deve caber em `max_connections`
  com margem para jobs/admin. Use pooler (PgBouncer/RDS Proxy) quando escalar horizontalmente.
- Filas: monitore profundidade, idade da mensagem mais antiga, taxa de consumo e DLQ.
  Capacidade = taxa de chegada × tempo de processamento, com margem.
- Cache: acerto, eviction, latência, stampede. Cache não corrige query ruim.
- Autoscaling reage depois; para picos, provisione ou use fila como amortecedor.
- Load test com carga realista e critério de aprovação; teste o **degradado**, não só o feliz.
- Meça saturação antes do limite: CPU throttling, memória, IOPS, conexões, threads, GC.
- Capacidade de banco e storage cresce mais devagar que app; planeje antes.

Lei de Little: `L = λ × W` (itens no sistema = chegada × tempo no sistema). Útil para filas.

---

## 8. Continuidade e DR

- Declare **RPO** (perda máxima de dados) e **RTO** (tempo de retorno) por serviço.
- Backup automático + retenção + criptografia + cópia em outra região/conta quando crítico.
- **Teste o restore** cronometrado; backup não testado é esperança.
- Documente dependências de recuperação: DNS, TLS, secrets, IAM, registry, cluster, banco.
- Runbook de failover com pré-condições, comandos e critério de retorno.
- Evite single point of failure: nó único, AZ única, disco local, IP fixo, pessoa única.
- Chaos engineering controlado: derrube pod/zona/dependência em ambiente não produtivo primeiro.
- Incidente de DR é diferente de incidente normal: declare comandante e comunicação cedo.

---

## 9. Custo (FinOps)

- Tag de custo em tudo; sem tag, não há dono nem chargeback.
- Revise: nós ociosos, volumes órfãos, snapshots antigos, IPs públicos, NAT, logs infinitos,
  réplicas superdimensionadas, provisioned concurrency parada, ambientes de lab ligados 24/7.
- Right-sizing com p95 real; A1/Graviton/Spot quando tolerável.
- Storage lifecycle: standard → infrequent → archive → delete.
- Budget + alerta de anomalia por conta/ambiente; revise semanalmente no começo.
- Custo de observabilidade é custo de produto: cardinais, retenção e sampling são decisões.
- Economia que aumenta risco (remover réplica, backup, monitoração) não é economia.

---

## 10. Production readiness review

- [ ] Arquitetura e dependências documentadas; SPOFs identificados.
- [ ] SLO, alertas, dashboard e on-call definidos.
- [ ] Capacidade e limites calculados; autoscaling testado.
- [ ] Deploy progressivo, rollback e feature flag prontos.
- [ ] Backup/restore e DR testados; RPO/RTO declarados.
- [ ] Segurança: IAM mínimo, rede, TLS/mTLS, secrets, policy, scan.
- [ ] Runbooks de incidente e contatos de escalonamento.
- [ ] Custos estimados com tags e budget.
- [ ] Dependências externas com timeout/retry/circuit breaker.
- [ ] Plano de carga e critério de go/no-go assinados.
