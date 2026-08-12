#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AMZ Norte — Postar notícia no site (comando simples)
=====================================================
Publica uma notícia no site AMZ Norte (projeto amz-norte-site):
1. salva no news_data.json
2. regenera o index.html a partir do template
3. faz commit + push no GitHub
4. faz deploy no Netlify (site ao vivo)

USO
---
  python publicar.py                          # assistente interativo (pergunta tudo)
  python publicar.py "Título" "Resumo"        # one-liner (publica direto)
  python publicar.py --listar                 # lista as notícias publicadas
  python publicar.py --remover 3              # remove a notícia de número 3
  python publicar.py --remover "trecho"       # remove por trecho do título
  python publicar.py --atualizar              # só regenera o index.html dos dados atuais
  python publicar.py --no-publicar ...        # atualiza local, SEM git push / deploy

FLAGS (one-liner)
-----------------
  --cat, --categoria   categoria (amazonas, manaus, segurança, política, economia,
                       meio ambiente, saúde, educação, cultura, urgente)
  --autor              autor (default: Paulo Amazonas)
  --img, --imagem      URL da imagem (se omitir, escolhe uma automática)
  --urgente            marca como urgente (vai para a sidebar Urgente)
  --publicar / --no-publicar   força ou evita git push + deploy
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Consoles do Windows (cp1252) quebram com acentos/emoji -> garante UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Garante que o script rode a partir da própria pasta (independente de onde foi chamado)
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

import post_news  # reutiliza a lógica já existente do projeto

SITE_URL = "https://peaceful-salamander-0032d1.netlify.app"

MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}

CATEGORIAS = {
    "amazonas": "Amazonas",
    "manaus": "Manaus",
    "segurança": "Segurança", "seguranca": "Segurança", "polícia": "Segurança", "policia": "Segurança",
    "política": "Política", "politica": "Política",
    "economia": "Economia",
    "meio ambiente": "Meio Ambiente", "meio-ambiente": "Meio Ambiente", "ambiente": "Meio Ambiente",
    "saúde": "Saúde", "saude": "Saúde",
    "educação": "Educação", "educacao": "Educação",
    "cultura": "Cultura",
    "urgente": "Urgente",
}

