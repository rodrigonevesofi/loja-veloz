#!/usr/bin/env python3
"""Smoke test ponta a ponta pelo API Gateway (só biblioteca padrão).

Uso: python scripts/smoke_test.py [--base-url http://localhost:8080] [--wait 60]
Usado no README (validação local), no CI (job e2e com Compose) e no CD (pós-deploy).
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid


def call(method: str, url: str, body: dict | None = None, headers: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"URL não suportada: {url}")
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})  # noqa: S310
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - URL vem do operador
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def wait_ready(base: str, seconds: int) -> None:
    deadline = time.time() + seconds
    while True:
        try:
            if call("GET", f"{base}/health/ready")[0] == 200:
                return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        if time.time() > deadline:
            sys.exit(f"gateway não ficou pronto em {seconds}s")
        time.sleep(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8080")
    ap.add_argument("--wait", type=int, default=60)
    args = ap.parse_args()
    base = args.base_url.rstrip("/")
    wait_ready(base, args.wait)

    checks: list[tuple[str, bool]] = []
    status, produtos = call("GET", f"{base}/api/produtos")
    checks.append(("catálogo disponível", status == 200 and len(produtos) > 0))

    chave = str(uuid.uuid4())
    pedido = {"cliente_id": "smoke-test", "itens": [{"sku": "SKU-003", "quantidade": 1}]}
    status, criado = call("POST", f"{base}/api/pedidos", pedido, {"Idempotency-Key": chave})
    # FALHA é aceitável aqui: o provedor simulado tem taxa de erro configurável
    checks.append(("pedido criado", status == 201 and criado["status"] in ("CONFIRMADO", "FALHA")))

    status, repetido = call("POST", f"{base}/api/pedidos", pedido, {"Idempotency-Key": chave})
    checks.append(("idempotência", status == 200 and repetido["id"] == criado["id"]))

    status, consultado = call("GET", f"{base}/api/pedidos/{criado['id']}")
    checks.append(("consulta do pedido", status == 200 and consultado["id"] == criado["id"]))

    status, _ = call("POST", f"{base}/api/pedidos", {"cliente_id": "x", "itens": []})
    checks.append(("validação de entrada (422)", status == 422))

    for nome, ok in checks:
        print(f"[{'OK' if ok else 'FALHOU'}] {nome}")
    print(f"pedido {criado.get('id')} -> {criado.get('status')} total={criado.get('total')}")
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
