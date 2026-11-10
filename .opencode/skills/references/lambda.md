# AWS Lambda — diagnóstico, performance e operação

Lambda é um runtime efêmero com limites duros. A maioria dos incidentes vem de
**timeout, concorrência, memória, rede/VPC, IAM, evento mal formatado ou retry sem idempotência** —
não de "a AWS caiu". Sempre confirme região, conta, função, alias/versão e horário UTC.

```bash
aws sts get-caller-identity
aws configure list
aws lambda get-function-configuration --function-name <fn> --region <region>
aws lambda get-function --function-name <fn> --region <region>
```

---

## 1. Limites que mudam o diagnóstico

| Item | Limite | Implicação |
|---|---|---|
| Timeout | 1 s – 900 s (15 min) | Acima disso: Step Functions, fila, ECS/Fargate ou Batch |
| Memória | 128 MB – 10.240 MB | CPU escala proporcionalmente (~1 vCPU perto de 1.769 MB) |
| `/tmp` | 512 MB – 10.240 MB | Efêmero; persiste entre invocações do mesmo ambiente, não é compartilhado |
| Pacote ZIP | 50 MB comprimido / 250 MB descomprimido | Acima: container image (até 10 GB) |
| Camadas | 5 por função | Contam no tamanho descomprimido |
| Variáveis de ambiente | 4 KB no total | Segredo grande deve ir para Secrets Manager/SSM |
| Payload síncrono | 6 MB | API Gateway/ALB impõem limites menores (ex.: 29 s de integração) |
| Payload assíncrono | 1 MB | Evento maior deve ir para S3 e passar a referência |
| Concorrência | 1.000 por região (default, ajustável) | Conta e reserva por função; throttle afeta todas |
| Provisioned concurrency | por função/alias | Custo mesmo sem tráfego, reduz cold start |
| Retenção de logs | não automática | Defina retention; log infinito é custo e risco |
| Execução assíncrona | 2 retries por padrão | Exige idempotência, DLQ/destination |

Detalhes de limite podem variar por região/conta; confirme na documentação vigente.

---

## 2. Fluxo de triagem

```
1. A função é invocada?        Invocations, API/ALB/event source, permissão
2. Falha antes da mão?         init, layer, import, variável, VPC, IAM
3. Falha durante?              exception, timeout, OOM, dependência, payload
4. Falha depois?               retry, DLQ, destination, idempotência, poison message
5. Escala?                     Throttles, ConcurrentExecutions, fila/IteratorAge
6. Está lenta?                 InitDuration, Duration p95/p99, downstream, cold start
```

Comandos de coleta rápida:

```bash
FN=<fn>; REGION=<region>
aws lambda get-function-configuration --function-name "$FN" --region "$REGION"
aws lambda list-event-source-mappings --function-name "$FN" --region "$REGION"
aws logs tail "/aws/lambda/$FN" --since 30m --follow --region "$REGION"
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Errors \
  --dimensions Name=FunctionName,Value="$FN" --start-time "$(date -u -d '1 hour ago' +%FT%TZ)" \
  --end-time "$(date -u +%FT%TZ)" --period 60 --statistics Sum --region "$REGION"
```

Métricas essenciais: `Invocations`, `Errors`, `Duration` (p50/p95/p99/max), `Throttles`,
`ConcurrentExecutions`, `UnreservedConcurrentExecutions`, `InitDuration`, `IteratorAge`,
`DeadLetterErrors`, `DestinationDeliveryFailures`, `ProvisionedConcurrencyUtilization`.

---

## 3. Taxonomia de erro

