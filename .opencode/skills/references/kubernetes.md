# Kubernetes — diagnóstico e operação

Use este guia para ir do sintoma à causa sem chutar. Sempre confirme **contexto** e
**namespace** antes de qualquer comando.

```bash
kubectl config current-context
kubectl config view --minify -o jsonpath='{.contexts[0].context.namespace}'
kubectl get ns
alias k=kubectl   # opcional
```

Em produção, use `--context` explícito e prefira `-n <namespace>` em todo comando.
Se o cluster for gerenciado (EKS/GKE/AKS/OKE), não presuma acesso a control plane/etcd.

---

## 1. Escada de triagem

```
1. É o cluster?      nodes Ready? control plane? DNS do cluster? API responde?
2. É o nó?           pressão de CPU/mem/disk/PID? kubelet? CNI? disco cheio?
3. É o workload?     Deployment/Rollout/StatefulSet replicas, conditions, eventos?
4. É o pod?          Pending/CrashLoop/ImagePull/Evicted/OOM/probe?
5. É o container?    processo, porta, env, volume, permissão, limite?
6. É a aplicação?    logs, latência, 5xx, pool, GC, lock, query, downstream?
7. É a rede?         Service endpoints, DNS, policy, mTLS, gateway, timeout?
8. É a dependência?  banco, cache, fila, API externa, DNS público, certificado?
```

Não pule etapas quando a resposta anterior não estiver confirmada. Em incidente, porém,
**mitigue no nível mais alto possível** (rollback/desvio) enquanto investiga.

---

## 2. Coleta inicial (30 segundos)

```bash
kubectl get nodes -o wide
kubectl get pods -A -o wide | grep -vE 'Running|Completed' || true
kubectl get events -A --sort-by=.lastTimestamp | tail -40
kubectl top nodes
kubectl top pods -A --sort-by=memory | head -20
kubectl get deploy,rs,sts,ds,rollout -A
kubectl get svc,ep -A | grep -v '<none>' || true
kubectl get pvc -A
```

Perguntas que essas saídas respondem: há nó NotReady? há pod fora de Running? há evento
recente de falha? há Service sem endpoint? há PVC pendente? há reinício em massa?

---

## 3. Decision tree — pod não sobe

| Estado | Primeiro comando | Causas prováveis | Ação |
|---|---|---|---|
| `Pending` | `kubectl describe pod <p>` | sem CPU/mem, taint, affinity, PVC, quota, IP | ver `Events`, requests, `describe node`, `get pvc` |
| `ImagePullBackOff`/`ErrImagePull` | `describe pod` | tag inexistente, registry privado sem secret, rate limit, DNS/rede | validar imagem, imagePullSecret, credenciais |
| `CrashLoopBackOff` | `logs <p> --previous`, `describe` | config/env ausente, migration, permissão, OOM, porta, dependência | ler log anterior, testar comando/entrypoint |
| `CreateContainerConfigError` | `describe pod` | Secret/ConfigMap ausente ou chave errada | criar/ corrigir objeto, validar `envFrom` |
| `RunContainerError` | `describe pod` | entrypoint inexistente, volume read-only, securityContext | validar imagem e mounts |
| `OOMKilled` | `describe pod` (Last State) | limite de memória baixo ou vazamento | analisar RSS/heap, ajustar limite com evidência |
| `Evicted` | `describe pod`, `describe node` | pressão de memória/disco/PID | liberar nó, ajustar requests/limits, revisar QoS |
| `Error`/`Completed` inesperado | `logs`, `describe` | app encerrou, job terminou, sinal | ver exit code e comando |
| `Terminating` eterno | `describe pod`, `get finalizers` | finalizer, volume preso, kubelet, PDB | remover causa, nunca `--force` sem confirmar |
| `Running` mas `0/1 Ready` | `describe`, logs, probe | readiness falhando, dependência, porta errada | testar endpoint de dentro do pod |
| `Succeeded` inesperado em Deployment | `describe`, `get rs` | comando curto, worker sem loop | corrigir entrypoint/processo |

### Comandos de aprofundamento

