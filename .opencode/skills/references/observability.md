# Observabilidade — sinais, SLO, PromQL e telemetria

Observabilidade não é "ter Grafana". É conseguir responder **por que** o usuário está
sofrendo, com dados correlacionáveis e custo controlado.

Perguntas que um sistema observável responde:

1. O serviço está saudável **para o usuário**? (SLI)
2. Desde quando, para quem e em que proporção? (impacto)
3. Onde está a causa? (serviço, dependência, infra, deploy)
4. O que mudou? (deploy, config, tráfego, dependência)
5. O que fazer agora e como saber se funcionou? (runbook + SLI)

---

## 1. Os três sinais, com propósito

| Sinal | Responde | Custo | Retenção típica |
|---|---|---|---|
| Métrica | "quanto / com que frequência / tendência" | baixo por série, alto com cardinalidade | semanas a meses |
| Log | "o que aconteceu neste evento" | alto volume | dias a semanas |
| Trace | "onde o tempo foi gasto na jornada" | alto por amostra | dias |

Use **eventos** (deploy, mudança de config, incidente, escala) como quarta dimensão:
sem linha do tempo, correlação vira adivinhação.

---

## 2. SLI, SLO e error budget

Escolha o SLI que representa a jornada do usuário, não a saúde interna do pod.

Exemplos:

- Disponibilidade: `requests 2xx/3xx válidas / requests totais` (exclua health checks).
- Latência: `% de requests < 500 ms` ou p95 < 500 ms.
- Qualidade: `respostas completas / respostas` (ex.: busca que retorna resultado).
- Throughput/frescor: `eventos processados em < 60 s / eventos`.
- Saturação: `% de tempo com fila > X` (SLI interno, não substitui SLO de usuário).

Definição completa:

```yaml
SLI: proporção de requisições HTTP bem-sucedidas e rápidas
Query: sum(rate(http_requests_total{status=~"2..|3.."}[5m])) / sum(rate(http_requests_total[5m]))
Janela: 28 dias rolantes
SLO: 99,9%
Error budget: 0,1% = ~40 min/mês
Consequência: budget esgotado → congelar mudanças arriscadas e priorizar confiabilidade
```

**Burn rate** = taxa de erro observada / taxa tolerada. Para SLO 99,9%, tolerância = 0,1%.

Alertas multi-janela (padrão SRE):

| Janela | Burn rate | Consumo do budget | Ação |
|---|---|---|---|
| 1h | > 14,4 | 2% em 1h | página imediata |
| 6h | > 6 | 5% em 6h | página/ticket urgente |
| 3d | > 1 | 10% em 3d | ticket, tendência |

Exija **duas janelas** (longa e curta) para reduzir ruído e detectar recuperação.

```promql
# taxa de erro (SLI invertido)
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
clamp_min(sum(rate(http_requests_total[5m])), 0.0001)

# burn rate para SLO 99.9% (tolerância 0.001)
(
  sum(rate(http_requests_total{status=~"5.."}[1h]))
  / clamp_min(sum(rate(http_requests_total[1h])), 0.0001)
) / 0.001
```

Regras de ouro:

- Alerta **sintoma de usuário** primeiro; causa depois.
- Não alerte em CPU alta se o SLI está bom; alerte em saturação **com previsão de impacto**.
- Todo alerta tem: dono, severidade, runbook, dashboard e critério de resolução.
- Alerta que ninguém age é ruído: remova ou converta em painel.
- Evite `for: 0m`. Use janela que absorva picos sem atrasar detecção real.

---

## 3. Convenções de métrica

- Nome: `<dominio>_<unidade>_<tipo>` (`http_request_duration_seconds`, `queue_messages_total`).
- Unidades no nome (`_seconds`, `_bytes`, `_milliseconds`); não misture.
- Labels de baixa cardinalidade: `service`, `env`, `version`, `method`, `route` **template**
  (`/os/{id}`, nunca `/os/123`), `status_class`.
- **Nunca** use `user_id`, `email`, `request_id`, `trace_id`, URL crua, timestamp ou payload
  como label. Isso explode o Prometheus e o custo.
