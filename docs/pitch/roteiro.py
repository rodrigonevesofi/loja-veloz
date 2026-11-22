"""Roteiro do vídeo pitch: texto de cada slide (vira legenda e narração).

A narração é gerada a partir da legenda por `para_fala()`, que reescreve termos técnicos
em inglês de um jeito que o modelo de voz em português pronuncia melhor.
"""

import re

AUTOR = "Rodrigo Neves Vieira"
CURSO = "ADS 5° NA"
DISCIPLINA = "Cloud DevOps — Projeto de Entrega Contínua"
REPO = "github.com/rodrigonevesofi/loja-veloz"

# (id, texto falado/legendado). Mantenha frases curtas: o modelo de voz erra menos.
SLIDES = [
    (
        "capa",
        "Olá, eu sou Rodrigo Neves Vieira, do quinto semestre de Análise e Desenvolvimento de Sistemas. "
        "Este é o pitch do projeto Pedidos Veloz, da disciplina de Cloud DevOps.",
    ),
    (
        "problema",
        "A Loja Veloz cresceu rápido e tem três problemas: deploys que derrubam a produção, "
        "dificuldade para escalar nos picos e falhas que ninguém consegue rastrear entre os serviços. "
        "E faltam só quatro semanas para uma campanha promocional.",
    ),
    (
        "arquitetura",
        "A plataforma tem quatro microsserviços. O gateway é a única entrada. "
        "O serviço de pedidos orquestra uma saga: reserva o estoque, cobra o pagamento "
        "e, se algo falhar, devolve a reserva. Cada serviço com dados tem o seu próprio banco no PostgreSQL. "
        "Não usei mensageria no MVP porque o cliente precisa da resposta na hora.",
    ),
    (
        "demo",
        "Para rodar localmente, um único comando, docker compose up, sobe nove contêineres: "
        "os quatro serviços, o banco e a observabilidade. "
        "O smoke test passa pelo gateway e valida catálogo, criação de pedido, idempotência, consulta e validação. "
        "E esse mesmo teste roda no GitHub Actions a cada mudança.",
    ),
    (
        "observabilidade",
        "Cada pedido gera um trace com OpenTelemetry que atravessa os serviços. "
        "Os logs saem em JSON com o mesmo trace id. "
        "O Prometheus coleta taxa, erros e latência, além de métricas de negócio, como pedidos por status. "
        "O Grafana já sobe com um dashboard, e os alertas seguem os SLOs.",
    ),
    (
        "containers",
        "Cada serviço tem um Dockerfile multi-stage: um estágio instala as dependências "
        "e o outro leva só o necessário. A imagem roda sem root, sem pip, "
        "e é versionada pelo hash do commit, nunca com a tag latest.",
    ),
    (
        "kubernetes",
        "No Kubernetes, uso Kustomize com uma base e um overlay por ambiente. "
        "A readiness checa o banco, e a liveness só o processo. "
        "O namespace aplica o Pod Security restricted, as network policies bloqueiam tudo por padrão, "
        "o Istio cifra o tráfego com mTLS, e os segredos vêm do Secrets Manager, nunca do Git.",
    ),
    (
        "deploy",
        "No deploy, todos os serviços usam rolling update sem derrubar réplicas. "
        "No serviço de pedidos, que mexe com dinheiro, uso canary: cinco, dez e vinte e cinco por cento do tráfego, "
        "com checagem automática de erro e latência. Se piorar, o tráfego volta em segundos. "
        "Descartei blue-green porque dobra a infraestrutura.",
    ),
    (
        "escala",
        "Para escalar, o HPA aumenta as réplicas pela CPU: sobe rápido na abertura da campanha e desce devagar. "
        "Pedidos vai até trinta réplicas, e pagamentos para em seis, por causa do limite do provedor. "
        "O VPA só recomenda recursos, para não brigar com o HPA.",
    ),
    (
        "cicd",
        "O pipeline no GitHub Actions faz lint, testes, validação dos manifests e do Terraform, "
        "teste ponta a ponta e scan de vulnerabilidades. Depois publica as imagens. "
        "O deploy usa OIDC, sem nenhuma chave guardada, e produção exige aprovação. "
        "Esta execução real está toda verde.",
    ),
    (
        "fechamento",
        "A infraestrutura também é código: o Terraform cria a rede, o cluster e o banco gerenciado. "
        "Resumindo: deploy sem medo, escala sob demanda e falhas rastreáveis. "
        "O link do repositório está na tela. Obrigado!",
    ),
]

# termos em inglês -> grafia que o modelo PT-BR pronuncia melhor (ordem importa: mais longos primeiro)
PRONUNCIA = [
    ("docker compose up", "dóquer compôus âp"),
    ("docker compose", "dóquer compôus"),
    ("dockerfile", "dóquer fáiou"),
    ("github actions", "guít rãb éctions"),
    ("cloud devops", "cláud dévópis"),
    ("pod security restricted", "pód seguiúriti restrícted"),
    ("network policies", "nét uórk pólicis"),
    ("secrets manager", "sícrets ménedjer"),
    ("rolling update", "rôlin ápdeit"),
    ("smoke test", "smôuk tést"),
    ("multi-stage", "múlti stêidj"),
    ("blue-green", "blú grín"),
    ("opentelemetry", "ôupen telemétri"),
    ("trace id", "trêis ái dí"),
    ("prometheus", "promêteus"),
    ("postgresql", "póstgres"),
    ("kubernetes", "kubernétis"),
    ("kustomize", "câstomáiz"),
    ("readiness", "rédinés"),
    ("liveness", "láivnés"),
    ("overlay", "ôverlei"),
    ("namespace", "nêimspeis"),
    ("pipeline", "páipláin"),
    ("terraform", "tera fórm"),
    ("dashboard", "déchbord"),
    ("deploys", "diplóis"),
    ("deploy", "diplói"),
    ("gateway", "gueituêi"),
    ("canary", "canéri"),
    ("grafana", "grafana"),
    ("latest", "lêitest"),
    ("commit", "comít"),
    ("istio", "ístio"),
    ("pitch", "pítch"),
    ("trace", "trêis"),
    ("json", "djêison"),
    ("lint", "línt"),
    ("scan", "iscân"),
    ("root", "rút"),
    ("mtls", "eme tê éle ésse"),
    ("oidc", "ó i dê cê"),
    ("slos", "ésse éle ós"),
    ("hpa", "agá pê á"),
    ("vpa", "vê pê á"),
    ("cpu", "cê pê u"),
    ("mvp", "eme vê pê"),
    ("pip", "pípi"),
    ("git", "guít"),
]


def para_fala(texto: str) -> str:
    """Texto da legenda -> texto para o TTS (minúsculas, sem siglas, pronúncia ajustada)."""
    t = texto.lower()
    for termo, fala in PRONUNCIA:
        t = re.sub(rf"(?<![\w-]){re.escape(termo)}(?![\w-])", fala, t)
    return re.sub(r"\s+", " ", t).strip()
