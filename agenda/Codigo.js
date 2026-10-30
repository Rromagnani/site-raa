// Agenda de consultas telepresenciais do site www.raa.com.br.
//
// Roda como Google Apps Script na conta roberto@raa.com.br (e-mails saem pelo apelido contato@),
// publicado como "app da Web":
//   GET  ?acao=horarios  → horários livres dos próximos dias
//   POST {acao:"reservar", ...} → grava a reserva, cria o evento com Google Meet e envia os e-mails
// O gatilho lembretes() roda a cada 10 minutos e envia os avisos de 24 h e de 1 h antes.
// Instalação: rodar instalar() uma vez no editor (cria a planilha e o gatilho).

const CFG = {
  ADVOGADO: 'roberto@raa.com.br',          // dono do script: recebe os avisos; a agenda dele bloqueia horários
  REMETENTE: 'contato@raa.com.br',         // apelido do Gmail usado para enviar os e-mails
  ESCRITORIO: 'Romagnani Advogados Associados',
  WHATSAPP: '+55 11 99649-1980',
  SITE: 'https://www.raa.com.br',
  AREAS: ['Trabalhista', 'Tributário', 'Cível'],
  DIAS: 15,                                 // janela de agendamento
  DIAS_SEMANA: [2, 3, 4],                   // 1 = segunda … 7 = domingo
  HORAS: [10, 11, 12, 13, 14, 15],          // início de cada consulta de 1 h (última termina às 16 h)
  POR_DIA: 3,
  ANTECEDENCIA_H: 2,                        // não oferece horários a menos de 2 h
  TZ: 'America/Sao_Paulo',
  PLANILHA: 'Agenda - Consultas telepresenciais',
};
const COLS = ['id', 'criado', 'inicio', 'nome', 'celular', 'email', 'area', 'resumo',
              'evento', 'meet', 'lembrete24h', 'lembrete1h', 'status'];
const HORA_MS = 3600e3;

// ---------- web ----------

function doGet(e) {
  const acao = (e && e.parameter && e.parameter.acao) || 'horarios';
  if (acao !== 'horarios') return json_({ ok: false, erro: 'Ação inválida.' });
  return json_({ ok: true, dias: horariosLivres_() });
}

function doPost(e) {
  let d;
  try { d = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false, erro: 'Dados inválidos.' }); }
  if (d.acao !== 'reservar') return json_({ ok: false, erro: 'Ação inválida.' });
  try {
    return json_(reservar_(d));
  } catch (err) {
    console.error(err && err.stack || err);
    return json_({ ok: false, erro: 'Não foi possível concluir o agendamento agora. Tente de novo em instantes ou fale conosco pelo WhatsApp ' + CFG.WHATSAPP + '.' });
  }
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

// ---------- horários ----------

// Os 3 horários de cada dia são sorteados a partir da própria data, então ficam fixos entre visitas.
function sorteio_(ymd) {
  let h = 2166136261;
  for (const c of 'raa-agenda-' + ymd) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  const rnd = () => { h = Math.imul(h ^ (h >>> 15), 2246822507); h = Math.imul(h ^ (h >>> 13), 3266489909); return ((h ^= h >>> 16) >>> 0) / 4294967296; };
  const horas = CFG.HORAS.slice();
  for (let i = horas.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [horas[i], horas[j]] = [horas[j], horas[i]]; }
  return horas.slice(0, CFG.POR_DIA).sort((a, b) => a - b);
}

// Brasil sem horário de verão desde 2019: São Paulo = UTC−3.
function instante_(ymd, hora) {
  return new Date(ymd + 'T' + String(hora).padStart(2, '0') + ':00:00-03:00');
}

function candidatos_() {
  const agora = Date.now(), lista = [];
  for (let i = 0; i < CFG.DIAS; i++) {
    const dia = new Date(agora + i * 864e5);
    const ymd = Utilities.formatDate(dia, CFG.TZ, 'yyyy-MM-dd');
    if (CFG.DIAS_SEMANA.indexOf(Number(Utilities.formatDate(dia, CFG.TZ, 'u'))) < 0) continue;
    for (const h of sorteio_(ymd)) {
      const ini = instante_(ymd, h);
      if (ini.getTime() - agora >= CFG.ANTECEDENCIA_H * HORA_MS) lista.push({ ymd: ymd, hora: h, ini: ini });
    }
  }
  return lista;
}

