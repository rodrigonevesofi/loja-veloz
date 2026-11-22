#!/usr/bin/env bash
# Promoção progressiva (canary) do serviço de Pedidos com gate automático de qualidade.
#
#   scripts/canary.sh <tag-candidata>
#
# 1. publica a tag candidata no Deployment pedidos-canary;
# 2. aumenta o peso no VirtualService 5% -> 10% -> 25%, esperando BAKE_SECONDS em cada passo
#    (o canary recebe ~1/3 das réplicas do estável, suficiente para 25% do tráfego);
# 3. em cada passo consulta o Prometheus: taxa de 5xx e p95 do canary;
# 4. se algum limite estourar: peso volta a 0% (rollback em segundos, sem redeploy) e sai com erro;
# 5. se tudo passar: promove a tag para o Deployment estável e zera o canary.
# Evolução natural: Argo Rollouts/Flagger fazem exatamente este laço de forma declarativa.
set -euo pipefail

TAG="${1:?uso: canary.sh <tag>}"
NS="${NAMESPACE:-loja-veloz}"
IMAGE="${IMAGE_REPO:-ghcr.io/loja-veloz/loja-veloz-pedidos}:${TAG}"
PROM_URL="${PROM_URL:-http://localhost:9090}"
MAX_ERROR_RATE="${MAX_ERROR_RATE:-0.01}"   # 1% de 5xx
MAX_P95="${MAX_P95_SECONDS:-0.8}"          # 800 ms
BAKE_SECONDS="${BAKE_SECONDS:-120}"

log() { printf '[canary %s] %s\n' "$(date +%H:%M:%S)" "$*"; }

set_weights() {  # $1 = peso stable, $2 = peso canary
  kubectl -n "$NS" patch virtualservice pedidos --type=json -p \
    "[{\"op\":\"replace\",\"path\":\"/spec/http/0/route/0/weight\",\"value\":$1},
      {\"op\":\"replace\",\"path\":\"/spec/http/0/route/1/weight\",\"value\":$2}]" >/dev/null
  log "pesos: stable=$1% canary=$2%"
}

query() {  # devolve o escalar da consulta PromQL (0 se não houver amostras)
  curl -fsS --get "$PROM_URL/api/v1/query" --data-urlencode "query=$1" |
    python3 -c 'import json,sys; r=json.load(sys.stdin)["data"]["result"]; v=r[0]["value"][1] if r else "0"; print("0" if v=="NaN" else v)'
}

rollback() {
  log "ROLLBACK: $1"
  set_weights 100 0
  kubectl -n "$NS" scale deployment/pedidos-canary --replicas=0
  exit 1
}

stable=$(kubectl -n "$NS" get deployment pedidos -o jsonpath='{.status.readyReplicas}')
replicas=$(( stable / 3 > 0 ? stable / 3 : 1 ))
log "implantando $IMAGE no canary ($replicas réplica(s); estável tem $stable)"
kubectl -n "$NS" scale deployment/pedidos-canary --replicas="$replicas"
kubectl -n "$NS" set image deployment/pedidos-canary "pedidos=$IMAGE"
kubectl -n "$NS" rollout status deployment/pedidos-canary --timeout=180s || rollback "canary não ficou pronto"

SEL='service="pedidos",version="canary"'
for peso in 5 10 25; do
  set_weights $((100 - peso)) "$peso"
  sleep "$BAKE_SECONDS"
  err=$(query "sum(rate(http_requests_total{$SEL,status=~\"5..\"}[2m])) / sum(rate(http_requests_total{$SEL}[2m]))")
  p95=$(query "histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{$SEL}[2m])))")
  log "gate: erro=$err (máx $MAX_ERROR_RATE) p95=${p95}s (máx ${MAX_P95}s)"
  awk -v a="$err" -v b="$MAX_ERROR_RATE" 'BEGIN { exit !(a > b) }' && rollback "taxa de erro $err > $MAX_ERROR_RATE"
  awk -v a="$p95" -v b="$MAX_P95" 'BEGIN { exit !(a > b) }' && rollback "p95 ${p95}s > ${MAX_P95}s"
done

log "gates aprovados: promovendo $TAG para o Deployment estável (rolling update)"
kubectl -n "$NS" set image deployment/pedidos "pedidos=$IMAGE"
kubectl -n "$NS" rollout status deployment/pedidos --timeout=300s
set_weights 100 0
kubectl -n "$NS" scale deployment/pedidos-canary --replicas=0
log "concluído"
