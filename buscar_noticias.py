# -*- coding: utf-8 -*-
"""
buscar_noticias.py - Versão para rodar no GitHub Actions.

Este arquivo e uma cópia adaptada do agregador.py, feita para rodar nos
servidores do GitHub, e não no seu computador. Assim o site continua
atualizando mesmo com o seu PC desligado.

Diferenças em relação ao programa local:
  - Salva as fotos direto em publico/fotos (a pasta que vai ao site)
  - Grava apenas o indice.html, o noticias.json e o logo
  - Não usa nada do seu computador

O GitHub roda este arquivo por meio do arquivo buscar-noticias.yml, que fica
em .github/workflows.
"""

import json
import gzip
import os
import re
import sys
import time
import urllib.request
import urllib.error
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from difflib import SequenceMatcher
from html import unescape

# Onde os arquivos do site ficam neste repositório
PASTA = "publico"
PASTA_FOTOS = os.path.join(PASTA, "fotos")
RAIZ = os.path.dirname(os.path.abspath(__file__))

MAX_POR_FONTE = 30
LIMITE_LARGURA = 1600
LIMITE_FOTOS = 16          # quantas fotos baixar por rodada
FOTOS_POR_FONTE = 8        # quantas paginas abrir para buscar foto (Folha)
ALTURA_RODADA = 6 * 60      # 6 minutos: se passar disso, a rodada para

# O horario do site e o de Brasilia (UTC-3), e nao o do servidor.
#
# O GitHub roda em UTC. Sem esta conversao, o site mostrava 3 horas a mais
# do que a hora real aqui dentro: as 19:28 aparecia como 22:28.
# O Brasil nao tem horario de verao desde 2019, entao UTC-3 vale o ano todo.
FUSO = timezone(timedelta(hours=-3))

FONTES = [
    {"nome": "G1 Mundo", "url": "https://g1.globo.com/rss/g1/mundo/", "maximo": 14},
    {"nome": "BBC News Brasil", "url": "https://feeds.bbci.co.uk/portuguese/rss.xml", "maximo": 14},
    {"nome": "Folha de S.Paulo - Mundo", "url": "https://feeds.folha.uol.com.br/mundo/rss091.xml", "maximo": 12},
    {"nome": "G1 Ciencia", "url": "https://g1.globo.com/rss/g1/ciencia/", "maximo": 9},
    {"nome": "Metropoles Ciencia", "url": "https://www.metropoles.com/ciencia/feed/", "maximo": 8},
    {"nome": "Metropoles", "url": "https://www.metropoles.com/feed/", "maximo": 8},
    {"nome": "NASA", "url": "https://www.nasa.gov/news-release/feed/", "maximo": 7},
    {"nome": "UOL Noticias", "url": "https://rss.uol.com.br/feed/noticias.xml", "maximo": 6},
]

PALAVRAS_PARADA = {
    "a", "o", "as", "os", "um", "uma", "de", "do", "da", "dos", "das", "em", "no",
    "na", "nos", "nas", "por", "pelo", "pela", "para", "com", "sem", "sob", "sobre",
    "entre", "e", "ou", "que", "se", "nao", "ja", "sao", "foi", "esta", "estao", "tem",
    "ha", "vai", "vao", "mais", "mas", "muito", "todo", "toda", "seu", "sua", "ele",
    "ela", "apos", "durante", "contra", "ate", "onde", "quando", "como", "qual",
    "isso", "esse", "essa", "cada", "outro", "outra", "mesmo", "mesma", "pode",
    "podem", "faz", "diz", "disse", "afirmou",
}

# Politica nacional brasileira: o site e sobre o MUNDO.
POLITICA_NACIONAL = {
    "debate presidencial": 1, "debate da globo": 1, "flavio bolsonaro": 1,
    "bolsonaro": 1, "plenario": 1, "camara dos deputados": 1, "senado federal": 1,
    "congresso nacional": 1, "emenda constitucional": 1, "tse": 1,
    "tribunal superior eleitoral": 1, "kassio": 1, "mendonca": 1,
    "eleicao presidencial": 1, "segundo turno": 1, "inss": 1, "piso salarial": 1,
    "marcha para brasil": 1, "nossa senhora": 1, "drex": 1, "consignado": 1,
    "aneel": 1, "mprj": 1, "delegacia": 1, "delegado": 1, "shopping": 1,
    "bolsa familia": 1, "plano diretor": 1, "violencia na escola": 1,
    "campeonato brasileiro": 1, "clube brasileiro": 1,
}

