# Playbooks — incidentes, operação e postmortem

Em incidente, clareza vence completude. Siga o playbook, comunique cedo, mitigue antes de
entender tudo. Nunca faça duas mudanças arriscadas ao mesmo tempo.

---

## 1. Severidade

| Sev | Critério | Resposta | Comunicação |
|---|---|---|---|
| **SEV-1** | Serviço crítico indisponível, perda de dados, risco de segurança, impacto amplo | Todos disponíveis, incident commander imediato, war room | A cada 15 min; executivos/stakeholders |
| **SEV-2** | Degradação relevante, erro/latência acima do SLO, workaround existe | On-call + time do serviço, escalonamento em 15 min | A cada 30 min |
| **SEV-3** | Impacto limitado, cliente/tenant específico, sem risco de piorar | Dono trata no horário | Diária/status |
| **SEV-4** | Sem impacto ao usuário; risco, dívida, alerta cosmético | Backlog com prioridade | Semanal |

Na dúvida entre dois níveis, **assuma o mais alto** até provar o contrário. Sev não é
hierarquia de culpa; é alocação de recursos e comunicação.

---

## 2. Papéis (mesmo que uma pessoa acumule)

- **Incident Commander (IC)**: decide prioridade, coordena, mantém o tempo. Não debuga.
- **Operations Lead**: executa mitigação e coordena técnicos.
- **Communications Lead**: status para stakeholders, clientes e suporte.
- **Scribe**: linha do tempo UTC, decisões, comandos, donos.
- **Subject Matter Experts**: investigam hipóteses específicas.

Uma pessoa pode acumular, mas o IC não deve ser a mesma que executa. Em SEV-1, nomeie
explicitamente no canal: "Eu sou o IC até <hora>".

---

## 3. Primeiros 5 minutos

1. Declare o incidente, severidade e canal. Fixe o IC.
2. Responda: **quem** é afetado, **o quê** não funciona, **desde quando**, **qual** região/tenant.
3. Verifique mudanças nas últimas 24h: deploy, config, infra, feature flag, dependência.
4. Verifique o painel de SLI e o erro dominante (5xx, timeout, latência, fila).
5. Escolha a mitigação de menor risco: rollback, flag off, desvio de tráfego, pausa de fila,
   failover, escalar com cautela.
6. Comunique o primeiro status em até 15 min, mesmo sem causa.
7. Abra a linha do tempo e registre cada ação com horário e resultado.

**Não faça** nas primeiras horas: refatorar, atualizar dependência, "limpar" recursos,
mudar várias coisas juntas, reiniciar tudo sem hipótese, culpar pessoa.

---

## 4. Comunicação

Template de status:

```text
[SEV-x] <serviço> — <status: investigando/mitigando/monitorando/resolvido>
Impacto: <quem/quantos/o quê>
Início: <UTC>
Última atualização: <UTC>
Situação: <fato objetivo>
Ação atual: <mitigação em curso, dono>
Próxima atualização: <UTC + intervalo>
```

Cadência: SEV-1 15 min, SEV-2 30 min, mesmo que a atualização seja "sem mudança".
Nunca estime causa raiz publicamente antes de confirmar. Evite jargão interno.

---

## 5. Playbook — deploy quebrou o serviço

**Sinais**: erro/latência começou logo após deploy, versão nova no trace/log, canary falhando.

1. Confirme correlação temporal: horário do deploy × início do sintoma × versão nos pods/logs.
2. Pare a progressão: `kubectl argo rollouts abort <r> -n <ns>` ou flag off.
3. Se já em 100%, reverta a imagem no Git (`git revert`) e deixe o Argo CD sincronizar.
   Rollback manual no cluster cria drift; use só como ponte.
4. Valide o SLI no serviço estável e confirme que o tráfego voltou.
5. Preserve evidências: logs da versão ruim, trace, métricas, configuração.
6. Causa raiz: migração incompatível? config? dependência? carga? permissão?
7. Prevenção: análise mais forte, teste de contrato, expand/contract, canary maior, feature flag.

Não aumente timeout, réplicas ou retries como primeira ação. Pergunte o que mudou.

---

## 6. Playbook — latência alta

1. Separe **saturação** (CPU/mem/IO/conexões/fila) de **dependência** (banco/cache/API) e
   de **código** (query, lock, GC, serialização).
2. Compare p50 vs p95 vs p99: p99 alto com p50 normal sugere cauda (GC, lock, cold start,
   minoria de tenants, retry).
