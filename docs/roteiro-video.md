# Roteiro do vídeo pitch (até 4 minutos)

Grave a tela com áudio (OBS Studio ou Xbox Game Bar `Win+Alt+R`). Antes, deixe pronto:
`docker compose up -d --build --wait`, abas abertas no Jaeger (16686), Grafana (3000) e GitHub Actions,
um terminal na raiz do repositório e `docs/relatorio-pratico.pdf` aberto na figura de arquitetura.
Publique no YouTube como **não listado** e cole o link no README e nos dois PDFs (`docs/build_reports.py`, variável `VIDEO_URL`).

| Tempo | Tela | Fala (resumo) |
|---|---|---|
| **0:00–0:25** · Problema | Slide/README com o contexto | "A Loja Veloz tem deploys que derrubam a produção, não escala no pico e não sabe onde uma falha começa. Em 4 semanas precisamos de um MVP para a campanha. Este é o Pedidos Veloz." |
| **0:25–1:00** · Arquitetura | Figura de arquitetura do relatório | Gateway → Pedidos orquestra a saga (reserva no Estoque → cobrança em Pagamentos → baixa ou compensação). Database-per-service no PostgreSQL. Por que não há mensageria no MVP: o fluxo precisa de resposta síncrona; o próximo passo é o outbox. |
| **1:00–1:45** · Demo local | Terminal: `docker compose ps`, `python scripts/smoke_test.py`, um `curl` de pedido | "Um único comando sobe 9 contêineres com healthcheck." Mostrar o pedido `CONFIRMADO`, repetir com a mesma `Idempotency-Key` e receber o mesmo ID. |
| **1:45–2:20** · Observabilidade | Jaeger: trace do POST /api/pedidos; Grafana: dashboard | Um trace atravessa 4 serviços (spans `saga.criar_pedido`, chamadas HTTP, SQL). Dashboard RED + negócio (pedidos por status, receita). Logs JSON com o mesmo `trace_id`. Opcional: subir `PAYMENT_PROVIDER_FAILURE_RATE=0.3` e mostrar `FALHA` + `saga.compensar`. |
| **2:20–2:50** · Containers + Kubernetes | `services/pedidos/Dockerfile` e `deploy/k8s/base/pedidos.yaml` | Multi-stage, não-root UID 10001, sem pip, tag `sha-<commit>`. No K8s: probes (readiness ≠ liveness), PSA restricted, NetworkPolicy default deny, mTLS do Istio, Secrets via External Secrets. |
| **2:50–3:25** · CI/CD | GitHub Actions: execução do pipeline | Lint → testes → validação de manifests e Terraform → E2E com Compose → build + Trivy → push GHCR → staging automático → aprovação → produção. OIDC: nenhuma chave AWS guardada. |
| **3:25–3:55** · Deploy e escala | `components/istio/traffic.yaml`, `scripts/canary.sh`, HPA | Rolling update com `maxUnavailable 0` em tudo; canary 5→10→25% em Pedidos com gate de erro e p95 no Prometheus e rollback em segundos. HPA sobe rápido e desce devagar; VPA só recomenda. Teste k6 da campanha. |
| **3:55–4:00** · Fechamento | README | "Deploy sem medo, escala sob demanda e falhas rastreáveis, tudo como código." |

Dica: ensaie com cronômetro; se passar de 4 min, corte a demo de falha (1:45–2:20) para só o trace.