FORA_DO_TEMA = {
    # ----------------------------------------------
    # FOFOCA E MUNDO DOS ARTISTAS
    #
    # O site e sobre o que acontece no mundo. Fofoca de celebridade,
    # bastidor de novela e sucesso de rede social nao entram.
    #
    # Cuidado com termos genericos como "atriz" ou "cantor": eles aparecem
    # legitimamente em noticia internacional (um artista que se manifesta
    # sobre uma guerra, por exemplo). Por isso o filtro exige o assunto
    # claramente de entretenimento junto, e nao a palavra sozinha.
    # ----------------------------------------------
    "fofoca": 1, "fofocando": 1, "fofocaram": 1, "fofocou": 1,
    "treta": 1, "tretas": 1, "babado": 1,
    "novo namoro": 1, "namorando": 1, "terminou o namoro": 1,
    "se separou": 1, "separam": 1, "divorcio": 1,
    "pedido de casamento": 1,
    "discutem": 1, "troca de caps": 1, "grito": 1,
    "bastidores de novela": 1, "bastidores": 1,
    "elenco de": 1,
    "novela das 9": 1, "novela das oito": 1, "final da novela": 1,
    "estreia da novela": 1, "personagem": 1, "protagonista": 1,
    "viralizou nas redes": 1, "reels": 1, "tiktok": 1,
    "seguidores": 1, "perfil": 1, "sigam no": 1,
    "podcast": 1, "podcasters": 1,
    "fans ": 1, "viraliza": 1, "viralizam": 1, "viralizou": 1,
    "bbb": 1, "big brother": 1, "a fazenda": 1,
    "bbf": 1, "power couple": 1,

    "celebridade": 1, "celebridades": 1,
    "cantor sertanejo": 1, "cantora sertaneja": 1, "sertanejo": 1,
    "atriz brasileira": 1, "ator brasileiro": 1,
    "cantora brasileira": 1, "cantor brasileiro": 1,
    "artista brasileiro": 1, "artista nacional": 1,
    "apresentadora brasileira": 1, "apresentador brasileiro": 1,
    "reality show": 1, "de frente para o sol": 1,
    "power couple": 1, "homenagem a": 1,
    "anime": 1, "manga": 1, "k-pop": 1, "kpop": 1,

    # ----------------------------------------------
    # LOTERIA, ESPORTE, TEMPO E COZINHA
    # ----------------------------------------------
    "lotofacil": 1, "lotomania": 1, "quina": 1, "dupla sena": 1,
    "dia de sorte": 1, "super sete": 1, "mega-sena": 1,
    "sorteio": 1, "apostas": 1, "prêmio da sena": 1,
    "tempo hoje": 1, "previsao do tempo": 1, "previsao para": 1,
    "receita de": 1, "bolo de": 1, "torta de": 1, "passo a passo": 1,
    "inss": 1, "meia passagem": 1, "shopping": 1,
    "vestibular": 1, "bolsa de estudos": 1, "enem": 1,
    "brasileirao": 1, "libertadores": 1, "campeonato": 1, "gol de": 1,
    # Assunto brasileiro local, que nao e dos temas do blog (geopolitica,
    # politica internacional, economia, historia, ciencia).
    "tre oficializa": 1, "datafolha": 1, "quociente eleitoral": 1,
    "candidatos a governador": 1, "candidato a senador": 1,
    "candidato a deputado": 1, "candidato a vereador": 1,
    "desistencia de": 1, "comite politico": 1, "comites politicos": 1,
    "reuniao partidaria": 1, "convencao partidaria": 1,
    "pesquisa eleitoral": 1, "intolerancia politica": 1,
    "universidade federal": 1, "jantar intimista": 1, "aniversario em": 1,
    "vaquinha": 1, "apto destruido": 1, "apartamento destruido": 1,
    "incendio no df": 1, "bombeiros": 1,
    "restaurante": 1, "show": 1, "concerto": 1, "bar": 1,
    "feira de exposicao": 1, "feira do livro": 1, "feira deTunes": 1,
    "classico contra": 1, "escalacao": 1, "ingressos": 1, "soccer": 1,
    "exposicao": 1, "museu": 1, "students visitaram": 1, "estudantes visitaram": 1,
    "meteorologia": 1, "tempestade": 1, "granizo": 1, "alerta para tempestade": 1,
    "nations league": 1, "champions": 1, "uefa": 1, "mundial de": 1,
    "temporada de": 1, "classificacao": 1, "jogos de": 1,
}

