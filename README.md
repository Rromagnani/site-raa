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
| Vídeos do escritório | Canal youtube.com/@RomagnaniAdvogados — **basta publicar no YouTube que aparece no site** |
| Vídeos dos tribunais | Canais oficiais do STF e do STJ |

## Como publicar uma nova newsletter

Crie um arquivo em `content/newsletter/` com o nome `AAAA-MM-DD.txt`
(ex.: `2026-10-05.txt`). A primeira linha é o título; o restante é o texto.
Linhas que começam com número (`1. Introdução`) viram subtítulos.
Pode ser criado direto no site do GitHub (*Add file → Create new file*).

## Ajustes comuns

- **Temas das notícias**: listas `AREAS` (buscas) e `REGRAS` (classificação) em `build.py`.
- **Filtrar assuntos indesejados**: expressão `FORA` em `build.py`.
- **Textos institucionais, cores, contatos**: `templates/index.html`.

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
