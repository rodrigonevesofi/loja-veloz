"""Prepara a narração gravada (uma faixa por slide) para a montagem.

    python docs/pitch/preparar_audio.py <pasta-com-SLIDE-01.m4a ... SLIDE-11.m4a>

Para cada slide: converte, corta o silêncio das bordas (com folga), aplica filtro de graves
e normaliza o volume (todas as faixas no mesmo nível). Saída: docs/pitch/out/audio/NN-id.wav,
que é o que montar.py usa.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
from montar import FFMPEG  # noqa: E402
from roteiro import SLIDES  # noqa: E402

OUT = Path(__file__).parent / "out" / "audio"
FOLGA = 0.10  # segundos mantidos antes e depois da fala


def limites_da_fala(path: Path) -> tuple[float, float]:
    x, sr = sf.read(str(path))
    if x.ndim > 1:
        x = x.mean(axis=1)
    w = int(sr * 0.05)
    db = np.array(
        [20 * np.log10(np.sqrt(np.mean(x[i : i + w] ** 2)) + 1e-9) for i in range(0, len(x) - w, w)]
    )
    voz = np.where(db > max(db.max() - 30, -50))[0]
    ini = max(voz[0] * 0.05 - FOLGA, 0)
    fim = min((voz[-1] + 1) * 0.05 + FOLGA, len(x) / sr)
    return ini, fim


def main() -> None:
    origem = Path(sys.argv[1])
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for n, (sid, _texto) in enumerate(SLIDES, 1):
            src = origem / f"SLIDE-{n:02d}.m4a"
            bruto = Path(tmp) / f"{n:02d}.wav"
            subprocess.run(
                [
                    FFMPEG,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(src),
                    "-ac",
                    "1",
                    "-ar",
                    "48000",
                    str(bruto),
                ],
                check=True,
            )
            ini, fim = limites_da_fala(bruto)
            dest = OUT / f"{n:02d}-{sid}.wav"
            subprocess.run(
                [
                    FFMPEG,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(bruto),
                    "-ss",
                    f"{ini:.2f}",
                    "-to",
                    f"{fim:.2f}",
                    "-af",
                    "highpass=f=80,loudnorm=I=-18:TP=-2:LRA=9",
                    "-ar",
                    "48000",
                    "-ac",
                    "1",
                    str(dest),
                ],
                check=True,
            )
            dest.with_suffix(".txt").unlink(missing_ok=True)  # descarta o cache de narração sintética
            print(f"{dest.name}: {fim - ini:5.1f}s (corte {ini:.2f}–{fim:.2f}s)")


if __name__ == "__main__":
    main()
