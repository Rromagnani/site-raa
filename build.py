#!/usr/bin/env python3
"""Gera o site www.raa.com.br em ./public.

Busca notícias jurídicas (Google Notícias, filtrado por fontes confiáveis) e
vídeos (canais do STF e do STJ), e monta as páginas a partir de
templates/. Só usa a biblioteca padrão do Python — roda em qualquer lugar,
inclusive no GitHub Actions, sem instalar nada.
"""
import datetime as dt
import email.utils
import html
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "public"
UA = "Mozilla/5.0 (compatible; RAA-site-bot/1.0; +https://www.raa.com.br)"

FONTES = "(site:migalhas.com.br OR site:conjur.com.br OR site:jota.info OR site:stj.jus.br OR site:stf.jus.br OR site:tst.jus.br OR site:cnj.jus.br)"

AREAS = [
    ("tributario", "Tributário", "(tributário OR tributária OR ICMS OR PIS OR Cofins OR IBS OR CBS OR Receita Federal OR execução fiscal)"),
    ("trabalhista", "Trabalhista", "(trabalhista OR TST OR empregado OR empregador OR CLT)"),
    ("civil", "Civil e Empresarial", "(STJ contrato OR responsabilidade civil OR recuperação judicial OR societário OR empresarial)"),
    ("imobiliario", "Imobiliário", "(imóvel OR imobiliário OR locação OR usucapião OR condomínio OR ITBI)"),
    ("familia", "Família e Sucessões", "(família OR divórcio OR inventário OR herança OR pensão alimentícia OR partilha OR guarda)"),
    ("consumidor", "Consumidor", "(consumidor OR CDC OR indenizará OR plano de saúde OR Procon)"),
]

CANAIS = [
    # Para voltar a exibir os vídeos do escritório, reative a linha abaixo.
    # ("UCETskzV5b4--3Qu1l0R6wug", "Romagnani Advogados", 12),
    ("UCsW4QSB1USsu9ouuFUWe4Iw", "STF", 6),
    ("UCfO_b7sApXI23VnsljvSAJg", "STJ", 6),
]

# Classificação pelo TÍTULO (o Google casa termos no corpo e mistura as áreas).
# A ordem importa: a primeira área que casar fica com a notícia.
REGRAS = [
    ("tributario", r"tribut|icms|\biss\b|\bpis\b|cofins|\bibs\b|\bcbs\b|\bipi\b|irpj|csll|itbi|itcmd|iptu|receita federal|\bfisco|fiscal|imposto|split payment|carf|\bctn\b|contribuinte|\btaxas?\b|pgfn|d[ií]vida ativa|simples nacional"),
    ("trabalhista", r"\btst\b|\btrt|trabalh|empregad|emprego|\bclt\b|demiss|dispensad|rescis|sindica|jornada|horas? extras?|fgts|periculosidade|insalubridade|aprendiz|ass[eé]dio moral|terceiriza"),
    ("familia", r"div[oó]rcio|uni[aã]o est[aá]vel|invent[aá]rio|heran[cç]a|herdeir|partilha|pens[aã]o aliment|guarda d|c[oô]njuge|casamento|testamento|sucess[aãó]|ado[cç][aã]o|paternidade|filiação|\bm[aã]e\b|\bpai\b|\bfilh[oa]s?\b"),
    ("imobiliario", r"im[oó]ve|imobili|loca[cç][aã]o|locat[aá]ri|aluguel|usucapi[aã]o|condom[ií]n|incorporador|registro de im|fundi[aá]ri|despejo|aliena[cç][aã]o fiduci|\bterreno"),
    ("consumidor", r"consumidor|\bcdc\b|plano de sa[uú]de|procon|companhia a[eé]rea|\bvoo\b|negativa[cç]|cobran[cç]a indevida|indenizar[aá]|\bgolpe|\bpix\b|fraude banc|e-commerce|propaganda enganosa|\boferta"),
    ("civil", r"\bstj\b|contrat|responsabilidade civil|recupera[cç][aã]o judicial|fal[eê]ncia|societ[aá]r|\bs[oó]cios?\b|empresa|execu[cç][aã]o|coisa julgada|credor|d[ií]vida|arbitra|danos? mora|indeniza|repetitivo|cpc\b|processo civil"),
]
REGRAS = [(a, re.compile(r, re.I)) for a, r in REGRAS]
# Fora do foco do escritório ou sem valor como notícia.
FORA = re.compile(r"pris[aã]o|\bpres[oa]\b|pena de|homic|crime|criminal|pol[ií]cia|elei[cç]|eleitoral|\blula\b|bolsonaro|impeachment|intranet|edi[cç][oõ]es|\bpauta\b|podcast|lan[cç]a (obra|livro|guia)|inscri[cç][oõ]es|assessora|pr[eê]mio|f[oó]rum|webinar|evento|^arquivos? |p[aá]gina \d|\bjota principal\b|morta\b|morto\b|estelionato|prisional|terras raras|confira a programa|^banca |defende redes|encontro (no|debate)", re.I)


