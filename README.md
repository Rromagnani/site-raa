# Site Romagnani Advogados Associados — www.raa.com.br

Site estático gerado por `build.py`, hospedado gratuitamente no **GitHub Pages** e
atualizado sozinho pelo **GitHub Actions**:

- todo dia às **06h** e, nos dias úteis, também às **14h** (horário de Brasília);
- a cada alteração enviada ao repositório;
- manualmente, na aba *Actions → Atualizar e publicar site → Run workflow*.

Se as fontes de notícias estiverem fora do ar, a publicação é cancelada e a
versão anterior continua no ar — o site nunca fica vazio.

## O que é atualizado automaticamente

| Conteúdo | Fonte |
|---|---|
| Notícias por área (até 9 por área) | Google Notícias, restrito a Migalhas, Conjur, JOTA, STF, STJ, TST e CNJ, classificadas pelo título |
| Vídeos dos tribunais | Canais oficiais do STF e do STJ |

## Newsletter semanal

Uma edição por semana, em `content/newsletter/AAAA-MM-DD.md`, com fotos. O passo a passo
(escolha do tema, apuração, tom de voz, imagens e formato) está em [NEWSLETTER.md](NEWSLETTER.md).
As edições antigas (`.txt`) continuam funcionando.

## Agendamento de consultas telepresenciais

Página `static/agendar/` ("Agende sua consulta telepresencial"). Os horários e as reservas ficam num
Google Apps Script na conta roberto@raa.com.br (projeto "Agenda do site RAA"; código em `agenda/`):

- terças, quartas e quintas, próximos 15 dias, 3 horários sorteados por dia entre 10h e 16h, 1 hora cada;
- horários ocupados no Google Agenda de roberto@ não aparecem;
- a reserva cria o evento com Google Meet, grava na planilha "Agenda - Consultas telepresenciais" e envia
  e-mail (de contato@) ao cliente e a roberto@; lembretes 24 h e 1 h antes (gatilho a cada 10 min);
- para cancelar, basta apagar o evento na agenda: o horário volta ao site em até 10 minutos.

Para alterar regras (dias, horários, quantidade), edite `CFG` em `agenda/Codigo.js`, cole no editor do
Apps Script e use *Implantar → Gerenciar implantações → editar → Nova versão* (o endereço não muda).

## Ajustes comuns

- **Temas das notícias**: listas `AREAS` (buscas) e `REGRAS` (classificação) em `build.py`.
- **Filtrar assuntos indesejados**: expressão `FORA` em `build.py`.
- **Textos institucionais, cores, contatos**: `templates/index.html`.
- **Fotos**: em `static/img/fotos/`, nomeadas `area-N.webp` (ex.: `familia-3.webp`). As fotos
  se revezam sozinhas a cada dia. Para trocar, substitua o arquivo mantendo o nome; para
  acrescentar, ajuste a contagem em `FOTOS` no `templates/index.html`. Origem e licença de cada
  foto (Unsplash, uso comercial livre): `static/img/fotos/CREDITOS.json`.
- **Vídeos do escritório**: desativados; para reativar, descomente a linha do canal em `CANAIS` (`build.py`).

## Testar no computador

```bash
python3 build.py && python3 -m http.server 8765 -d public
```

## Publicação inicial (uma única vez)

1. Criar conta gratuita em github.com e um repositório público, ex. `site-raa`.
2. Enviar esta pasta para o repositório.
3. No repositório: *Settings → Pages → Source: GitHub Actions*.
4. *Settings → Pages → Custom domain*: `www.raa.com.br` e marcar *Enforce HTTPS*.
5. No painel de DNS do domínio (Registro.br ou onde o DNS estiver), trocar o
   registro **CNAME de `www`** para `USUARIO.github.io` (no lugar de `ghs.googlehosted.com`).
6. Para `raa.com.br` sem “www”, criar registros **A** apontando para
   185.199.108.153, 185.199.109.153, 185.199.110.153 e 185.199.111.153.
