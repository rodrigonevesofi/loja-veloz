"""Monta o vídeo final com ffmpeg: slide + narração por segmento, legendas e áudio normalizado.

python docs/pitch/montar.py        # -> docs/pitch/out/pitch-pedidos-veloz.mp4 (+ .srt para o YouTube)
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from roteiro import SLIDES  # noqa: E402

HERE = Path(__file__).parent
OUT = HERE / "out"
LEAD, TAIL, FPS = 0.45, 0.75, 30  # silêncio antes/depois de cada fala (s)


def tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
    for p in base.glob(f"Gyan.FFmpeg*/*/bin/{name}.exe"):
        return str(p)
    sys.exit(f"{name} não encontrado: instale o ffmpeg")


FFMPEG, FFPROBE = tool("ffmpeg"), tool("ffprobe")


def run(*args: str) -> None:
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def duracao(path: Path) -> float:
    r = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(json.loads(r.stdout)["format"]["duration"])


def ts(t: float) -> str:
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def frases(texto: str, max_chars: int = 84) -> list[str]:
    """Quebra a fala em legendas curtas (por frase e, se preciso, por vírgula)."""
    blocos = []
    for frase in re.split(r"(?<=[.!?:])\s+", texto):
        if len(frase) <= max_chars:
            blocos.append(frase)
            continue
        atual = ""
        for parte in re.split(r"(?<=,)\s+", frase):
            if atual and len(atual) + len(parte) + 1 > max_chars:
                blocos.append(atual)
                atual = parte
            else:
                atual = f"{atual} {parte}".strip()
        blocos.append(atual)
    return blocos


def main() -> None:
    segs = OUT / "segmentos"
    segs.mkdir(parents=True, exist_ok=True)
    lista, srt, t0, idx = [], [], 0.0, 1
    for n, (sid, texto) in enumerate(SLIDES, 1):
        img = OUT / "slides" / f"{n:02d}-{sid}.png"
        wav = OUT / "audio" / f"{n:02d}-{sid}.wav"
        fala = duracao(wav)
        total = LEAD + fala + TAIL
        seg = segs / f"{n:02d}.mp4"
        fade_out = max(total - 0.35, 0)
        run(
            "-loop",
            "1",
            "-framerate",
            str(FPS),
            "-t",
            f"{total:.3f}",
            "-i",
            str(img),
            "-i",
            str(wav),
            "-filter_complex",
            f"[0:v]fade=t=in:st=0:d=0.3,fade=t=out:st={fade_out:.3f}:d=0.35,format=yuv420p[v];"
            f"[1:a]aresample=48000,adelay={int(LEAD * 1000)}:all=1,apad,atrim=0:{total:.3f}[a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-tune",
            "stillimage",
            "-r",
            str(FPS),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(seg),
        )
        lista.append(f"file '{seg.as_posix()}'")
        # legendas: distribui o tempo da fala proporcionalmente ao tamanho de cada trecho
        partes = frases(texto)
        chars = sum(len(p) for p in partes)
        t = t0 + LEAD
        for p in partes:
            d = fala * len(p) / chars
            srt.append(f"{idx}\n{ts(t)} --> {ts(t + d - 0.05)}\n{p}\n")
            idx += 1
            t += d
        t0 += total
        print(f"segmento {n:02d} {sid:<16} {total:6.2f}s")

    (segs / "lista.txt").write_text("\n".join(lista), encoding="utf-8")
    srt_path = OUT / "pitch-pedidos-veloz.srt"
    srt_path.write_text("\n".join(srt), encoding="utf-8")
    bruto = OUT / "bruto.mp4"
    run("-f", "concat", "-safe", "0", "-i", str(segs / "lista.txt"), "-c", "copy", str(bruto))
    final = OUT / "pitch-pedidos-veloz.mp4"
    run(
        "-i",
        str(bruto),
        "-i",
        str(srt_path),
        "-map",
        "0:v",
        "-map",
        "0:a",
        "-map",
        "1:s",
        "-c:v",
        "copy",
        "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar",
        "48000",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=por",
        "-movflags",
        "+faststart",
        str(final),
    )
    bruto.unlink()
    print(f"\nvídeo: {final}  ({duracao(final):.1f}s)\nlegenda para o YouTube: {srt_path}")


if __name__ == "__main__":
    main()