INDICIOS_MUNDO = {
    "onu": 1, "nato": 1, "uniao europeia": 1, "g20": 1, "g7": 1, "fmi": 1,
    "opec": 1, "nasa": 1, "bilateral": 1, "diplomatico": 1, "embaixada": 1,
    "tratado": 1, "estados unidos": 1, "eua": 1, "china": 1, "rusia": 1,
    "ucrania": 1, "israel": 1, "palestina": 1, "gaza": 1, "iran": 1, "iraque": 1,
    "siria": 1, "afeganistao": 1, "japao": 1, "india": 1, "egipto": 1,
    "nigeria": 1, "franca": 1, "alemanha": 1, "reino unido": 1, "italia": 1,
    "espanha": 1, "portugal": 1, "holanda": 1, "belgica": 1, "suica": 1,
    "polonia": 1, "turquia": 1, "grecia": 1, "venezuela": 1, "argentina": 1,
    "colombia": 1, "chile": 1, "mexico": 1, "canada": 1, "australia": 1,
    "cuba": 1, "haiti": 1, "vietnam": 1, "indonesia": 1, "taiwan": 1,
    "coreia": 1, "pakista": 1, "bangladesh": 1, "africa": 1,
    "guerra": 1, "conflito": 1, "ataque": 1, "missil": 1, "refugiados": 1,
    "cessar-fogo": 1, "militantes": 1, "invasao": 1, "terrorista": 1,
    "economia": 1, "inflacao": 1, "petroleo": 1, "bolsa de valores": 1,
    "dolar": 1, "mercado": 1, "comercio": 1, "sanções": 1, "sancoes": 1,
    "guerra comercial": 1, "tarifa": 1, "pib": 1, "mercado": 1,
    "ciencia": 1, "pesquisa": 1, "descoberta": 1, "nasa": 1, "spacecraft": 1,
    "telescope": 1, "rover": 1, "satellite": 1, "lunar": 1, "galaxy": 1,
    "scientist": 1, "research": 1, "virus": 1, "pandemia": 1, "vacina": 1,
    "energia nuclear": 1, "climate": 1, "aquecimento global": 1,
    "religiao": 1, "religião": 1, "igreja": 1, "islam": 1, "cristao": 1,
    "judaismo": 1, "judaísmo": 1, "budismo": 1, "hinduismo": 1, "torah": 1,
    "coran": 1, "corã": 1, "biblia": 1, "bíblia": 1, "vaticano": 1,
    "pontifico": 1, "bispo": 1, "migracao": 1, "refugio": 1,
    "historia": 1, "guerra fria": 1, "holocausto": 1, "revolucao": 1,
    "ditadura": 1, "imperio": 1, "colonial": 1, "seculo": 1, "decada": 1,
    "desastre": 1, "terremoto": 1, "tsunami": 1, "furacao": 1, "ciclone": 1,
    "enchente": 1, "sequestro": 1, "espionagem": 1, "cibernetica": 1,
    "hack": 1, "investigacao": 1, "investigação": 1, "misterio": 1,
    "mistério": 1, "agente secreto": 1, "vazamento de dados": 1,
    "desinformacao": 1, "desinformação": 1, "corrupcao": 1, "corrupção": 1,
    "brasil": 1, "lula": 1, "itamaraty": 1, "petrobras": 1, "planalto": 1,
}

# Palavras que indicam assunto internacional (pesos mais fortes)
# Os CINCO temas do blog sao geopolítica, politica internacional, economia
# mundial, historia e ciencia. Eles tem peso dobrado abaixo, porque sao o
# foco do site. As outras editorias (guerras, religioes, mistérios, Brasil no
# mundo) continuam existindo, mas nao devem tomar o espaco delas.
FOCO = ("Geopolitica", "Politica internacional", "Economia mundial",
        "Historia", "Ciencia e tecnologia")