// Períodos ocupados: agenda do advogado + reservas da planilha.
function ocupados_(de, ate) {
  const res = [];
  const fb = Calendar.Freebusy.query({
    timeMin: de.toISOString(), timeMax: ate.toISOString(), timeZone: CFG.TZ,
    items: [{ id: CFG.ADVOGADO }],
  });
  Object.keys(fb.calendars || {}).forEach(id => {
    const c = fb.calendars[id];
    if (c.errors && c.errors.length) console.warn('Agenda ' + id + ' indisponível: ' + JSON.stringify(c.errors));
    (c.busy || []).forEach(b => res.push([new Date(b.start).getTime(), new Date(b.end).getTime()]));
  });
  linhas_().forEach(r => {
    if (r.status === 'confirmada') { const t = new Date(r.inicio).getTime(); res.push([t, t + HORA_MS]); }
  });
  return res;
}

function livre_(ini, ocup) {
  const a = ini.getTime(), b = a + HORA_MS;
  return !ocup.some(o => o[0] < b && o[1] > a);
}

function horariosLivres_() {
  const cands = candidatos_();
  if (!cands.length) return [];
  const ocup = ocupados_(cands[0].ini, new Date(cands[cands.length - 1].ini.getTime() + HORA_MS));
  const dias = [];
  cands.filter(c => livre_(c.ini, ocup)).forEach(c => {
    let d = dias[dias.length - 1];
    if (!d || d.data !== c.ymd) dias.push(d = { data: c.ymd, horarios: [] });
    d.horarios.push(String(c.hora).padStart(2, '0') + ':00');
  });
  return dias;
}

// ---------- reserva ----------

function limpa_(v, max) { return String(v == null ? '' : v).replace(/\s+/g, ' ').trim().slice(0, max); }

function reservar_(d) {
  if (d.site) return { ok: true };  // campo-armadilha preenchido: robô
  const r = {
    nome: limpa_(d.nome, 100), celular: limpa_(d.celular, 30), email: limpa_(d.email, 120).toLowerCase(),
    area: limpa_(d.area, 30), resumo: String(d.resumo || '').trim().slice(0, 800),
  };
  const digitos = r.celular.replace(/\D/g, '');
  if (r.nome.length < 3) return { ok: false, erro: 'Informe seu nome completo.' };
  if (digitos.length < 10 || digitos.length > 13) return { ok: false, erro: 'Informe um celular válido, com DDD.' };
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(r.email)) return { ok: false, erro: 'Informe um e-mail válido.' };
  if (CFG.AREAS.indexOf(r.area) < 0) return { ok: false, erro: 'Escolha a área da consulta.' };
  if (r.resumo.length < 10) return { ok: false, erro: 'Conte em poucas palavras qual é o problema.' };
  if (!d.consentimento) return { ok: false, erro: 'É preciso concordar com o uso dos dados para o agendamento.' };

  const alvo = candidatos_().filter(c => c.ymd === d.data && String(c.hora).padStart(2, '0') + ':00' === d.hora)[0];
  if (!alvo) return { ok: false, erro: 'Esse horário não está mais disponível. Escolha outro.', recarregar: true };

  const trava = LockService.getScriptLock();
  trava.waitLock(30000);
  try {
    const agora = Date.now();
    const futura = linhas_().filter(x => x.status === 'confirmada' && x.email === r.email && new Date(x.inicio).getTime() > agora)[0];
    if (futura) return { ok: false, erro: 'Você já tem uma consulta marcada para ' + quando_(new Date(futura.inicio)) + '. Para remarcar, fale conosco pelo WhatsApp ' + CFG.WHATSAPP + '.' };
    if (!livre_(alvo.ini, ocupados_(alvo.ini, new Date(alvo.ini.getTime() + HORA_MS))))
      return { ok: false, erro: 'Esse horário acabou de ser reservado. Escolha outro.', recarregar: true };

    const fim = new Date(alvo.ini.getTime() + HORA_MS);
    const ev = Calendar.Events.insert({
      summary: 'Consulta telepresencial: ' + r.nome + ' (' + r.area + ')',
      description: 'Agendada pelo site.\n\nCliente: ' + r.nome + '\nCelular: ' + r.celular + '\nE-mail: ' + r.email +
                   '\nÁrea: ' + r.area + '\n\nResumo:\n' + r.resumo,
      start: { dateTime: alvo.ini.toISOString(), timeZone: CFG.TZ },
      end: { dateTime: fim.toISOString(), timeZone: CFG.TZ },
      attendees: [{ email: r.email, displayName: r.nome }],
      conferenceData: { createRequest: { requestId: Utilities.getUuid(), conferenceSolutionKey: { type: 'hangoutsMeet' } } },
      guestsCanSeeOtherGuests: false,
    }, 'primary', { conferenceDataVersion: 1, sendUpdates: 'none' });

    r.id = Utilities.getUuid().slice(0, 8);
    r.criado = new Date().toISOString();
    r.inicio = alvo.ini.toISOString();
    r.evento = ev.id;
    r.meet = ev.hangoutLink || '';
    r.lembrete24h = alvo.ini.getTime() - agora > 24 * HORA_MS ? '' : 'n/a';  // marcada com menos de 24 h: só o aviso de 1 h
    r.lembrete1h = '';
    r.status = 'confirmada';
    planilha_().appendRow(COLS.map(c => r[c]));
    SpreadsheetApp.flush();

    enviar_(r, 'confirmacao');
    return { ok: true, quando: quando_(alvo.ini), meet: r.meet };
  } finally {
    trava.releaseLock();
  }
}

