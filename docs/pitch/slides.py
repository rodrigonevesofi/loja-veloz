"""Renderiza os slides do pitch em PNG 1920x1080 (Pillow).

    python docs/pitch/slides.py            # gera docs/pitch/out/slides/*.png

Os dados de evidência são reais: saída do smoke test, trechos do Dockerfile e dos
manifests lidos do próprio repositório e jobs da última execução do GitHub Actions
(buscados na API pública; sem rede, usa o cache em out/actions.json).
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from roteiro import AUTOR, CURSO, DISCIPLINA, REPO, SLIDES  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "out"
W, H = 1920, 1080

BG = "#0d1715"
PANEL = "#15221f"
PANEL2 = "#1b2c28"
LINE = "#2a3f3a"
TEXT = "#e8f2ef"
MUTED = "#93a8a2"
ACCENT = "#2dd4bf"
GREEN = "#4ade80"
AMBER = "#fbbf24"
BLUE = "#60a5fa"
RED = "#f87171"
TERM = "#0a0f0e"

FONT_DIRS = ["C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu"]


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    files = {
        "r": ["segoeui.ttf", "DejaVuSans.ttf"],
        "b": ["segoeuib.ttf", "DejaVuSans-Bold.ttf"],
        "sb": ["seguisb.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"],
        "m": ["consola.ttf", "DejaVuSansMono.ttf"],
        "mb": ["consolab.ttf", "DejaVuSansMono-Bold.ttf"],
    }[name]
    for d in FONT_DIRS:
        for f in files:
            if Path(d, f).exists():
                return ImageFont.truetype(str(Path(d, f)), size)
    return ImageFont.load_default(size)


class Slide:
    def __init__(self, n: int, total: int, kicker: str, title: str, subtitle: str = ""):
        self.im = Image.new("RGB", (W, H), BG)
        self.d = ImageDraw.Draw(self.im)
        d = self.d
        d.rectangle([0, 0, W, 8], fill=ACCENT)
        d.text((96, 64), kicker.upper(), font=font("b", 24), fill=ACCENT)
        d.text((W - 96, 64), "PEDIDOS VELOZ", font=font("b", 24), fill=MUTED, anchor="ra")
        d.text((96, 108), title, font=font("b", 64), fill=TEXT)
        if subtitle:
            d.text((98, 196), subtitle, font=font("r", 32), fill=MUTED)
        d.line([96, H - 92, W - 96, H - 92], fill=LINE, width=2)
        d.text((96, H - 70), f"{AUTOR} · {CURSO}", font=font("r", 24), fill=MUTED)
        d.text((W - 96, H - 70), f"{n:02d} / {total:02d}", font=font("b", 24), fill=MUTED, anchor="ra")
        for i in range(total):  # barra de progresso
            x = 760 + i * 36
            d.rounded_rectangle([x, H - 60, x + 26, H - 54], 3, fill=ACCENT if i < n else LINE)

    # ---- primitivas -------------------------------------------------------------
    def box(self, xy, fill=PANEL, outline=LINE, r=18, width=2):
        self.d.rounded_rectangle(xy, r, fill=fill, outline=outline, width=width)

    def card(self, x, y, w, h, title, body="", color=ACCENT, title_size=34, body_size=26):
        self.box([x, y, x + w, y + h])
        self.d.rounded_rectangle([x, y, x + 8, y + h], 4, fill=color)
        ty = self.text_block(x + 32, y + 26, title, w - 64, font("b", title_size), TEXT, spacing=6)
        if body:
            self.text_block(x + 32, ty + 12, body, w - 64, font("r", body_size), MUTED)

    def text_block(self, x, y, text, width, f, fill, spacing=10):
        for para in text.split("\n"):
            line = ""
            for word in para.split():
                trial = f"{line} {word}".strip()
                if self.d.textlength(trial, font=f) > width and line:
                    self.d.text((x, y), line, font=f, fill=fill)
                    y += f.size + spacing
                    line = word
                else:
                    line = trial
            self.d.text((x, y), line, font=f, fill=fill)
            y += f.size + spacing
        return y

    def bullets(self, x, y, items, width, size=30, color=ACCENT, gap=22):
        f = font("r", size)
        for it in items:
            self.d.ellipse([x, y + size * 0.45, x + 12, y + size * 0.45 + 12], fill=color)
            y = self.text_block(x + 30, y, it, width - 30, f, TEXT, spacing=8) + gap - 8
        return y

    def terminal(self, xy, title, lines, size=26):
        x0, y0, x1, y1 = xy
        self.box(xy, fill=TERM)
        self.d.rounded_rectangle([x0, y0, x1, y0 + 52], 18, fill=PANEL2)
        self.d.rectangle([x0, y0 + 30, x1, y0 + 52], fill=PANEL2)
        for i, c in enumerate([RED, AMBER, GREEN]):
            self.d.ellipse([x0 + 24 + i * 28, y0 + 18, x0 + 40 + i * 28, y0 + 34], fill=c)
        self.d.text((x0 + 120, y0 + 12), title, font=font("r", 22), fill=MUTED)
        y = y0 + 76
        for ln in lines:
            color = TEXT
            if ln.startswith("$"):
                color = ACCENT
            elif "[OK]" in ln or "success" in ln:
                color = GREEN
            elif ln.startswith("#"):
                color = MUTED
            self.d.text((x0 + 32, y), ln, font=font("m", size), fill=color)
            y += size + 12

    def arrow(self, x1, y1, x2, y2, color=MUTED, width=4, label=""):
        self.d.line([x1, y1, x2, y2], fill=color, width=width)
        import math

        a = math.atan2(y2 - y1, x2 - x1)
        s = 16
        p = [
            (x2, y2),
            (x2 - s * math.cos(a - 0.45), y2 - s * math.sin(a - 0.45)),
            (x2 - s * math.cos(a + 0.45), y2 - s * math.sin(a + 0.45)),
        ]
        self.d.polygon(p, fill=color)
        if label:
            self.d.text(
                ((x1 + x2) / 2, (y1 + y2) / 2 - 18), label, font=font("r", 22), fill=MUTED, anchor="ms"
            )

    def check(self, cx, cy, r, color=GREEN, ok=True):
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        if ok:
            k = r / 16
            self.d.line(
                [(cx - 8 * k, cy), (cx - 2 * k, cy + 7 * k), (cx + 9 * k, cy - 7 * k)],
                fill=BG,
                width=max(3, int(4 * k)),
                joint="curve",
            )
        else:
            self.d.line([(cx - 7, cy), (cx + 7, cy)], fill=BG, width=4)

    def node(self, x, y, w, h, title, sub="", color=ACCENT, fill=PANEL):
        self.box([x, y, x + w, y + h], fill=fill, outline=color, width=3)
        cy = y + h / 2
        self.d.text((x + w / 2, cy - (14 if sub else 0)), title, font=font("b", 30), fill=TEXT, anchor="mm")
        if sub:
            self.d.text((x + w / 2, cy + 22), sub, font=font("r", 21), fill=MUTED, anchor="mm")


# ---- dados reais -------------------------------------------------------------------
def actions_jobs() -> dict:
    cache = OUT / "actions.json"
    try:
        api = "https://api.github.com/repos/rodrigonevesofi/loja-veloz/actions/runs?branch=main&event=push&status=success&per_page=1"
        run = json.load(urllib.request.urlopen(api, timeout=10))["workflow_runs"][0]  # noqa: S310
        jobs = json.load(urllib.request.urlopen(run["jobs_url"] + "?per_page=50", timeout=10))["jobs"]  # noqa: S310
        data = {
            "run": run["run_number"],
            "sha": run["head_sha"][:7],
            "jobs": [
                {
                    "name": j["name"],
                    "conclusion": j["conclusion"],
                    "started": j["started_at"],
                    "completed": j["completed_at"],
                }
                for j in jobs
            ],
        }
        cache.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return data
    except Exception:  # noqa: BLE001 - sem rede: usa a última coleta
        return json.loads(cache.read_text(encoding="utf-8"))


def trecho(path: str, inicio: str, n: int) -> list[str]:
    linhas = (ROOT / path).read_text(encoding="utf-8").splitlines()
    i = next(k for k, ln in enumerate(linhas) if inicio in ln)
    return [re.sub(r"\s+#.*$", "", ln).rstrip() for ln in linhas[i : i + n]]


# ---- slides ------------------------------------------------------------------------
def s_capa(s: Slide):
    d = s.d
    d.rectangle([0, 8, W, H], fill=BG)
    d.rectangle([0, 0, 24, H], fill=ACCENT)
    d.text((140, 250), "CLOUD DEVOPS · PITCH", font=font("b", 30), fill=ACCENT)
    d.text((136, 300), "Pedidos Veloz", font=font("b", 132), fill=TEXT)
    d.text((142, 470), "Entrega contínua de microsserviços:", font=font("r", 44), fill=MUTED)
    d.text(
        (142, 528),
        "do Docker Compose ao Kubernetes, com CI/CD e observabilidade",
        font=font("r", 44),
        fill=MUTED,
    )
    d.line([142, 640, 900, 640], fill=LINE, width=2)
    d.text((142, 676), AUTOR, font=font("b", 48), fill=TEXT)
    d.text((142, 744), f"{CURSO}  ·  {DISCIPLINA}", font=font("r", 32), fill=MUTED)
    d.text((142, 820), REPO, font=font("m", 32), fill=ACCENT)


def s_problema(s: Slide):
    cards = [
        (
            "Deploys derrubam a produção",
            "Indisponibilidade a cada atualização: deploy manual, sem health check.",
            RED,
        ),
        ("Não escala no pico", "Capacidade fixa, máquinas configuradas à mão por cada time.", AMBER),
        (
            "Falhas sem rastreio",
            "Logs soltos por máquina; ninguém sabe em qual serviço o erro começou.",
            BLUE,
        ),
    ]
    for i, (t, b, c) in enumerate(cards):
        s.card(96 + i * 584, 300, 552, 340, t, b, color=c, title_size=36, body_size=28)
    s.box([96, 690, W - 96, 880], fill=PANEL2, outline=ACCENT)
    s.d.text((140, 735), "Prazo: 4 semanas até a campanha promocional", font=font("b", 40), fill=TEXT)
    s.d.text(
        (140, 800),
        "Objetivo: MVP com deploy seguro, escala automática e telemetria ponta a ponta.",
        font=font("r", 30),
        fill=MUTED,
    )


def s_arquitetura(s: Slide):
    s.node(96, 470, 220, 110, "Cliente", "HTTPS", color=MUTED)
    s.node(380, 470, 260, 110, "gateway", "entrada única")
    s.node(720, 300, 300, 130, "pedidos", "saga + idempotência")
    s.node(720, 640, 300, 120, "estoque", "reserva FOR UPDATE")
    s.node(1110, 300, 300, 130, "pagamentos", "stateless")
    s.node(1500, 300, 324, 130, "Provedor externo", "cartão / PIX", color=MUTED)
    s.node(1110, 640, 300, 120, "PostgreSQL", "1 banco por serviço", color=BLUE)
    s.arrow(316, 525, 380, 525)
    s.arrow(640, 505, 720, 380)
    s.arrow(640, 550, 720, 690)
    s.d.text((545, 400), "/api/pedidos", font=font("m", 22), fill=MUTED)
    s.d.text((520, 640), "/api/produtos", font=font("m", 22), fill=MUTED)
    s.arrow(1020, 365, 1110, 365, label="2 cobrar")
    s.arrow(1410, 365, 1500, 365)
    s.arrow(860, 430, 860, 640)
    s.d.text((880, 505), "1 reservar", font=font("r", 22), fill=MUTED)
    s.d.text((880, 535), "3 baixar / liberar", font=font("r", 22), fill=MUTED)
    s.arrow(1020, 700, 1110, 700, color=BLUE)
    s.arrow(1000, 430, 1120, 640, color=BLUE)
    s.box([1500, 520, 1824, 880], fill=PANEL2, outline=ACCENT)
    s.d.text((1530, 548), "Sem mensageria", font=font("b", 30), fill=TEXT)
    s.text_block(
        1530,
        600,
        "no MVP: o cliente precisa da resposta na hora. Próximo passo: outbox + broker.",
        270,
        font("r", 25),
        MUTED,
    )
    s.box([96, 800, 1410, 880], fill=PANEL)
    s.d.text(
        (126, 822),
        "Falhou o pagamento? A saga compensa: libera a reserva no estoque (idempotente)",
        font=font("r", 28),
        fill=TEXT,
    )


def s_demo(s: Slide, jobs: dict):
    s.terminal(
        [96, 260, 1180, 900],
        "terminal — ambiente local",
        [
            "$ docker compose up -d --build --wait",
            "# 9 contêineres com healthcheck: 4 serviços, postgres,",
            "# otel-collector, jaeger, prometheus, grafana",
            "",
            "$ python scripts/smoke_test.py",
            "[OK] catálogo disponível",
            "[OK] pedido criado",
            "[OK] idempotência",
            "[OK] consulta do pedido",
            "[OK] validação de entrada (422)",
            "pedido d61a2fa3-…  -> CONFIRMADO  total=59.90",
        ],
        size=28,
    )
    e2e = next(j for j in jobs["jobs"] if j["name"].startswith("E2E"))
    s.box([1230, 260, W - 96, 900], fill=PANEL2, outline=GREEN)
    s.d.text((1270, 296), "No GitHub Actions", font=font("b", 36), fill=TEXT)
    s.d.text((1270, 352), f"execução #{jobs['run']} · commit {jobs['sha']}", font=font("m", 24), fill=MUTED)
    s.check(1294, 454, 24)
    s.d.text((1338, 432), e2e["name"], font=font("b", 30), fill=TEXT)
    s.d.text((1338, 474), e2e["conclusion"], font=font("m", 26), fill=GREEN)
    s.text_block(
        1270,
        560,
        "Mesmo comando do desenvolvedor, executado a cada push: sobe o Compose, roda o "
        "smoke test e derruba o ambiente.",
        520,
        font("r", 28),
        MUTED,
    )


def s_observabilidade(s: Slide):
    cols = [
        (
            "Métricas",
            "Prometheus + Grafana",
            ["RED por serviço e rota", "pedidos por status e receita", "alertas por SLO: 5xx, p95"],
            AMBER,
        ),
        (
            "Logs",
            "JSON em stdout",
            ["trace_id e request_id", "uma linha por evento", "Loki no Kubernetes"],
            BLUE,
        ),
        (
            "Traces",
            "OpenTelemetry → Jaeger",
            ["contexto W3C traceparent", "spans de negócio da saga", "tail sampling em produção"],
            ACCENT,
        ),
    ]
    for i, (t, sub, items, c) in enumerate(cols):
        x = 96 + i * 584
        s.box([x, 260, x + 552, 600])
        s.d.rounded_rectangle([x, 260, x + 552, 268], 4, fill=c)
        s.d.text((x + 32, 290), t, font=font("b", 40), fill=TEXT)
        s.d.text((x + 32, 344), sub, font=font("r", 26), fill=c)
        s.bullets(x + 32, 410, items, 490, size=27, color=c, gap=16)
    s.terminal(
        [96, 640, W - 96, 900],
        "formato do log do serviço pedidos (stdout, com OpenTelemetry ativo)",
        [
            '{"level": "INFO", "service": "pedidos", "logger": "pedidos.saga", "msg": "pedido finalizado",',
            ' "pedido_id": "d61a2fa3-9504-4058-8b31-79ee86fcf6ea", "status": "CONFIRMADO",',
            ' "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "span_id": "00f067aa0ba902b7"}',
        ],
        size=25,
    )


def s_containers(s: Slide):
    code = (
        trecho("services/pedidos/Dockerfile", "FROM python", 3)
        + ["..."]
        + trecho("services/pedidos/Dockerfile", "AS runtime", 1)
        + ["..."]
        + trecho("services/pedidos/Dockerfile", "USER 10001", 1)
        + trecho("services/pedidos/Dockerfile", 'CMD ["uvicorn"', 1)
    )
    s.terminal([96, 260, 1100, 900], "services/pedidos/Dockerfile", code, size=24)
    s.bullets(
        1160,
        290,
        [
            "Multi-stage: o build fica fora da imagem final",
            "Usuário não-root (UID 10001), sem pip",
            "Tag imutável sha-<commit> + X.Y.Z; nunca :latest",
            "GHCR com SBOM e proveniência; scan Trivy no CI",
        ],
        660,
        size=31,
        gap=34,
    )


def s_kubernetes(s: Slide):
    code = (
        trecho("deploy/k8s/base/pedidos.yaml", "readinessProbe:", 3)
        + trecho("deploy/k8s/base/pedidos.yaml", "livenessProbe:", 3)
        + ["..."]
        + trecho("deploy/k8s/base/pedidos.yaml", "          securityContext:", 5)
    )
    base = min(len(c) - len(c.lstrip()) for c in code if c.strip() and c != "...")
    code = [c[base:] if c != "..." else c for c in code]
    s.terminal([96, 260, 980, 900], "deploy/k8s/base/pedidos.yaml", code, size=26)
    s.bullets(
        1040,
        280,
        [
            "Kustomize: base + overlays local, staging, prod",
            "Pod Security Admission: restricted",
            "NetworkPolicy: tudo bloqueado por padrão",
            "Istio: mTLS STRICT + autorização por identidade",
            "Secrets: AWS Secrets Manager via External Secrets",
            "PDB e réplicas espalhadas por zona",
        ],
        790,
        size=30,
        gap=26,
    )


def s_deploy(s: Slide):
    s.box([96, 260, W - 96, 560])
    s.d.text((136, 286), "ROLLING UPDATE · todos os serviços", font=font("b", 26), fill=ACCENT)
    steps = [
        ("v1", "4 pods prontos"),
        ("v1 + v2", "pod novo só recebe tráfego quando pronto"),
        ("v2", "4 pods prontos"),
    ]
    for i, (t, b) in enumerate(steps):
        x = 136 + i * 580
        s.d.text((x, 360), t, font=font("b", 44), fill=TEXT)
        s.text_block(x, 430, b, 440, font("r", 27), MUTED)
        if i < 2:
            s.arrow(x + 470, 386, x + 560, 386, color=ACCENT)
    s.d.text(
        (136, 510),
        "maxUnavailable: 0 · maxSurge: 25% · rollback automático se travar",
        font=font("m", 26),
        fill=GREEN,
    )
    s.box([96, 600, W - 96, 900], outline=AMBER)
    s.d.text((136, 626), "CANARY · serviço de pedidos (mexe com dinheiro)", font=font("b", 26), fill=AMBER)
    for i, p in enumerate([5, 10, 25]):
        x = 136 + i * 330
        s.d.text((x, 676), f"{p}% do tráfego", font=font("b", 30), fill=TEXT)
        s.d.rounded_rectangle([x, 724, x + 290, 760], 10, fill=PANEL2)
        s.d.rounded_rectangle([x, 724, x + max(24, int(290 * p / 25)), 760], 10, fill=AMBER)
    s.text_block(
        1150,
        680,
        "Gate no Prometheus a cada passo: 5xx ≤ 1% e p95 ≤ 800 ms. Falhou → peso volta a 0% em segundos.",
        630,
        font("r", 27),
        TEXT,
    )
    s.d.text(
        (136, 810),
        "Blue-green descartado: dobra a infraestrutura e não reduz o raio de impacto.",
        font=font("r", 27),
        fill=MUTED,
    )


def s_escala(s: Slide):
    rows = [
        ("Serviço", "Réplicas (prod)", "Por quê"),
        ("gateway", "3 – 10", "proxy assíncrono: CPU acompanha a carga"),
        ("pedidos", "4 – 30", "o mais exigido na campanha"),
        ("estoque", "3 – 10", "teto = pool de conexões do PostgreSQL"),
        ("pagamentos", "2 – 6", "rate limit do provedor externo"),
    ]
    y = 270
    for i, (a, b, c) in enumerate(rows):
        fill = ACCENT if i == 0 else (PANEL if i % 2 else PANEL2)
        s.d.rounded_rectangle([96, y, 1250, y + 80], 10, fill=fill)
        col = BG if i == 0 else TEXT
        f = font("b" if i == 0 else "r", 30)
        s.d.text((126, y + 22), a, font=font("b", 30) if i else f, fill=col)
        s.d.text((430, y + 22), b, font=f, fill=col)
        s.d.text((700, y + 22), c, font=font("r", 26) if i else f, fill=col if i == 0 else MUTED)
        y += 92
    s.card(
        1300,
        270,
        524,
        280,
        "HPA · CPU 65–70%",
        "Sobe rápido: +100% ou +4 pods a cada 15 s. Desce devagar: janela de 5 min.",
        color=GREEN,
        body_size=27,
    )
    s.card(
        1300,
        580,
        524,
        300,
        "VPA · modo Off",
        "Só recomenda requests. HPA e VPA na mesma métrica (CPU) brigariam.",
        color=BLUE,
        body_size=27,
    )
    s.d.text(
        (96, 760),
        "Validação: teste de carga k6 simulando o pico (150 req/s) com os mesmos limites dos SLOs.",
        font=font("r", 27),
        fill=MUTED,
    )


def s_cicd(s: Slide, jobs: dict):
    from datetime import datetime as dt

    def dur(j):
        if not j["started"] or not j["completed"]:
            return ""
        f = lambda v: dt.fromisoformat(v.replace("Z", "+00:00"))  # noqa: E731
        secs = int((f(j["completed"]) - f(j["started"])).total_seconds())
        return f"{secs // 60}m{secs % 60:02d}s" if secs >= 60 else f"{secs}s"

    s.d.text(
        (W - 96, 210),
        f"GitHub Actions · execução #{jobs['run']} · {jobs['sha']}",
        font=font("m", 26),
        fill=MUTED,
        anchor="ra",
    )
    lista = [j for j in jobs["jobs"]]
    col_h = 70
    for i, j in enumerate(lista):
        col, row = divmod(i, 8)
        x, y = 96 + col * 880, 270 + row * col_h
        ok = j["conclusion"] == "success"
        cor = GREEN if ok else MUTED
        s.d.rounded_rectangle([x, y, x + 840, y + 58], 10, fill=PANEL)
        s.check(x + 34, y + 29, 16, color=cor, ok=ok)
        nome = j["name"] if len(j["name"]) < 46 else j["name"][:44] + "…"
        s.d.text((x + 70, y + 12), nome, font=font("r", 27), fill=TEXT if ok else MUTED)
        s.d.text(
            (x + 820, y + 14),
            dur(j) if ok else "desligado (sem AWS)",
            font=font("m", 24),
            fill=MUTED,
            anchor="ra",
        )
    s.d.text(
        (96, 850),
        "Deploy já configurado, ligado quando houver conta AWS · login por OIDC, sem senha salva no GitHub"
        " · produção só com aprovação manual",
        font=font("r", 28),
        fill=ACCENT,
    )


def s_fechamento(s: Slide):
    s.card(
        96,
        270,
        860,
        300,
        "Terraform (IaC)",
        "VPC em 3 zonas, cluster EKS, PostgreSQL RDS Multi-AZ, "
        "Secrets Manager e role OIDC. Estado separado por ambiente.",
        color=BLUE,
        body_size=28,
    )
    trio = [
        ("Deploy sem medo", "rolling + canary com rollback"),
        ("Escala sob demanda", "HPA por serviço"),
        ("Falhas rastreáveis", "traces, logs e métricas"),
    ]
    for i, (t, b) in enumerate(trio):
        y = 270 + i * 104
        s.d.rounded_rectangle([1010, y, W - 96, y + 88], 12, fill=PANEL2)
        s.d.text((1040, y + 12), t, font=font("b", 32), fill=TEXT)
        s.d.text((1040, y + 52), b, font=font("r", 24), fill=MUTED)
    s.box([96, 640, W - 96, 880], fill=PANEL2, outline=ACCENT, width=3)
    s.d.text((W / 2, 700), "Repositório", font=font("b", 30), fill=MUTED, anchor="mm")
    s.d.text((W / 2, 770), REPO, font=font("mb", 54), fill=ACCENT, anchor="mm")
    s.d.text(
        (W / 2, 838),
        "README com o passo a passo · relatórios em docs/",
        font=font("r", 26),
        fill=MUTED,
        anchor="mm",
    )


TITULOS = {
    "capa": ("", "", ""),
    "problema": ("Contexto", "O problema da Loja Veloz", ""),
    "arquitetura": ("Arquitetura", "Quatro microsserviços, uma saga", "Database-per-service no PostgreSQL"),
    "demo": (
        "Demonstração",
        "O ambiente funcionando",
        "Um comando para subir tudo; o mesmo teste roda no CI",
    ),
    "observabilidade": ("Observabilidade", "Métricas, logs e traces", "Um trace_id liga os três sinais"),
    "containers": ("Contêineres", "Imagens enxutas, seguras e versionadas", ""),
    "kubernetes": ("Kubernetes", "Produção com segurança por padrão", ""),
    "deploy": ("Estratégia de deploy", "Rolling update + canary", ""),
    "escala": ("Escalabilidade", "HPA por serviço, VPA recomendando", ""),
    "cicd": ("CI/CD", "Pipeline real, todo verde", ""),
    "fechamento": ("Infraestrutura e resumo", "Tudo como código", ""),
}


def main() -> list[Path]:
    (OUT / "slides").mkdir(parents=True, exist_ok=True)
    jobs = actions_jobs()
    paths = []
    for n, (sid, _texto) in enumerate(SLIDES, 1):
        kicker, title, sub = TITULOS[sid]
        s = Slide(n, len(SLIDES), kicker, title, sub)
        fn = globals()[f"s_{sid}"]
        fn(s, jobs) if sid in ("demo", "cicd") else fn(s)
        p = OUT / "slides" / f"{n:02d}-{sid}.png"
        s.im.save(p)
        paths.append(p)
    print(f"{len(paths)} slides em {OUT / 'slides'}")
    return paths


if __name__ == "__main__":
    main()