PESOS = {
    "Geopolitica": {"geopolitica": 6, "diplomacia": 5, "diplomatico": 5, "nato": 5,
        "onu": 4, "tratado": 4, "alianca": 4, "uniao europeia": 4, "g20": 4,
        "embaixada": 4, "fronteira": 3, "hegemonia": 5, "potencia": 3},
    "Guerras e conflitos": {"guerra": 6, "conflito": 4, "ataque": 4, "bombardeio": 6,
        "missil": 4, "explosao": 4, "morre": 3, "feridos": 3, "militares": 4,
        "exercito": 4, "invasao": 6, "artilharia": 6, "trégua": 6, "cessar-fogo": 6,
        "refugiados": 4, "terrorista": 3, "massacre": 5, "conflito armado": 6},
    "Politica internacional": {"governo": 2, "eleicao": 4, "referendo": 4,
        "sanções": 4, "sancoes": 4, "impeachment": 5, "golpe": 4, "democracia": 3,
        "autoritarismo": 4, "justica internacional": 5, "parlamento": 3},
    "Economia mundial": {"economia": 5, "inflacao": 5, "pib": 5, "bolsa": 4,
        "dolar": 4, "juros": 4, "banco central": 5, "mercado": 3, "petroleo": 4,
        "guerra comercial": 5, "tarifa": 3, "recessao": 5, "investimento": 3},
    "Historia": {"historia": 6, "guerra fria": 7, "holocausto": 5,
        "segunda guerra": 6, "ditadura": 3, "revolucao": 3, "seculo": 3,
        "decada": 4, "imperio": 4, "colonial": 4, "centenario": 6},
    "Religioes e sociedade": {"religiao": 6, "religião": 6, "igreja": 4,
        "catolico": 5, "católica": 5, "cristao": 5, "cristã": 5, "islam": 6,
        "islâmico": 6, "islamico": 6, "muçulmano": 6, "musulmao": 6,
        "judaísmo": 6, "judaico": 6, "cristianismo": 6, "budismo": 6,
        "hinduismo": 6, "torah": 5, "coran": 6, "corã": 6, "biblia": 5,
        "bíblia": 5, "vaticano": 5, "pontifico": 5, "imã": 4, "rabino": 4,
        "liberdade religiosa": 6, "diáspora": 5},
    "Ciencia e tecnologia": {"ciencia": 5, "cientista": 5, "pesquisa": 4,
        "nasa": 5, "telescope": 5, "spacecraft": 5, "rover": 5, "satellite": 4,
        "lunar": 5, "galaxy": 5, "scientist": 5, "research": 4, "discovery": 5,
        "energia nuclear": 6, "genoma": 5, "vaccine": 4, "inteligencia artificial": 5,
        "virus": 3, "pandemia": 4, "climate": 3, "aquecimento global": 4},
    "Grandes acontecimentos": {"desastre": 5, "terremoto": 5, "tsunami": 5,
        "furacao": 5, "ciclone": 4, "enchente": 4, "catastrofe": 5, "explosao": 4,
        "acidente": 3, "colapso": 4, "evacuacao": 4, "desaparecimento": 4},
    "Misterios e investigacoes": {"misterio": 6, "mistério": 6, "investigacao": 5,
        "investigação": 5, "espionagem": 6, "espiao": 6, "espião": 6,
        "agente secreto": 6, "cibernetica": 5, "hack": 4, "vazamento de dados": 5,
        "wikileaks": 6, "desinformacao": 5, "desinformação": 5, "corrupcao": 3,
        "corrupção": 3, "revelações": 5, "revelacoes": 5},
    # "Brasil" sozinho e palavrao fraca: quase toda noticia do G1 Mundo
    # menciona o Brasil de passagem, e isso nao faz dela noticia sobre o
    # Brasil. O que define a editoria e a RELACAO com o exterior.
    "Brasil no mundo": {"itamaraty": 6, "lula": 5,
        "itamaraty": 5, "petrobras": 4, "planalto": 4, "brasilia": 4,
        "combustível": 4, "gasolina": 3, "alimentos": 3, "câmbio": 4, "cambio": 4,
        "relacoes exteriores": 5, "exportação brasileira": 5,
        "plano diretor": 4, "sanção contra": 4,
        "acordo comercial": 4, "sobre o brasil": 4, "ao brasil": 3,
        "tributar": 4, "imposto": 3, "tarifa": 4},
}

ORDEM = ["Geopolitica", "Guerras e conflitos", "Politica internacional",
         "Economia mundial", "Grandes acontecimentos", "Misterios e investigacoes",
         "Ciencia e tecnologia", "Religioes e sociedade", "Historia",
         "Brasil no mundo"]


# ------------------------------------------------------------- utilitarios