```bash
kubectl describe pod <pod> -n <ns>
kubectl logs <pod> -n <ns> --tail=200 --timestamps
kubectl logs <pod> -n <ns> -c <container> --previous
kubectl get pod <pod> -n <ns> -o yaml
kubectl get pod <pod> -n <ns> -o jsonpath='{.status.containerStatuses[*].state}'
kubectl get pod <pod> -n <ns> -o jsonpath='{.status.podIP}'
```

Exit codes: `137` = SIGKILL (frequentemente OOM), `143` = SIGTERM, `1` = erro genérico,
`126/127` = permissão/comando não encontrado.

---

## 4. Recursos, QoS e agendamento

```bash
kubectl describe node <node> | sed -n '/Allocated resources/,/Events/p'
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].resources}'
kubectl get resourcequota,limitrange -n <ns>
kubectl describe node <node> | grep -E 'Taints|Pressure|Conditions'
```

- `requests` definem agendamento e QoS; `limits` definem teto e podem matar o container.
- QoS: `Guaranteed` (requests=limits) > `Burstable` > `BestEffort`. Produção crítica deve
  ser `Guaranteed` ou `Burstable` bem dimensionado.
- `Pending` por falta de recurso: verifique **soma de requests** dos pods no nó, não o uso real.
- Fragmentação: pods grandes podem não caber mesmo com CPU livre.
- `top pod` mostra uso, não reserva. Não dimensione só por ele; use p95 histórico.

**OOM:** diferencie limite do container de memória do nó. Se o nó está sob pressão,
`kubelet` despeja pods; se o container passa do limit, é `OOMKilled`. Para Java/Node/.NET,
meça heap/RSS e considere `GOMEMLIMIT`, `-Xmx`, `--max-old-space-size` coerentes com o limite.

---

## 5. Probes e ciclo de vida

```bash
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].readinessProbe}'
kubectl exec -n <ns> <pod> -- wget -qO- http://127.0.0.1:<porta>/ready
kubectl exec -n <ns> <pod> -- sh -c 'ss -lntp || netstat -lntp'
```

- `liveness` falhando reinicia; não aponte para dependência externa (derruba o serviço em cascata).
- `readiness` falhando remove do Service; deve refletir capacidade real de atender.
- `startupProbe` evita reinício prematuro de app lenta.
- `initialDelaySeconds`/`timeoutSeconds`/`failureThreshold` devem caber no pior caso real.
- `terminationGracePeriodSeconds` + `preStop` precisam ser maiores que o drain de conexões.
- Probe em porta errada, path errado, HTTP 3xx ou host header incorreto é causa comum.

---

## 6. Rede: Service, DNS, Ingress/Gateway

```bash
kubectl get svc <svc> -n <ns> -o wide
kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=<svc>
kubectl run tmp-net --rm -it --image=nicolaka/netshoot -n <ns> -- bash
# dentro: dig <svc>.<ns>.svc.cluster.local; curl -v http://<svc>:<port>; nc -zv <host> <port>
```

Checklist:

- Selector do Service casa com labels dos pods? (`kubectl get pods --show-labels`)
- `targetPort` está correto (nome da porta vs número)?
- Endpoints existem e estão `Ready`? Se não, readiness/probe ou selector.
- `NetworkPolicy` bloqueia? Teste de pod no mesmo namespace e em outro.
- DNS: `nslookup <svc>` e `cat /etc/resolv.conf` dentro do pod; verifique `ndots` e search.
- Ingress/Gateway: classe, TLS secret, host, path, annotations, controller logs.
- Timeout: diferencie connect timeout (rede/porta) de read timeout (app lenta).
- `502/503` no gateway: endpoints vazios, app fechando conexão, mTLS, readiness.

**Netshoot** é o canivete: `dig`, `curl`, `nc`, `tcpdump`, `ss`, `mtr`.

---

## 7. Istio / service mesh

```bash
istioctl version
kubectl get pods -n istio-system
kubectl get virtualservice,destinationrule,gateway,peerauthentication -n <ns>
istioctl analyze -n <ns>
istioctl proxy-status
istioctl proxy-config cluster <pod> -n <ns>
istioctl proxy-config route <pod> -n <ns>
istioctl proxy-config endpoint <pod> -n <ns>
kubectl logs <pod> -n <ns> -c istio-proxy --tail=200
```

Problemas clássicos:

| Sintoma | Causa provável | Verificação |
|---|---|---|
| Pod sem `istio-proxy` | namespace sem label `istio-injection=enabled`, annotation `sidecar.istio.io/inject: "false"` | labels do ns/pod |
| `503 UF`/`NR` | nenhum endpoint saudável, subset errado, porta errada | `proxy-config endpoint`, labels do subset |
| `503` após deploy | VirtualService/DestinationRule desatualizado, subset sem pods | `istioctl analyze`, `get vs,dr` |
| mTLS `STRICT` quebra cliente fora do mesh | PeerAuthentication/permissão | `istioctl x describe pod`, modo do namespace |
| Tráfego não divide | peso 100/0, rota errada, host/gateway | `get vs -o yaml`, `proxy-config route` |
| Latência alta | sidecar, retry/timeout, outlier detection, DNS | `istioctl proxy-config`, métricas Envoy |

Para canary: confirme que o `VirtualService` tem a rota referenciada no Rollout
(`spec.strategy.canary.trafficRouting.istio.virtualService.routes`) e que os Services
`stable`/`canary` selecionam os pods certos. Verifique o peso efetivo no Envoy, não só no YAML.

---

## 8. Storage

```bash
kubectl get pvc,pv -A
kubectl describe pvc <pvc> -n <ns>
kubectl get storageclass
kubectl exec -n <ns> <pod> -- df -h
kubectl exec -n <ns> <pod> -- mount | grep <volume>
```

- `Pending`: StorageClass inexistente, provisioner sem permissão, zona/AZ incompatível, capacity.
- `ReadWriteOnce` + múltiplos pods em nós diferentes = um deles falha.
- Disco cheio no nó gera `DiskPressure` e eviction; verifique `df -h` no nó.
- Volume lento degrada app e pode estourar timeout. Verifique IOPS/latência do provedor.
- `emptyDir` não é persistência; `hostPath` é risco de segurança e acoplamento ao nó.
- Backup só existe se o **restore** foi testado. Declare RPO/RTO.

---

## 9. Nós e runtime

```bash
kubectl describe node <node>
kubectl get node <node> -o jsonpath='{.status.conditions}'
kubectl get pods -A --field-selector spec.nodeName=<node>
kubectl top node <node>
# no nó (com acesso):
df -h; free -m; uptime; dmesg -T | tail -50; journalctl -u kubelet --since '30 min ago'
crictl ps -a; crictl logs <id>; crictl images
```

- `NotReady`: kubelet parado, CNI quebrado, disco cheio, relógio, certificado, pressão.
- `MemoryPressure`: pods BestEffort/Burstable são despejados primeiro.
- `DiskPressure`: imagens/containers antigos, logs, volume local; `kubelet` faz GC agressivo.
- `PIDPressure`: fork bomb/thread leak; verifique `ps` e limites de processo.
- `NetworkUnavailable`: CNI. Verifique DaemonSet do CNI, rotas e logs.
- Em cloud, valide security group/NSG, rota, NAT e endpoint do control plane.
- `kubectl debug node/<node>` cria pod privilegiado — use só com autorização.

---

## 10. HPA, PDB, desrupturas

```bash
kubectl get hpa -A
kubectl describe hpa <hpa> -n <ns>
kubectl get pdb -A
kubectl get poddisruptionbudget <pdb> -n <ns> -o yaml
```

- HPA sem `metrics-server` ou com métrica custom quebrada não escala.
- HPA + requests baixos = escala por métrica errada; CPU throttling pode ser o real problema.
- `maxReplicas` atingido: não é solução mágica; verifique gargalo downstream.
- PDB `minAvailable` alto + nó único = drain trava para sempre.
- `drain` deve respeitar PDB; nunca use `--force` sem confirmar perda de disponibilidade.
- Cluster Autoscaler/Karpenter: verifique limites, taints, templates e tempo de provisionamento.

---

## 11. RBAC, admission e webhooks

```bash
kubectl auth can-i <verbo> <recurso> -n <ns> --as=system:serviceaccount:<ns>:<sa>
kubectl get clusterrolebinding,rolebinding -A | grep <sa>
kubectl get validatingwebhookconfiguration,mutatingwebhookconfiguration
kubectl get events -A | grep -iE 'denied|forbidden|webhook|admission'
```

