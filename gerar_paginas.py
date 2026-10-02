# -*- coding: utf-8 -*-
"""
gerar_paginas.py - Cria as páginas de cada editoria, mais o sitemap e o
robots.txt.

O site tem uma página para cada uma das 8 editorias (Geopolitica,
Guerras e conflitos, Politica internacional, Economia mundial, Historia,
Religioes e sociedade, Ciencia e tecnologia, Brasil no mundo).

Cada pagina mostra as noticias daquela editoria, lidas do arquivo
noticias.json. Sao paginas estaticas de verdade: nao dependem de JavaScript
para mostrar o texto, entao os buscadores conseguem ler e o site abre
rapido no celular.

Este arquivo roda dentro do GitHub Actions, logo depois de buscar_noticias.py.
Ele le o noticias.json e escreve os arquivos HTML na pasta publica.
"""

import html
import json
import os

PASTA = "publico"
DOMINIO = "https://www.mundoemquestao.com.br"

# As 8 editorias do site: nome que aparece / parte do endereco / descricao
EDITORIAS = [
    {"nome": "Geopolitica", "titulo": "Geopolítica", "url": "geopolitica",
     "desc": "Diplomacia, aliancas e a tensao entre as grandes potencias. Quem puxa a corda e o que cada pais defende."},
    {"nome": "Guerras e conflitos", "titulo": "Guerras e conflitos", "url": "guerras-e-conflitos",
     "desc": "Confrontos armados, territorio, forcas envolvidas e consequencias humanas."},
    {"nome": "Politica internacional", "titulo": "Política internacional", "url": "politica-internacional",
     "desc": "Governos, aliancas, elections e decisoes que afetam outros paises."},
    {"nome": "Economia mundial", "titulo": "Economia mundial", "url": "economia-mundial",
     "desc": "Petroleo, dolar, inflacao, comercio e sancoes."},
    {"nome": "Historia", "titulo": "História", "url": "historia",
     "desc": "Acontecimentos antigos que ajudam a explicar os conflitos de hoje."},
    {"nome": "Religioes e sociedade", "titulo": "Religiões e sociedade", "url": "religioes-e-sociedade",
     "desc": "Cristianismo, islamismo, judaísmo e outras tradicoes em seu contexto."},
    {"nome": "Ciencia e tecnologia", "titulo": "Ciência e tecnologia", "url": "ciencia-e-tecnologia",
     "desc": "IA, espaco, energia nuclear, novas tecnologias e descobertas."},
    {"nome": "Brasil no mundo", "titulo": "Brasil no mundo", "url": "brasil-no-mundo",
     "desc": "Como o que acontece fora chega aqui: economia, combustivel e politica."},
]

META = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{titulo}</title>
<meta name="description" content="{descricao}">
<link rel="canonical" href="{url}">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon.png">
<meta name="theme-color" content="#0F2347">

<meta property="og:type" content="website">
<meta property="og:locale" content="pt_BR">
<meta property="og:site_name" content="Mundo em Questão">
<meta property="og:title" content="{titulo}">
<meta property="og:description" content="{descricao}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{dominio}/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{titulo}">
<meta name="twitter:description" content="{descricao}">
<meta name="twitter:image" content="{dominio}/og.png">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@500;700;800&family=Source+Serif+4:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">

<style>
/* O visual e o mesmo da pagina principal: fundo creme, texto azul-marinho
   e detalhes dourados. As fontes sao as duas mesmas. */
:root {{
  --bg: #FBF7EF; --ink: #14284A; --ink2: #4A5B78; --line: #E3D9C6;
  --ouro: #B8891F; --card: #FFFFFF; --sombra: 0 1px 2px rgba(20,40,74,.06);
  --titulo: 'Bricolage Grotesque', system-ui, -apple-system, sans-serif;
  --body: 'Source Serif 4', Georgia, serif;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--ink);
  font-family: var(--body); font-size: 1.125rem; line-height: 1.65;
}}
.wrap {{ max-width: 1080px; margin: 0 auto; padding: 0 20px 64px; }}

