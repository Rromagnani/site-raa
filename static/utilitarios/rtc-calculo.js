// Motor da calculadora de IBS e CBS por operação (Reforma Tributária do Consumo, LC 214/2025).
// Reproduz, no navegador, as regras da calculadora oficial da Receita Federal para o regime regular
// (github.com/ReceitaFederal/calculadora-rtc-regime-regular), com a base oficial em dados-rtc.js.
// Depende de RTC (dados-rtc.js). Sem acesso ao DOM: pode ser testado fora da página.

// Fração do IBS de referência em cada ano da transição (EC 132/2023 e LC 214/2025).
const RTC_TRANS = { 2029: .1, 2030: .2, 2031: .3, 2032: .4, 2033: 1 };
const RTC_ANOS = [2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033];

// Arredondamento em centavos, meio para cima (como o BigDecimal HALF_UP da API).
const rtcR2 = v => Math.sign(v) * Math.round((Math.abs(v) + 1e-9) * 100) / 100;

const rtcClasse = cod => RTC.cls.find(c => c.c === cod);

// Alíquotas nominais (em %) do ano. 2026: base oficial. 2027 e 2028: CBS de referência − 0,1 ponto e IBS de 0,05% + 0,05%.
// De 2029 a 2033: IBS de referência proporcional; a divisão entre Estado e Município depende das alíquotas de cada ente.
function rtcAliquotas(ano, prem) {
  if (ano <= 2026) return { cbs: RTC.ref2026.CBS, uf: RTC.ref2026.IBSUF, mun: RTC.ref2026.IBSMun, oficial: true };
  if (ano <= 2028) return { cbs: Math.max(Math.round((prem.cbsRef - .1) * 1e4) / 1e4, 0), uf: .05, mun: .05 };
  return { cbs: prem.cbsRef, ibs: prem.ibsRef * RTC_TRANS[ano] };
}

// Classificações vinculadas a um NCM (8 dígitos) ou NBS (9 dígitos). As tabelas oficiais usam prefixos e exceções.
function rtcVinculadas(codigo, tipo) {
  const lista = tipo === "nbs" ? RTC.nbs : RTC.ncm, out = [];
  for (const [pref, cl, exc] of lista)
    if (codigo.startsWith(pref) && !(exc || []).some(e => codigo.startsWith(e)) && !out.includes(cl)) out.push(cl);
  return out;
}
// A classificação exige NCM/NBS de uma lista fechada?
const rtcTemLista = (cl, tipo) => (tipo === "nbs" ? RTC.nbs : RTC.ncm).some(l => l[1] === cl);

function rtcDescNbs(cod) { const l = RTC.listaNbs.find(n => n[0] === cod); return l ? l[1] : ""; }
function rtcDescNcm(cod) {
  for (let n = cod.length; n >= 2; n--) if (RTC.descNcm[cod.slice(0, n)]) return RTC.descNcm[cod.slice(0, n)];
  return "";
}

// e: { ano, natureza: "bem"|"servico", codigo, classe, valor, outros, desc, icmsIss, pisCofins, inclui, cbsRef, ibsRef }
function rtcCalcular(e) {
  const cl = rtcClasse(e.classe);
  if (!cl) return { erro: "Classificação tributária não encontrada." };
  const avisos = [], erros = [];
  const tipo = e.natureza === "servico" ? "nbs" : "ncm";

  // Vínculo NCM/NBS × classificação (a API recusa com o erro REG-011).
  if (e.codigo && rtcTemLista(cl.c, tipo) && !rtcVinculadas(e.codigo, tipo).includes(cl.c))
    erros.push(`${tipo.toUpperCase()} ${e.codigo} não está vinculada à classificação ${cl.c} na tabela oficial. A redução não se aplica a esse item (erro REG-011 na calculadora da Receita).`);
  if (e.codigo && !cl.n.includes(tipo.toUpperCase()))
    erros.push(`A classificação ${cl.c} se aplica a itens identificados por ${cl.n}, e não por ${tipo.toUpperCase()}.`);

  const A = rtcAliquotas(e.ano, e);
  // Componentes da base (ElementoBaseCalculo da API): PIS/Cofins só em 2026; ICMS e ISS até 2032.
  const dedPis = e.ano === 2026 ? e.pisCofins : 0;
  const dedLoc = e.ano <= 2032 ? e.icmsIss : 0;
  if (e.pisCofins && e.ano > 2026) avisos.push("PIS e Cofins deixam de existir em 2027 e não foram deduzidos.");
  if (e.icmsIss && e.ano > 2032) avisos.push("ICMS e ISS são extintos em 2033 e não foram deduzidos.");
  const bruto = e.valor + e.outros - e.desc - dedPis - dedLoc;

  const [rCbs, rUf, rMun] = cl.r.map(v => v / 100);
  const efet = {
    cbs: A.cbs * (1 - rCbs),
    uf: A.uf != null ? A.uf * (1 - rUf) : null,
    mun: A.mun != null ? A.mun * (1 - rMun) : null,
    ibs: A.ibs != null ? A.ibs * (1 - rUf) : null,
  };
  const semTributo = cl.cst === "400" || cl.cst === "410";
  const tTotal = semTributo ? 0 : (efet.cbs + (efet.ibs != null ? efet.ibs : efet.uf + efet.mun)) / 100;
  const base = Math.max(rtcR2(e.inclui ? bruto / (1 + tTotal) : bruto), 0);

  const linhas = [];
  const add = (nome, nominal, red, ef) => {
    const calc = rtcR2(base * ef / 100);
    linhas.push({ nome, nominal, red, ef, calc });
  };
  add("CBS (União)", A.cbs, cl.r[0], efet.cbs);
  if (efet.ibs != null) add("IBS (Estado + Município)", A.ibs, cl.r[1], efet.ibs);
  else { add("IBS estadual", A.uf, cl.r[1], efet.uf); add("IBS municipal", A.mun, cl.r[2], efet.mun); }

  let situacao = "devido";
  if (semTributo) { situacao = "sem"; linhas.forEach(l => { l.calc = 0; l.devido = 0; }); }
  else if (cl.cst === "510" || cl.cst === "515") { situacao = "diferido"; linhas.forEach(l => { l.dif = l.calc; l.devido = 0; }); }
  else if (cl.cst === "550") { situacao = "suspenso"; linhas.forEach(l => { l.susp = l.calc; l.devido = 0; }); }
  else linhas.forEach(l => { l.devido = l.calc; });

  const soma = k => rtcR2(linhas.reduce((s, l) => s + (l[k] || 0), 0));
  return {
    cl, A, base, linhas, situacao, erros, avisos, oficial: !!A.oficial,
    total: soma("devido"), diferido: soma("dif"), suspenso: soma("susp"), calculado: soma("calc"),
    precoFinal: rtcR2(base + soma("devido")),
  };
}
