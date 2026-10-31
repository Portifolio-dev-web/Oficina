# -*- coding: utf-8 -*-
"""
Narra um vídeo com a voz "Lucas - Português BR" do ElevenLabs,
encaixando cada fala exatamente no tempo de cada bloco da legenda (.srt).

Como usar (na pasta do vídeo):
    1) Coloque sua chave da API do ElevenLabs abaixo em API_KEY
       (ou na variável de ambiente ELEVENLABS_API_KEY).
    2) python narrar_srt.py

O que ele faz:
    - lê o .srt e gera UM áudio por bloco de legenda (pasta "narracao/01.mp3", "02.mp3"...)
    - mede cada áudio; se alguma fala passar do tempo até a próxima legenda,
      acelera só aquela fala (sem mudar o tom), até o limite MAX_ACELERA
    - posiciona cada fala no milissegundo de início da legenda
    - junta tudo no vídeo, sem recomprimir a imagem -> "<video>_narrado.mp4"

Áudios que já existem na pasta "narracao" não são gerados de novo
(não gasta crédito duas vezes). Para refazer uma fala, apague o arquivo dela e rode de novo.
Também dá para gerar as falas pelo site, salvar como 01.mp3, 02.mp3... e rodar só para montar.
"""
import json, os, re, subprocess, sys, urllib.request, urllib.error
from pathlib import Path

# ----------------- CONFIGURAÇÃO -----------------
API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "COLE_SUA_CHAVE_AQUI")
VOICE_ID = "R1FbOy3y7r4840b0cKEC"          # Lucas - Português BR (jovem, calmo)
MODEL_ID = "eleven_multilingual_v2"        # melhor pronúncia em PT-BR para narração
VIDEO    = "demo_oficina_facil.mp4"
SRT      = "demo_oficina_facil.srt"
VOZ = {                                    # ajustes da voz
    "stability": 0.55,                     # mais alto = mais constante entre as falas
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True,
    "speed": 1.0,                          # 0.7 a 1.2
}
FOLGA       = 0.15   # segundos de respiro antes da próxima legenda
MAX_ACELERA = 1.20   # acelera no máximo 20% se uma fala não couber
VOLUME      = 1.0    # volume da narração
# -------------------------------------------------

PASTA = Path(__file__).resolve().parent
os.chdir(PASTA)
CLIPES = PASTA / "narracao"
CLIPES.mkdir(exist_ok=True)


def ler_srt(caminho):
    txt = Path(caminho).read_text(encoding="utf-8-sig").replace("\r", "")
    blocos = []
    for bloco in re.split(r"\n\s*\n", txt.strip()):
        linhas = bloco.strip().split("\n")
        idx = next(i for i, l in enumerate(linhas) if "-->" in l)
        a, b = [x.strip() for x in linhas[idx].split("-->")]
        texto = " ".join(l.strip() for l in linhas[idx + 1:] if l.strip())
        blocos.append((seg(a), seg(b), texto))
    return blocos


def seg(t):
    h, m, s = t.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def duracao(arq):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(arq)], capture_output=True, text=True)
    return float(out.stdout.strip())


def gerar(texto, anterior, proximo, destino):
    url = (f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
           f"?output_format=mp3_44100_128")
    corpo = {"text": texto, "model_id": MODEL_ID, "voice_settings": VOZ}
    # contexto vizinho: mantém a entonação contínua entre as falas
    if anterior: corpo["previous_text"] = anterior
    if proximo:  corpo["next_text"] = proximo
    req = urllib.request.Request(url, data=json.dumps(corpo).encode("utf-8"), method="POST",
                                 headers={"xi-api-key": API_KEY, "Content-Type": "application/json",
                                          "Accept": "audio/mpeg"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            destino.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"\nErro da API ElevenLabs ({e.code}): {e.read().decode('utf-8', 'ignore')}")


def main():
    for prog in ("ffmpeg", "ffprobe"):
        if subprocess.run([prog, "-version"], capture_output=True).returncode != 0:
            sys.exit(f"{prog} não encontrado. Instale com:  winget install Gyan.FFmpeg")

    falas = ler_srt(SRT)
    dur_video = duracao(VIDEO)
    print(f"{len(falas)} falas no SRT | vídeo com {dur_video:.1f}s\n")

    # 1) gera os áudios que ainda não existem
    faltando = [i for i in range(len(falas)) if not (CLIPES / f"{i+1:02d}.mp3").exists()]
    if faltando and API_KEY.startswith("COLE_"):
        sys.exit("Coloque sua chave da API em API_KEY (ou gere as falas no site e salve em narracao/).")
    for i in faltando:
        ant = falas[i - 1][2] if i > 0 else None
        prox = falas[i + 1][2] if i + 1 < len(falas) else None
        print(f"  gerando fala {i+1:02d}/{len(falas)} ...")
        gerar(falas[i][2], ant, prox, CLIPES / f"{i+1:02d}.mp3")

    # 2) mede, calcula encaixe e monta o filtro
    entradas, filtros, rotulos = [], [], []
    print("\n nº  início   espaço  fala   ajuste")
    for i, (ini, fim, texto) in enumerate(falas):
        arq = CLIPES / f"{i+1:02d}.mp3"
        d = duracao(arq)
        limite = (falas[i + 1][0] if i + 1 < len(falas) else dur_video) - ini - FOLGA
        fator = 1.0
        aviso = ""
        if d > limite:
            fator = min(d / limite, MAX_ACELERA)
            aviso = f"acelerada {fator:.2f}x"
            if d / fator > limite + 0.05:
                aviso += "  <-- AINDA NÃO CABE: encurte o texto desta legenda"
        print(f" {i+1:02d} {ini:7.2f}s  {limite:5.2f}s  {d:5.2f}s  {aviso}")
        entradas += ["-i", str(arq)]
        ms = int(round(ini * 1000))
        cadeia = f"[{i+1}:a]aresample=44100,"
        if fator > 1.0:
            cadeia += f"atempo={fator:.4f},"
        cadeia += f"adelay={ms}|{ms},volume={VOLUME}[a{i}]"
        filtros.append(cadeia)
        rotulos.append(f"[a{i}]")

    filtros.append("".join(rotulos) +
                   f"amix=inputs={len(rotulos)}:normalize=0:dropout_transition=0,apad[narr]")
    saida = Path(VIDEO).stem + "_narrado.mp4"
    cmd = (["ffmpeg", "-y", "-v", "error", "-stats", "-i", VIDEO] + entradas +
           ["-filter_complex", ";".join(filtros),
            "-map", "0:v", "-map", "[narr]", "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-t", f"{dur_video:.3f}", saida])
    print("\nMontando o vídeo final...")
    subprocess.run(cmd, check=True)
    print(f"\nPronto: {saida}")


if __name__ == "__main__":
    main()