// ---------- lembretes (gatilho a cada 10 min) ----------

function lembretes() {
  const sh = planilha_(), agora = Date.now();
  linhas_().forEach(r => {
    if (r.status !== 'confirmada') return;
    const falta = new Date(r.inicio).getTime() - agora;
    if (falta <= 0) return;
    const marcar = (col, v) => sh.getRange(r._linha, COLS.indexOf(col) + 1).setValue(v);
    const precisa24 = !r.lembrete24h && falta <= 24 * HORA_MS;
    const precisa1 = !r.lembrete1h && falta <= HORA_MS;
    if (cancelada_(r)) { marcar('status', 'cancelada'); return; }  // libera o horário no site
    if (!precisa24 && !precisa1) return;
    if (precisa1) {
      enviar_(r, 'lembrete1h');
      marcar('lembrete1h', new Date().toISOString());
      if (!r.lembrete24h) marcar('lembrete24h', 'n/a');
    } else {
      enviar_(r, 'lembrete24h');
      marcar('lembrete24h', new Date().toISOString());
    }
  });
}

// Se o evento for apagado na agenda, a reserva é cancelada: o horário volta ao site e os lembretes não saem.
function cancelada_(r) {
  try { return Calendar.Events.get('primary', r.evento).status === 'cancelled'; }
  catch (err) { return /not found|404|410/i.test(String(err)); }
}

// ---------- e-mails ----------

