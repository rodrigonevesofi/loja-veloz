# Atalhos do dia a dia. Tudo aqui também pode ser executado manualmente (ver README).
SERVICES := gateway pedidos pagamentos estoque
TAG      ?= dev
REGISTRY ?= ghcr.io/rodrigonevesofi

.PHONY: help up down logs ps smoke load test lint fmt images kind-load k8s-render k8s-rules

help:            ## lista os comandos
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

up:              ## sobe toda a plataforma local (app + observabilidade)
	docker compose up -d --build --wait

down:            ## derruba e apaga volumes
	docker compose down -v

logs:            ## logs JSON de todos os serviços
	docker compose logs -f gateway pedidos pagamentos estoque

ps:
	docker compose ps

smoke:           ## teste ponta a ponta pelo gateway
	python3 scripts/smoke_test.py --base-url http://localhost:8080

load:            ## carga de campanha com k6 (veja o efeito no Grafana)
	docker run --rm -i --network host grafana/k6:0.55.0 run - < scripts/load/pico-campanha.js

test:            ## testes unitários de todos os componentes
	@for d in libs/veloz_common $(addprefix services/,$(SERVICES)); do \
	  echo "== $$d"; (cd $$d && OTEL_SDK_DISABLED=true PYTHONPATH=. python3 -m pytest -q) || exit 1; \
	done

lint:            ## ruff + hadolint + shellcheck
	ruff check . && ruff format --check .
	docker run --rm -i -v "$$PWD/.hadolint.yaml:/.config/hadolint.yaml" hadolint/hadolint:v2.12.0 < services/gateway/Dockerfile
	shellcheck scripts/*.sh deploy/compose/postgres/*.sh

fmt:
	ruff format . && ruff check --fix .
	terraform fmt -recursive infra/terraform

images:          ## build das 4 imagens com a tag $(TAG)
	@for s in $(SERVICES); do \
	  docker build -f services/$$s/Dockerfile -t $(REGISTRY)/loja-veloz-$$s:$(TAG) \
	    --build-arg APP_VERSION=$(TAG) --build-arg VCS_REF=$$(git rev-parse --short HEAD 2>/dev/null || echo local) . || exit 1; \
	done

kind-load:       ## carrega as imagens num cluster kind local
	@for s in $(SERVICES); do kind load docker-image $(REGISTRY)/loja-veloz-$$s:$(TAG) --name loja-veloz; done

k8s-render:      ## renderiza os overlays (o mesmo que o CI valida)
	@for o in local staging prod; do kubectl kustomize deploy/k8s/overlays/$$o > /tmp/loja-veloz-$$o.yaml && echo "ok $$o"; done