| Sintoma | Causa provável | Confirmação | Correção |
|---|---|---|---|
| `Task timed out` | downstream lento, VPC/NAT, loop, cold start, timeout curto | `Duration` ≈ timeout, log sem erro | medir downstream, timeout coerente, async/Step Functions |
| `Runtime exited with error` | exceção não tratada, `process.exit`, OOM | log/stack, `Duration`, memória | tratar erro, limite de memória, menos alocação |
| `Runtime exited without providing a reason` | crash nativo, SIGKILL, extensão | log, `OOMKilled` não existe aqui; ver memória | investigar lib nativa, memória, runtime |
| `Throttles` / `429 TooManyRequestsException` | concorrência esgotada, burst | `ConcurrentExecutions`, `UnreservedConcurrentExecutions` | reserved/provisioned, reduzir fan-out, fila, backoff |
| `ECONNREFUSED`/`ETIMEDOUT` | VPC sem rota/NAT, SG, endpoint, DNS | testar de outra Lambda/VPC | corrigir rota/SG/endpoint |
| `AccessDenied`/`not authorized` | IAM do role, KMS, recurso cross-account | `aws lambda get-function-configuration` role, CloudTrail | policy mínima correta, condição de conta |
| `Cannot find module`/`ImportModuleError` | pacote/layer ausente, caminho, arquitetura | testar zip local, `Architectures` | empacotar certo, camada compatível |
| `ENOSPC` | `/tmp` cheio | log, uso de `/tmp` | limpar, streaming/S3, aumentar `/tmp` |
| `ENOMEM` | memória insuficiente | `Duration`, log | aumentar memória, reduzir carga, streaming |
| `InvalidSignatureException`/`403` | credencial, clock, assinatura | log, role | corrigir credencial/relógio |
| `PayloadTooLarge`/evento vazio | limite de payload, evento mal formatado | log do evento, tamanho | S3/referência, validar schema |
| `IteratorAge` crescente | consumo mais lento que produção | métrica do event source | paralelismo, batch, otimizar, shard |
| Poison message | evento inválido reprocessado | DLQ/retry, logs repetidos | validação, DLQ, idempotência, descarte |

**Importante:** em invocação assíncrona, o cliente recebe `202` e o erro aparece só em métrica,
DLQ/destination e logs. Em event source mapping, a Lambda pode reprocessar o lote inteiro.

---

## 4. Timeout — o campeão de incidentes

1. Verifique se o tempo é gasto em **init** (`InitDuration`) ou em execução.
2. Se init: pacote grande, camada, import pesado, VPC fria, extensão, provisioned concurrency.
3. Se execução: abra trace/log com duração por etapa e meça o downstream.
4. Cheque `connect` vs `read`: DNS, TLS, NAT, SG, endpoint, pool.
5. Confirme se o timeout da Lambda é **menor** que o timeout do downstream (senão você mata
   a chamada antes de receber o erro real) e maior que o p99 saudável.
6. Corrija a causa. Aumentar timeout só é correto quando o trabalho **precisa** daquele tempo.

Padrão robusto: timeout do cliente < timeout da função < timeout do evento assíncrono,
com retry apenas em erro transitório e **idempotência** em toda escrita.

---

## 5. Concorrência e throttling

```bash
aws lambda get-account-settings --region <region>
aws lambda get-function-concurrency --function-name <fn> --region <region>
aws lambda put-function-concurrency --function-name <fn> --reserved-concurrent-executions <n>
aws lambda delete-function-concurrency --function-name <fn>
aws lambda put-provisioned-concurrency-config --function-name <fn> --qualifier <alias> \
  --provisioned-concurrent-executions <n>
aws lambda get-provisioned-concurrency-config --function-name <fn> --qualifier <alias>
```

- **Throttle** não é falha da função: a invocação é rejeitada (`429`) ou fica na fila.
- Síncrono: cliente recebe 429; precisa backoff.
- Assíncrono: Lambda retenta (2x) e depois DLQ/destination.
- Event source mapping: a Lambda pausa o shard/fila e pode aumentar `IteratorAge`.
- **Reserved concurrency** isola a função, mas também limita o teto.
- **Provisioned concurrency** reduz cold start e reserva capacidade; custa parado.
- Fan-out (SNS/S3/Step Functions) pode esgotar a conta inteira: reserve funções críticas.
- `maxConcurrency` em event source mapping controla paralelismo por fila/shard.

Diagnóstico de throttle: compare `ConcurrentExecutions` com o limite da conta, verifique
outras funções, verifique reserva e picos de fan-out. Não basta aumentar reserva se o
downstream não aguenta.

---

## 6. Cold start e performance

Fontes de latência de inicialização: download do pacote, runtime, imports, SDK clients,
conexão TLS, VPC ENI (hoje via Hyperplane, mas ainda há custo), extensões e layers.

Mitigações, em ordem de custo-benefício:

1. Reduzir pacote (tree-shake, `--omit=dev`, dependências mínimas).
2. Inicializar SDK/cliente **fora do handler** (reuso entre invocações).
3. Evitar trabalho pesado no init; lazy init do que é raro.
4. Escolher runtime eficiente e arquitetura ARM64 (Graviton) quando compatível.
5. Provisioned concurrency para caminho crítico e picos previsíveis.
6. SnapStart (Java) quando aplicável.
7. Aquecer com eventos sintéticos apenas se provisioned não for opção; não confie em
   "warm keep-alive" como garantia.