def sem_acentos(t):
    n = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in n if not unicodedata.combining(c))


def limpar(t):
    if not t:
        return ""
    t = unescape(t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&[a-z]+;", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tem_palavra(texto, palavra):
    p = r"(?<![a-z0-9])" + re.escape(sem_acentos(palavra)) + r"(?![a-z0-9])"
    return re.search(p, sem_acentos(texto)) is not None


def palavras_importantes(t):
    limpo = re.sub(r"[^a-z0-9\s]", " ", sem_acentos(t))
    return {p for p in limpo.split() if len(p) > 3 and p not in PALAVRAS_PARADA}


# --------------------------------------------------------------- download

def baixar(url, timeout=20, como_texto=False):
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
         "Accept-Language": "pt-BR,pt;q=0.9"}
    if como_texto:
        h["Accept"] = "text/html,application/xhtml+xml"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h),
                                    timeout=timeout) as r:
            d = r.read()
            if r.headers.get("Content-Encoding", "").lower() == "gzip" or d[:2] == b"\x1f\x8b":
                d = gzip.decompress(d)
            return d
    except Exception:
        return None


def extrair(feed, fonte):
    """Extrai as noticias e devolve uma lista."""
    try:
        raiz = ET.fromstring(feed)
    except ET.ParseError:
        try:
            texto = feed.decode("latin-1").encode("utf-8")
            raiz = ET.fromstring(texto)
        except Exception:
            return []

    nos = raiz.findall(".//item") or raiz.findall(
        ".//{http://www.w3.org/2005/Atom}entry")
    saida = []

    for no in nos:
        titulo = limpar(no.findtext("title") or
                       no.findtext("{http://www.w3.org/2005/Atom}title") or "")
        link = (no.findtext("link") or "").strip()
        resumo = limpar(no.findtext("description") or
                        no.findtext("{http://www.w3.org/2005/Atom}summary") or "")

        data = None
        bruto = (no.findtext("pubDate") or
                 no.findtext("{http://www.w3.org/2005/Atom}published") or "")
        if bruto:
            try:
                data = parsedate_to_datetime(bruto.strip())
                if data.tzinfo is None:
                    data = data.replace(tzinfo=timezone.utc)
                data = data.astimezone(timezone.utc)
            except Exception:
                data = None

        img = None
        for e in no.iter():
            tag = e.tag.split("}")[-1].lower()
            if tag in ("content", "thumbnail", "enclosure"):
                u = e.get("url") or e.get("href")
                if u and re.search(r"\.(jpe?g|png|webp)(\?|$)", u, re.I):
                    img = u
                    break
        if img and "ichef.bbci.co.uk" in img:
            img = re.sub(r"/(240|320|640)/", "/1536/", img, count=1)
        if img and "imguol.com.br" in img:
            img = None     # UOL só oferece 142x100: inútil na tela

        if titulo and link:
            saida.append({"titulo": titulo, "resumo": resumo, "link": link,
                          "quando": data, "imagem": img, "fonte": fonte})

    return saida


def foto_na_pagina(link):
    """A Folha esconde a foto na página, não no feed."""
    html = baixar(link, timeout=12, como_texto=True)
    if not html:
        return None
    html = html.decode("utf-8", "ignore")
    for pad in (r'<meta\s+property="og:image"\s+content="([^"]+)"',
                r'<meta\s+content="([^"]+)"\s+property="og:image"'):
        m = re.search(pad, html, re.I)
        if m and m.group(1).lower().startswith("http"):
            return m.group(1)
    return None


# -------------------------------------------------------------- filtros

def e_politica_nacional(n):
    texto = n["titulo"] + " " + n["resumo"]
    for termo in POLITICA_NACIONAL:
        if tem_palavra(texto, termo):
            return True
    if tem_palavra(texto, "lula") or tem_palavra(texto, "lula"):
        for externo in ("onu", "nato", "estados unidos", "china", "rusia",
                        "acordo comercial", "tarifa", "g20", "embaixada"):
            if tem_palavra(texto, externo):
                return False
        return True
    return False


