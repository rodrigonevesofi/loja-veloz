// Teste de carga simulando o pico da campanha promocional (k6).
// Local:  docker run --rm -i --network host grafana/k6:0.55.0 run - < scripts/load/pico-campanha.js
// K8s:    BASE_URL=https://staging.lojaveloz.example k6 run scripts/load/pico-campanha.js
// Durante a execução, observe o HPA:  kubectl get hpa -n loja-veloz -w
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:8080";
const SKUS = ["SKU-001", "SKU-002", "SKU-003", "SKU-004"];

export const options = {
  scenarios: {
    campanha: {
      executor: "ramping-arrival-rate",
      startRate: 5,
      timeUnit: "1s",
      preAllocatedVUs: 50,
      maxVUs: 300,
      stages: [
        { target: 20, duration: "1m" },   // aquecimento
        { target: 150, duration: "2m" },  // abertura da campanha
        { target: 150, duration: "3m" },  // pico sustentado
        { target: 10, duration: "1m" },   // fim
      ],
    },
  },
  // mesmos limites dos SLOs: o teste falha se o sistema degradar
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{rota:criar_pedido}": ["p(95)<800"],
    "http_req_duration{rota:catalogo}": ["p(95)<300"],
  },
};

export default function () {
  const catalogo = http.get(`${BASE}/api/produtos`, { tags: { rota: "catalogo" } });
  check(catalogo, { "catálogo 200": (r) => r.status === 200 });

  const pedido = {
    cliente_id: `carga-${__VU}`,
    itens: [{ sku: SKUS[Math.floor(Math.random() * SKUS.length)], quantidade: 1 }],
  };
  const res = http.post(`${BASE}/api/pedidos`, JSON.stringify(pedido), {
    headers: { "Content-Type": "application/json", "Idempotency-Key": `${__VU}-${__ITER}-${Date.now()}` },
    tags: { rota: "criar_pedido" },
  });
  check(res, { "pedido 201": (r) => r.status === 201 });
  sleep(0.5);
}
