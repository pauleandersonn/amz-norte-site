#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""AMZ Norte — busca automática de notícias (a cada 5 min).

Puxa os feeds do Amazonas / nacional / internacional, descarta o que já está no
site, publica as novidades no news_data.json, regenera o index.html e (respeitando
um intervalo mínimo) faz o deploy no Netlify. A manchete do hero é consequência:
é a notícia local mais recente que entra no topo.

Nada é inventado: título, resumo, link, fonte, hora e imagem (og:image) vêm da
matéria original.

Uso:
    python busca_noticias.py              # uma rodada (uso da tarefa agendada)
    python busca_noticias.py --dry-run    # mostra o que publicaria, sem gravar
    python busca_noticias.py --sem-deploy # publica local, não sobe no Netlify
    python busca_noticias.py --forcar     # ignora cotas do dia

Estado (dedupe, cotas, último deploy) em _automacao/estado.json.
Log em _automacao/busca.log.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
os.chdir(BASE)
sys.path.insert(0, str(BASE))

import atualizar_home as ah  # noqa: E402  (feeds, filtros, og:image)
import post_news  # noqa: E402

ESTADO_DIR = BASE / "_automacao"
ESTADO_PATH = ESTADO_DIR / "estado.json"
LOCK_PATH = ESTADO_DIR / "rodando.lock"
LOG_PATH = ESTADO_DIR / "busca.log"

# ── Configuração (env > padrão) ────────────────────────────────────────────
MAX_POR_RODADA = int(os.getenv("AMZ_MAX_POR_RODADA", "4"))
# vaga reservada por seção na rodada: sem isso o local sempre enche as 4 vagas
# e nacional/internacional nunca renovam
CAPS_RODADA = {
    "local": int(os.getenv("AMZ_RODADA_LOCAL", "2")),
    "nacional": int(os.getenv("AMZ_RODADA_NACIONAL", "1")),
    "internacional": int(os.getenv("AMZ_RODADA_INTERNACIONAL", "1")),
}
MAX_HORAS = int(os.getenv("AMZ_MAX_HORAS", "48"))
COTAS = {
    "local": int(os.getenv("AMZ_MAX_LOCAL_DIA", "60")),
    "nacional": int(os.getenv("AMZ_MAX_NACIONAL_DIA", "24")),
    "internacional": int(os.getenv("AMZ_MAX_INTERNACIONAL_DIA", "16")),
}
DEPLOY_MIN_MINUTOS = int(os.getenv("AMZ_DEPLOY_MIN_MINUTOS", "5"))
MAX_ULTIMAS = 50
MAX_NACINT = 8
LOCK_VALIDADE_MIN = 25


def log(msg: str) -> None:
    """Log em arquivo (o launcher do pythonw não tem console) + stdout."""
    linha = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        ESTADO_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8", errors="replace") as f:
            f.write(linha + "\n")
    except Exception:
        pass
    try:
        print(linha)
    except Exception:
        pass


# ── Estado ─────────────────────────────────────────────────────────────────
def carregar_estado() -> dict:
    padrao = {
        "links": [],
        "titulos": [],
        "posts_por_dia": {},
        "ultimo_deploy": "",
        "ultima_rodada": "",
    }
    try:
        estado = json.loads(ESTADO_PATH.read_text(encoding="utf-8"))
    except Exception:
        return padrao
    for chave, valor in padrao.items():
        estado.setdefault(chave, valor)
    return estado