- Histograma para latência; evite média. Use p50/p95/p99 e `_bucket`.
- Counter só cresce; use `rate`/`increase`, nunca valor absoluto.
- Gauge para valor instantâneo (fila, conexões, temperatura).
- Summary é difícil de agregar entre instâncias; prefira histograma.

No repo, o padrão é ilustrativo e deve ser mantido:

```text
oficina_http_requests_total{service,env,version,endpoint,route,method,status_class,fault_mode}
oficina_http_requests_good_total{...}
oficina_http_errors_total{...}
oficina_http_request_duration_milliseconds_bucket{le,service,env,version,endpoint}
```

SLI de sucesso e latência derivados dele:

```promql
# taxa de sucesso
sum(rate(oficina_http_requests_good_total{service="oficina-lanternagem-do-rasta"}[5m]))
/
clamp_min(sum(rate(oficina_http_requests_total{service="oficina-lanternagem-do-rasta"}[5m])), 0.0001)

# p95 em ms
histogram_quantile(0.95,
  sum(rate(oficina_http_request_duration_milliseconds_bucket{
    service="oficina-lanternagem-do-rasta"}[5m])) by (le)
)
```

Cuidado com `service` label: se o valor não casar exatamente, a query retorna vazio e a
análise "falha" sem erro. Confirme com `count by (service) (...)`.

---

## 4. PromQL — receitas

```promql
# taxa por segundo
sum(rate(http_requests_total[5m]))

# total em janela
sum(increase(http_requests_total[1h]))

# erro por status e rota
sum by (route, status) (rate(http_requests_total{status=~"5.."}[5m]))

# p50/p90/p99 (histograma)
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))

# média (use com cautela)
sum(rate(http_request_duration_seconds_sum[5m])) / sum(rate(http_request_duration_seconds_count[5m]))

# top ofensores
topk(10, sum by (route) (rate(http_requests_total{status=~"5.."}[5m])))

# série ausente (serviço sem scrape)
absent(up{job="minha-app"} == 1)

# alvo down
up == 0

# saturação de CPU por container vs limit
sum by (namespace, pod) (rate(container_cpu_usage_seconds_total{container!=""}[5m]))
/
clamp_min(sum by (namespace, pod) (kube_pod_container_resource_limits{resource="cpu"}), 0.001)

# memória working set vs limit
sum by (namespace, pod) (container_memory_working_set_bytes{container!=""})
/
clamp_min(sum by (namespace, pod) (kube_pod_container_resource_limits{resource="memory"}), 1)

# restarts recentes
increase(kube_pod_container_status_restarts_total[1h]) > 0

# previsão de disco cheio (4h)
predict_linear(node_filesystem_avail_bytes{mountpoint="/"}[6h], 4*3600) < 0

# fila crescendo
deriv(queue_messages{queue="x"}[10m]) > 0

# proporção de erros por serviço
sum by (service) (rate(http_requests_total{status=~"5.."}[5m]))
/
clamp_min(sum by (service) (rate(http_requests_total[5m])), 0.0001)
```

Regras práticas:

- Sempre agregue com `sum by (...)` antes de `histogram_quantile`.
- `rate` exige ≥ 2 pontos; janela menor que o scrape gera vazio/ruído.
- `clamp_min` evita divisão por zero.
- `absent`/`up` são seus alertas de **cegueira**, não de aplicação.
- `offset` compara com período anterior; útil para sazonalidade.
- `@` fixa timestamp para investigação reproduzível.
- Explore no Grafana/Prometheus antes de codificar alerta ou AnalysisTemplate.

---

## 5. Dashboards que servem em incidente

Ordem de cima para baixo:

1. **SLI e impacto**: sucesso, erro, p95/p99, throughput, budget restante.
2. **Mudanças**: deploys, versões, rollout phase, feature flags.
3. **Saturação**: CPU, memória, conexões, fila, IOPS, threads, GC.
4. **Dependências**: banco, cache, fila, APIs externas, DNS.
5. **Por rota/tenant/região**: onde dói.
6. **Logs/traces**: links diretos filtrados pelo intervalo.