# Palavras que, sozinhas, nao provam que a noticia e sobre o mundo dos
# artistas: um famoso pode ser citado numa noticia de guerra ou de politica.
# Nesses casos a noticia entra normalmente. So e descartada se a materia for
# APENAS sobre o famoso, sem nenhum assunto internacional.
# Palavras que, sozinhas, nao provam que a noticia e sobre o mundo dos
# artistas. Um famoso pode ser citado numa noticia de guerra, e "artista"
# tambem e o nome de quem pinta a estelares em um texto de ciencia.
#
# Por isso: so e fofoca se a materia NAO tiver assunto internacional nem
# cientifico. Ver a funcao so_mundo_dos_artistas logo abaixo.
CELEBRIDADE_NEUTRA = {
    "namorado de": 1, "namorada de": 1, "noivo de": 1, "noiva de": 1,
    "se declara para": 1, "declarou-se para": 1,
    "famoso": 1, "famosa": 1, "famosos": 1, "famosas": 1,
    "celebrity": 1, "cantora": 1, "cantor": 1,
    "astros": 1,
}


def so_mundo_dos_artistas(n):
    """
    Diz se a noticia e SO sobre o mundo dos artistas, sem assunto real.

    Exemplo que entra: "Famosos criticam guerra na Ucrania" -> tem assunto
    internacional, entao passa.
    Exemplo que sai: "Cantor sertanejo se separou da esposa" -> e fofoca.
    """
    texto = sem_acentos(n["titulo"] + " " + n["resumo"]).lower()

    tem_artista = any(tem_palavra(texto, p) for p in CELEBRIDADE_NEUTRA)

    # Assunto internacional claro? Entao a noticia passa, IMPORTANTE mesmo
    # que cite gente famosa.
    # Assunto real (internacional ou cientifico)? Entao a noticia passa,
    # IMPORTANTE mesmo que cite gente famosa. "Artista" aqui pode ser quem
    # pinta as estrelas, e nao quem canta.
    for externo in ("guerra", "conflito", "ataque", "onu", "nato", "g20",
                    "diplomacia", "gaza", "ucrania", "israel", "palestina",
                    "iran", "china", "rusia", "eua", "estados unidos",
                    "economia", "inflacao", "dolar", "petroleo", "tarifa",
                    "sancoes", "sanções", "eleicao", "presidencia",
                    "governo", "parlamento", "nasa", "espaco", "descoberta",
                    "astronomo", "astronomia", "telescopio", "satelite",
                    "estrela", "galaxia", "planeta", "marte", "lua",
                    "cientista", "pesquisa", "universo", "cosmologia",
                    "experimento", "laboratorio", "tecnologia", "inteligencia artificial",
                    # ciencia e historia sao editorias do site: nunca vao embora
                    "arqueologia", "arqueologo", "arqueologa", "restos arqueologicos",
                    "civilizacao", "civilizacao antiga", "pre-historia", "fossil",
                    "sismologia", "geologia", "ecologia", "biodiversidade",
                    "genetica", "biociencias", "medicina", "virus", "epidemia",
                    "orbital", "missao espacial", "observatorio"):
        if tem_palavra(texto, externo):
            return False

    return tem_artista


def e_mundial(n):
    texto = sem_acentos(n["titulo"] + " " + n["resumo"]).lower()
    for t in FORA_DO_TEMA:
        if tem_palavra(texto, t):
            return False

    # Noticia que e so sobre o mundo dos artistas, sem assunto real
    if so_mundo_dos_artistas(n):
        return False

    return True


def classificar(n):
    texto = sem_acentos(n["titulo"] + " " + n["resumo"]).lower()

    # Rede de seguranca: materia de fofoca nao vira "Politica internacional"
    # so porque nenhuma editoria combinou com ela.
    if so_mundo_dos_artistas(n):
        return "Misterios e investigacoes"

    pontos = {}
    for cat, palavras in PESOS.items():
        pontos[cat] = sum(peso for termo, peso in palavras.items()
                          if tem_palavra(texto, termo))
    # Dobra o peso dos cinco temas do blog antes de escolher a editoria.
    for foco in FOCO:
        pontos[foco] = pontos.get(foco, 0) * 2

    melhor = max(pontos, key=lambda c: pontos[c])

    # Se nenhuma editoria combinou, a materia nao serve para este site.
    # Antes caia em "Politica internacional" e virava o carrinho de lixo:
    # vaquinha de incendio,(lua de polpicos e shows de-rock entravam como
    # se fossem politica internacional. Agora e descartada.
    if pontos[melhor] == 0:
        return ""
    if pontos.get("Brasil no mundo", 0) >= pontos[melhor]:
        return "Brasil no mundo"
    return melhor