# Fotos automáticas (temáticas do Amazonas) — escolhida de forma determinística
IMAGENS_PADRAO = [
    "https://images.unsplash.com/photo-1518182170546-07661fd94144?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1597733336794-12d05021d510?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1591081658714-f576fb7ea3ed?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1604599340287-2042e85a3802?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1557804506-669a67965ba0?auto=format&fit=crop&w=1200&q=80",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def data_pt(agora: datetime | None = None) -> str:
    """Data em pt-BR: '12 de agosto de 2026'."""
    agora = agora or datetime.now()
    return f"{agora.day} de {MESES_PT[agora.month]} de {agora.year}"


def normalizar_categoria(valor: str) -> str:
    return CATEGORIAS.get(valor.strip().lower(), valor.strip().title() or "Amazonas")


def imagem_automatica() -> str:
    data = post_news.load_news_data()
    n = len(data.get("ultimas_noticias", []))
    return IMAGENS_PADRAO[n % len(IMAGENS_PADRAO)]


def perguntar(mensagem: str, default: str | None = None, obrigatorio: bool = False) -> str:
    """input() segura: não quebra se o terminal fechar / receber EOF."""
    while True:
        try:
            sufixo = f" [{default}]" if default else ""
            valor = input(f"{mensagem}{sufixo}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return default or ""
        if not valor and default:
            return default
        if valor or not obrigatorio:
            return valor
        print("  ⚠️ Campo obrigatório. Digite algo.")


# ---------------------------------------------------------------------------
# Site (index.html)
# ---------------------------------------------------------------------------

def regenerar_site():
    """Regenera index.html (hero, ticker e seções) a partir do template + dados."""
    return post_news.update_index_html()


# ---------------------------------------------------------------------------
# Deploy (git + Netlify)
# ---------------------------------------------------------------------------

def achar_netlify() -> str | None:
    import shutil
    binario = shutil.which("netlify.cmd") or shutil.which("netlify")
    if binario:
        return binario
    for cand in (
        Path.home() / "AppData" / "Roaming" / "npm" / "netlify.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "netlify",
    ):
        if cand.exists():
            return str(cand)
    return None


def publicar_no_netlify(mensagem: str) -> bool:
    """git add/commit/push + netlify deploy --prod. Retorna True se concluiu."""
    print("\n🚀 Publicando no site (git + Netlify)...")
    ok = True

    # 1) Git: versão/backup no GitHub (o push também dispara o deploy CI do Netlify)
    for cmd in (
        ["git", "add", "-A"],
        [
            "git", "-c", "user.name=Pauleanderson Gomes",
            "-c", "user.email=pauleandersongomes@gmail.com",
            "commit", "-m", mensagem,
        ],
        ["git", "push"],
    ):
        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                encoding="utf-8", errors="replace", cwd=str(BASE_DIR), timeout=180,
            )
            saida = (r.stderr or r.stdout).strip()
            if r.returncode != 0 and "nothing to commit" not in saida:
                print(f"  ⚠️ git {' '.join(cmd[:2])}: {saida[:200]}")
                ok = False
        except subprocess.TimeoutExpired:
            print(f"  ⚠️ git {' '.join(cmd[:2])}: demorou demais (timeout)")
            ok = False
        except Exception as e:
            print(f"  ⚠️ git {' '.join(cmd[:2])}: {e}")
            ok = False

    # 2) Deploy direto no Netlify (garantia extra além do push)
    netlify_bin = achar_netlify()
    if not netlify_bin:
        print("  ⚠️ netlify CLI não encontrado — o push no GitHub deve publicar sozinho (CI).")
    else:
        try:
            if netlify_bin.lower().endswith(".cmd"):
                comando = ["cmd", "/c", netlify_bin, "deploy", "--prod", "--dir", "."]
            else:
                # shim do npm sem extensão (script bash) — precisa rodar via sh
                comando = ["sh", "-c", f'"{netlify_bin}" deploy --prod --dir "."']
            r = subprocess.run(
                comando,
                capture_output=True, text=True,
                encoding="utf-8", errors="replace", cwd=str(BASE_DIR), timeout=240,
            )
            if r.returncode == 0:
                print("  ✅ Deploy Netlify concluído.")
            else:
                saida = (r.stdout or r.stderr) or ""
                print(f"  ⚠️ netlify deploy: {saida.strip()[-250:]}")
                ok = False
        except subprocess.TimeoutExpired:
            print("  ⚠️ netlify deploy: demorou demais (timeout)")
            ok = False
        except Exception as e:
            print(f"  ⚠️ netlify deploy falhou: {e}")
            ok = False

    print(f"\n🌐 Site: {SITE_URL}")
    return ok


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def listar():
    data = post_news.load_news_data()
    noticias = data.get("ultimas_noticias", [])
    print(f"\n📰 Notícias publicadas no site ({len(noticias)} no total):\n")
    if not noticias:
        print("  (nenhuma ainda — rode `python publicar.py` para a primeira)")
        return
    for i, n in enumerate(noticias[:20], start=1):
        print(
            f"  {i:>2}. [{n.get('hora', '--:--')}] {n.get('titulo', '?')}"
            f"  — {n.get('categoria', 'Amazonas')}"
        )
    if len(noticias) > 20:
        print(f"  ... e mais {len(noticias) - 20} (use --remover N para apagar)")
    print()


def remover(alvo: str, publicar: bool):
    data = post_news.load_news_data()
    noticias = data.get("ultimas_noticias", [])

    indice = None
    if alvo.isdigit():
        indice = int(alvo) - 1
        if indice < 0 or indice >= len(noticias):
            print(f"❌ Número inválido (tem {len(noticias)} notícia(s)).")
            return
    else:
        for i, n in enumerate(noticias):
            if alvo.lower() in n.get("titulo", "").lower():
                indice = i
                break
        if indice is None:
            print(f"❌ Nenhuma notícia encontrada com '{alvo}'.")
            return

    removida = noticias.pop(indice)
    data["ultimas_noticias"] = noticias

    # limpa das listas derivadas
    titulo = removida.get("titulo")
    for chave in ("urgentes", "mais_lidas"):
        data[chave] = [x for x in data.get(chave, []) if x.get("titulo") != titulo]

    post_news.save_news_data(data)
    print(f"🗑️ Removida: {titulo}")

    if regenerar_site():
        print("✅ Site local atualizado.")
    if publicar:
        publicar_no_netlify(f"remove: {titulo[:70]}")
    else:
        print(f"\n🌐 Site: {SITE_URL}  (rode sem --no-publicar para atualizar o ar)")


def adicionar(titulo: str, resumo: str, categoria: str, autor: str,
              imagem: str | None, urgente: bool, publicar: bool,
              link: str | None = None):
    titulo = titulo.strip()
    resumo = resumo.strip()
    if not titulo:
        print("❌ Título obrigatório.")
        return

    # evita duplicar a mesma notícia por engano
    existentes = post_news.load_news_data().get("ultimas_noticias", [])
    if any(
        (n.get("titulo") or "").strip().lower() == titulo.lower()
        for n in existentes
    ):
        print(f"⚠️ Já existe uma notícia com este título. Nada foi adicionado.")
        return

    if not resumo:
        resumo = "Leia a matéria completa no AMZ Norte."  # resumo opcional com fallback

    cat_norm = normalizar_categoria(categoria)
    if urgente and cat_norm not in {"Urgente", "Segurança"}:
        cat_norm = "Urgente"
    imagem = (imagem or "").strip() or imagem_automatica()

    nova = post_news.add_new_noticia(titulo, resumo, cat_norm, autor or "Paulo Amazonas",
                                     imagem, link=(link or "").strip() or None)
    nova["data"] = data_pt()

    # grava a data em pt-BR (add_new_noticia usa nome do mês em inglês)
    dados = post_news.load_news_data()
    dados["ultimas_noticias"][0]["data"] = nova["data"]
    post_news.save_news_data(dados)

    if not regenerar_site():
        print("❌ Falha ao regenerar o index.html.")
        return

    if publicar:
        publicar_no_netlify(f"notícia: {titulo[:70]}")
    else:
        print(f"\n🌐 Site: {SITE_URL}  (local atualizado; rode sem --no-publicar para subir)")


def assistente(publicar_default: bool):
    """Modo interativo: pergunta tudo, mostra o resumo e confirma o deploy."""
    print()
    print("══════════════════════════════════════════")
    print("  📰 AMZ Norte — Nova notícia")
    print("══════════════════════════════════════════")

    titulo = perguntar("Título", obrigatorio=True)
    resumo = perguntar("Resumo (uma ou duas frases)")
    autor = perguntar("Autor", default="Paulo Amazonas")

    print("\nCategoria:")
    opcoes = ["Amazonas", "Manaus", "Segurança", "Política",
              "Economia", "Meio Ambiente", "Saúde", "Educação",
              "Cultura", "Urgente"]
    for i, c in enumerate(opcoes, start=1):
        print(f"  {i:>2}) {c}")
    while True:
        escolha = perguntar("Escolha o número", default="1")
        if escolha.isdigit() and 1 <= int(escolha) <= len(opcoes):
            categoria = opcoes[int(escolha) - 1]
            break
        if escolha.strip().lower() in CATEGORIAS:
            categoria = normalizar_categoria(escolha)
            break
        print("  ⚠️ Opção inválida.")

    imagem = perguntar("URL da imagem (Enter = automática)")
    link = perguntar("Link da matéria original (opcional, p/ o botão 'Ler matéria completa')")
    urgente = categoria == "Urgente" or categoria == "Segurança"

    print("\n──────────────────────────────────────────")
    print(f"  Título   : {titulo}")
    print(f"  Resumo   : {resumo or '(—)'}")
    print(f"  Categoria: {categoria}")
    print(f"  Autor    : {autor}")
    print(f"  Imagem   : {'automática' if not imagem else imagem[:70] + ('…' if len(imagem) > 70 else '')}")
    print("──────────────────────────────────────────")

    confirmar = perguntar("\nPublicar agora (git push + Netlify)?", default="S" if publicar_default else "n")
    publicar = confirmar.strip().lower() in ("s", "sim", "y", "yes")

    if not publicar:
        print("⚠️ Salvando localmente (sem publicar). Depois rode `python publicar.py --publicar` ou poste outra.")
        adicionar(titulo, resumo, categoria, autor, imagem, urgente, publicar=False, link=link)
        return

    adicionar(titulo, resumo, categoria, autor, imagem, urgente, publicar=True, link=link)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="publicar.py",
        description="Posta uma notícia no site AMZ Norte e publica (GitHub + Netlify).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("USO")[1] if "USO" in __doc__ else "",
    )
    parser.add_argument("titulo", nargs="?", help="Título da notícia (one-liner; sem isso entra no assistente)")
    parser.add_argument("resumo", nargs="?", help="Resumo da notícia")
    parser.add_argument("--cat", "--categoria", dest="categoria", default="Amazonas", help="Categoria da notícia")
    parser.add_argument("--autor", default="Paulo Amazonas", help="Autor (default: Paulo Amazonas)")
    parser.add_argument("--img", "--imagem", dest="imagem", default=None, help="URL da imagem")
    parser.add_argument("--link", "--fonte", dest="link", default=None, help="URL da matéria original (fonte)")
    parser.add_argument("--urgente", action="store_true", help="Marca como urgente")
    parser.add_argument("--listar", action="store_true", help="Lista as notícias publicadas")
    parser.add_argument("--remover", metavar="N|TÍTULO", help="Remove a notícia (número ou trecho do título)")
    parser.add_argument("--atualizar", action="store_true", help="Só regenera o index.html local (use --publicar para subir)")
    parser.add_argument("--publicar", action="store_true", help="Força git push + deploy Netlify")
    parser.add_argument("--no-publicar", action="store_true", help="Só atualiza local, sem git push / deploy")
    args = parser.parse_args()

    publicar = not args.no_publicar or args.publicar

    if args.listar:
        listar()
        return
    if args.atualizar:
        print("🔄 Regenerando index.html...")
        if regenerar_site():
            print("✅ Site local atualizado.")
            if args.publicar:
                publicar_no_netlify("update: index.html")
        return
    if args.remover:
        remover(args.remover, publicar)
        return

    if args.titulo:
        adicionar(args.titulo, args.resumo or "", args.categoria, args.autor,
                  args.imagem, args.urgente, publicar, args.link)
    else:
        assistente(publicar_default=publicar)


if __name__ == "__main__":
    main()