Use variáveis (`service`, `env`, `namespace`, `route`) e `$__rate_interval`.
Não monte dashboard de 60 painéis: em incidente ninguém lê. Um painel bom tem pergunta no
título ("p99 acima do SLO?"), unidade clara, threshold visível e link para runbook.

RED (serviços): Rate, Errors, Duration.
USE (recursos): Utilization, Saturation, Errors.
Quatro sinais de ouro: latência, tráfego, erros, saturação.

---

## 6. OpenTelemetry

Pipeline de referência do repo:

```
App (OTel SDK) --OTLP/HTTP 4318--> Collector --OTLP/gRPC 4317--> Tempo
                                    |
                                    +--> métricas próprias em :8888 (scrape)
```

Boas práticas:

- **Resource** obrigatório: `service.name`, `service.version`, `deployment.environment`,
  `service.instance.id`, `cloud.region`, `k8s.namespace.name`, `k8s.pod.name`.
- **Propagação** W3C `traceparent`/`tracestate` entre HTTP, gRPC e filas.
- **Spans** com nome estável e atributos sem alta cardinalidade; registre exceções e status.
- **Sampling**: head sampling para volume; tail sampling no Collector para manter erros/lentos.
- **Batch** + `memory_limiter` no Collector; dimensione fila e timeout.
- Exporte para backend resiliente; se o Collector cair, a app não pode cair junto.
- Não use o Collector como armazenamento; ele é pipeline.
- Em Lambda, inicialize tracer fora do handler e faça flush.
- Instrumentação automática + spans manuais nos pontos de negócio críticos.

Exemplo de Collector com resiliência:

```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }

processors:
  memory_limiter: { check_interval: 1s, limit_percentage: 75, spike_limit_percentage: 20 }
  batch: { send_batch_size: 512, timeout: 5s }
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow
        type: latency
        latency: { threshold_ms: 500 }
      - name: baseline
        type: probabilistic
        probabilistic: { sampling_percentage: 5 }

exporters:
  otlp/tempo:
    endpoint: tempo.observability.svc.cluster.local:4317
    tls: { insecure: true }

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, tail_sampling, batch]
      exporters: [otlp/tempo]
```

Monitore o próprio pipeline: spans aceitos/recusados/descartados, fila, latência de export,
`prometheus_target_scrape_pool_sync_total`, `up`, `scrape_duration_seconds`, `scrape_samples_scraped`.
Se a observabilidade cai, você fica cego: trate como incidente.

---

## 7. Logs

- JSON estruturado, uma linha por evento, timestamp UTC ISO-8601.
- Campos: `timestamp`, `level`, `message`, `service`, `env`, `version`, `trace_id`, `span_id`,
  `request_id`, `route`, `status`, `duration_ms`, `error.kind`, `error.message`.
- **Nunca** logue token, senha, cookie, Authorization, PII, payload de cartão ou documento.
- Nível correto: `ERROR` para falha que exige ação; `WARN` para degradação; `INFO` para evento
  de negócio; `DEBUG` desligado em produção.
- Alta cardinalidade em log é aceitável; em métrica, não.
- Retenção por criticidade e compliance; archive para S3 se necessário.
- Amostragem em volume extremo, preservando erros.
- Correlação: `trace_id` no log permite pular para o trace no Grafana/Tempo/X-Ray.
- Não logue a mesma exceção em cada camada; escolha um ponto e adicione contexto.

Consultas úteis (CloudWatch Insights / Loki-like):

```sql
fields @timestamp, level, message, trace_id, route, status, duration_ms
| filter level = "error" and route = "/os/{id}"
| stats count() by bin(1m)
```

```sql
fields @timestamp, message, trace_id
| filter trace_id = "<id>"
| sort @timestamp asc
```

---

## 8. Traces

- Um trace por jornada; spans para entrada, banco, cache, fila, chamada externa.
- Nome do span: verbo + recurso (`GET /os/{id}`, `db.query ordens_servico`).
- Atributos: `http.method`, `http.route`, `http.status_code`, `db.system`, `db.operation`,
  `messaging.system`, `peer.service`, sem IDs de usuário.