def fazer_resumo(n):
    if len(n["resumo"]) < 40:
        return ("[VERIFICAR] A fonte nao enviou um resumo desta noticia. "
                "Clique em 'Ler na fonte' para ver o texto original."), True
    t = n["resumo"]
    for sep in (". ", "; ", " - ", " — "):
        if sep in t[:320]:
            corte = t.index(sep) + len(sep)
            if corte > 60:
                t = t[:corte]
                break
    if len(t) > 320:
        t = t[:320].rsplit(" ", 1)[0] + "..."
    return t, False


def duplicadas(a, b):
    pa, pb = palavras_importantes(a), palavras_importantes(b)
    if not pa or not pb or not (pa & pb):
        return 0.0
    cobertura = len(pa & pb) / min(len(pa), len(pb))
    if cobertura < 0.5:
        return 0.0
    return 0.6 * cobertura + 0.4 * SequenceMatcher(
        None, sem_acentos(a), sem_acentos(b)).ratio()


def agrupar(noticias):
    ordenadas = sorted(noticias, key=lambda n: n["quando"] or datetime.min.replace(
        tzinfo=timezone.utc), reverse=True)
    grupos = []
    for n in ordenadas:
        for g in grupos:
            if duplicadas(g[0]["titulo"], n["titulo"]) >= 0.62:
                g.append(n)
                break
        else:
            grupos.append([n])
    return grupos


def balancear(noticias):
    por_fonte = {}
    for n in noticias:
        por_fonte.setdefault(n["fonte"], []).append(n)
    tetos = {f["nome"]: f["maximo"] for f in FONTES}
    for itens in por_fonte.values():
        itens.sort(key=lambda n: n["quando"] or datetime.min.replace(tzinfo=timezone.utc),
                   reverse=True)
    restantes = {k: list(v) for k, v in por_fonte.items()}
    usadas = {k: 0 for k in restantes}
    saida = []
    while True:
        houve = False
        for nome in restantes:
            if not restantes[nome]:
                continue
            if usadas[nome] >= tetos.get(nome, 12):
                continue
            saida.append(restantes[nome].pop(0))
            usadas[nome] += 1
            houve = True
        if not houve:
            break
    return saida


# ------------------------------------------------------------------ fotos

def salvar_fotos(noticias, inicio):
    if not os.path.isdir(PASTA_FOTOS):
        os.makedirs(PASTA_FOTOS, exist_ok=True)

    nomes = {}
    baixadas = 0
    for i, n in enumerate(noticias):
        if baixadas >= LIMITE_FOTOS or time.time() - inicio > ALTURA_RODADA:
            break
        url = n.get("imagem")
        if not url or url in nomes:
            continue
        h = {"User-Agent": "Mozilla/5.0 AppleWebKit/537.36", "Referer": n["link"]}
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h),
                                        timeout=15) as r:
                dados = r.read()
                tipo = r.headers.get("Content-Type", "").lower()
        except Exception:
            continue
        if not tipo.startswith("image/") or len(dados) < 8000:
            continue
        # Foto grande vira arquivo grande, e o GitHub guarda todas as
        # versoes de todo arquivo. Sem reduzir, o repo passa de 1 GB.
        if len(dados) > 220 * 1024:
            dados = _reduzir(dados)

        ext = ".jpg"
        if "png" in tipo:
            ext = ".png"
        elif "webp" in tipo:
            ext = ".webp"
        nome = "n%d%s" % (i, ext)
        try:
            with open(os.path.join(PASTA_FOTOS, nome), "wb") as f:
                f.write(dados)
            nomes[url] = "fotos/" + nome
            baixadas += 1
        except OSError:
            continue
    return nomes


def _reduzir(dados):
    """Reduz a foto com o compressor que ja vem no Windows."""
    import tempfile
    pasta = os.path.join(tempfile.gettempdir(), "reduzir_foto")
    os.makedirs(pasta, exist_ok=True)
    orig = os.path.join(pasta, "o.jpg")
    novo = os.path.join(pasta, "r.jpg")
    try:
        with open(orig, "wb") as f:
            f.write(dados)
        import subprocess
        subprocess.run(
            ["powerShell", "-NoProfile", "-Command",
             "$ErrorActionPreference='Stop';"
             "Add-Type -AssemblyName System.Drawing;"
             "$img=[System.Drawing.Image]::FromFile('%s');"
             "$w=%d; $h=[int]($img.Height*$w/$img.Width);"
             "$b=New-Object System.Drawing.Bitmap $w,$h;"
             "$g=[System.Drawing.Graphics]::FromImage($b);"
             "$g.DrawImage($img,0,0,$w,$h);"
             "$b.Save('%s',[System.Drawing.Imaging.ImageFormat]::Jpeg);"
             "$g.Dispose(); $b.Dispose(); $img.Dispose();" % (orig, 1200, novo)],
            capture_output=True, timeout=25)
        with open(novo, "rb") as f:
            return f.read()
    except Exception:
        return dados