3. Veja trace lento: qual span domina? O tempo é no serviço ou no downstream?
4. Verifique pool de conexões, threads, event loop, GC, DNS e TLS.
5. Verifique se mudou tráfego, versão, config, índice, volume de dados.
6. Mitigue: cache, desvio, reduzir carga não crítica, escalar com cautela, rollback.
7. Corrija a causa; meça novamente com a mesma janela e query.

Diagnóstico rápido: `kubectl top`, métricas de pool, `pg_stat_activity`, latência do
downstream, `container_cpu_cfs_throttled_periods_total`.

---

## 7. Playbook — erros 5xx

1. Identifique status, rota, versão, tenant e início.
2. Se 100% em uma rota: deploy/config daquela rota, dependência específica, dados inválidos.
3. Se intermitente: capacidade, timeout, retry, conexão, concorrência, poison message.
4. Leia logs com `trace_id` e trace completo; procure a primeira exceção, não a última.
5. Verifique downstream: banco, cache, fila, API externa, DNS, TLS, certificado.
6. Mitigue com rollback/flag/desvio; preserve request de exemplo (sem PII).
7. Confirme recuperação pelo SLI e ausência de novo padrão de erro.

Nunca "resolva" 5xx silenciando log ou aumentando retry sem idempotência.

---

## 8. Playbook — Kubernetes indisponível

1. `kubectl get nodes` e `get pods -A | grep -v Running`: é cluster, nó ou workload?
2. Se API não responde: verifique endpoint, credenciais, VPN, control plane gerenciado
   (status do provedor), certificado, DNS.
3. Se nós NotReady: kubelet, CNI, disco, memória, relógio, certificado, SG/NSG.
4. Se um workload: decision tree em `references/kubernetes.md`.
5. Se todos os pods de um serviço: deployment/rollout, quota, policy, secret, imagem, PDB.
6. Evite `drain`/`delete` em massa; proteja o control plane e o storage.
7. Restaure capacidade, valide endpoints e SLI, depois investigue a causa.

Em cluster gerenciado, colete eventos e métricas do provedor antes de reiniciar nós.

---

## 9. Playbook — Lambda com erro/throttle

1. `get-function-configuration`, `list-event-source-mappings`, logs e métricas.
2. Se `Throttles`: concorrência da conta/reserva, fan-out, pico, outras funções.
3. Se `Task timed out`: init × execução; downstream, VPC/NAT, DNS, pool, timeout.
4. Se erro de código: stack, payload, dependência, variável, layer, arquitetura.
5. Se assíncrono/stream: DLQ/destination, retry, poison message, `IteratorAge`.
6. Mitigue: mover alias para versão anterior, pausar event source, aumentar concorrência
   com cautela, desviar tráfego, reprocessar DLQ após correção.
7. Corrija: idempotência, timeout coerente, memória, IAM, VPC, validação de schema.
8. Prevenção: alarmes de erro/throttle/p99/IteratorAge/DLQ e teste de carga.

Detalhes em `references/lambda.md`.

---

## 10. Playbook — banco saturado (Postgres)

1. `pg_stat_activity`: conexões por estado, queries longas, `idle in transaction`, locks.
2. `pg_locks` + `pg_blocking_pids()`: ache o bloqueador, não mate aleatoriamente.
3. `pg_stat_statements`: top por tempo total e por chamada; compare com baseline.
4. Verifique pool da app (`pool_size`, `max_overflow`, timeout), réplicas e picos.
5. Verifique IOPS, disco, CPU, memória, autovacuum, bloat, checkpoint.
6. Mitigue: cancelar query específica, matar sessão bloqueadora autorizada, reduzir carga,
   aumentar pool com cuidado, failover para réplica de leitura.
7. Corrija: índice, query, paginação, cache, arquivamento, pooler, capacidade.
8. Nunca reinicie o banco como primeira ação em produção.

Cuidado: `idle in transaction` segura locks e vacuum; `long-running` pode ser relatório.
Sempre confirme o impacto antes de encerrar sessão.

---

## 11. Playbook — fila/backlog crescendo

1. Compare taxa de produção × consumo; veja idade da mensagem mais antiga.
2. Consumidor está vivo? Erro? Throttle? Concorrência baixa? Downstream lento?
3. Há poison message bloqueando lote/shard? DLQ crescendo?
4. Mitigue: aumentar consumidores com cautela, pausar produtor não crítico, isolar poison,
   aumentar visibility timeout se correto, desviar para processamento em lote.