header.top {{
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
  padding: 18px 0; border-bottom: 1px solid var(--line); margin-bottom: 32px;
}}
.marca {{
  display: flex; align-items: center; gap: 10px; text-decoration: none;
  color: var(--ink); font-family: var(--titulo); font-weight: 800; font-size: 1.05rem;
  min-height: 44px;
}}
.marca-logo {{ width: 30px; height: 30px; }}
nav {{ margin-left: auto; }}
nav a {{
  color: var(--ink2); text-decoration: none; font-size: .95rem;
  padding: 12px 12px; display: inline-block; min-height: 44px; line-height: 20px;
}}
nav a:hover {{ color: var(--ouro); }}
nav a:focus-visible, .marca:focus-visible {{
  outline: 2px solid var(--ouro); outline-offset: 2px; border-radius: 4px;
}}

.cabecalho-secao {{ margin-bottom: 28px; }}
h1 {{
  font-family: var(--titulo); font-weight: 800;
  font-size: clamp(2rem, 5vw, 3.2rem); line-height: 1.05;
  margin: 0 0 10px; letter-spacing: -.02em;
}}
.desc-secao {{ color: var(--ink2); font-size: 1.1rem; max-width: 60ch; margin: 0; }}
.voltar {{ display: inline-flex; align-items: center; gap: 6px; color: var(--ouro);
  text-decoration: none; font-size: .95rem; margin-bottom: 18px; min-height: 44px; }}
.voltar:hover {{ text-decoration: underline; }}

.texto {{ max-width: 68ch; }}
.texto p {{ font-size: 1.125rem; line-height: 1.7; color: var(--ink); margin: 0 0 18px; }}
.texto h2 {{
  font-family: var(--titulo); font-weight: 700; font-size: 1.4rem;
  margin: 34px 0 12px; color: var(--ink);
}}
.texto a {{ color: var(--ouro); }}
.texto strong {{ font-weight: 600; }}

.vazio {{
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 32px; text-align: center; color: var(--ink2);
}}

.item {{
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 22px; margin-bottom: 16px; box-shadow: var(--sombra);
}}
.item h2 {{
  font-family: var(--titulo); font-weight: 700; font-size: 1.3rem;
  line-height: 1.25; margin: 0 0 8px; letter-spacing: -.01em;
}}
.item h2 a {{ color: var(--ink); text-decoration: none; }}
.item h2 a:hover {{ color: var(--ouro); }}
.item p {{ margin: 0 0 12px; color: var(--ink2); max-width: 68ch; }}
.meta {{
  display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center;
  font-size: .875rem; color: var(--ink2);
}}
.meta .fonte {{ color: var(--ouro); font-weight: 600; }}
.meta a {{ color: var(--ink2); }}
.verificar {{
  display: inline-block; background: #FFF4D6; border: 1px solid #E8C766;
  color: #7A5A08; font-size: .8125rem; padding: 2px 8px; border-radius: 6px;
}}
footer {{
  border-top: 1px solid var(--line); margin-top: 40px; padding-top: 22px;
  font-size: .875rem; color: var(--ink2);
}}
footer a {{ color: var(--ink2); }}
.rodape-links {{ display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 10px; }}
.rodape-links a {{ min-height: 44px; display: inline-flex; align-items: center; }}
@media (max-width: 640px) {{
  .wrap {{ padding: 0 16px 48px; }}
  header.top {{ gap: 10px; }}
  nav {{ margin-left: 0; width: 100%; order: 3; }}
  .item {{ padding: 18px; }}
}}
</style>
</head>
<body>
<div class="wrap">

  <header class="top">
    <a href="/" class="marca">
      <img class="marca-logo" src="/logo.png" width="30" height="30" alt="">
      <span>Mundo em Questão</span>
    </a>
    <nav aria-label="Principal">
      <a href="/">Boletim</a>
      <a href="/#secoes">Seções</a>
      <a href="/sobre/">Sobre</a>
    </nav>
  </header>

  <main>
    <div class="cabecalho-secao">
      <a href="/" class="voltar">&larr; Voltar ao boletim</a>
      <h1>{nome}</h1>
      <p class="desc-secao">{desc}</p>
    </div>

    {conteudo}
  </main>

  <footer>
    <div class="rodape-links">
      <a href="/">Boletim</a>
      <a href="/sobre/">Sobre</a>
      <a href="/como-apuramos/">Como apuramos</a>
      <a href="/privacidade/">Privacidade</a>
    </div>
    <p>Mundo em Questão — {total} notícias de {fontes} veículos.
       Atualizado em {gerado_em}. Todo o conteúdo vem dos veículos citados,
       com o link para a matéria original. This software is a news aggregator;
       nao reproduz os textos originais.</p>
  </footer>

