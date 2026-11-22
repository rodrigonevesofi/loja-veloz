# Plataforma do cluster (pré-requisitos do app)

Instalado uma vez por cluster pela equipe de plataforma/SRE. O pipeline do app **não** mexe aqui.

| Componente | Para quê | Instalação |
|---|---|---|
| Istio (perfil `default` + **Istio CNI**) | mTLS, retries/timeouts, canary, Gateway API | `istioctl install --set profile=default --set components.cni.enabled=true` |
| Gateway API CRDs | `Gateway`/`HTTPRoute` | `kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.1/standard-install.yaml` |
| kube-prometheus-stack | Prometheus, Alertmanager, Grafana, ServiceMonitor/PrometheusRule | `helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack -n monitoring` |
| OpenTelemetry Collector | recebe OTLP, tail sampling, coleta logs | `helm upgrade --install otel-collector open-telemetry/opentelemetry-collector -n observability -f helm/otel-collector.values.yaml` |
| Grafana Tempo + Loki | armazenamento de traces e logs | `helm upgrade --install tempo grafana/tempo -n observability` / `helm upgrade --install loki grafana/loki -n observability` |
| External Secrets Operator | Secrets a partir do AWS Secrets Manager | `helm upgrade --install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace` |
| cert-manager | certificados TLS do Gateway | `helm upgrade --install cert-manager jetstack/cert-manager -n cert-manager --create-namespace --set crds.enabled=true` |
| Vertical Pod Autoscaler | recomendações de requests/limits | `helm upgrade --install vpa fairwinds-stable/vpa -n kube-system` |
| metrics-server | métricas de CPU/memória para o HPA | já incluso como add-on no EKS (Terraform) |

Depois: `kubectl apply -k deploy/k8s/platform`.

> Por que Istio CNI? Sem ele, cada pod recebe o init container `istio-init`, que precisa de
> `NET_ADMIN`/`NET_RAW` e seria **rejeitado** pelo Pod Security Admission `restricted` do namespace
> `loja-veloz`. Alternativa equivalente: Istio **ambient mode** (sem sidecars).