def classificar(titulo):
    if len(titulo) < 30 or titulo.upper() == titulo or FORA.search(titulo):
        return None
    return next((a for a, r in REGRAS if r.search(titulo)), None)


def baixar(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def google_news(consulta, janela):
    q = urllib.parse.quote(f"{FONTES} {consulta} when:{janela}")
    url = f"https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    raiz = ET.fromstring(baixar(url))
    itens = []
    for it in raiz.iter("item"):
        titulo = (it.findtext("title") or "").strip()
        fonte = (it.findtext("source") or "").strip()
        if fonte and titulo.endswith(" - " + fonte):
            titulo = titulo[: -len(fonte) - 3]
        titulo = re.sub(r"\s+-\s+(Migalhas|Consultor Jurídico|JOTA Info|STJ|STF|TST)$", "", titulo)
        if not titulo:
            continue
        data = email.utils.parsedate_to_datetime(it.findtext("pubDate"))
        itens.append({"titulo": titulo, "link": it.findtext("link"), "fonte": fonte,
                      "data": data.astimezone(dt.timezone.utc).isoformat()})
    return itens


def noticias():
    consultas = [c for _, _, c in AREAS] + ["(STJ OR TST OR STF) decide", "(STJ OR TST) tese OR repetitivo"]
    pool = []
    for c in consultas:
        try:
            pool += google_news(c, "3d")
        except Exception as e:  # uma consulta falhar não derruba o site
            print(f"[aviso] notícias '{c[:30]}': {e}", file=sys.stderr)
    pool.sort(key=lambda x: x["data"], reverse=True)
    vistos, por_area, saida = set(), {}, []
    for it in pool:
        chave = re.sub(r"\W+", "", it["titulo"].lower())[:60]
        area = classificar(it["titulo"])
        if not area or chave in vistos or por_area.get(area, 0) >= 9:
            continue
        vistos.add(chave)
        por_area[area] = por_area.get(area, 0) + 1
        saida.append({**it, "area": area})
    return saida


def duracao(video_id):
    """Duração em segundos (0 = transmissão ao vivo/agendada; None = não conseguiu ler)."""
    try:
        pagina = baixar(f"https://www.youtube.com/watch?v={video_id}").decode("utf-8", "ignore")
    except Exception:
        return None
    m = re.search(r'"lengthSeconds":"(\d+)"', pagina)
    return int(m.group(1)) if m else None


def videos():
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    saida = []
    for cid, nome, limite in CANAIS:
        try:
            raiz = ET.fromstring(baixar(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"))
        except Exception as e:
            print(f"[aviso] vídeos de {nome}: {e}", file=sys.stderr)
            continue
        n = 0
        for en in raiz.findall("a:entry", ns):
            vid = en.findtext("yt:videoId", namespaces=ns)
            titulo = en.findtext("a:title", namespaces=ns) or ""
            if FORA.search(titulo):
                continue
            # Fora: chamadas curtas/Shorts, transmissões ao vivo e sessões de várias horas.
            seg = duracao(vid)
            if seg is None or not 60 <= seg <= 90 * 60:
                continue
            saida.append({"id": vid, "titulo": titulo, "duracao": seg,
                          "data": en.findtext("a:published", namespaces=ns),
                          "canal": nome, "proprio": nome.startswith("Romagnani")})
            n += 1
            if n == limite:
                break
    return saida


META = re.compile(r"^(Resumo|Área|Capa):\s*(.+)$")
IMG = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)$")


def caminho_img(nome):
    """'foto.webp' → img/newsletter/foto.webp; 'fotos/x.webp' → img/fotos/x.webp."""
    return nome if nome.startswith("http") else "img/" + (nome if "/" in nome else f"newsletter/{nome}")


def newsletters():
    """Arquivos em content/newsletter/AAAA-MM-DD.md (ou .txt, formato antigo).

    1ª linha: título (com ou sem '# '). Logo abaixo, opcionais: 'Resumo:', 'Área:', 'Capa:'.
    No texto (.md): '## subtítulo', '- item', '> destaque', '![legenda](foto.webp)',
    **negrito** e [link](https://...).
    """
    lista = []
    for f in sorted((ROOT / "content/newsletter").glob("*.*"), reverse=True):
        if f.suffix not in (".md", ".txt"):
            continue
        linhas = f.read_text(encoding="utf-8").strip().splitlines()
        titulo, meta, corpo = linhas[0].lstrip("# ").strip(), {}, []
        for l in linhas[1:]:
            m = META.match(l.strip())
            if m and not corpo:
                meta[m.group(1)] = m.group(2).strip()
            elif l.strip() or f.suffix == ".md":
                corpo.append(l)
        imgs = [IMG.match(l.strip()) for l in corpo]
        capa = meta.get("Capa") or next((m.group(2) for m in imgs if m), "fotos/escritorio-3.webp")
        # a primeira foto do texto vira a capa; não repete logo abaixo dela
        primeira = next((i for i, l in enumerate(corpo) if l.strip()), None)
        if primeira is not None and imgs[primeira] and imgs[primeira].group(2) == capa:
            del corpo[primeira]
        texto = [l for l in corpo if l.strip() and not IMG.match(l.strip()) and not l.startswith(("#", "- ", ">"))]
        resumo = meta.get("Resumo") or next((l for l in texto if len(l) > 90), texto[0] if texto else "")
        resumo = re.sub(r"\*\*|\[|\]\([^)]*\)", "", resumo)
        palavras = sum(len(l.split()) for l in corpo)
        lista.append({"slug": f.stem, "titulo": titulo, "corpo": corpo, "md": f.suffix == ".md",
                      "area": meta.get("Área", ""), "capa": caminho_img(capa),
                      "minutos": max(1, round(palavras / 200)),
                      "resumo": resumo[:220] + ("…" if len(resumo) > 220 else "")})
    return lista


def inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', t)
    return t


def md_html(linhas):
    """Markdown simples → HTML (só o que as newsletters usam)."""
    partes, lista = [], []
    def fecha_lista():
        if lista:
            partes.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in lista) + "</ul>")
            lista.clear()
    for l in linhas:
        l = l.strip()
        m = IMG.match(l)
        if l.startswith("- "):
            lista.append(l[2:]); continue
        fecha_lista()
        if not l:
            continue
        if m:
            partes.append(f'<figure><img src="../{caminho_img(m.group(2))}" alt="{html.escape(m.group(1))}" loading="lazy"></figure>')
        elif l.startswith("## "):
            partes.append(f"<h2>{inline(l[3:])}</h2>")
        elif l.startswith("> "):
            partes.append(f"<blockquote>{inline(l[2:])}</blockquote>")
        else:
            partes.append(f"<p>{inline(l)}</p>")
    fecha_lista()
    return "\n".join(partes)


