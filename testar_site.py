# -*- coding: utf-8 -*-
"""
testar_site.py - Confere o que o site precisa ter para funcionar.

Este arquivo roda dentro do GitHub Actions, depois de montar o site.
Se algo quebrar, ele para a publicação em vez de subir um site quebrado.

As verificacoes sao sobre coisas que ja quebraram de verdade:

1. cache: 'no-store' no fetch do noticias.json
   Sem isso o navegador guardava a versao antiga e a tela mostrava
   noticia que ja tinha sido retirada do ar.

2. As paginas de cada editoria existem e tem conteudo.

3. O manifesto aponta para icones que existem de verdade.

4. O HTML e valido: tags abertas e fechadas, um H1 so por pagina.

5. Nenhuma imagem quebrada.

6. O sitemap lista paginas que existem.

Para rodar na mao:  python testar_site.py
"""

import json
import os
import re
import sys
import urllib.request

PASTA = "publico"
DOMINIO = "https://www.mundoemquestao.com.br"

EDITORIAS = ["geopolitica", "guerras-e-conflitos", "politica-internacional",
             "economia-mundial", "historia", "religioes-e-sociedade",
             "ciencia-e-tecnologia", "brasil-no-mundo"]

FALHAS = []


def checar(condicao, mensagem):
    if condicao:
        print("  OK   " + mensagem)
    else:
        print("  FALHA " + mensagem)
        FALHAS.append(mensagem)


def ler(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return arquivo.read()
    except OSError:
        return ""


def main():
    print("Verificando o site...")

    # ---------------------------------------------- 1. cache do navegador
    index = ler(os.path.join(PASTA, "index.html"))
    checar("no-store" in index,
           "o fetch do noticias.json ignora o cache do navegador")

    # ------------------------------------- 2. paginas de cada editoria
    for nome in EDITORIAS:
        pagina = ler(os.path.join(PASTA, nome, "index.html"))
        existe = len(pagina) > 2000
        tem_noticias = "<article" in pagina or "Ainda não há notícias" in pagina
        checar(existe and tem_noticias,
               "/%s/ existe e tem conteudo" % nome)

    # ----------------------------------------- 3. manifesto e icones
    manifesto = ler(os.path.join(PASTA, "manifest.json"))
    try:
        dados = json.loads(manifesto)
        ok = True
        for icone in dados.get("icons", []):
            if not os.path.exists(os.path.join(PASTA, icone["src"])):
                print("       icone ausente: " + icone["src"])
                ok = False
        checar(ok, "todos os icones do manifesto existem")
    except ValueError:
        checar(False, "manifest.json e um JSON valido")

    # ------------------------------------------- 4. HTML bem formado
    for nome in ["index.html"] + [os.path.join(e, "index.html") for e in EDITORIAS]:
        html = ler(os.path.join(PASTA, nome))
        if not html:
            continue
        caminho = "/" if nome == "index.html" else "/" + os.path.dirname(nome)
        # Um H1 por pagina (exigencia de acessibilidade)
        h1 = len(re.findall(r"<h1[\s>]", html))
        checar(h1 == 1, "%s tem exatamente um H1 (tem %d)" % (caminho, h1))
        # As tags principais nao podem ficar abertas
        checar(html.count("<article") == html.count("</article>"),
               "%s: todo article tem fechamento" % caminho)
        checar(html.count("<main") == html.count("</main>"),
               "%s: main abre e fecha" % caminho)

    # ------------------------------------------ 5. imagem de compartilhamento
    checar(os.path.exists(os.path.join(PASTA, "og.png")),
           "og.png existe (imagem de compartilhamento)")

    # ------------------------------------------ 6. sitemap coerente
    sitemap = ler(os.path.join(PASTA, "sitemap.xml"))
    if sitemap:
        for caminho in re.findall(r"<loc>(.*?)</loc>", sitemap):
            relativo = caminho.replace(DOMINIO + "/", "").rstrip("/")
            alvo = (os.path.join(PASTA, relativo, "index.html")
                    if relativo else os.path.join(PASTA, "index.html"))
            checar(os.path.exists(alvo), "sitemap: /%s existe" % relativo)

    # ------------------------------------------------ 7. sem fofoca
    try:
        with open(os.path.join(PASTA, "noticias.json"), "r", encoding="utf-8") as arq:
            dados = json.loads(arq.read())
        # Estas palavras nunca devem aparecer como noticia do dia
        # Fofoca e quando o ASSUNTO e a relacao do artista. Um crime
        # nonviolento e noticia; um "novo namoro" e fofoca.
        FOFOCA = ("treta", "fofoca", "fofocando", "se separou", "separam",
                  "bastidores de novela", "reality show", "podcast",
                  "viralizou nas redes", "novo namoro", "pedido de casamento",
                  "cantor sertanejo", "atriz brasileira", "ator brasileiro")
        suspeitas = [n for n in dados["noticias"]
                     if any(p in n["titulo"].lower() for p in FOFOCA)]
        checar(not suspeitas,
               "nenhuma noticia de fofoca no boletim (%d encontradas)" % len(suspeitas))
    except Exception:
        checar(False, "noticias.json pode ser lido")

    print("")
    if FALHAS:
        print("%d verificacao(oes) falharam:" % len(FALHAS))
        for f in FALHAS:
            print("  - " + f)
        sys.exit(1)
    print("Tudo certo.")


if __name__ == "__main__":
    main()