- `Forbidden`: RBAC. Confirme `ServiceAccount` do pod, não seu usuário.
- Webhook com `failurePolicy: Fail` e backend fora do ar bloqueia criação/atualização de recursos.
- Policy Kyverno/OPA negando: leia a mensagem exata; corrija o manifesto, não desative a policy.
- `ImagePullSecret` ausente em namespace novo é causa comum de falha em lote.
- PodSecurity Admission: labels do namespace (`enforce/audit/warn`) explicam rejeições.

---

## 12. Argo CD e Argo Rollouts

**Argo CD**

```bash
argocd app list
argocd app get <app>
argocd app diff <app>
argocd app sync <app> --dry-run
argocd app history <app>
kubectl -n argocd logs -l app.kubernetes.io/name=argocd-application-controller --tail=200
```

| Sintoma | Causa provável |
|---|---|
| `OutOfSync` persistente | recurso mutado por webhook/controller, campo gerenciado por outro dono, `ignoreDifferences` |
| `SyncFailed` | validação, CRD ausente, RBAC, recurso imutável, quota |
| `Degraded` | workload não fica Ready; ver pods/eventos |
| `Prune` não remove | finalizer, dependência, `PruneLast`, política de retenção |
| App saudável mas tráfego errado | HPA/rollout/VS alterando campos; ver diff real |
| Drift volta sozinho | `selfHeal` + outro operador escrevendo; ache o dono do campo |

**Argo Rollouts**

```bash
kubectl argo rollouts list rollouts -n <ns>
kubectl argo rollouts get rollout <r> -n <ns> --watch
kubectl argo rollouts describe rollout <r> -n <ns>
kubectl argo rollouts history rollout <r> -n <ns>
kubectl argo rollouts promote <r> -n <ns>
kubectl argo rollouts abort <r> -n <ns>
kubectl argo rollouts retry rollout <r> -n <ns>
kubectl get analysisrun,analysistemplate -n <ns>
kubectl describe analysisrun <ar> -n <ns>
```

- Travado em `Progressing`: análise falhando, pause manual, VS/DestinationRule ausente,
  service selector errado, imagem ruim, readiness falhando.
- `Degraded`: `progressDeadlineSeconds` estourado ou análise com `failureLimit` atingido.
- Análise sempre falha: query sem dados, Prometheus inacessível, label `service` errada,
  janela curta demais, divisão por zero, `successCondition` invertida.
- Antes de promover, valide o pod/serviço canary diretamente e a métrica no Prometheus.
- Rollback imediato: `abort` (tráfego volta) + `git revert` para o estado desejado.
  Corrigir só no cluster cria drift e o Argo CD desfaz.

---

## 13. Depuração avançada (com autorização)

```bash
# container efêmero no pod existente (não altera a imagem)
kubectl debug -it <pod> -n <ns> --image=nicolaka/netshoot --target=<container>

# cópia do pod com shell e ferramentas
kubectl debug <pod> -n <ns> --image=busybox --copy-to=debug-<pod> -- sleep 3600

# nó
kubectl debug node/<node> -it --image=busybox

# processo/rede do host (caso extremo, exige privilégio)
nsenter -t 1 -m -u -i -n -p -- bash
```

Prefira `kubectl debug` a instalar pacote no container de produção. Nunca deixe pod de
debug rodando; use `--rm`/`--copy-to` e remova depois. Em cluster com policy, pode ser negado.

Ferramentas de análise local: `kubectl-neat`, `kubectl-tree`, `kubectl-ctx`, `stern`,
`k9s`, `popeye`, `kube-score`, `pluto` (APIs depreciadas).

---

## 14. Validação pós-correção

1. Pods `Ready` e sem restart crescente por ≥ 10 min.
2. Endpoints do Service preenchidos e saudáveis.
3. SLI voltou ao baseline (latência, erro, throughput), não só "pod verde".
4. Métricas de saturação (CPU, mem, conexões, fila) estáveis.
5. Nenhum evento novo de warning/erro.
6. Rollout `Healthy`, análise passando, tráfego no peso esperado.
7. Logs sem novo padrão de erro e com `trace_id` correlacionável.

Se o sintoma sumiu mas a causa não foi identificada, **não feche**: documente como
"mitigado, causa desconhecida" e mantenha investigação com prazo.