</div>
</body>
</html>
"""


# Paginas fixas: Sobre, Como apuramos e Privacidade.
# Sao as mesmas para sempre, entao ficam escritas aqui.
FIXAS = [
    {"url": "sobre", "h1": "Sobre o Mundo em Questão",
     "titulo": "Sobre — Mundo em Questão",
     "desc": "O que e o Mundo em Questao, para quem e e o que o leitor encontra aqui.",
     "corpo": """
  <div class="texto">
    <p>O Mundo em Questão é um boletim diário sobre o que acontece no mundo.
       Ele reúne, em um só lugar, o que saiu nos veículos de newsdade reconhecidos —
       geopolítica, guerras e conflitos, política internacional, economia,
       história, religiões, ciência e tecnologia — e mostra como cada um desses
       assuntos chega até o Brasil.</p>

    <p>O site existe para quem quer entender o cenário internacional sem perder
       horas. Em vez de abrir quinze portais, a pessoa lê o boletim, escolhe a
       editoria que lhe interessa e clica em "Ler na fonte" para ir à matéria
       original, sempre com o link e o nome do veículo.</p>

    <p>A editoria <strong>Brasil no mundo</strong> é o diferencial: quase todo
       aggregator trata o Brasil como mais um item da lista. Aqui ele é o fio
       condutor. Uma guerra no Oriente Médio, uma mudança no preço do petróleo
       ou uma sanção contra a China aparece junto com o que isso significa para
       o combustível, a comida, o câmbio e a política externa daqui.</p>

    <p>Nenhum texto original é copiado. Publicamos um recorte do resumo do
       próprio veículo, com a fonte e o link ao lado, sempre.</p>
  </div>"""},

    {"url": "como-apuramos", "h1": "Como apuramos",
     "titulo": "Como apuramos — Mundo em Questão",
     "desc": "Como as noticias sao selecionadas, como as fontes sao citadas e como pedir uma correcao.",
     "corpo": """
  <div class="texto">
    <p><strong>De onde vêm as notícias.</strong> Lemos os feeds RSS de veículos
       reconhecidos — G1 Mundo, G1 Ciência, BBC News Brasil, Folha de S.Paulo,
       UOL, Metrópoles, Metrópoles Ciência e NASA. As notícias são lidas
       diretamente do feed do veículo, não de cópias ou reprintes.</p>

    <p><strong>Como selecionamos.</strong> Nem tudo o que sai nesses veículos
       interessa a um site sobre o mundo. Descartamos loterias, futebol,
       entretenimento e — principalmente — a política nacional brasileira que
       não tem relação com o exterior. O que fica é o que afeta，其他 países
       ou chega até o Brasil por algum caminho.</p>

    <p><strong>A fonte sempre aparece.</strong> Toda notícia mostra o nome do
       veículo e um link "Ler na fonte" que leva à matéria original. Quando o
       mesmo assunto sai em dois veículos, eles são agrupados e os demais
       aparecem em "Também saiu em". Nenhum texto é reproduzido na íntegra:
       publicamos um resumo e apontamos quem escreveu.</p>

    <p><strong>Quando não temos certeza.</strong> Se o resumo da fonte não é
       suficiente para dizer com segurança o que aconteceu, a notícia aparece
       marcada com <strong>[VERIFICAR]</strong>. É um aviso de que vale conferir
       na matéria original antes de usar a informação.</p>

    <p><strong>Parte do processo é automática.</strong> A coleta acontece de
       duas em duas horas por um programa que roda nos servidores do GitHub,
       sem ninguém do nosso lado clicando em nada. O que é automático é a
       <em>coleta, a organização e a classificação</em> por editoria. Não é
       automático o que exige conhecimento do contexto, e por isso a
       classificação é apenas uma primeira triagem: se algo estiver errado,
       o link para a fonte original está logo ao lado.</p>

    <p><strong>Encontrou um erro?</strong> Escreva para
       <a href="mailto:contato@mundoemquestao.com.br">contato@mundoemquestao.com.br</a>
       com o assunto "Correção" e o link da notícia. Corrigimos e, se for o caso,
       tiramos a matéria do ar.</p>
  </div>"""},

    {"url": "privacidade", "h1": "Política de Privacidade",
     "titulo": "Privacidade — Mundo em Questão",
     "desc": "Quais dados o Mundo em Questao guarda, por que e como voce pede a remocao.",
     "corpo": """
  <div class="texto">
    <p>Esta política explica quais dados o Mundo em Questão guarda sobre
       você, em conformidade com a Lei Geral de Proteção de Dados (Lei nº
       13.709/2018).</p>

    <h2>O que guardamos</h2>
    <p>Por padrão, <strong>nada</strong>. O site não pede cadastro, não usa
       cookies de rastreamento, não tem anúncios e não instala ferramentas de
       análise de audiência. Ler o boletim não gera nenhum registro sobre você.</p>

    <h2>O que o site guarda no seu próprio navegador</h2>
    <p>O botão "Atualizar" e a busca funcionam no seu aparelho, sem enviar
       nada para nenhum servidor de terceiros. Se você assinar o lembrete
       diário (quando disponível), o endereço do navegador e o horário que você
       escolher ficam guardados <strong>só no seu próprio dispositivo</strong>,
       para que a página saiba que você já assinou.</p>

    <h2>Serviços de terceiros</h2>
    <p>As notícias vêm dos veículos citados, e as fotos são baixadas dos
       servidores deles para o site, de modo que a foto não depende de
       requisição externa enquanto você lê. Nenhum desses veículos recebe
       informação sobre você. As fontes de letra são carregadas do Google
       Fonts, o que pode registrar o endereço IP de quem abre a página.</p>

    <h2>Seus direitos</h2>
    <p>Você pode pedir, a qualquer momento, a exclusão de qualquer dado seu.
       Como não guardamos dados seus, normalmente basta apagar o histórico do
       navegador. Se preferir falar com alguém, escreva para
       <a href="mailto:contato@mundoemquestao.com.br">contato@mundoemquestao.com.br</a>.</p>

    <p><em>Última atualização: outubro de 2026.</em></p>
  </div>"""},
]


def esc(t):
    """Escapa o texto para poder ir dentro do HTML."""
    return html.escape(t or "", quote=True)


def cabecalho_json_ld(nome, desc, url, noticias):
    """Dados estruturados: ajuda o Google a entender a pagina."""
    itens = [{
        "@type": "NewsArticle",
        "headline": esc(n["titulo"]),
        "datePublished": (n["quando"] or "").replace(" ", "T") + ":00-03:00",
        "description": esc(n["resumo"][:280]),
        "mainEntityOfPage": esc(n["link"]),
        "image": [n["imagem"].replace("fotos/", DOMINIO + "/fotos/")
                  if n.get("imagem") else DOMINIO + "/og.png"],
        "publisher": {
            "@type": "Organization",
            "name": esc(n["fonte"]),
            "url": "https://www.mundoemquestao.com.br",
        },
    } for n in noticias[:20]]

    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": nome + " — Mundo em Questão",
        "description": desc,
        "url": url,
        "inLanguage": "pt-BR",
        "isPartOf": {
            "@type": "WebSite",
            "name": "Mundo em Questão",
            "url": DOMINIO,
        },
        "mainEntity": {
            "@type": "ItemList",
            "itemListElement": itens,
        },
    }


def montar_lista(noticias):
    """Monta o HTML das noticias de uma editoria."""
    if not noticias:
        return ('<div class="vazio"><p> Ainda não há notícias nesta editoria. '
                'Volte em breve — o boletim é atualizado ao longo do dia.</p>'
                '<p><a href="/">Ver o boletim completo</a></p></div>')

    partes = []
    for n in noticias:
        img = ""
        if n.get("imagem"):
            img = ('<img src="/%s" alt="" loading="lazy" width="640" '
                   'height="360" style="width:100%%;height:auto;border-radius:10px;'
                   'margin-bottom:14px">' % esc(n["imagem"]))

        outras = ""
        if n.get("outras_fontes"):
            nomes = ", ".join(esc(o["fonte"]) for o in n["outras_fontes"][:3])
            outras = ('<span>Também em: %s</span>' % nomes)

        verif = (' <span class="verificar">[VERIFICAR]</span>'
                 if n.get("verificar") else "")

        partes.append(
            '<article class="item">%s'
            '<h2><a href="%s">%s</a></h2>'
            '<p>%s</p>'
            '<div class="meta">'
            '<span>%s</span>'
            '<span class="fonte">%s</span>'
            '<a href="%s" target="_blank" rel="noopener noreferrer">'
            'Ler na fonte &rarr;</a>'
            '%s%s'
            '</div></article>'
            % (img, esc(n["link"]), esc(n["titulo"]), esc(n["resumo"]),
               esc(n["quando"]), esc(n["fonte"]), esc(n["link"]),
               verif, outras))
    return "".join(partes)


def gerar_pagina(editoria, dados, pasta):
    url = "%s/%s/" % (DOMINIO, editoria["url"])
    titulo = "%s — Mundo em Questão" % editoria["titulo"]
    descricao = editoria["desc"]

    noticias = [n for n in dados["noticias"] if n["categoria"] == editoria["nome"]]

    pagina = META.format(
        titulo=esc(titulo),
        descricao=esc(descricao),
        url=esc(url),
        dominio=DOMINIO,
        nome=esc(editoria["titulo"]),
        desc=esc(descricao),
        conteudo=montar_lista(noticias),
        total=len(dados["noticias"]),
        fontes=len({n["fonte"] for n in dados["noticias"]}),
        gerado_em=esc(dados["gerado_em"]),
    )

    # dados estruturados, logo antes do </head>
    ld = json.dumps(cabecalho_json_ld(editoria["nome"], descricao, url, noticias),
                    ensure_ascii=False, indent=2)
    pagina = pagina.replace("</head>",
                            '<script type="application/ld+json">%s</script>\n</head>'
                            % ld)

    destino = os.path.join(pasta, editoria["url"])
    if not os.path.isdir(destino):
        os.makedirs(destino, exist_ok=True)
    with open(os.path.join(destino, "index.html"), "w", encoding="utf-8") as arquivo:
        arquivo.write(pagina)
    return len(noticias)


def gerar_pagina_fixa(fixa, dados, pasta):
    """Cria uma das paginas fixas (Sobre, Como apuramos, Privacidade)."""
    url = "%s/%s/" % (DOMINIO, fixa["url"])

    pagina = META.format(
        titulo=esc(fixa["titulo"]),
        descricao=esc(fixa["desc"]),
        url=esc(url),
        dominio=DOMINIO,
        nome=esc(fixa["h1"]),
        desc=esc(fixa["desc"]),
        conteudo=fixa["corpo"].strip(),
        total=len(dados["noticias"]),
        fontes=len({n["fonte"] for n in dados["noticias"]}),
        gerado_em=esc(dados["gerado_em"]),
    )

    destino = os.path.join(pasta, fixa["url"])
    if not os.path.isdir(destino):
        os.makedirs(destino, exist_ok=True)
    with open(os.path.join(destino, "index.html"), "w", encoding="utf-8") as arquivo:
        arquivo.write(pagina)


def gerar_sitemap(dados):
    """Lista todas as páginas do site para o Google."""
    hoje = (dados["gerado_em"] or "")[:10] or "2026-01-01"
    paginas = [("", hoje, 1.0, "daily"), ("sobre/", hoje, 0.5, "monthly"),
               ("como-apuramos/", hoje, 0.5, "monthly"),
               ("privacidade/", hoje, 0.3, "yearly")]
    for e in EDITORIAS:
        paginas.append((e["url"] + "/", hoje, 0.7, "daily"))

    partes = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for caminho, data, prioridade, freq in paginas:
        partes.append("  <url>")
        partes.append("    <loc>%s/%s</loc>" % (DOMINIO, caminho))
        partes.append("    <lastmod>%s</lastmod>" % data)
        partes.append("    <changefreq>%s</changefreq>" % freq)
        partes.append("    <priority>%.1f</priority>" % prioridade)
        partes.append("  </url>")
    partes.append("</urlset>")

    with open(os.path.join(PASTA, "sitemap.xml"), "w", encoding="utf-8") as arquivo:
        arquivo.write("\n".join(partes))


def gerar_robots():
    texto = """User-agent: *
Allow: /

Sitemap: https://www.mundoemquestao.com.br/sitemap.xml
"""
    with open(os.path.join(PASTA, "robots.txt"), "w", encoding="utf-8") as arquivo:
        arquivo.write(texto)


def main():
    caminho = os.path.join(PASTA, "noticias.json")
    with open(caminho, "r", encoding="utf-8") as arquivo:
        dados = json.load(arquivo)

    for e in EDITORIAS:
        n = gerar_pagina(e, dados, PASTA)
        print("  /%s/ %d noticias" % (e["url"], n))

    for fixa in FIXAS:
        gerar_pagina_fixa(fixa, dados, PASTA)
        print("  /%s/ criada" % fixa["url"])

    gerar_sitemap(dados)
    gerar_robots()
    print("sitemap.xml e robots.txt criados")


if __name__ == "__main__":
    main()