def limpar_fotos(usados):
    """Remove as fotos que nao estao mais em uso, para o repo nao crescer."""
    if not os.path.isdir(PASTA_FOTOS):
        return
    manter = {v.split("/")[-1] for v in usados.values()}
    for nome in os.listdir(PASTA_FOTOS):
        if nome not in manter:
            try:
                os.remove(os.path.join(PASTA_FOTOS, nome))
            except OSError:
                pass


# ------------------------------------------------------------------- main

def main():
    inicio = time.time()
    agora = datetime.now(FUSO)
    print("Buscando as noticias...")

    noticias, erros = [], []
    for f in FONTES:
        feed = baixar(f["url"])
        if not feed:
            erros.append(f["nome"] + ": falha ao baixar")
            continue
        itens = [n for n in extrair(feed, f["nome"])[:MAX_POR_FONTE]
                 if e_mundial(n) and not e_politica_nacional(n)]

        if f["nome"].startswith("Folha"):
            # A Folha nao manda foto no feed; temos que abrir a pagina. Isso
            # e lento (uma requisicao por noticia) e por isso limitamos as 8
            # primeiras. O resto aparece sem imagem, o que ainda e melhor
            # que gastar 3 minutos do limite mensal do GitHub.
            for n in itens[:FOTOS_POR_FONTE]:
                if time.time() - inicio > ALTURA_RODADA:
                    break
                n["imagem"] = foto_na_pagina(n["link"])

        noticias.extend(itens)
        print("  %s: %d" % (f["nome"], len(itens)))

    if not noticias:
        print("Nenhuma noticia. Mantendo o site como esta.")
        return

    noticias = balancear(noticias)
    grupos = agrupar(noticias)

    resultado = []
    for g in grupos:
        p = g[0]
        resumo, verificar = fazer_resumo(p)
        resultado.append({
            "id": len(resultado) + 1,
            "titulo": p["titulo"], "resumo": resumo, "fonte": p["fonte"],
            "link": p["link"],
            # A hora tambem vem em UTC do feed. Sem converter, o horario de
            # cada noticia aparecia adiantado em tres horas.
            "quando": (p["quando"] or agora).astimezone(FUSO).strftime(
                "%Y-%m-%d %H:%M"),
            "timestamp": (p["quando"] or agora).timestamp(),
            "categoria": classificar(p),
            "outras_fontes": [{"fonte": o["fonte"], "link": o["link"]}
                             for o in g[1:]],
            "verificar": verificar, "imagem": p.get("imagem"),
        })

    # Materia que nenhuma editoria reconheceu nao entra no site. Antes
    # elas apareciam com o rotulo "Politica internacional", que nao era
    # verdade: eram assuntos locais, deultura ou de-Moda.
    sem_editoria = [n for n in resultado if not n["categoria"]]
    resultado = [n for n in resultado if n["categoria"]]
    for i, n in enumerate(resultado, start=1):
        n["id"] = i

    resultado.sort(key=lambda n: n["timestamp"], reverse=True)

    fotos = salvar_fotos(resultado, inicio)
    for n in resultado:
        if n["imagem"] in fotos:
            n["imagem"] = fotos[n["imagem"]]
    limpar_fotos(fotos)

    categorias = {}
    for n in resultado:
        categorias[n["categoria"]] = categorias.get(n["categoria"], 0) + 1

    dados = {"gerado_em": agora.strftime("%Y-%m-%d %H:%M"),
             "total": len(resultado), "noticias": resultado, "erros": erros,
             "categorias": categorias}

    with open(os.path.join(PASTA, "noticias.json"), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))

    print("\n%d noticias de %d fontes em %d segundos"
          % (len(resultado), len({n["fonte"] for n in resultado}),
             time.time() - inicio))
    if erros:
        print("Fontes que falharam: " + ", ".join(erros))


if __name__ == "__main__":
    main()