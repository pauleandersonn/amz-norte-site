#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Atualização editorial MANUAL da home do AMZ Norte.

Roda quando o Paule pedir ("atualizar o portal"): puxa as manchetes reais dos
feeds do Amazonas / nacional / internacional, remonta news_data.json, atualiza
hero + ticker do template.html e regenera o index.html.

Nada aqui é agendado e nada é inventado: título, resumo, link, fonte, hora e
imagem (og:image) vêm da matéria original.

Uso:
    python atualizar_home.py            # monta e regenera o index.html local
    python atualizar_home.py --dry-run  # só mostra o que seria publicado
"""

from __future__ import annotations

import html
import json
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}

FEEDS_LOCAL = {
    "d24am": "https://d24am.com/feed/",
    "Em Tempo": "https://emtempo.com.br/feed/",
    "A Crítica": "https://www.acritica.com/rss",
    "Amazonas1": "https://amazonas1.com.br/feed/",
    "CM7 Brasil": "https://cm7brasil.com/feed/",
}
FEEDS_NACIONAL = [
    ("G1", "https://g1.globo.com/rss/g1/"),
    ("CNN Brasil", "https://www.cnnbrasil.com.br/feed/"),
]
FEEDS_INTERNACIONAL = [
    ("Euronews", "https://pt.euronews.com/rss"),
    ("ONU News", "https://news.un.org/feed/subscribe/pt/news/all/rss.xml"),
]

# Assuntos que o portal não cobre (mesmo filtro do antigo pipeline)
BLOQUEIO = (
    "futebol", "brasileirão", "flamengo", "corinthians", "palmeiras", "vasco",
    "botafogo", "são paulo fc", "grêmio", "santos", "fluminense", "cruzeiro",
    "atlético", "copinha", "olimpíada", "olimpíadas", "fofoca", "bbb",
    "celebridade", "influencer", "novela", "reality", "loteria", "horóscopo",
    # esporte (o termo "futebol" não pega tudo: "Taça das Favelas" passava)
    "taça", "campeonato", "copa", "jogador", "gol", "técnico do time",
    "estádio", "série a", "série b", "libertadores", "brasileira", "seleção brasileira",
)

CATEGORIAS = (
    ("Meio Ambiente", ("incêndio", "queimada", "desmatamento", "garimpo",
                       "ambienta", "floresta", "amazônia", "clima", "seca",
                       "cheia", "rio madeira", "rio amazonas", "biodiversidade")),
    ("Segurança", ("polícia", "policia", "policial", "preso", "prisão", "morto",
                   "morte", "assassin", "crime", "apreend", "apreens", "facção",
                   "homicídio", "tiros", "violência", "operação", "tráfico",
                   "skunk", "droga", "assalto", "roubo")),
    ("Política", ("câmara", "camara", "senado", "deputado", "senador",
                  "governo", "prefeitura", "prefeito", "governador", "eleição",
                  "ministro", "vereador", "aleam", "assembleia", "mpam",
                  "ministério público", "stf", "congresso", "ajuste fiscal")),
    ("Economia", ("dólar", "mercado", "inflação", "juros", "salário", "economia",
                  "pib", "emprego", "concurso", "imposto", "iptu", "comércio",
                  "bolsa", "câmbio", "grãos", "soja")),
    ("Saúde", ("saúde", "hospital", "anvisa", "medicamento", "doença", "câncer",
               "sus", "vacina", "dengue", "médic", "inss", "perícia")),
    ("Educação", ("educação", "escola", "aluno", "estudante", "matrícula",
                  "seduc", "professor", "universidade", "enem", "vestibular")),
    ("Cultura", ("cultura", "festival", "show", "música", "cinema",
                 "documentário", "exposição", "teatro", "livro", "artista")),
)
# Manaus > Amazonas > resto (mesma regra do destaque do site)
PRIORIDADE_LOCAL = ("manaus", "amazonas")


def sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    ).lower()


def limpar(markup: str) -> str:
    texto = re.sub(r"<[^>]+>", " ", markup or "")
    texto = html.unescape(texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def resumir(texto: str, limite: int = 230) -> str:
    """Corta no fim de frase mais próximo do limite (sem cortar palavra)."""
    texto = texto.strip()
    if len(texto) <= limite:
        return texto
    corte = texto[:limite]
    fim = max(corte.rfind(". "), corte.rfind("! "), corte.rfind("? "))
    if fim > 90:
        return corte[: fim + 1]
    return corte.rsplit(" ", 1)[0] + "…"


def classificar(titulo: str, resumo: str) -> str:
    base = sem_acento(f"{titulo} {resumo}")
    for categoria, chaves in CATEGORIAS:
        if any(sem_acento(k) in base for k in chaves):
            return categoria
    if "manaus" in base:
        return "Manaus"
    if "amazonas" in base:
        return "Amazonas"
    return "Brasil"


def bloqueada(titulo: str) -> bool:
    """Filtro de assunto. Casa a palavra inteira: "gol" não pode pegar "golpe"."""
    base = sem_acento(titulo)
    return any(
        re.search(rf"\b{re.escape(sem_acento(b))}\b", base) for b in BLOQUEIO
    )


def buscar_feed(url: str, fonte: str) -> list[dict]:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as resp:
        root = ET.fromstring(resp.read())
    itens = []
    for item in root.findall(".//item"):
        data_txt = (item.findtext("pubDate") or "").strip()
        try:
            quando = parsedate_to_datetime(data_txt)
        except (TypeError, ValueError):
            continue
        if quando.tzinfo:
            quando = quando.astimezone().replace(tzinfo=None)
        imagem = ""
        for caminho in (
            ".//{http://search.yahoo.com/mrss/}content",
            "{http://search.yahoo.com/mrss/}thumbnail",
            ".//enclosure",
        ):
            el = item.find(caminho)
            if el is not None:
                candidata = el.get("url") or ""
                if candidata and not candidata.lower().endswith((".mp4", ".mp3")):
                    imagem = candidata
                    break
        titulo = limpar(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        if not titulo or not link:
            continue
        itens.append({
            "titulo": titulo,
            "resumo": resumir(limpar(item.findtext("description"))),
            "link": link,
            "imagem": imagem,
            "fonte": fonte,
            "quando": quando,
        })
    return itens


def og_image(url: str) -> str:
    """Imagem real da matéria (og:image) — feeds locais quase nunca trazem."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as resp:
            pagina = resp.read(400_000).decode("utf-8", "replace")
    except Exception:
        return ""
    padroes = (
        r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
        r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image',
        r'name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)',
    )
    for padrao in padroes:
        achado = re.search(padrao, pagina, re.I)
        if achado:
            return html.unescape(achado.group(1)).replace("&amp;", "&")
    return ""