- Registre erro com `record_exception` + `set_status(ERROR)` uma vez.
- Amostragem consistente entre serviços para não quebrar o trace.
- Em fila, propague contexto na mensagem (atributos) e crie span de produtor/consumidor.
- Use trace para achar o **gargalo**: duração do span filho vs tempo total; spans órfãos
  indicam propagação quebrada; trace ausente indica instrumentação/sampling.

---

## 9. Kubernetes e infra

- `kube-state-metrics`: estado desejado/observado (réplicas, restarts, phases, PDB).
- `node-exporter`: CPU, memória, disco, rede, load, pressão.
- `cAdvisor`: uso por container, throttling, OOM, working set.
- `kubelet`/API: latência, erros, liderança, fila de trabalho.
- Em cloud gerenciado, control plane pode ser invisível: use métricas do provedor.
- Scrape: `ServiceMonitor`/`PodMonitor` com labels corretos; confirme em
  `Targets` do Prometheus antes de culpar a app.
- `up == 0` e `absent` são alertas de cobertura, não de negócio.

Saturação que precede incidente:

```promql
# CPU throttling
sum by (namespace, pod) (rate(container_cpu_cfs_throttled_periods_total[5m]))
/
clamp_min(sum by (namespace, pod) (rate(container_cpu_cfs_periods_total[5m])), 0.001)

# disco enchendo
node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} < 0.15

# load alto vs CPU
node_load1 / count by (instance) (node_cpu_seconds_total{mode="idle"})
```

---

## 10. DORA no Prometheus (padrão do repo)

```promql
# Deployment Frequency (syncs bem-sucedidos)
sum(increase(argocd_app_sync_total{phase="Succeeded"}[1d]))

# Change Failure Rate
sum(increase(argocd_app_sync_total{phase=~"Failed|Error"}[1d]))
/
clamp_min(sum(increase(argocd_app_sync_total[1d])), 1)

# Lead Time (publicado pelo CI no Pushgateway)
quantile_over_time(0.50, dora_lead_time_seconds[7d])
quantile_over_time(0.90, dora_lead_time_seconds[7d])

# MTTR aproximado por rollout Degraded
sum(changes(rollout_info{phase="Degraded"}[7d])) / 2
```

Limitações a declarar: `argocd_app_sync_total` mede sync, não valor entregue; CFR por sync
não captura falha que só aparece horas depois; Lead Time via Pushgateway depende do CI e do
`github-sha`; MTTR por `rollout_info` é aproximação. Complemente com incidentes reais.

---

## 11. Custo e cardinalidade

- Uma label com 1 milhão de valores pode inviabilizar o Prometheus.
- Estime séries: `métricas × valores por label × alvos`. Monitore
  `prometheus_tsdb_head_series` e `scrape_samples_scraped`.
- Retenção maior não substitui agregação; use recording rules para consultas pesadas.
- Reduza logs de debug, amostre traces, agregue métricas.
- Separe retenção de negócio (SLO) de debug (curta).
- Alerta de crescimento de custo de telemetria por serviço/time.
- Não use Prometheus como banco de eventos/auditoria.

---

## 12. Checklist de observabilidade de um serviço

- [ ] SLI e SLO documentados, com query versionada.
- [ ] Dashboard com impacto no topo e links para logs/traces.
- [ ] Alertas de sintoma + burn rate, com runbook e dono.
- [ ] Métricas com labels de baixa cardinalidade e unidades corretas.
- [ ] Logs estruturados, sem PII, com `trace_id` e retenção definida.
- [ ] Traces cobrindo jornada crítica, com propagação e sampling.
- [ ] Scrape/alvos monitorados; alerta de cegueira (`up`, `absent`).
- [ ] Eventos de deploy correlacionados no dashboard.
- [ ] Pipeline OTel com memória limitada, batch e monitoração.
- [ ] Custo de telemetria revisado e orçado.