5. Corrija: performance do consumidor, batch, paralelismo, idempotência, capacidade downstream.
6. Reprocesse DLQ só após validar que a causa foi corrigida e que duplicatas são seguras.

---

## 12. Playbook — observabilidade fora do ar

1. Confirme: Prometheus/Grafana/Collector/Tempo/Alertmanager estão de pé?
2. Scrape targets `up == 0`? Collector com fila/drop? Disco cheio? OOM? Certificado?
3. Se a telemetria caiu, declare cegueira: use logs do provedor, métricas de infra e
   health checks diretos até restaurar.
4. Priorize restaurar **alertas e SLI** antes de dashboards históricos.
5. Verifique retenção/volume: disco cheio é causa comum em Prometheus/Tempo local.
6. Após restaurar, valide séries, regras, alertas e ausência de gaps.
7. Prevenção: HA, retenção adequada, alerta de pipeline, limite de memória, backup de config.

Lembre: `emptyDir` em Prometheus/Tempo perde dados em restart; `remote_write`/storage
persistente é requisito para produção.

---

## 13. Playbook — TLS, DNS e certificado

1. `openssl s_client -connect host:443 -servername host` e `curl -vI https://host`.
2. Verifique validade, cadeia, SAN, relógio do cliente/servidor.
3. DNS: `dig +short`, TTL, resolver correto, zona privada, split-horizon.
4. Certificado expirado: renove e recarregue; confirme automação (cert-manager/ACME).
5. Propagação: TTL alto atrasa; planeje antes. Rollback de DNS tem o mesmo TTL.
6. Nunca desative verificação TLS como correção permanente.

---

## 14. Playbook — suspeita de segurança

1. Não destrua evidências; isole o recurso comprometido (rede/credencial) sem apagar logs.
2. Acione segurança/DPO conforme política; trate como SEV-1 se dados/credenciais expostos.
3. Rotacione credenciais e revogue sessões/tokens; verifique chaves e permissões.
4. Audite CloudTrail/OCI Audit/K8s audit/Git; identifique origem e escopo.
5. Comunique conforme obrigação legal; não especule publicamente.
6. Corrija causa, adicione detecção e revise acessos. Postmortem com cuidado de PII.

---

## 15. Postmortem (blameless)

```markdown
# Postmortem — <incidente> (<data>)

## Resumo executivo
<2-4 linhas: impacto, duração, causa, status>

## Impacto
- Usuários/tenants/regiões:
- SLI/SLO e budget consumido:
- Receita/contrato (se aplicável):
- Dados afetados (sim/não, escopo):

## Linha do tempo (UTC)
| Hora | Evento | Fonte |
|---|---|---|

## Causa raiz
<factual, técnica, sem culpa individual>

## Causas contribuintes
- detecção tardia
- alerta ausente/ruidoso
- teste/cobertura
- processo/revisão
- capacidade

## O que funcionou
<rollback, alerta, runbook, comunicação>

## Ações
| Ação | Tipo (prevenção/detecção/mitigação) | Dono | Prazo | Critério de pronto |
|---|---|---|---|---|

## Lições
<2-5 bullets acionáveis>
```

Regras: sem "falta de atenção"; toda ação tem dono e prazo; no máximo 5 ações
prioritárias; revise alertas e runbook; compartilhe em até 5 dias úteis.
Acompanhe conclusão em revisão semanal até fechar.

---

## 16. On-call saudável

- Runbooks por alerta, com comandos e links, testados nos últimos 90 dias.
- Alertas acionáveis; se ninguém age, não é alerta.
- Handoff com: incidentes abertos, mudanças recentes, riscos, pendências, acesso.
- Limite de carga: incidentes por turno, toil, interrupções; meça e reduza.
- Escalonamento claro e sem medo de acordar sênior.
- Pós-turno: registrar ruído e propor correção. Plantão não é castigo.
- Acesso de emergência documentado e auditado.

---

## 17. Template de runbook

````markdown
# Runbook — <alerta/serviço>

## Sintoma
<o que o alerta/usuário vê>

## Impacto
<quem/o quê; severidade inicial>

## Verificação (read-only)
```bash
<comandos com resultado esperado>
```

## Diagnóstico
<decision tree curta: se X, então Y>

## Mitigação
```bash
<comando + rollback>
```

## Escalonamento
<quem, quando, canal>

## Validação
<SLI/query e critério de resolvido>

## Causa raiz e prevenção
<o que investigar depois>
````

Mantenha o runbook curto o suficiente para ser lido sob pressão. Um runbook que exige
30 minutos de leitura não é runbook.