function esc_(s) {
  return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function quando_(dt) {
  const dias = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado'];
  const meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  const p = Utilities.formatDate(dt, CFG.TZ, 'u d M HH:mm').split(' ');
  return dias[Number(p[0]) % 7] + ', ' + p[1] + ' de ' + meses[Number(p[2]) - 1] + ', às ' + p[3].replace(':00', 'h');
}

function enviar_(r, tipo) {
  const quando = quando_(new Date(r.inicio));
  const primeiro = esc_(r.nome.split(' ')[0]);
  const titulos = {
    confirmacao: ['Consulta confirmada', 'Sua consulta telepresencial está confirmada.'],
    lembrete24h: ['Lembrete: sua consulta é amanhã', 'Passando para lembrar da sua consulta de amanhã.'],
    lembrete1h: ['Sua consulta começa em 1 hora', 'Sua consulta começa daqui a 1 hora.'],
  }[tipo];
  const botao = r.meet ? '<p style="margin:26px 0"><a href="' + esc_(r.meet) + '" style="background:#0E1B2C;color:#EDE7DC;padding:13px 26px;border-radius:999px;text-decoration:none;font-weight:600">Entrar na sala (Google Meet)</a></p>' +
    '<p style="font-size:13px;color:#5E6878">Ou copie o endereço: ' + esc_(r.meet) + '</p>' : '';
  const quadro = '<table style="border-collapse:collapse;font-size:15px;margin:18px 0">' +
    [['Data', quando], ['Duração', '1 hora'], ['Área', r.area], ['Formato', 'Videochamada (Google Meet)']]
      .map(l => '<tr><td style="padding:6px 18px 6px 0;color:#5E6878">' + l[0] + '</td><td style="padding:6px 0;font-weight:600">' + esc_(l[1]) + '</td></tr>').join('') + '</table>';
  const moldura = corpo => '<div style="background:#F7F4EE;padding:28px 12px;font-family:Arial,Helvetica,sans-serif;color:#1B2433">' +
    '<div style="max-width:560px;margin:0 auto;background:#fff;border:1px solid #DDD5C7;border-radius:14px;overflow:hidden">' +
    '<div style="background:#0E1B2C;color:#C9A46A;padding:18px 26px;font-family:Georgia,serif;letter-spacing:.12em;font-size:15px">ROMAGNANI ADVOGADOS ASSOCIADOS</div>' +
    '<div style="padding:26px;font-size:15px;line-height:1.6">' + corpo + '</div></div>' +
    '<p style="max-width:560px;margin:14px auto 0;font-size:12px;color:#5E6878;text-align:center">' + CFG.ESCRITORIO + ' · Av. Paulista, 1079 · São Paulo/SP · ' + CFG.SITE.replace('https://', '') + '</p></div>';

  // cliente
  const dicas = tipo === 'confirmacao'
    ? '<p>Na hora marcada, basta clicar no botão abaixo pelo computador ou celular. Se puder, separe os documentos relacionados ao assunto para facilitar a conversa.</p>'
    : '<p>É só clicar no botão abaixo no horário marcado.</p>';
  const rodape = '<p style="margin-top:22px">Precisa remarcar ou cancelar? Responda este e-mail ou fale conosco pelo WhatsApp <a href="https://wa.me/' + CFG.WHATSAPP.replace(/\D/g, '') + '">' + CFG.WHATSAPP + '</a>.</p><p>Até breve,<br><b>' + CFG.ESCRITORIO + '</b></p>';
  envia_({
    to: r.email, name: CFG.ESCRITORIO, replyTo: CFG.REMETENTE,
    subject: titulos[0] + ' · ' + quando,
    htmlBody: moldura('<p>Olá, ' + primeiro + '!</p><p>' + titulos[1] + '</p>' + quadro + dicas + botao + rodape),
  });

  // advogado
  const ficha = '<table style="border-collapse:collapse;font-size:15px;margin:18px 0">' +
    [['Cliente', r.nome], ['Celular', r.celular], ['E-mail', r.email], ['Área', r.area], ['Data', quando]]
      .map(l => '<tr><td style="padding:6px 18px 6px 0;color:#5E6878">' + l[0] + '</td><td style="padding:6px 0;font-weight:600">' + esc_(l[1]) + '</td></tr>').join('') + '</table>' +
    '<p style="color:#5E6878;margin-bottom:4px">Resumo do problema</p><p style="background:#F7F4EE;padding:14px;border-radius:10px;white-space:pre-wrap">' + esc_(r.resumo) + '</p>';
  const abertura = { confirmacao: 'Nova consulta telepresencial agendada pelo site.', lembrete24h: 'Lembrete: consulta amanhã.', lembrete1h: 'Lembrete: a consulta começa em 1 hora.' }[tipo];
  envia_({
    to: CFG.ADVOGADO, name: 'Agenda do site', replyTo: r.email,
    subject: (tipo === 'confirmacao' ? 'Nova consulta: ' : titulos[0] + ': ') + r.nome + ' (' + r.area + ') · ' + quando,
    htmlBody: moldura('<p>' + abertura + '</p>' + ficha + botao),
  });
}

// Envia pelo apelido contato@ quando ele estiver disponível no Gmail; senão, pela própria conta.
function envia_(m) {
  if (GmailApp.getAliases().indexOf(CFG.REMETENTE) >= 0) m.from = CFG.REMETENTE;
  GmailApp.sendEmail(m.to, m.subject, '', m);
}

// ---------- planilha ----------

function planilha_() {
  const props = PropertiesService.getScriptProperties();
  let id = props.getProperty('PLANILHA_ID'), ss;
  if (id) ss = SpreadsheetApp.openById(id);
  else {
    ss = SpreadsheetApp.create(CFG.PLANILHA);
    props.setProperty('PLANILHA_ID', ss.getId());
    const sh = ss.getSheets()[0];
    sh.setName('Reservas');
    sh.appendRow(COLS);
    sh.setFrozenRows(1);
    sh.getRange('A:M').setNumberFormat('@');  // tudo como texto (celular com +, nada vira fórmula)
  }
  return ss.getSheetByName('Reservas');
}

function linhas_() {
  const v = planilha_().getDataRange().getValues();
  return v.slice(1).map((l, i) => {
    const o = { _linha: i + 2 };
    COLS.forEach((c, j) => { o[c] = l[j] instanceof Date ? l[j].toISOString() : String(l[j]); });
    return o;
  });
}

// ---------- instalação e diagnóstico (rodar no editor) ----------

function instalar() {
  const ss = planilha_().getParent();
  ScriptApp.getProjectTriggers().forEach(t => { if (t.getHandlerFunction() === 'lembretes') ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('lembretes').timeBased().everyMinutes(10).create();
  console.log('Planilha: ' + ss.getUrl());
  diagnostico();
}

function diagnostico() {
  const fb = Calendar.Freebusy.query({
    timeMin: new Date().toISOString(), timeMax: new Date(Date.now() + 864e5).toISOString(),
    items: [{ id: CFG.ADVOGADO }],
  });
  console.log('Agendas: ' + JSON.stringify(fb.calendars));
  console.log('Horários livres: ' + JSON.stringify(horariosLivres_()));
  console.log('Apelidos de envio: ' + GmailApp.getAliases().join(', '));
}
