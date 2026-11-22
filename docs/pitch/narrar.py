"""Gera a narração de cada slide com a voz clonada (F5-TTS + checkpoint PT-BR).

Rode com o Python do ambiente do F5-TTS:

    <venv-f5>/python docs/pitch/narrar.py --ckpt <model_last.safetensors> [--so 03]

Entrada: docs/pitch/voz/referencia.wav (≈10 s da sua voz) e REF_TEXT abaixo, que precisa
ser exatamente o que foi falado na gravação. Saída: docs/pitch/out/audio/NN-id.wav.
Um áudio só é regenerado se o texto mudar (cache por hash).
"""

import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from roteiro import SLIDES, para_fala  # noqa: E402

HERE = Path(__file__).parent
REF_WAV = HERE / "voz" / "referencia.wav"
REF_TEXT = (
    "olá, eu sou o rodrigo. neste vídeo eu vou apresentar a plataforma pedidos veloz, "
    "com contêineres, kubernétis, entrega contínua e observabilidade."
)


def preparar_ambiente() -> None:
    """Contorna duas arestas do Windows sem mexer no pacote f5-tts.

    1. torchaudio >= 2.9 lê áudio via torchcodec, que exige DLLs do FFmpeg 4–7; lemos o WAV
       de referência com soundfile, que não depende do FFmpeg.
    2. O pydub (pré-processamento da referência) precisa do executável ffmpeg no PATH.
    """
    import os
    import shutil

    import soundfile as sf
    import torch
    import torchaudio

    def _load(path, *_a, **_k):
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
        return torch.from_numpy(data.T.copy()), sr

    torchaudio.load = _load
    if not shutil.which("ffmpeg"):
        base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
        for exe in base.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"):
            os.environ["PATH"] = f"{exe.parent}{os.pathsep}{os.environ['PATH']}"
            break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument(
        "--model", default="F5TTS_Base", help="arquitetura do checkpoint (F5TTS_Base ou F5TTS_v1_Base)"
    )
    ap.add_argument("--so", default="", help="gera só os slides cujo número começa com este prefixo")
    ap.add_argument(
        "--nfe",
        type=int,
        default=16,
        help="passos de inferência: 16 ≈ 16x tempo real na CPU; 32 = melhor e 2x mais lento",
    )
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    preparar_ambiente()
    from f5_tts.api import F5TTS

    tts = F5TTS(model=args.model, ckpt_file=args.ckpt, device="cpu")
    out = HERE / "out" / "audio"
    out.mkdir(parents=True, exist_ok=True)
    for n, (sid, texto) in enumerate(SLIDES, 1):
        if args.so and not f"{n:02d}".startswith(args.so):
            continue
        fala = para_fala(texto)
        dest = out / f"{n:02d}-{sid}.wav"
        marca = dest.with_suffix(".txt")
        chave = hashlib.sha256(
            f"{fala}|{args.nfe}|{args.speed}|{args.seed}|{args.model}".encode()
        ).hexdigest()
        if dest.exists() and marca.exists() and marca.read_text(encoding="utf-8") == chave:
            print(f"[cache] {dest.name}")
            continue
        print(f"[gerando] {dest.name}: {fala[:70]}…", flush=True)
        tts.infer(
            ref_file=str(REF_WAV),
            ref_text=REF_TEXT,
            gen_text=fala,
            file_wave=str(dest),
            nfe_step=args.nfe,
            speed=args.speed,
            seed=args.seed,
            remove_silence=True,
        )
        marca.write_text(chave, encoding="utf-8")


if __name__ == "__main__":
    main()
