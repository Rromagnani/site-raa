#!/usr/bin/env python3
"""Gera o site www.raa.com.br em ./public.

Busca notícias jurídicas (Google Notícias, filtrado por fontes confiáveis) e
vídeos (canal do escritório + STF/STJ), e monta as páginas a partir de
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
    ("UCETskzV5b4--3Qu1l0R6wug", "Romagnani Advogados", 12),
    ("UCsW4QSB1USsu9ouuFUWe4Iw", "STF", 4),
    ("UCfO_b7sApXI23VnsljvSAJg", "STJ", 4),
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


def videos():
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    saida = []
    for cid, nome, limite in CANAIS:
        try:
            raiz = ET.fromstring(baixar(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"))
        except Exception as e:
            print(f"[aviso] vídeos de {nome}: {e}", file=sys.stderr)
            continue
        for en in raiz.findall("a:entry", ns)[:limite]:
            saida.append({"id": en.findtext("yt:videoId", namespaces=ns),
                          "titulo": en.findtext("a:title", namespaces=ns),
                          "data": en.findtext("a:published", namespaces=ns),
                          "canal": nome, "proprio": nome.startswith("Romagnani")})
    return saida


def newsletters():
    """Cada arquivo content/newsletter/AAAA-MM-DD.txt: 1ª linha = título, resto = texto."""
    lista = []
    for f in sorted((ROOT / "content/newsletter").glob("*.txt"), reverse=True):
        linhas = f.read_text(encoding="utf-8").strip().splitlines()
        corpo = [l for l in linhas[1:] if l.strip()]
        resumo = next((l for l in corpo if len(l) > 90), corpo[0] if corpo else "")
        lista.append({"slug": f.stem, "titulo": linhas[0], "corpo": corpo,
                      "resumo": resumo[:220] + ("…" if len(resumo) > 220 else "")})
    return lista


def corpo_html(linhas):
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
        "newsletters": [{k: v for k, v in n.items() if k != "corpo"} | {"data": data_br(n["slug"])} for n in nls],
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
                  .replace("{{corpo}}", corpo_html(n["corpo"])))
        (OUT / "newsletter" / f"{n['slug']}.html").write_text(pagina, encoding="utf-8")

    urls = ["https://www.raa.com.br/"] + [f"https://www.raa.com.br/newsletter/{n['slug']}.html" for n in nls]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")


if __name__ == "__main__":
    main()