def prioridade(item: dict) -> tuple[int, float]:
    base = sem_acento(item["titulo"] + " " + item["resumo"])
    for nivel, chave in enumerate(PRIORIDADE_LOCAL):
        if chave in base:
            return nivel, -item["quando"].timestamp()
    return len(PRIORIDADE_LOCAL), -item["quando"].timestamp()


def coletar(feeds: dict | list, horas: int = 30) -> list[dict]:
    limite = datetime.now() - timedelta(hours=horas)
    itens: list[dict] = []
    if isinstance(feeds, dict):
        fontes = list(feeds.items())
    else:
        fontes = feeds
    for fonte, url in fontes:
        try:
            encontrados = buscar_feed(url, fonte)
        except Exception as erro:  # feed fora do ar não derruba a rodada
            print(f"  ⚠️  {fonte}: {type(erro).__name__} {erro}")
            continue
        recentes = [i for i in encontrados if i["quando"] >= limite]
        print(f"  · {fonte}: {len(encontrados)} itens ({len(recentes)} nas últimas {horas}h)")
        itens.extend(recentes)
    return itens


def dedupe(itens: list[dict]) -> list[dict]:
    vistos: set[str] = set()
    saida = []
    for item in itens:
        chave = sem_acento(re.sub(r"[^a-z0-9 ]", "", item["titulo"].lower()))
        chave = re.sub(r"\s+", " ", chave).strip()[:80]
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append(item)
    return saida


def dedupe_similar(itens: list[dict], limite: float = 0.6) -> list[dict]:
    """Duas fontes cobrindo a mesma matéria (ex.: ajuste fiscal) não podem
    ocupar dois lugares na home — descarta título quase igual por Jaccard."""
    saida: list[dict] = []
    for item in itens:
        tokens = set(sem_acento(item["titulo"]).split())
        if any(
            len(tokens & (outro := set(sem_acento(o["titulo"]).split())))
            / (len(tokens | outro) or 1) >= limite
            for o in saida
        ):
            continue
        saida.append(item)
    return saida


def montar_noticia(item: dict) -> dict:
    return {
        "titulo": item["titulo"],
        "resumo": item["resumo"],
        "categoria": item["categoria"],
        "autor": "Paulo Amazonas",
        "data": item["quando"].strftime("%d/%m/%Y"),
        "hora": item["quando"].strftime("%H:%M"),
        "imagem": item["imagem"],
        "link": item["link"],
        "fonte": item["fonte"],
    }


