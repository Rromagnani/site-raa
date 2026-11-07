// Relatório em PDF no papel timbrado do escritório, comum a todas as calculadoras.
// A página monta o conteúdo e chama relatorio({...}); o navegador abre a impressão ("Salvar como PDF").
// O timbre (faixa superior, brasão, marca d'água e rodapé com endereço) se repete em todas as páginas.

const relEsc = t => String(t).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Tabela no estilo do relatório. cab: títulos das colunas (ou null); linhas: arrays de células em HTML.
function relTabela(cab, linhas, cls = "") {
  return `<table class="r-tab ${cls}">${cab ? `<thead><tr>${cab.map(c => `<th>${c}</th>`).join("")}</tr></thead>` : ""}` +
    `<tbody>${linhas.map(l => `<tr>${l.map(c => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

// Dados informados em duas colunas de pares (rótulo, valor).
function relDados(pares) {
  const l = [];
  for (let i = 0; i < pares.length; i += 2) {
    const b = pares[i + 1] || ["", ""];
    l.push([pares[i][0], relEsc(pares[i][1]), b[0], relEsc(b[1])]);
  }
  return relTabela(null, l, "r-dados");
}

// Quadros coloridos de destaque: [{ titulo, valor, texto, cor, selo }].
function relKpis(itens) {
  return `<div class="r-kpis" style="grid-template-columns:repeat(${itens.length},1fr)">` + itens.map(k =>
    `<div class="r-kpi" style="border-top-color:${k.cor || "#1F3864"}">${k.selo ? `<span class="r-selo">${k.selo}</span>` : ""}` +
    `<small>${k.titulo}</small><b>${k.valor}</b>${k.texto ? `<span>${k.texto}</span>` : ""}</div>`).join("") + "</div>";
}

// o: { eyebrow, titulo, para, ref, conclusao, corpo, ressalva, arquivo }
function relatorio(o) {
  let rel = document.getElementById("rel");
  if (!rel) { rel = document.createElement("div"); rel.id = "rel"; document.body.appendChild(rel); }
  const hoje = new Date().toLocaleDateString("pt-BR", { day: "numeric", month: "long", year: "numeric" });
  rel.innerHTML = `
    <img class="t-fix t-barra" src="timbre/barra-ouro.webp" alt="">
    <img class="t-fix t-logo" src="timbre/logo.webp" alt="Romagnani Advogados Associados">
    <img class="t-fix t-marca" src="timbre/marca.webp" alt="">
    <img class="t-fix t-end" src="timbre/endereco.webp" alt="www.raa.com.br · Av. Paulista, 1079, 7º e 8º andar, Bela Vista, São Paulo/SP">
    <div class="t-fix t-faixa"></div>
    <table class="t-pg"><thead><tr><td><div></div></td></tr></thead><tfoot><tr><td><div></div></td></tr></tfoot><tbody><tr><td>
      <div class="r-eye">${o.eyebrow}</div>
      <h1>${o.titulo}</h1>
      <div class="r-meta">${o.para ? `Preparado para <b>${relEsc(o.para)}</b> · ` : ""}Emitido em ${hoje}${o.ref ? " · " + o.ref : ""}</div>
      ${o.conclusao ? `<div class="r-concl">${o.conclusao}</div>` : ""}
      ${o.corpo}
      <p class="r-nota" style="margin-top:5mm">${o.ressalva || "Simulação de caráter informativo, que não substitui a análise de um profissional para o caso concreto."}</p>
      <div class="r-ass"><b>Romagnani Advogados Associados</b>contato@raa.com.br · +55 11 99649-1980 · www.raa.com.br</div>
    </td></tr></tbody></table>`;

  // iPhone/iPad: o Safari do iOS não repete elementos fixos em cada página e ignora as margens do @page.
  // Nele o timbre vira estático: logo no início e endereço no fim do relatório, sem faixas nem marca d'água.
  const ios = /iP(hone|od|ad)/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  document.body.classList.toggle("rel-ios", ios);
  if (ios) rel.appendChild(rel.querySelector(".t-end"));

  // Nome sugerido do PDF: sem acentos nem caracteres fora do ASCII (regra do escritório).
  const antes = document.title;
  document.title = (o.arquivo || o.titulo).normalize("NFKD").replace(/[^\x20-\x7E]/g, "").replace(/[\\/:*?"<>|]/g, "-");
  document.body.classList.add("rel-on");
  window.addEventListener("afterprint", () => { document.title = antes; document.body.classList.remove("rel-on"); }, { once: true });
  const imgs = [...rel.querySelectorAll("img")];
  Promise.all(imgs.map(i => i.complete ? 0 : new Promise(ok => { i.onload = i.onerror = ok; }))).then(() => window.print());
}