def corpo_html(linhas):
    """Formato antigo (.txt): heurística de subtítulos."""
    partes = []
    for l in linhas:
        e = html.escape(l)
        e = re.sub(r"(https?://\S+)", r'<a href="\1" target="_blank" rel="noopener">\1</a>', e)
        if re.match(r"^\d+(\.\d+)*[\.\)]\s", l) and len(l) < 120:
            partes.append(f"<h2>{e}</h2>")
        elif len(l) < 70 and l.endswith(":"):
            partes.append(f"<h3>{e}</h3>")
        else:
            partes.append(f"<p>{e}</p>")
    return "\n".join(partes)


def data_br(slug):
    a, m, d = slug.split("-")
    meses = "jan fev mar abr mai jun jul ago set out nov dez".split()
    return f"{int(d)} {meses[int(m) - 1]} {a}"


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "static", OUT)

    agora = dt.datetime.now(dt.timezone.utc)
    news, vids, nls = noticias(), videos(), newsletters()
    print(f"{len(news)} notícias, {len(vids)} vídeos, {len(nls)} newsletters")
    if len(news) < 10:  # fontes fora do ar: falha de propósito e o site anterior continua no ar
        sys.exit("Poucas notícias obtidas — publicação cancelada.")

    dados = {
        "atualizado": agora.isoformat(),
        "areas": [{"slug": s, "nome": n} for s, n, _ in AREAS],
        "noticias": news,
        "videos": vids,
        "newsletters": [{k: v for k, v in n.items() if k not in ("corpo", "md")} | {"data": data_br(n["slug"])} for n in nls],
    }
    js = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    (OUT / "dados.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")

    tpl = (ROOT / "templates/index.html").read_text(encoding="utf-8")
    (OUT / "index.html").write_text(tpl.replace("/*__DADOS__*/null", js), encoding="utf-8")

    tpl_nl = (ROOT / "templates/newsletter.html").read_text(encoding="utf-8")
    (OUT / "newsletter").mkdir()
    for n in nls:
        pagina = (tpl_nl.replace("{{titulo}}", html.escape(n["titulo"]))
                  .replace("{{data}}", data_br(n["slug"]))
                  .replace("{{resumo}}", html.escape(n["resumo"]))
                  .replace("{{capa}}", "../" + n["capa"])
                  .replace("{{area}}", html.escape(n["area"] or "Newsletter"))
                  .replace("{{minutos}}", str(n["minutos"]))
                  .replace("{{corpo}}", md_html(n["corpo"]) if n["md"] else corpo_html(n["corpo"])))
        (OUT / "newsletter" / f"{n['slug']}.html").write_text(pagina, encoding="utf-8")

    urls = ["https://www.raa.com.br/"] + [f"https://www.raa.com.br/newsletter/{n['slug']}.html" for n in nls]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")


if __name__ == "__main__":
    main()
