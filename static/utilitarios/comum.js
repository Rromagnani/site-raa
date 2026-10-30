// Funções comuns às calculadoras.

// "5.000,50", "5000,5", "5000.50" ou "5000" → número.
function numero(txt) {
  let s = String(txt || "").replace(/[^\d,.-]/g, "");
  if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
  else if ((s.match(/\./g) || []).length > 1) s = s.replace(/\./g, "");
  const n = parseFloat(s);
  return isFinite(n) ? n : 0;
}

const _moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const moeda = v => _moeda.format(Math.round(v * 100) / 100);
const pct = (v, casas = 2) => (v * 100).toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas }) + "%";
const r2 = v => Math.round(v * 100) / 100;

// Campos de valor: formata ao sair do campo (ex.: 5000 → 5.000,00).
document.querySelectorAll("input[data-moeda]").forEach(el => {
  el.addEventListener("blur", () => {
    if (el.value.trim()) el.value = numero(el.value).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  });
});

document.querySelectorAll("[data-ano]").forEach(el => (el.textContent = new Date().getFullYear()));