Ajuste de memória:

- CPU, rede e disco escalam com memória. Mais memória pode **reduzir** custo e latência.
- Faça benchmark com carga realista em 2–3 pontos (ex.: 512, 1024, 2048 MB) e compare
  custo por invocação × p95.
- AWS Lambda Power Tuning (Step Functions) automatiza o trade-off.

```bash
# exemplo de invocação local/remota
aws lambda invoke --function-name "$FN" --region "$REGION" \
  --payload '{"test":true}' --cli-binary-format raw-in-base64-out /tmp/out.json
cat /tmp/out.json
```

Em Node, `process.env.AWS_LAMBDA_FUNCTION_MEMORY_SIZE` e `os.totalmem()` ajudam a adaptar
buffers/pools. Em Java, heap deve deixar espaço para metaspace/nativo. Em Python, evite
carregar datasets grandes por invocação.

---

## 7. VPC, rede e DNS

Se a função está em VPC:

- Subnets precisam de rota para o destino; internet exige **NAT Gateway** (ou VPC endpoint).
- Serviços AWS devem usar **VPC endpoints** (S3, DynamoDB, SQS, Secrets Manager, KMS, logs)
  para evitar NAT e latência.
- Security group de saída e do destino precisam permitir porta/ origem.
- DNS: use o resolver da VPC; `Route53 Resolver` para zonas privadas/híbridas.
- Muitas funções × subnets × ENIs: monitore limites e reutilize.
- Para RDS/ElastiCache: pool de conexões é crítico. Cada ambiente de execução pode abrir
  conexão; use RDS Proxy, pooler ou HTTP API.
- IPv6: confirme suporte do runtime, subnet e destino.

Teste de conectividade deve ser feito **de dentro da VPC**, não da sua máquina.

---

## 8. IAM, segredos e permissões

```bash
aws lambda get-function-configuration --function-name "$FN" --query Role
aws iam get-role --role-name <role>
aws iam list-attached-role-policies --role-name <role>
aws iam list-role-policies --role-name <role>
aws lambda get-policy --function-name "$FN"   # resource policy (quem invoca)
```

Checklist:

- Role de execução correto e mínimo; evite `*` em recurso.
- `kms:Decrypt` quando usar KMS/Secrets; condição de conta/região.
- Bucket/objeto, tabela, fila e tópico com ARN específico.
- Cross-account: trust policy + resource policy + permissão dos dois lados.
- Segredos em Secrets Manager/SSM; cache no init com TTL e fallback; nunca em log.
- Rotação: função precisa sobreviver a credencial expirada; trate `AccessDenied` e recarregue.
- CloudTrail é a fonte para saber **quem** negou/alterou; logs da função não mostram IAM.

---

## 9. Event sources, retries e idempotência

| Fonte | Modelo | Retry/comportamento | Cuidados |
|---|---|---|---|
| API Gateway/ALB/Function URL | síncrono | cliente decide | timeout de integração, payload, status |
| S3 | assíncrono | 2 retries + DLQ/destination | evento pode duplicar; idempotência |
| SNS | assíncrono | política de retry da assinatura | duplicatas, ordem não garantida |
| EventBridge | assíncrono | retry + DLQ | schema, regras, duplicatas |
| SQS | poll | visibility timeout + DLQ | batch, `partial batch response`, poison |
| Kinesis | poll | retry até expirar, bisect | shard, ordem por partition key, IteratorAge |
| DynamoDB Streams | poll | retry/bisect | ordem por shard, idempotência |
| Kafka/MSK | poll | offset/retry | lag, partição, commit |

Boas práticas obrigatórias:

- **Idempotência** por chave de negócio (tabela de dedup, condição no DynamoDB, `INSERT ... ON CONFLICT`).
- **DLQ ou on-failure destination** para assíncrono e event source; alarme em `DeadLetterErrors`.
- **Partial batch response** em SQS para não reprocessar lote inteiro.
- **Visibility timeout** > p99 de processamento; senão a mensagem reaparece em paralelo.
- **Ordem**: SQS standard não garante; FIFO tem custo/limite. Kinesis garante por shard.
- **Poison message**: limite de recebimentos, validação de schema, quarentena.
- **Fan-out** com controle de concorrência e backoff para não derrubar downstream.

```bash
QURL=$(aws sqs get-queue-url --queue-name <q> --query QueueUrl --output text)
aws sqs get-queue-attributes --queue-url "$QURL" \
  --attribute-names ApproximateNumberOfMessages ApproximateAgeOfOldestMessage \
  VisibilityTimeout RedrivePolicy
aws kinesis describe-stream-summary --stream-name <stream>
aws lambda list-event-source-mappings --function-name "$FN" --query 'EventSourceMappings[].[UUID,State,LastProcessingResult]'
```