def salvar_estado(estado: dict) -> None:
    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    # guarda só os 2000 mais recentes (dedupe de longo prazo)
    estado["links"] = estado["links"][-2000:]
    estado["titulos"] = estado["titulos"][-2000:]
    estado["ultima_rodada"] = datetime.now().isoformat(timespec="seconds")
    ESTADO_PATH.write_text(
        json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def hoje_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def cota_usada(estado: dict, secao: str) -> int:
    dia = estado["posts_por_dia"].get(hoje_iso()) or {}
    return int(dia.get(secao, 0))


def contar(estado: dict, secao: str) -> None:
    dia = estado["posts_por_dia"].setdefault(hoje_iso(), {})
    dia[secao] = int(dia.get(secao, 0)) + 1
    dia["total"] = int(dia.get("total", 0)) + 1
    # limpa contadores de dias antigos
    for chave in [c for c in estado["posts_por_dia"] if c < (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")]:
        estado["posts_por_dia"].pop(chave, None)


def lock_ativo() -> bool:
    """Evita duas rodadas ao mesmo tempo (a de 5 min sobrepondo a anterior)."""
    try:
        idade = (time.time() - LOCK_PATH.stat().st_mtime) / 60
    except FileNotFoundError:
        return False
    return idade < LOCK_VALIDADE_MIN


# ── Dedupe ─────────────────────────────────────────────────────────────────
def chave_titulo(titulo: str) -> str:
    base = ah.sem_acento(titulo)
    base = "".join(c for c in base if c.isalnum() or c == " ")
    return " ".join(base.split())[:90]


def chave_link(link: str) -> str:
    return (link or "").strip().split("?")[0].rstrip("/").lower()


def links_do_site(dados: dict) -> set[str]:
    links: set[str] = set()
    for secao in ("ultimas_noticias", "mais_lidas", "urgentes", "nacionais", "internacionais"):
        for item in dados.get(secao, []):
            if item.get("link"):
                links.add(chave_link(item["link"]))
    return links


def titulos_do_site(dados: dict) -> set[str]:
    titulos: set[str] = set()
    for secao in ("ultimas_noticias", "mais_lidas", "urgentes", "nacionais", "internacionais"):
        for item in dados.get(secao, []):
            if item.get("titulo"):
                titulos.add(chave_titulo(item["titulo"]))
    return titulos


def eh_novo(item: dict, links: set[str], titulos: set[str]) -> bool:
    if chave_link(item["link"]) in links:
        return False
    if chave_titulo(item["titulo"]) in titulos:
        return False
    # mesma matéria em dois portais: título quase igual já publicado
    tokens = set(ah.sem_acento(item["titulo"]).split())
    for outro in titulos:
        outros = set(outro.split())
        if tokens and outros and len(tokens & outros) / (len(tokens | outros) or 1) >= 0.6:
            return False
    return True


# ── Coleta ─────────────────────────────────────────────────────────────────
def coletar_secao(nome: str, feeds, links: set[str], titulos: set[str]) -> list[dict]:
    itens = ah.coletar(feeds, horas=MAX_HORAS)
    itens = ah.dedupe_similar(ah.dedupe(itens))
    novos = [i for i in itens if not ah.bloqueada(i["titulo"]) and eh_novo(i, links, titulos)]
    novos.sort(key=lambda i: i["quando"])  # mais antigo primeiro → mais novo entra no topo
    log(f"  {nome}: {len(itens)} itens nos feeds, {len(novos)} novos")
    return novos


def ja_publicado_no_estado(item: dict, estado: dict) -> bool:
    return (
        chave_link(item["link"]) in {chave_link(l) for l in estado["links"]}
        or chave_titulo(item["titulo"]) in set(estado["titulos"])
    )


def publicar(item: dict, secao: str) -> dict:
    categoria = ah.classificar(item["titulo"], item["resumo"])
    if not item.get("imagem"):
        item["imagem"] = ah.og_image(item["link"])
    noticia = post_news.add_new_noticia(
        item["titulo"],
        item["resumo"] or "Leia a matéria completa no AMZ Norte.",
        categoria,
        "Paulo Amazonas",
        item.get("imagem") or None,
        link=item["link"],
        fonte=item["fonte"],
        secao=secao,
    )
    return noticia


def anexar_nacint(secao: str, noticia: dict) -> None:
    dados = post_news.load_news_data()
    lista = dados.setdefault(secao, [])
    if any(chave_link(n.get("link", "")) == chave_link(noticia.get("link", "")) for n in lista):
        return
    lista.insert(0, noticia)
    dados[secao] = lista[:MAX_NACINT]
    post_news.save_news_data(dados)


# ── Deploy ─────────────────────────────────────────────────────────────────
def achar_netlify() -> list[str] | None:
    import shutil

    for nome in ("netlify.cmd", "netlify"):
        caminho = shutil.which(nome)
        if caminho:
            return [caminho]
    for cand in (
        Path.home() / "AppData" / "Roaming" / "npm" / "netlify.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "netlify",
    ):
        if cand.exists():
            return [str(cand)]
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    return [npx, "--yes", "netlify-cli@latest"] if npx else None


def deploy() -> bool:
    cmd_base = achar_netlify()
    if not cmd_base:
        log("  ⚠️ Netlify CLI não encontrado — site atualizado só localmente")
        return False
    if cmd_base[0].lower().endswith(".cmd"):
        cmd = ["cmd", "/c", *cmd_base, "deploy", "--prod", "--dir", "."]
    elif cmd_base[0].lower().endswith(("npx", "npx.cmd")):
        cmd = list(cmd_base) + ["deploy", "--prod", "--dir", "."]
    else:
        cmd = ["sh", "-c", f'"{cmd_base[0]}" deploy --prod --dir "."']
    log(f"  🚀 deploy: {' '.join(cmd[:3])} ...")
    try:
        # pythonw (tarefa agendada) não tem stdin/console: sem DEVNULL + NO_WINDOW
        # o cmd/netlify morre com 0xC000013A (CTRL_C_EXIT) e o deploy não sobe.
        r = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=str(BASE), timeout=300,
            stdin=subprocess.DEVNULL, creationflags=0x08000000,
        )
    except subprocess.TimeoutExpired:
        log("  ⚠️ deploy: timeout de 5 min")
        return False
    except Exception as erro:
        log(f"  ⚠️ deploy falhou: {erro}")
        return False
    if r.returncode == 0:
        url = ""
        for linha in (r.stdout or "").splitlines():
            if "Production URL" in linha:
                url = linha.strip()
        log(f"  ✅ deploy ok {url}")
        return True
    log(f"  ⚠️ deploy retornou {r.returncode}: {(r.stdout or r.stderr or '').strip()[-300:]}")
    return False


# ── Rodada ─────────────────────────────────────────────────────────────────
def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    args = set(sys.argv[1:])
    dry = "--dry-run" in args
    forcar = "--forcar" in args
    sem_deploy = "--sem-deploy" in args or os.getenv("AMZ_SEM_DEPLOY") == "1"

    if not dry and lock_ativo():
        log("rodada anterior ainda em andamento — saindo")
        return 0

    ESTADO_DIR.mkdir(parents=True, exist_ok=True)
    if not dry:
        LOCK_PATH.write_text(str(os.getpid()), encoding="utf-8")

    try:
        return rodada(dry=dry, forcar=forcar, sem_deploy=sem_deploy)
    finally:
        if not dry:
            try:
                LOCK_PATH.unlink()
            except FileNotFoundError:
                pass


def rodada(*, dry: bool, forcar: bool, sem_deploy: bool) -> int:
    estado = carregar_estado()
    dados = post_news.load_news_data()
    links = links_do_site(dados) | {chave_link(l) for l in estado["links"]}
    titulos = titulos_do_site(dados) | set(estado["titulos"])

    log("── rodada ──")
    candidatos: dict[str, list[dict]] = {}
    for secao, feeds in (
        ("local", ah.FEEDS_LOCAL),
        ("nacional", ah.FEEDS_NACIONAL),
        ("internacional", ah.FEEDS_INTERNACIONAL),
    ):
        try:
            itens = coletar_secao(secao, feeds, links, titulos)
        except Exception as erro:
            log(f"  ⚠️ {secao}: {type(erro).__name__} {erro}")
            itens = []
        # pauta local do AM dentro do feed nacional não duplica a home
        if secao == "nacional":
            itens = [
                i for i in itens
                if "manaus" not in ah.sem_acento(i["titulo"] + i["resumo"])
                and "amazonas" not in ah.sem_acento(i["titulo"] + i["resumo"])
            ]
        candidatos[secao] = [i for i in itens if not ja_publicado_no_estado(i, estado)]

    # plano da rodada: local primeiro, respeitando cota de cada seção
    plano: list[tuple[str, dict]] = []
    for secao in ("local", "nacional", "internacional"):
        disponivel = len(candidatos[secao])
        if not disponivel:
            continue
        restante_rodada = MAX_POR_RODADA - len(plano)
        if restante_rodada <= 0:
            break
        if forcar:
            limite = min(restante_rodada, CAPS_RODADA[secao])
        else:
            cota_restante = max(COTAS[secao] - cota_usada(estado, secao), 0)
            limite = min(restante_rodada, CAPS_RODADA[secao], cota_restante)
        if limite <= 0:
            log(f"  {secao}: cota do dia esgotada ({cota_usada(estado, secao)}/{COTAS[secao]})")
            continue
        for item in candidatos[secao][:limite]:
            plano.append((secao, item))

    if not plano:
        log("nada novo — rodada encerrada")
        if not dry:
            salvar_estado(estado)
        return 0

    log(f"{len(plano)} nova(s) matéria(s) para publicar")
    for secao, item in plano:
        log(f"  + [{secao}] {item['titulo'][:80]}")
        if dry:
            continue
        noticia = publicar(item, secao)
        if secao in ("nacional", "internacional"):
            anexar_nacint("nacionais" if secao == "nacional" else "internacionais", noticia)
        estado["links"].append(chave_link(item["link"]))
        estado["titulos"].append(chave_titulo(item["titulo"]))
        contar(estado, secao)

    if dry:
        log("(--dry-run: nada gravado, nada publicado)")
        return 0

    if not post_news.update_index_html():
        log("  ⚠️ falha ao regenerar o index.html")
        salvar_estado(estado)
        return 1

    # deploy só se passou o intervalo mínimo desde o último (evita 288 deploys/dia)
    deve_deploy = not sem_deploy
    if deve_deploy and estado.get("ultimo_deploy"):
        try:
            ultimo = datetime.fromisoformat(estado["ultimo_deploy"])
            minutos = (datetime.now() - ultimo).total_seconds() / 60
            if minutos < DEPLOY_MIN_MINUTOS:
                log(f"  deploy adiado ({minutos:.0f} min < {DEPLOY_MIN_MINUTOS}) — sobe na próxima")
                deve_deploy = False
        except ValueError:
            pass

    if not deve_deploy:
        if sem_deploy:
            log("  deploy desligado (--sem-deploy)")
        _resumo(estado)
        salvar_estado(estado)
        return 0

    if deploy():
        estado["ultimo_deploy"] = datetime.now().isoformat(timespec="seconds")
    _resumo(estado)
    salvar_estado(estado)
    return 0


def _resumo(estado: dict) -> None:
    dia = estado["posts_por_dia"].get(hoje_iso()) or {}
    log(
        "hoje: total {t} · local {l}/{cl} · nacional {n}/{cn} · internacional {i}/{ci}".format(
            t=dia.get("total", 0),
            l=dia.get("local", 0), cl=COTAS["local"],
            n=dia.get("nacional", 0), cn=COTAS["nacional"],
            i=dia.get("internacional", 0), ci=COTAS["internacional"],
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
