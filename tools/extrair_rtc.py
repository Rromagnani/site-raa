"""Extrai da base oficial da calculadora da Receita (calculadora-pro.db) os dados usados pela calculadora web."""
import sqlite3, json, sys, re
db, saida = sys.argv[1], sys.argv[2]
c = sqlite3.connect(db)
versao = c.execute("select * from VERSAO_BASE_DADO").fetchall()
CSTS = ("000", "200", "400", "410", "510", "515", "550")
TIPOS = ("Padrão", "Sem alíquota")
cls = []
q = """select ct.CLTR_ID, ct.CLTR_CD, ct.CLTR_DESCRICAO, s.SITR_CD, s.SITR_DESCRICAO, ct.CLTR_TIPO_ALIQUOTA, ct.CLTR_NOMENCLATURA,
  ct.CLTR_INICIO_VIGENCIA, ct.CLTR_FIM_VIGENCIA, ct.CLTR_IN_APROPRIACAO_CREDITOS_ADQUIRENTES_CBS, ct.CLTR_IN_APROPRIACAO_CREDITOS_ADQUIRENTES_IBS,
  (select t.TRTR_DESCRICAO from TRATAMENTO_CLASSIFICACAO tc join TRATAMENTO_TRIBUTARIO t on t.TRTR_ID=tc.TRCL_TRTR_ID where tc.TRCL_CLTR_ID=ct.CLTR_ID and tc.TRCL_FIM_VIGENCIA is null),
  (select f.FDLG_TEXTO_CURTO from FUNDAMENTACAO_CLASSIFICACAO fc join FUNDAMENTACAO_LEGAL f on f.FDLG_ID=fc.FDCL_FDLG_ID where fc.FDCL_CLTR_ID=ct.CLTR_ID and fc.FDCL_FIM_VIGENCIA is null)
  from CLASSIFICACAO_TRIBUTARIA ct join SITUACAO_TRIBUTARIA s on s.SITR_ID=ct.CLTR_SITR_ID
  where ct.CLTR_FIM_VIGENCIA is null and s.SITR_FIM_VIGENCIA is null order by ct.CLTR_CD"""
ids = {}
for r in c.execute(q).fetchall():
    (id_, cd, desc, cst, cstd, tipo, nom, ini, fim, crCbs, crIbs, trat, fund) = r
    if cst not in CSTS or tipo not in TIPOS or cd in ("200022", "200024"): continue
    red = {}
    for tb, sig in ((2, "cbs"), (3, "uf"), (4, "mun")):
        v = c.execute("select PERE_VALOR from PERCENTUAL_REDUCAO where PERE_CLTR_ID=? and PERE_TBTO_ID=? and PERE_FIM_VIGENCIA is null", (id_, tb)).fetchone()
        red[sig] = v[0] if v else 0
    ids[id_] = cd
    cls.append({"c": cd, "d": desc.strip().rstrip("."), "cst": cst, "cstd": cstd, "t": trat or "", "n": nom, "ini": ini[:4],
                "r": [red["cbs"], red["uf"], red["mun"]], "cr": int(bool(crCbs or crIbs)), "f": fund or ""})
def aplic(tab, pre, exc, epre):
    # Uma mesma (código, classificação) pode vir em várias linhas, cada uma com parte das exceções: unificar.
    grupos = {}
    for aid, cd, cl in c.execute(f"select {pre}_ID,{pre}_{tab}_CD,{pre}_CLTR_ID from {tab}_APLICAVEL where {pre}_FIM_VIGENCIA is null"):
        if cl not in ids: continue
        ex = [e[0] for e in c.execute(f"select {epre}_{tab}_CD from EXCECAO_{tab}_APLICAVEL where {epre}_{tab}A_ID=? and {epre}_FIM_VIGENCIA is null", (aid,))]
        g = grupos.setdefault((cd, ids[cl]), set()); g.update(ex)
    return [[cd, cl] + ([sorted(ex)] if ex else []) for (cd, cl), ex in sorted(grupos.items())]
ncm = aplic("NCM", "NCMA", "EXCECAO", "ENCM")
nbs = aplic("NBS", "NBSA", "EXCECAO", "ENBS")
# descrições de NCM só dos códigos citados; NBS completa (serviços)
desc_ncm = {}
for cd, _, *x in ncm:
    for n in range(len(cd), 1, -1):  # descrição do próprio código ou do nível superior mais próximo
        r = c.execute("select NCM_DESCRICAO from NCM where NCM_CD=? and (NCM_FIM_VIGENCIA is null or NCM_FIM_VIGENCIA >= '2026-01-01')", (cd[:n],)).fetchone()
        if r: desc_ncm[cd[:n]] = re.sub(r"<[^>]+>", "", r[0]).lstrip("- ").strip(); break
lista_nbs = [[cd, d] for cd, d in c.execute("select NBS_CD,NBS_DESCRICAO from NBS where NBS_FIM_VIGENCIA is null order by NBS_CD")]
ref = {r[0]: r[1] for r in c.execute("select t.TBTO_SIGLA, a.ALRE_VALOR from ALIQUOTA_REFERENCIA a join TRIBUTO t on t.TBTO_ID=a.ALRE_TBTO_ID where a.ALRE_INICIO_VIGENCIA<='2026-12-31'")}
dados = {"versao": str(versao[-1]), "ref2026": ref, "cls": cls, "ncm": ncm, "nbs": nbs, "descNcm": desc_ncm, "listaNbs": lista_nbs}
js = "// Gerado por tools/extrair_rtc.py a partir da base oficial da calculadora da Receita Federal\n// (github.com/ReceitaFederal/calculadora-rtc-regime-regular, licença MIT). Não editar à mão.\nconst RTC = " + json.dumps(dados, ensure_ascii=False, separators=(",", ":")) + ";\n"
open(saida, "w").write(js)
print(len(cls), "classificações;", len(ncm), "NCM;", len(nbs), "NBS;", len(lista_nbs), "NBS lista;", round(len(js.encode())/1024), "KB", versao[-1], ref)
