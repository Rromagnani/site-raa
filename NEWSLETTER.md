# Newsletter semanal — manual editorial

Uma edição por semana, publicada às segundas-feiras. Este é o roteiro seguido a cada edição.

## 1. Escolher o tema

- Partir das notícias da semana (`public/dados.json`, gerado pelo `build.py`) e das
  decisões do STF, STJ e TST dos últimos 7 dias.
- Preferir o assunto que **mais afeta a vida das pessoas ou o dia a dia das empresas**
  nas áreas do escritório: Trabalhista, Tributário, Civil e Empresarial, Imobiliário,
  Família e Sucessões e Consumidor.
- Evitar: matéria criminal, política partidária, casos envolvendo pessoas famosas, e
  temas já tratados nas últimas 8 edições.
- Priorizar decisões **já tomadas** (julgamento concluído, tese fixada, lei publicada),
  em vez de julgamentos só iniciados.

## 2. Apurar

- Confirmar os fatos em **pelo menos duas fontes**, de preferência o próprio tribunal
  mais um veículo jurídico (Migalhas, Conjur, JOTA).
- Anotar o número do processo, a data, o placar e o que foi decidido. Na dúvida,
  não afirmar.
- No máximo uma citação curta (menos de 15 palavras) de cada fonte, entre aspas e com
  autoria. O restante é escrito com palavras próprias.

## 3. Escrever: linguagem humanizada, sem juridiquês

- Abrir com uma situação da vida real, não com o número da lei.
- Frases curtas. Termo técnico só se for indispensável, e explicado na hora.
- Estrutura sugerida (subtítulos em forma de pergunta ou frase simples):
  1. Abertura humana (2 parágrafos)
  2. O que foi decidido, em poucas palavras (lista de 3 a 5 itens)
  3. Por que isso importa
  4. Perguntas práticas (“E quem já…?”, “Quando começa a valer?”)
  5. O que muda para as empresas / para as famílias
  6. Em resumo (um destaque `>`)
  7. Fontes (links)
- Entre 700 e 1.100 palavras (4 a 6 minutos de leitura).
- Tom informativo, sem promessas de resultado e sem oferta de serviços, conforme as
  regras de publicidade da OAB (Provimento 205/2021).

## 4. Imagens

- De 4 a 5 fotos por edição, **ligadas ao tema** de cada trecho.
- Só fotos gratuitas do Unsplash (nunca as marcadas como “Unsplash+”/premium).
- Salvar em `static/img/newsletter/AAAA-MM-DD-N.webp` (1400 px, WebP) e registrar a
  origem em `static/img/newsletter/CREDITOS.json`.
- A primeira foto do texto vira a capa da edição.

## 5. Formato do arquivo

`content/newsletter/AAAA-MM-DD.md` (data da publicação):

```
# Título curto e humano
Resumo: uma ou duas frases que aparecem no card e no topo da edição.
Área: Trabalhista · Família

![descrição da foto](AAAA-MM-DD-1.webp)

Texto…

## Subtítulo
- item com **destaque**
> Frase de destaque
[texto do link](https://…)
```

## 6. Publicar

1. `python3 build.py` e conferir a edição no navegador (capa, fotos, links).
2. Commit com a mensagem `Newsletter AAAA-MM-DD: <tema>` e `git push`. O GitHub
   Actions publica o site em seguida.
