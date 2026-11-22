"""Gera docs/relatorio-teorico.pdf e docs/relatorio-pratico.pdf.

    pip install reportlab
    python docs/build_reports.py

Preencha AUTOR, REPO_URL e VIDEO_URL antes de gerar a versão de entrega.
"""

from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

AUTOR = "Rodrigo Neves Vieira"
DISCIPLINA = "Cloud DevOps — Projeto de Entrega Contínua"
CURSO = "ADS 5° NA"
DATA = "Novembro de 2026"
REPO_URL = "https://github.com/rodrigonevesofi/loja-veloz"
VIDEO_URL = "https://youtu.be/SEU-LINK-AQUI"

OUT = Path(__file__).resolve().parent

# ------------------------------------------------------------------ fontes e estilos
FONTS = {
    "Body": ["C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "Body-Bold": ["C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "Body-Italic": [
        "C:/Windows/Fonts/segoeuii.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    ],
    "Mono": ["C:/Windows/Fonts/consola.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"],
}
FALLBACK = {
    "Body": "Helvetica",
    "Body-Bold": "Helvetica-Bold",
    "Body-Italic": "Helvetica-Oblique",
    "Mono": "Courier",
}
F = {}
for name, paths in FONTS.items():
    path = next((p for p in paths if Path(p).exists()), None)
    if path:
        pdfmetrics.registerFont(TTFont(name, path))
        F[name] = name
    else:
        F[name] = FALLBACK[name]
pdfmetrics.registerFontFamily(F["Body"], normal=F["Body"], bold=F["Body-Bold"], italic=F["Body-Italic"])

INK = colors.HexColor("#1f2937")
MUTED = colors.HexColor("#6b7280")
ACCENT = colors.HexColor("#0f766e")
SOFT = colors.HexColor("#ecfdf5")
LINE = colors.HexColor("#d1d5db")

S = {
    "title": ParagraphStyle(
        "t", fontName=F["Body-Bold"], fontSize=17, leading=21, textColor=INK, spaceAfter=2
    ),
    "sub": ParagraphStyle("s", fontName=F["Body"], fontSize=10.5, leading=14, textColor=ACCENT, spaceAfter=4),
    "meta": ParagraphStyle("m", fontName=F["Body"], fontSize=8.5, leading=11.5, textColor=MUTED),
    "h1": ParagraphStyle(
        "h1",
        fontName=F["Body-Bold"],
        fontSize=11.5,
        leading=14,
        textColor=ACCENT,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=1,
    ),
    "h2": ParagraphStyle(
        "h2", fontName=F["Body-Bold"], fontSize=9.6, leading=12, textColor=INK, spaceBefore=4, spaceAfter=1
    ),
    "p": ParagraphStyle(
        "p",
        fontName=F["Body"],
        fontSize=9.1,
        leading=12.2,
        textColor=INK,
        alignment=TA_JUSTIFY,
        spaceAfter=3.5,
    ),
    "li": ParagraphStyle("li", fontName=F["Body"], fontSize=9.1, leading=12, textColor=INK),
    "cell": ParagraphStyle("c", fontName=F["Body"], fontSize=8.1, leading=10.2, textColor=INK),
    "cellb": ParagraphStyle(
        "cb", fontName=F["Body-Bold"], fontSize=8.1, leading=10.2, textColor=colors.white
    ),
    "ref": ParagraphStyle(
        "r",
        fontName=F["Body"],
        fontSize=7.9,
        leading=10,
        textColor=INK,
        leftIndent=10,
        firstLineIndent=-10,
        spaceAfter=1.5,
    ),
    "code": ParagraphStyle(
        "code",
        fontName=F["Mono"],
        fontSize=7.6,
        leading=9.6,
        textColor=INK,
        backColor=SOFT,
        borderPadding=(4, 5, 4, 5),
        spaceBefore=3,
        spaceAfter=6,
    ),
}


def code(t: str) -> str:
    return f'<font face="{F["Mono"]}" size="8">{t}</font>'


def P(text, style="p"):
    return Paragraph(text, S[style])


def H1(text):
    return P(text, "h1")


def H1G(text):
    return Paragraph(text, ParagraphStyle("h1g", parent=S["h1"], keepWithNext=0))


def H2(text):
    return P(text, "h2")


def bullets(items, style="li"):
    return ListFlowable(
        [ListItem(P(i, style), leftIndent=11, value="•") for i in items],
        bulletType="bullet",
        start="•",
        leftIndent=11,
        bulletFontSize=8,
        spaceAfter=3,
    )


def table(rows, widths, header=True):
    data = [[P(c, "cellb" if header and r == 0 else "cell") for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=[w * cm for w in widths], repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), ACCENT)]
        style += [("BACKGROUND", (0, r), (-1, r), colors.HexColor("#f9fafb")) for r in range(2, len(rows), 2)]
    t.setStyle(TableStyle(style))
    t.spaceAfter = 5
    return t


def header(titulo, subtitulo):
    links = (
        f"<b>Autor:</b> {AUTOR} &nbsp;·&nbsp; <b>Curso:</b> {CURSO} &nbsp;·&nbsp; {DATA}<br/>"
        f"<b>Disciplina:</b> {DISCIPLINA}<br/>"
        f'<b>Repositório:</b> <link href="{REPO_URL}" color="#0f766e">{REPO_URL}</link> &nbsp;·&nbsp; '
        f'<b>Vídeo pitch:</b> <link href="{VIDEO_URL}" color="#0f766e">{VIDEO_URL}</link>'
    )
    rule = Table([[""]], colWidths=[17 * cm], rowHeights=[2])
    rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 1.2, ACCENT)]))
    return [P(titulo, "title"), P(subtitulo, "sub"), P(links, "meta"), Spacer(1, 4), rule, Spacer(1, 2)]


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(F["Body"], 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(2 * cm, 1.15 * cm, f"Loja Veloz · Pedidos Veloz · {doc.title}")
    canvas.drawRightString(A4[0] - 2 * cm, 1.15 * cm, f"página {doc.page}")
    canvas.restoreState()


def build(path: Path, title: str, story) -> int:
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        title=title,
        author=AUTOR,
        subject=DISCIPLINA,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.8 * cm,
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return doc.page


# ------------------------------------------------------------------ diagramas
def _box(d, x, y, w, h, label, sub="", fill="#ffffff", stroke="#0f766e"):
    d.add(
        Rect(
            x,
            y,
            w,
            h,
            rx=4,
            ry=4,
            fillColor=colors.HexColor(fill),
            strokeColor=colors.HexColor(stroke),
            strokeWidth=0.9,
        )
    )
    d.add(
        String(
            x + w / 2,
            y + h / 2 + (2 if sub else -3),
            label,
            fontName=F["Body-Bold"],
            fontSize=7.6,
            textAnchor="middle",
            fillColor=INK,
        )
    )
    if sub:
        d.add(
            String(
                x + w / 2,
                y + h / 2 - 8,
                sub,
                fontName=F["Body"],
                fontSize=6.2,
                textAnchor="middle",
                fillColor=MUTED,
            )
        )


def _arrow(d, x1, y1, x2, y2, label="", dashed=False, color="#374151", lx=0, ly=0):
    c = colors.HexColor(color)
    d.add(Line(x1, y1, x2, y2, strokeColor=c, strokeWidth=0.8, strokeDashArray=[2, 2] if dashed else None))
    import math

    a = math.atan2(y2 - y1, x2 - x1)
    s = 4.2
    p1 = (x2 - s * math.cos(a - 0.45), y2 - s * math.sin(a - 0.45))
    p2 = (x2 - s * math.cos(a + 0.45), y2 - s * math.sin(a + 0.45))
    d.add(Polygon([x2, y2, *p1, *p2], fillColor=c, strokeColor=c, strokeWidth=0.3))
    if label:
        d.add(
            String(
                (x1 + x2) / 2 + lx,
                (y1 + y2) / 2 + ly,
                label,
                fontName=F["Body"],
                fontSize=6,
                textAnchor="middle",
                fillColor=MUTED,
            )
        )


def diagrama_arquitetura() -> Drawing:
    d = Drawing(17 * cm, 6.9 * cm)
    # zona do cluster
    d.add(
        Rect(
            78,
            6,
            390,
            180,
            rx=6,
            ry=6,
            fillColor=colors.HexColor("#f8fafc"),
            strokeColor=colors.HexColor("#94a3b8"),
            strokeWidth=0.6,
            strokeDashArray=[3, 2],
        )
    )
    d.add(
        String(
            84,
            177,
            "Kubernetes · namespace loja-veloz (PSA restricted · mTLS Istio · NetworkPolicy default-deny)",
            fontName=F["Body"],
            fontSize=6.2,
            fillColor=MUTED,
        )
    )
    _box(d, 4, 92, 62, 28, "Cliente", "HTTPS", fill="#f1f5f9", stroke="#64748b")
    _box(d, 88, 92, 70, 30, "Gateway API", "Istio · TLS", fill="#ecfdf5")
    _box(d, 176, 92, 66, 30, "gateway", "roteamento /api")
    _box(d, 268, 130, 74, 32, "pedidos", "saga + idempotência")
    _box(d, 268, 52, 74, 30, "estoque", "reserva FOR UPDATE")
    _box(d, 384, 130, 74, 32, "pagamentos", "stateless · HPA ≤ 6")
    _box(d, 384, 52, 74, 30, "PostgreSQL", "RDS · db por serviço", fill="#eff6ff", stroke="#1d4ed8")
    _box(d, 384, 12, 74, 28, "otel-collector", "→ Jaeger / Tempo", fill="#fef3c7", stroke="#b45309")
    _box(d, 268, 12, 74, 28, "Prometheus", "→ Grafana · alertas", fill="#fef3c7", stroke="#b45309")
    _arrow(d, 66, 106, 88, 106)
    _arrow(d, 158, 107, 176, 107)
    _arrow(d, 242, 112, 268, 142, "/api/pedidos", lx=-14, ly=6)
    _arrow(d, 242, 100, 268, 70, "/api/produtos", lx=-16, ly=-6)
    _arrow(d, 342, 148, 384, 148, "2 cobrar", ly=3)
    _arrow(d, 296, 130, 296, 82)
    for i, txt in enumerate(["1 reservar", "3 baixar / liberar"]):
        d.add(String(300, 110 - i * 8, txt, fontName=F["Body"], fontSize=6, fillColor=MUTED))
    _arrow(d, 342, 136, 384, 75, dashed=True, color="#1d4ed8")
    _arrow(d, 342, 66, 384, 66, dashed=True, color="#1d4ed8")
    _arrow(d, 305, 40, 305, 52, dashed=True, color="#b45309")  # scrape /metrics
    _arrow(d, 342, 56, 384, 34, dashed=True, color="#b45309")  # OTLP
    d.add(String(312, 44, "scrape", fontName=F["Body"], fontSize=5.8, fillColor=colors.HexColor("#b45309")))
    d.add(String(366, 50, "OTLP", fontName=F["Body"], fontSize=5.8, fillColor=colors.HexColor("#b45309")))
    return d


def diagrama_pipeline() -> Drawing:
    d = Drawing(17 * cm, 2.5 * cm)
    etapas = [
        ("lint", "ruff·hadolint"),
        ("testes", "pytest x5"),
        ("manifests", "kubeconform"),
        ("terraform", "validate"),
        ("e2e", "compose"),
        ("build+scan", "Trivy·SBOM"),
        ("push", "GHCR sha-*"),
        ("staging", "auto"),
        ("produção", "canary"),
    ]
    w, gap, x = 48, 4.5, 2
    for i, (a, b) in enumerate(etapas):
        fill = "#ecfdf5" if i < 5 else ("#eff6ff" if i < 7 else "#fef3c7")
        _box(d, x, 22, w, 30, a, b, fill=fill)
        if i < len(etapas) - 1:
            _arrow(d, x + w, 37, x + w + gap, 37)
        x += w + gap
    d.add(String(2, 8, "CI (todo PR)", fontName=F["Body-Bold"], fontSize=6.5, fillColor=ACCENT))
    d.add(
        String(
            268,
            8,
            "artefato imutável (main/tag)",
            fontName=F["Body-Bold"],
            fontSize=6.5,
            fillColor=colors.HexColor("#1d4ed8"),
        )
    )
    d.add(
        String(
            372,
            8,
            "CD (build once, deploy many)",
            fontName=F["Body-Bold"],
            fontSize=6.5,
            fillColor=colors.HexColor("#b45309"),
        )
    )
    return d


# ------------------------------------------------------------------ relatório teórico
def relatorio_teorico():
    s = header(
        "Relatório Técnico — Parte Teórica",
        "Microsserviços, contêineres, orquestração, CI/CD e observabilidade na plataforma Pedidos Veloz",
    )
    s += [
        H1("1. Contexto"),
        P(
            "A Loja Veloz cresceu rápido e passou a ter três sintomas em produção: indisponibilidade durante deploys, "
            "dificuldade de escalar em picos e baixa rastreabilidade de falhas entre serviços. Cada time sobe partes "
            "do sistema em máquinas diferentes, sem padrão. O objetivo é um MVP em quatro semanas, antes de uma "
            "campanha promocional, que reduza o risco de deploy, encurte o tempo de entrega e torne a operação "
            "observável. Este documento fundamenta as escolhas técnicas; o relatório prático descreve a implementação."
        ),
        H1("2. Microsserviços e o papel do DevOps em ambientes cloud-native"),
        P(
            "<b>Arquitetura de microsserviços</b> é o estilo em que a aplicação é composta por serviços pequenos, "
            "implantáveis de forma independente, cada um dono de uma capacidade de negócio (<i>bounded context</i>) "
            "e dos seus dados, comunicando-se por APIs bem definidas (Lewis &amp; Fowler). Os ganhos são deploy e "
            "escala independentes, isolamento de falhas e autonomia dos times. O custo é a complexidade de um "
            "sistema distribuído: latência e falhas parciais de rede, consistência eventual (sem transações ACID entre "
            "serviços) e diagnóstico mais difícil. Por isso microsserviços só funcionam com automação e telemetria "
            "fortes, e é aí que entra o DevOps."
        ),
        P(
            "<b>DevOps</b> é a combinação de cultura, práticas e ferramentas que aproxima desenvolvimento e operação "
            "para entregar mudanças com frequência e segurança. Seu sucesso é medido pelas quatro métricas DORA: "
            "frequência de deploy, <i>lead time</i> de mudança, taxa de falha de mudanças e tempo de recuperação. Em "
            "ambientes <b>cloud-native</b> (CNCF), as aplicações são empacotadas em contêineres, orquestradas "
            "dinamicamente e gerenciadas de forma declarativa. A metodologia <b>12-Factor App</b> define as "
            "propriedades que tornam isso possível: configuração por variáveis de ambiente (III), processos stateless "
            "(VI), port binding (VII), descartabilidade com boot rápido e shutdown gracioso (IX), paridade entre "
            "ambientes (X) e logs como fluxo de eventos em stdout (XI)."
        ),
        H1("3. Conteinerização: Docker e Kubernetes"),
        P(
            "Um <b>contêiner</b> é um processo isolado pelo kernel (namespaces e cgroups) que carrega a aplicação e "
            "todas as suas dependências numa <b>imagem</b> imutável e versionada. Isso elimina o “funciona na minha "
            "máquina”: o mesmo artefato roda no notebook, no CI e em produção. Comparado a máquinas virtuais, não há "
            "um sistema operacional por instância, então sobe em segundos e usa menos recursos. Boas práticas: "
            "<i>builds</i> multi-stage, imagem base mínima, usuário não-root, dependências fixadas e tags imutáveis."
        ),
        table(
            [
                ["", "Docker / Docker Compose", "Kubernetes"],
                [
                    "Papel",
                    "Construir e executar contêineres; Compose descreve um ambiente multi-serviço num YAML",
                    "Orquestrar contêineres num cluster de várias máquinas, mantendo o estado desejado",
                ],
                ["Escopo", "Um host", "Muitos nós, zonas de disponibilidade"],
                [
                    "Resiliência e escala",
                    "restart policy; escala manual",
                    "self-healing, rolling update, rollback, HPA/VPA, PDB",
                ],
                [
                    "Rede e segurança",
                    "redes bridge, volumes",
                    "Services/DNS, NetworkPolicy, RBAC, Pod Security, Secrets",
                ],
                [
                    "Quando usar",
                    "Desenvolvimento local, testes E2E no CI, ambientes simples",
                    "Produção com alta disponibilidade, picos de tráfego e muitos serviços",
                ],
            ],
            [2.6, 7.0, 7.4],
        ),
        P(
            "Os dois se complementam: o Docker produz a imagem e o Compose dá ao time um ambiente local "
            "reproduzível com um comando; o Kubernetes executa essas mesmas imagens em produção. Usar Kubernetes "
            "localmente para todo desenvolvedor seria caro e lento; usar Compose em produção não oferece alta "
            "disponibilidade nem escala automática."
        ),
        H1("4. Orquestração de contêineres"),
        P(
            "O Kubernetes funciona por <b>reconciliação declarativa</b>: o operador descreve o estado desejado "
            "(por exemplo, “4 réplicas da imagem X, com 150m de CPU”) e controladores comparam continuamente esse "
            "estado com o real, corrigindo diferenças. Os objetos centrais são o <b>Pod</b> (unidade de execução), o "
            "<b>Deployment</b> (réplicas e atualizações), o <b>Service</b> (IP e DNS estáveis com balanceamento), "
            "<b>ConfigMaps</b> e <b>Secrets</b> (configuração separada da imagem) e o <b>HorizontalPodAutoscaler</b>. "
            "As probes definem o ciclo de vida: a <i>readiness</i> decide se o pod recebe tráfego, a <i>liveness</i> "
            "decide se deve ser reiniciado e a <i>startup</i> protege o boot. A estratégia RollingUpdate substitui "
            "pods aos poucos, só avançando quando os novos ficam prontos. Na segurança, o <b>Pod Security "
            "Admission</b> aplica os perfis <i>privileged</i>, <i>baseline</i> e <i>restricted</i> por namespace, e "
            "as <b>NetworkPolicies</b> controlam quem fala com quem. Um <b>service mesh</b> (Istio) acrescenta, sem "
            "mudar código, mTLS entre serviços, autorização por identidade, retries, timeouts, circuit breaking e "
            "divisão de tráfego por percentual, que é a base do <i>canary</i>."
        ),
        H1("5. CI/CD em ambientes distribuídos"),
        P(
            "<b>Integração contínua</b> é integrar código ao tronco várias vezes ao dia, com build e testes "
            "automáticos a cada mudança. <b>Entrega contínua</b> mantém o software sempre implantável, e "
            "<b>implantação contínua</b> leva cada mudança aprovada à produção sem intervenção manual. Com "
            "microsserviços, o pipeline precisa: (a) produzir <b>artefatos imutáveis</b> e promover a mesma imagem "
            "entre ambientes (<i>build once, deploy many</i>); (b) seguir a pirâmide de testes (muitos unitários, "
            "alguns de integração e contrato, poucos E2E); (c) validar a infraestrutura como código antes de "
            "aplicá-la; (d) proteger a cadeia de suprimentos com scan de vulnerabilidades, SBOM, proveniência e "
            "credenciais efêmeras (OIDC) em vez de chaves fixas; e (e) reduzir o raio de impacto com "
            "<b>entrega progressiva</b>: rolling, blue/green ou canary, com rollback automático guiado por métricas."
        ),
        H1("6. Observabilidade: métricas, logs e traces"),
        P(
            "Monitoramento responde a perguntas conhecidas (“a CPU passou de 80%?”); <b>observabilidade</b> é a "
            "capacidade de entender estados novos do sistema a partir dos dados que ele emite. São três sinais "
            "complementares. As <b>métricas</b> são séries numéricas baratas e agregáveis, ideais para dashboards, "
            "alertas e autoscaling; os métodos RED (taxa, erros, duração) para serviços e USE para recursos, junto "
            "com os <i>golden signals</i> do SRE, orientam o que medir, e SLIs/SLOs definem o nível aceitável. Os "
            "<b>logs</b> são eventos discretos e detalhados; estruturados em JSON e com identificadores de "
            "correlação, tornam-se pesquisáveis. Os <b>traces</b> registram o caminho de uma requisição por todos "
            "os serviços: cada operação é um <i>span</i> com início, duração e atributos, e o contexto viaja entre "
            "processos no header W3C <i>traceparent</i>. O <b>OpenTelemetry</b> (CNCF) padroniza APIs, SDKs e o "
            "protocolo OTLP para os três sinais, e o <i>Collector</i> desacopla a aplicação do backend "
            "(Jaeger, Tempo, Prometheus ou um fornecedor comercial). Em escala, controla-se o custo com "
            "amostragem (<i>head</i> ou <i>tail sampling</i>) e evitando labels de alta cardinalidade."
        ),
        H1("7. Justificativa das principais decisões"),
        table(
            [
                ["Decisão", "Alternativa considerada", "Por que escolhemos"],
                [
                    "Saga orquestrada síncrona (Pedidos coordena Estoque e Pagamentos)",
                    "Coreografia por eventos com broker",
                    "O cliente precisa da resposta na hora; menos componentes stateful para operar em 4 semanas. "
                    "Outbox + broker ficam como evolução.",
                ],
                [
                    "Database-per-service em PostgreSQL gerenciado (RDS)",
                    "Banco compartilhado; banco no cluster",
                    "Isolamento de esquema e de falhas; Multi-AZ, backups e patches sem esforço do time.",
                ],
                [
                    "Kubernetes gerenciado (EKS) + Kustomize base/overlays",
                    "Cluster próprio; Helm para o app",
                    "Menos operação do control plane; overlays deixam explícitas as diferenças entre ambientes.",
                ],
                [
                    "Rolling update em todos + canary em Pedidos",
                    "Blue/green",
                    "Zero downtime sem dobrar a capacidade; o canary limita o raio de impacto no serviço mais crítico.",
                ],
                [
                    "HPA por CPU + VPA só recomendando",
                    "VPA automático; KEDA",
                    "HPA e VPA na mesma métrica conflitam; CPU é bom sinal para serviços HTTP assíncronos.",
                ],
                [
                    "PSA restricted + NetworkPolicy + mTLS (Istio CNI)",
                    "Só NetworkPolicy",
                    "Defesa em profundidade: admissão, rede L3/L4 e identidade L7; o CNI mantém o perfil restricted.",
                ],
                [
                    "OpenTelemetry + Collector",
                    "SDK proprietário de APM",
                    "Padrão aberto, sem lock-in; o backend pode mudar sem alterar código.",
                ],
                [
                    "GitHub Actions + GHCR + OIDC na AWS",
                    "Jenkins; chaves de acesso fixas",
                    "Integrado ao repositório; credenciais efêmeras, com escopo por ambiente.",
                ],
            ],
            [5.0, 4.0, 8.0],
        ),
        KeepTogether(
            [
                H1G("8. Como a proposta ataca os problemas da Loja Veloz"),
                table(
                    [
                        ["Problema atual", "Causa raiz", "Prática adotada", "Como medir (SLI / DORA)"],
                        [
                            "Indisponibilidade em deploys",
                            "Deploy manual, sem health checks, troca brusca de versão",
                            "Rolling update com maxUnavailable 0, readiness, preStop, PDB; canary em Pedidos; rollback automático",
                            "Taxa de falha de mudanças; erros 5xx durante deploys",
                        ],
                        [
                            "Não escala no pico",
                            "Capacidade fixa, máquinas configuradas à mão",
                            "Processos stateless, HPA com scale-up agressivo, pisos de réplicas para a campanha, teste de carga k6",
                            "p95 de latência e saturação de CPU no pico",
                        ],
                        [
                            "Falhas difíceis de diagnosticar",
                            "Logs soltos por máquina, sem correlação entre serviços",
                            "OpenTelemetry (traces), logs JSON com trace_id, métricas RED e de negócio, alertas por sintoma",
                            "Tempo de recuperação (MTTR); tempo até detectar",
                        ],
                        [
                            "Entrega lenta e arriscada",
                            "Ambientes diferentes, sem testes automáticos",
                            "Compose padronizado, pipeline com gates, imagem imutável promovida entre ambientes, IaC",
                            "Lead time de mudança; frequência de deploy",
                        ],
                    ],
                    [3.2, 3.9, 6.3, 3.6],
                ),
            ]
        ),
        P(
            "<b>Riscos assumidos.</b> A saga síncrona acopla a latência do pedido à de Estoque e Pagamentos; isso é "
            "mitigado por timeouts curtos, retries apenas em falha de conexão, circuit breaker no mesh e compensação "
            "idempotente. O service mesh acrescenta latência (da ordem de milissegundos) e uma curva de aprendizado, "
            "compensadas pelo mTLS e pelo canary sem mudança de código. O banco gerenciado aumenta o custo fixo, mas "
            "tira do time a operação de backups, failover e patches justamente no período da campanha."
        ),
        H1("Referências"),
    ]
    refs = [
        "Kubernetes Documentation — Pods, Deployments, Services, ConfigMaps, Secrets, Horizontal Pod Autoscaling, "
        "Pod Security Admission, Network Policies. https://kubernetes.io/docs/",
        "Docker Docs — Multi-stage builds; Docker Compose. https://docs.docker.com/",
        "Wiggins, A. The Twelve-Factor App. https://12factor.net/",
        "HashiCorp — Terraform: modules, variables, state, S3 backend. https://developer.hashicorp.com/terraform",
        "GitHub Docs — Actions: workflows, environments, reusable workflows, OIDC. https://docs.github.com/actions",
        "Istio — Security (mTLS, AuthorizationPolicy), Traffic Management, Istio CNI. https://istio.io/latest/docs/",
        "OpenTelemetry — Concepts, Python SDK, Collector. https://opentelemetry.io/docs/",
        "Lewis, J.; Fowler, M. Microservices (2014). https://martinfowler.com/articles/microservices.html",
        "DORA / Google Cloud — Accelerate State of DevOps (métricas DORA). https://dora.dev/",
        "Case público: OpenTelemetry Demo (Astronomy Shop). https://github.com/open-telemetry/opentelemetry-demo",
    ]
    s += [P(r, "ref") for r in refs]
    return s


# ------------------------------------------------------------------ relatório prático
def relatorio_pratico():
    s = header(
        "Relatório Técnico — Parte Prática",
        "Implementação da plataforma Pedidos Veloz: do Docker Compose ao Kubernetes, com CI/CD e observabilidade",
    )
    s += [
        H1("1. Visão geral da solução"),
        P(
            "O MVP implementa os quatro serviços pedidos (API Gateway, Pedidos, Pagamentos e Estoque) em Python "
            "3.13/FastAPI, sobre um <i>microservice chassis</i> comum ("
            + code("libs/veloz_common")
            + ") que "
            "padroniza logs JSON, métricas Prometheus, tracing OpenTelemetry e health checks. O Pedidos orquestra "
            "uma saga: reserva itens no Estoque, cobra em Pagamentos e então dá baixa no estoque ou compensa "
            "(libera a reserva) se o pagamento for recusado ou falhar. Requisições repetidas com o mesmo "
            + code("Idempotency-Key")
            + " não duplicam pedidos, e o Estoque usa "
            + code("SELECT … FOR UPDATE")
            + " para impedir venda acima do disponível sob concorrência."
        ),
        diagrama_arquitetura(),
        P(
            "<i>Figura 1 — Arquitetura em produção. Setas tracejadas: dados (azul) e telemetria (laranja).</i>",
            "meta",
        ),
        Spacer(1, 3),
        table(
            [
                ["Pasta", "Conteúdo"],
                ["services/*", "Código, testes, Dockerfile multi-stage e requirements com versões exatas"],
                [
                    "docker-compose.yml, observability/",
                    "Ambiente local + Collector, Jaeger, Prometheus (alertas SLO) e Grafana",
                ],
                [
                    "deploy/k8s/",
                    "base · components (istio, canary-pedidos, monitoring, vpa) · overlays (local, staging, prod) · platform",
                ],
                [
                    ".github/workflows/",
                    "pipeline.yml (CI/CD) e deploy.yml (deploy reutilizável por ambiente)",
                ],
                [
                    "infra/terraform/",
                    "Módulo platform (VPC, EKS, RDS, Secrets Manager, IAM/OIDC) + envs/staging e envs/prod",
                ],
                [
                    "scripts/",
                    "smoke_test.py (E2E), canary.sh (promoção com gate), load/pico-campanha.js (k6)",
                ],
            ],
            [4.6, 12.4],
        ),
        H1("2. Ambiente local com Docker Compose"),
        P(
            "Todo o sistema sobe com "
            + code("docker compose up -d --build --wait")
            + ": nove contêineres (4 serviços, "
            "PostgreSQL, OpenTelemetry Collector, Jaeger, Prometheus e Grafana). A ordem de subida respeita "
            + code("depends_on: condition: service_healthy")
            + " com os HEALTHCHECKs das imagens, e um script de "
            "init cria um banco e um usuário por serviço. As variáveis têm defaults de desenvolvimento e podem ser "
            "sobrescritas por "
            + code(".env")
            + " (fora do Git). O "
            + code("docker compose watch")
            + " reconstrói o "
            "serviço ao salvar o código. Os contêineres da aplicação já rodam no dev com as restrições de produção: "
            + code("read_only")
            + ", "
            + code("cap_drop: ALL")
            + ", "
            + code("no-new-privileges")
            + " e limites de CPU e memória."
        ),
        table(
            [
                ["Rede", "Quem participa", "Motivo"],
                ["frontend", "gateway", "Único serviço publicado no host (porta 8080)"],
                ["backend", "4 serviços", "Chamadas entre microsserviços"],
                [
                    "data (internal)",
                    "postgres, pedidos, estoque",
                    "Banco sem rota externa; Pagamentos e Gateway não o alcançam",
                ],
                [
                    "telemetry",
                    "serviços + stack de observabilidade",
                    "OTLP, scrape e UIs (16686, 9090, 3000)",
                ],
            ],
            [3.0, 5.2, 8.8],
        ),
        P(
            "Volumes nomeados: "
            + code("pgdata")
            + ", "
            + code("prometheus-data")
            + " e "
            + code("grafana-data")
            + ". O README traz os comandos, as URLs e um passo a passo para simular falhas do provedor de pagamento."
        ),
        H1("3. Conteinerização e versionamento"),
        bullets(
            [
                "<b>Multi-stage:</b> o estágio <i>builder</i> instala as dependências num virtualenv (com cache do pip via "
                + code("--mount=type=cache")
                + "); o <i>runtime</i> copia só o venv e o código. "
                "Base " + code("python:3.13-slim-bookworm") + ", sem pip, sem compiladores.",
                "<b>Segurança:</b> usuário não-root com UID 10001 (o mesmo do "
                + code("runAsUser")
                + "), "
                + code("PYTHONDONTWRITEBYTECODE")
                + " para funcionar com root filesystem somente leitura, "
                + code("CMD")
                + " em forma exec (o uvicorn é PID 1 e recebe o SIGTERM para shutdown gracioso), "
                + code(".dockerignore")
                + " que exclui testes, docs e IaC do contexto, e hadolint no CI.",
                "<b>Versionamento:</b> tags imutáveis "
                + code("sha-&lt;commit&gt;")
                + " em todo push e "
                + code("X.Y.Z")
                + "/"
                + code("X.Y")
                + " em releases; nada de "
                + code(":latest")
                + ". Labels OCI ligam a imagem ao commit, "
                "e o BuildKit anexa SBOM e proveniência SLSA. Registry: GitHub Container Registry.",
            ]
        ),
        H1("4. Kubernetes — produção mínima"),
        P(
            "Os manifests usam Kustomize. A <b>base</b> contém, por serviço, ServiceAccount (sem token montado), "
            "Deployment, Service, HPA e PodDisruptionBudget, além de Namespace, ResourceQuota/LimitRange, "
            "NetworkPolicies e um ConfigMap gerado com hash no nome (mudou a configuração, roda um rolling update). "
            "<b>Components</b> opcionais adicionam Istio, canary, monitoramento e VPA; <b>overlays</b> definem "
            "local (kind, com PostgreSQL em StatefulSet), staging e produção."
        ),
        table(
            [
                ["Aspecto", "Implementação", "Justificativa"],
                [
                    "Probes",
                    "startup e liveness em /health/live; readiness em /health/ready (verifica o banco); "
                    "preStop sleep 5 s; grace 30 s",
                    "A readiness tira o pod do balanceamento quando uma dependência cai; a liveness nunca checa "
                    "dependências, para evitar reinício em cascata.",
                ],
                [
                    "Config",
                    "ConfigMap (envFrom) + variáveis específicas por contêiner",
                    "12-Factor III: a mesma imagem em todos os ambientes",
                ],
                [
                    "Secrets",
                    "local: secretGenerator (dev). staging/prod: ExternalSecret lendo o AWS Secrets Manager",
                    "Nenhuma credencial real no Git; rotação centralizada; o pod só vê um Secret comum.",
                ],
                [
                    "Pod Security",
                    "Namespace com PSA restricted (enforce/audit/warn); runAsNonRoot, "
                    "readOnlyRootFilesystem, drop ALL, seccomp RuntimeDefault",
                    "Controle nativo (substituiu a PodSecurityPolicy): pods inseguros são rejeitados na admissão, "
                    "não só detectados.",
                ],
                [
                    "Rede",
                    "Default deny + allowlist por fluxo; Pagamentos só sai para 443 público",
                    "Limita movimento lateral; o VPC CNI aplica as políticas (habilitado no Terraform).",
                ],
                [
                    "Mesh",
                    "Istio: mTLS STRICT, AuthorizationPolicy por ServiceAccount, timeouts, retries só em falha de "
                    "conexão, outlier detection",
                    "Identidade criptográfica e resiliência sem código. Istio CNI evita o "
                    "init container privilegiado e preserva o PSA restricted.",
                ],
                [
                    "Entrada",
                    "Gateway API (HTTPRoute) com Istio; TLS via cert-manager",
                    "Sucessora do Ingress; o ingress-nginx foi aposentado.",
                ],
            ],
            [2.3, 7.2, 7.5],
        ),
        H1("5. CI/CD"),
        diagrama_pipeline(),
        P(
            "O "
            + code("pipeline.yml")
            + " roda em todo PR: ruff (lint, formato e regras de segurança), hadolint, "
            "shellcheck e "
            + code("docker compose config")
            + "; pytest em matriz (chassis + 4 serviços) com relatório "
            "JUnit; renderização dos overlays com kustomize, validação de schema com kubeconform e scan de "
            "misconfiguração com Trivy; "
            + code("terraform fmt")
            + "/"
            + code("validate")
            + "; E2E subindo o Compose "
            "e rodando o smoke test; build de cada imagem com scan de vulnerabilidades (falha em CRITICAL/HIGH "
            "corrigíveis, resultado publicado em SARIF). Em "
            + code("main")
            + ", as imagens são publicadas e o "
            "workflow reutilizável "
            + code("deploy.yml")
            + " implanta em staging; em tag "
            + code("vX.Y.Z")
            + ", após aprovação no Environment "
            + code("production")
            + ", implanta em produção com canary."
        ),
        P(
            "<b>Secrets no pipeline:</b> o push no GHCR usa o "
            + code("GITHUB_TOKEN")
            + " efêmero, com "
            + code("packages: write")
            + " só no job de build. A AWS é acessada por <b>OIDC</b>: o job troca o token do "
            "GitHub por uma role temporária cuja trust policy aceita apenas "
            + code("repo:&lt;owner&gt;/&lt;repo&gt;:environment:&lt;env&gt;")
            + ", e a role só tem permissão de edição no namespace "
            + code("loja-veloz")
            + " (EKS access entry). "
            "Não há chave de acesso guardada. As permissões padrão do workflow são "
            + code("contents: read")
            + ", e o Dependabot mantém pip, Docker, Actions e Terraform atualizados."
        ),
        KeepTogether(
            [
                H1G("6. Observabilidade"),
                table(
                    [
                        ["Sinal", "Proposta implementada"],
                        [
                            "Métricas",
                            "RED por serviço e rota (http_requests_total, http_request_duration_seconds, in-flight) e "
                            "de negócio (pedidos_total{status}, receita, duração da saga, pagamentos_total{resultado}, "
                            "estoque_reservas_total{resultado}); spanmetrics no Collector. Dashboard Grafana provisionado com 12 painéis.",
                        ],
                        [
                            "Logs",
                            "JSON em stdout com ts, level, service, msg, trace_id, span_id, request_id e campos de negócio. "
                            "No Kubernetes, o Collector em DaemonSet (filelog) envia para o Loki.",
                        ],
                        [
                            "Traces",
                            "OpenTelemetry SDK + auto-instrumentação de FastAPI, httpx e psycopg, com spans de negócio "
                            "(saga.criar_pedido, saga.compensar, provedor.autorizar). Propagação W3C traceparent; exportação OTLP "
                            "para o Collector, depois Jaeger (local) ou Tempo (K8s).",
                        ],
                        [
                            "Alertas",
                            "Por sintoma, alinhados aos SLOs (99,5% de disponibilidade, p95 &lt; 500 ms): serviço fora, "
                            "5xx &gt; 5%, p95 alto, provedor instável, pedidos em FALHA &gt; 2%. Mesma regra no Compose e na PrometheusRule.",
                        ],
                    ],
                    [2.3, 14.7],
                ),
            ]
        ),
        P(
            "<b>Estratégia de tracing distribuído:</b> instrumentada (não só conceitual) e verificada em teste: uma "
            "requisição POST /pedidos gera um único trace com o span SERVER, o span da saga e as chamadas HTTP aos "
            "serviços dependentes. Localmente, 100% dos traces são amostrados. Em produção, os apps enviam tudo e o "
            "Collector faz <i>tail sampling</i>: mantém todos os traces com erro ou acima de 800 ms e 10% do "
            "restante, o que reduz custo sem perder os casos que importam."
        ),
        H1("7. Estratégia de deploy e de escalabilidade"),
        P(
            "<b>Deploy:</b> todos os serviços usam <b>rolling update</b> com "
            + code("maxSurge: 25%")
            + " e "
            + code("maxUnavailable: 0")
            + ", junto com readiness, "
            + code("minReadySeconds")
            + " e PDB, o que garante "
            "zero downtime e resolve a principal dor da empresa. Se o rollout não progredir em 180 s, o CD executa "
            + code("kubectl rollout undo")
            + ". O serviço de <b>Pedidos</b>, que movimenta dinheiro e estoque, usa "
            "<b>canary</b> em produção: "
            + code("scripts/canary.sh")
            + " sobe réplicas "
            + code("version: canary")
            + " e move o peso do VirtualService para 5%, 10% e 25%. A cada passo, consulta no Prometheus a taxa de "
            "5xx (até 1%) e o p95 (até 800 ms) apenas do canary. Se algum limite estourar, o peso volta a 0% em "
            "segundos; se tudo passar, a versão é promovida ao Deployment estável. O blue/green foi descartado porque "
            "dobra a capacidade e não reduz o raio de impacto. A evolução prevista é o Argo Rollouts ou o Flagger."
        ),
        P(
            "<b>Escala:</b> HPA autoscaling/v2 por CPU em todos os serviços stateless, com "
            + code("scaleUp")
            + " agressivo (+100% ou +4 pods a cada 15 s) para a abertura da campanha e "
            + code("scaleDown")
            + " conservador (janela de 5 min) para evitar oscilação. Os limites seguem cada gargalo: Pedidos tem de "
            "4 a 30 réplicas em produção; Estoque vai até 10, por causa do pool de conexões do PostgreSQL; Pagamentos "
            "vai até 6, de propósito, para respeitar o rate limit do provedor. O VPA roda em modo "
            + code("Off")
            + ", apenas recomendando requests, porque atuar sobre CPU junto com o HPA geraria conflito. O node group "
            "tem min/max no Terraform (com Karpenter recomendado), e o teste k6 "
            + code("pico-campanha.js")
            + " valida a escala com os mesmos limites dos SLOs."
        ),
        H1("8. Infraestrutura como código (Terraform)"),
        P(
            "O módulo "
            + code("modules/platform")
            + " usa módulos oficiais versionados (terraform-aws-modules) para "
            "criar: VPC em 3 AZs com subnets privadas, públicas e de banco; EKS com add-ons (VPC CNI com "
            "NetworkPolicy, metrics-server, Pod Identity, EBS CSI) e node group gerenciado; RDS PostgreSQL Multi-AZ, "
            "criptografado, com senha gerenciada no Secrets Manager; segredos por serviço; e as roles IAM do GitHub "
            "(OIDC) e do External Secrets (Pod Identity). As raízes "
            + code("envs/staging")
            + " e "
            + code("envs/prod")
            + " chamam o mesmo módulo com dimensionamento diferente (paridade de ambientes) e "
            "mantêm <b>states separados</b> em S3, criptografados e com lock nativo. A entrega é um esqueleto "
            "validado por " + code("terraform validate") + " no CI; aplicá-lo depende de uma conta AWS."
        ),
        H1("9. Referência pesquisada: como outros resolveram"),
        P(
            "O caso principal é o <b>OpenTelemetry Demo (Astronomy Shop)</b>, um e-commerce de referência da CNCF "
            "(github.com/open-telemetry/opentelemetry-demo) com mais de 10 microsserviços. Ele é distribuído com "
            "Docker Compose para desenvolvimento e Helm para Kubernetes, e centraliza a telemetria num OpenTelemetry "
            "Collector que exporta para Jaeger, Prometheus e Grafana, com <i>feature flags</i> para injetar falhas. "
            "Adotamos o mesmo desenho de telemetria (SDK, Collector e backends trocáveis), a paridade entre Compose e "
            "Kubernetes e a injeção de falhas configurável por variável de ambiente. O "
            "<b>Online Boutique</b> do Google Cloud (github.com/GoogleCloudPlatform/microservices-demo) inspirou a "
            "organização em Kustomize <i>components</i> opcionais (service mesh, network policies). Diferentemente "
            "dos dois, que são demos, aqui adicionamos PSA restricted, OIDC no pipeline, canary com gate e IaC."
        ),
        KeepTogether(
            [
                H1G("10. Validação executada e próximos passos"),
                bullets(
                    [
                        "<b>33 testes automatizados</b> passando (chassis 3, Estoque 9, Pedidos 9, Pagamentos 7, Gateway 5), "
                        "cobrindo a saga, a compensação, a idempotência, a concorrência no estoque, a validação de entrada e as "
                        "falhas de dependência. Ruff sem apontamentos.",
                        "<b>Pipeline real no GitHub Actions, todo verde:</b> o job E2E sobe os 9 contêineres com "
                        + code("docker compose up --wait")
                        + " e o smoke test passa nas 5 verificações (catálogo, criação, idempotência, consulta e 422); "
                        "kustomize + kubeconform validam os overlays local, staging, prod e a plataforma; Trivy sem "
                        "vulnerabilidades CRITICAL/HIGH; "
                        + code("terraform validate")
                        + " nos dois ambientes; as 4 imagens "
                        "publicadas no GHCR com SBOM e proveniência.",
                        "<b>Tracing verificado</b>: um único trace por pedido, cobrindo os spans de servidor, saga e cliente HTTP.",
                        "<b>Próximos passos:</b> outbox + broker para eventos "
                        + code("PedidoCriado")
                        + "; Argo Rollouts para o "
                        "canary declarativo; testes de contrato (Pact) entre serviços; Karpenter; policies Kyverno; e um Job de "
                        "migração de schema separado do boot da aplicação.",
                    ]
                ),
            ]
        ),
        KeepTogether(
            [
                H1G("11. Mapa de requisitos e evidências no repositório"),
                table(
                    [
                        ["Requisito do desafio", "Onde está"],
                        [
                            "Arquitetura multi-serviço; sobe com um comando; redes, volumes e variáveis",
                            "docker-compose.yml, .env.example, deploy/compose/postgres/init-db.sh, README §3",
                        ],
                        [
                            "Dockerfiles multi-stage, não-root, camadas e dependências mínimas",
                            "services/*/Dockerfile, .dockerignore, .hadolint.yaml",
                        ],
                        [
                            "Versionamento de imagens e registry",
                            "pipeline.yml (metadata-action: sha-*, X.Y.Z), GHCR",
                        ],
                        [
                            "Deployments, Services, ConfigMaps, Secrets, probes",
                            "deploy/k8s/base/*.yaml, base/config.env, overlays/*/external-secrets.yaml",
                        ],
                        [
                            "Segurança (Pod Security Admission e equivalentes)",
                            "base/namespace.yaml, base/networkpolicies.yaml, components/istio/mesh-security.yaml",
                        ],
                        [
                            "Pipeline: build, testes, publicação, lint, scan, secrets",
                            ".github/workflows/pipeline.yml e deploy.yml, .github/dependabot.yml",
                        ],
                        [
                            "Métricas, logs e traces; tracing distribuído instrumentado",
                            "libs/veloz_common, observability/, components/monitoring, platform/helm/otel-collector.values.yaml",
                        ],
                        [
                            "Estratégia de deploy (rolling + canary)",
                            "base/*.yaml (strategy), components/canary-pedidos, scripts/canary.sh",
                        ],
                        [
                            "Escalabilidade (HPA/VPA)",
                            "base/*.yaml (HPA), overlays/prod (pisos), components/vpa, scripts/load",
                        ],
                        ["IaC com Terraform", "infra/terraform/modules/platform, envs/staging, envs/prod"],
                        [
                            "Vídeo pitch",
                            "Link no README e no cabeçalho deste relatório; roteiro em docs/roteiro-video.md",
                        ],
                    ],
                    [7.0, 10.0],
                ),
            ]
        ),
    ]
    return s


if __name__ == "__main__":
    for nome, titulo, story, limite in [
        ("relatorio-teorico.pdf", "Relatório Teórico", relatorio_teorico(), (2, 3)),
        ("relatorio-pratico.pdf", "Relatório Prático", relatorio_pratico(), (3, 6)),
    ]:
        paginas = build(OUT / nome, titulo, story)
        ok = limite[0] <= paginas <= limite[1]
        print(f"{nome}: {paginas} página(s) {'OK' if ok else f'FORA DO LIMITE {limite}'}")