`LastProcessingResult` diferente de `No records processed`/`OK` é sinal de problema.

---

## 10. Observabilidade de Lambda

Mínimo viável:

- Logs estruturados em JSON com `request_id`, `function`, `version`, `cold_start`, `duration_ms`,
  `downstream_ms`, `status`, `error.kind`; **sem PII/segredo**.
- Retenção definida no log group (não deixe "Never expire").
- Alarme em `Errors`, `Throttles`, `Duration p99`, `IteratorAge`, `DeadLetterErrors`.
- Trace com X-Ray ou OpenTelemetry/ADOT; propague contexto para downstream.
- Lambda Insights para memória/CPU/rede quando necessário (custo adicional).
- Dashboard com invocações, erros, p95/p99, throttles, concorrência e idade de fila.

CloudWatch Logs Insights:

```sql
fields @timestamp, @message, @requestId
| filter @message like /(?i)(error|exception|timeout|failed)/
| sort @timestamp desc
| limit 50
```

```sql
fields @timestamp, @duration, @billedDuration, @memorySize, @maxMemoryUsed, @requestId
| stats avg(@duration), pct(@duration, 95), pct(@duration, 99), max(@duration),
        max(@maxMemoryUsed) by bin(5m)
```

```sql
filter @type = "REPORT"
| stats count() as invocations,
        sum(@duration) as total_ms,
        max(@maxMemoryUsed / @memorySize) as max_mem_ratio
by bin(1h)
```

`@maxMemoryUsed / @memorySize` próximo de 1 é sinal para revisar memória. `@initDuration`
aparece só em cold start.

X-Ray/OTel:

```bash
aws xray get-trace-summaries --start-time "$(date -u -d '1 hour ago' +%FT%TZ)" \
  --end-time "$(date -u +%FT%TZ)" --region "$REGION"
```

Em Node/Python, inicialize o tracer **fora do handler** e faça flush antes de congelar.
Em ambientes com ADOT, use a camada/extensão e exporte para o collector.

---

## 11. Deploy, versões e rollback

```bash
aws lambda publish-version --function-name "$FN"
aws lambda create-alias --function-name "$FN" --name live --function-version <v>
aws lambda update-alias --function-name "$FN" --name live --function-version <v2>
aws lambda get-alias --function-name "$FN" --name live
```

- Use **versão imutável + alias** (`live`, `prod`) e aponte event sources/gateways para o alias.
- Canary/linear via CodeDeploy para Lambda (`deploymentPreference`) quando disponível.
- Rollback = mover o alias para a versão anterior; não edite código em produção.
- CI/CD: `sam build && sam deploy`, `cdk diff && cdk deploy`, Serverless Framework ou Terraform.
- Teste local com `sam local invoke`/`sam local start-api`; cuidado com diferenças de IAM/VPC.
- Variáveis e camadas também são mudanças: versione e possa reverter.
- Mudança de schema de evento exige compatibilidade para frente/trás.

---

## 12. Custo

- Custo ≈ invocações × duração × memória + provisioned + logs + NAT + transferência.
- Logs verbosos e retenção infinita frequentemente superam o custo de compute.
- Mais memória pode reduzir custo total por rodar menos tempo; meça.
- NAT Gateway para tráfego AWS é caro: use VPC endpoints.
- Provisioned concurrency deve ser justificado por SLO, não por "medo de cold start".
- Alarmes de budget/anomalia por função e por conta; tags de owner/cost center.

---

## 13. Checklist de produção Lambda

- [ ] Timeout, memória e arquitetura definidos com benchmark real.
- [ ] Idempotência em toda escrita; DLQ/destination com alarme.
- [ ] Reserved/provisioned concurrency revisados; downstream com capacidade.
- [ ] VPC com rotas, NAT/endpoints, SG e DNS testados de dentro.
- [ ] IAM mínimo, segredos fora de env/log, rotação suportada.
- [ ] Logs estruturados, retenção e amostragem de trace definidas.
- [ ] Alarmes de erro, throttle, p99, IteratorAge e DLQ.
- [ ] Alias/versão com rollback em 1 comando; pipeline reproduzível.
- [ ] Limites de payload e schema validados; poison message tratada.
- [ ] Runbook com Sintoma → Verificação → Mitigação → Rollback.