def escolher(itens: list[dict], quantos: int) -> list[dict]:
    """Recência + peso local; tira esporte/fofoca e garante imagem quando der."""
    filtrados = [i for i in itens if not bloqueada(i["titulo"])]
    filtrados.sort(key=prioridade)
    escolhidos = filtrados[:quantos]
    faltam = quantos - len(escolhidos)
    if faltam > 0:  # completa com o que sobrou, sem repetir
        escolhidos += [i for i in filtrados if i not in escolhidos][:faltam]
    return escolhidos


def completar_imagens(itens: list[dict]) -> None:
    for item in itens:
        if not item["imagem"]:
            item["imagem"] = og_image(item["link"])
            print(f"  🖼  {'ok' if item['imagem'] else 'sem'} — {item['titulo'][:60]}")


def main() -> int:
    dry = "--dry-run" in sys.argv
    try:  # console do Windows (cp1252) não aceita os emojis do log
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("📡 Coletando feeds locais...")
    local = dedupe_similar(dedupe(coletar(FEEDS_LOCAL, horas=30)))
    print("📡 Coletando nacional...")
    nacional = dedupe_similar(dedupe(coletar(FEEDS_NACIONAL, horas=30)))
    # G1/CNN são nacionais, mas publicam pauta local do AM: isso já é "últimas"
    nacional = [
        n for n in nacional
        if "manaus" not in sem_acento(n["titulo"] + n["resumo"])
        and "amazonas" not in sem_acento(n["titulo"] + n["resumo"])
    ]
    print("📡 Coletando internacional...")
    internacional = dedupe_similar(dedupe(coletar(FEEDS_INTERNACIONAL, horas=36)))

    if len(local) < 6:
        print("  ⚠️  pouca pauta local nas últimas 30h — ampliando para 60h")
        local = dedupe_similar(dedupe(coletar(FEEDS_LOCAL, horas=60)))

    for grupo in (local, nacional, internacional):
        for item in grupo:
            item["categoria"] = classificar(item["titulo"], item["resumo"])

    ultimas = escolher(local, 16)
    nac = escolher(nacional, 6)
    inter = escolher(internacional, 6)

    if not ultimas:
        print("✖️  Nenhuma notícia local coletada — abortando sem tocar no site.")
        return 1

    print(f"\n🖼  Buscando imagens reais ({len(ultimas) + len(nac) + len(inter)} matérias)...")
    completar_imagens(ultimas + nac + inter)

    manchete = ultimas[0]
    urgentes = [n for n in ultimas if n["categoria"] == "Segurança"][:4] or ultimas[1:5]
    mais_lidas = ultimas[:5]

    dados = {
        "ultimas_noticias": [montar_noticia(n) for n in ultimas],
        "mais_lidas": [montar_noticia(n) for n in mais_lidas],
        "urgentes": [montar_noticia(n) for n in urgentes],
        "colunas": [
            {"nome": "Bastidores da Política", "autor": "Paulo Amazonas"},
            {"nome": "Observatório da Amazônia", "autor": "Paulo Amazonas"},
            {"nome": "Amazonas em Foco", "autor": "Paulo Amazonas"},
        ],
        "nacionais": [montar_noticia(n) for n in nac],
        "internacionais": [montar_noticia(n) for n in inter],
        "empregos": [],
    }

    print("\n=== MANCHETE (hero) ===")
    print(f"  {manchete['titulo']}")
    m = montar_noticia(manchete)
    print(f"  {m['fonte']} · {m['data']} {m['hora']}")
    print("\n=== ÚLTIMAS ===")
    for i, n in enumerate(dados["ultimas_noticias"], 1):
        print(f"  {i:2}. [{n['categoria']}] {n['titulo'][:78]}")
    print("\n=== NACIONAL / INTERNACIONAL ===")
    for n in dados["nacionais"] + dados["internacionais"]:
        print(f"  - ({n['fonte']}) {n['titulo'][:70]}")

    if dry:
        print("\n(--dry-run: nada foi gravado)")
        return 0

    (BASE / "news_data.json").write_text(
        json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    sys.path.insert(0, str(BASE))
    import post_news  # noqa: E402

    ok = post_news.update_index_html()
    print(f"\n✅ news_data.json + template.html + index.html {'atualizados' if ok else 'com erro na regeneração'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
