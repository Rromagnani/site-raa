#!/usr/bin/env python3
"""Comandos da rotina semanal da newsletter, reunidos num só lugar.

A rotina agendada usa só estes três comandos (menos pedidos de permissão):

  python3 tools/newsletter.py preparar
      Atualiza o repositório, gera o site e mostra as notícias da semana
      e os temas das edições já publicadas.

  python3 tools/newsletter.py foto DATA N CAMINHO_RAW ID_UNSPLASH
      Baixa a foto N da edição DATA (AAAA-MM-DD) do Unsplash em WebP, registra
      o crédito e monta a prancha .cache/fotos-DATA.jpg para conferência visual.
      CAMINHO_RAW é o trecho após https://images.unsplash.com/ (ex.: photo-123-abc).

  python3 tools/newsletter.py publicar DATA "Tema"
      Gera o site, confere a edição (arquivo, fotos, links), faz commit, push e
      acompanha a publicação no GitHub até o fim.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GH = str(Path.home() / ".local/bin/gh")
REPO = "Rromagnani/site-raa"
IMG = ROOT / "static/img/newsletter"
AUTOR = ["-c", "user.name=Roberto Romagnani", "-c", "user.email=roberto@raa.com.br"]


def sh(*cmd, check=True):
    r = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if check and r.returncode:
        sys.exit(f"Falhou: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}")
    return r.stdout.strip()


def preparar():
    sh("git", "pull", "-q", "--rebase")
    print(sh(sys.executable, "build.py"))
    dados = json.loads((ROOT / "public/dados.json").read_text())
    print("\n== NOTÍCIAS DA SEMANA (área | data | fonte | título | link)")
    for n in dados["noticias"]:
        print(f"{n['area']} | {n['data'][:10]} | {n['fonte']} | {n['titulo']} | {n['link']}")
    print("\n== EDIÇÕES JÁ PUBLICADAS (não repetir tema)")
    for f in sorted((ROOT / "content/newsletter").glob("*.*"), reverse=True):
        print(f"{f.stem} | {f.read_text(encoding='utf-8').splitlines()[0].lstrip('# ')}")


def foto(data, n, raw, uid):
    IMG.mkdir(parents=True, exist_ok=True)
    nome = f"{data}-{n}.webp"
    raw = raw.replace("https://images.unsplash.com/", "").split("?")[0]
    sh("curl", "-sfk", f"https://images.unsplash.com/{raw}?w=1400&q=70&fm=webp", "-o", str(IMG / nome))
    cred_f = IMG / "CREDITOS.json"
    cred = json.loads(cred_f.read_text()) if cred_f.exists() else {}
    cred[nome] = f"https://unsplash.com/photos/{uid}"
    cred_f.write_text(json.dumps(cred, indent=1, ensure_ascii=False) + "\n")
    # prancha com todas as fotos da edição, para conferir de uma vez (abrir com Read)
    from PIL import Image, ImageDraw
    fotos = sorted(IMG.glob(f"{data}-*.webp"))
    prancha = Image.new("RGB", (len(fotos) * 330, 230), "white")
    d = ImageDraw.Draw(prancha)
    for i, f in enumerate(fotos):
        im = Image.open(f).convert("RGB")
        im.thumbnail((320, 210))
        prancha.paste(im, (i * 330 + 5, 15))
        d.text((i * 330 + 8, 2), f.name, fill="black")
    (ROOT / ".cache").mkdir(exist_ok=True)
    destino = ROOT / f".cache/fotos-{data}.jpg"
    prancha.save(destino, quality=80)
    print(f"ok: {nome} ({(IMG / nome).stat().st_size // 1024} KB). Conferir: {destino}")


def publicar(data, tema):
    md = ROOT / f"content/newsletter/{data}.md"
    if not md.exists():
        sys.exit(f"Não encontrei {md}")
    texto = md.read_text(encoding="utf-8")
    faltando = [f for f in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", texto)
                if not (ROOT / "static/img" / (f if "/" in f else f"newsletter/{f}")).exists()]
    if faltando:
        sys.exit(f"Fotos citadas que não existem: {faltando}")
    print(sh(sys.executable, "build.py"))
    pagina = ROOT / f"public/newsletter/{data}.html"
    html = pagina.read_text(encoding="utf-8")
    externos = html.count('href="http')
    print(f"edição gerada: {len(html)//1024} KB, {html.count('<figure>')} fotos, "
          f"{html.count('<h2>')} subtítulos, {externos} links externos")
    sh("git", "add", "-A")
    if not sh("git", "status", "--porcelain"):
        print("Nada novo para publicar.")
        return
    sh("git", *AUTOR, "commit", "-q", "-m",
       f"Newsletter {data}: {tema}\n\nCo-Authored-By: Claude <noreply@anthropic.com>")
    sh("git", "push", "-q")
    time.sleep(10)
    run = sh(GH, "run", "list", "-R", REPO, "--limit", "1", "--json", "databaseId", "-q", ".[0].databaseId")
    r = subprocess.run([GH, "run", "watch", run, "-R", REPO, "--exit-status"], cwd=ROOT,
                       capture_output=True, text=True)
    if r.returncode:
        print(sh(GH, "run", "view", run, "-R", REPO, "--log-failed", check=False)[-3000:])
        sys.exit("A publicação no GitHub falhou (log acima).")
    print(f"PUBLICADO: https://www.raa.com.br/newsletter/{data}.html")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["preparar"]:
        preparar()
    elif a[:1] == ["foto"] and len(a) == 5:
        foto(*a[1:])
    elif a[:1] == ["publicar"] and len(a) == 3:
        publicar(*a[1:])
    else:
        sys.exit(__doc__)
