#!/usr/bin/env python3
"""
Script para automatizar postagem de notícias no site AMZ Norte
Usa template.html como base e preenche com dados do news_data.json

Regras do site:
- Destaque (hero/cards/últimas) prioriza MANAUS > AMAZONAS > demais (público principal)
- Toda notícia clicável abre noticia.html em nova aba (resumo + foto real + fonte)
- Seção compacta "Nacional & Internacional" alimentada por news_data["nacionais"]/["internacionais"]
"""

import html
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MESES_PT = {
    1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
    5: "maio", 6: "junho", 7: "julho", 8: "agosto",
    9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
}


def data_pt(agora: datetime | None = None) -> str:
    agora = agora or datetime.now()
    return f"{agora.day} de {MESES_PT[agora.month]} de {agora.year}"


def load_news_data():
    """Load existing news data or create default structure"""
    news_file = Path("news_data.json")
    if news_file.exists():
        with open(news_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {
            "ultimas_noticias": [],
            "mais_lidas": [],
            "urgentes": [],
            "nacionais": [],
            "internacionais": [],
            "empregos": [],
            "colunas": [
                {"nome": "Bastidores da Política", "autor": "Paulo Amazonas"},
                {"nome": "Observatório da Amazônia", "autor": "Paulo Amazonas"},
                {"nome": "Amazonas em Foco", "autor": "Paulo Amazonas"}
            ]
        }


def save_news_data(data):
    """Save news data to JSON file"""
    with open("news_data.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_category_class(categoria):
    """Map category to CSS class"""
    cat = categoria.lower().strip()
    if cat in ['segurança', 'urgente', 'polícia']:
        return 'red'
    elif cat in ['política', 'político']:
        return 'blue'
    elif cat in ['economia', 'econômico']:
        return 'amber'
    elif cat in ['meio ambiente', 'ambiente', 'meio-ambiente']:
        return 'green'
    elif cat in ['saúde', 'saude']:
        return 'red'
    elif cat in ['educação', 'educacao']:
        return 'blue'
    elif cat in ['cultura']:
        return 'amber'
    else:
        return 'green'


def prioridade_noticia(noticia) -> int:
    """Prioridade do destaque: Manaus (público principal) > Amazonas > demais.
    Analisa título + resumo + categoria (nem toda notícia tem categoria Manaus/Amazonas)."""
    texto = " ".join([
        noticia.get("titulo", ""),
        noticia.get("resumo", ""),
        noticia.get("categoria", ""),
    ]).lower()
    if "manaus" in texto:
        return 0
    if "amazonas" in texto:
        return 1
    return 2


def noticias_priorizadas(noticias):
    """Ordena para o destaque: Manaus/Amazonas primeiro (estável p/ recência)."""
    return sorted(noticias, key=prioridade_noticia)


def link_noticia(noticia) -> str:
    """URL da página da notícia (noticia.html) com os dados codificados."""
    q = {
        "u": noticia.get("link", ""),
        "t": noticia.get("titulo", ""),
        "r": noticia.get("resumo", ""),
        "c": noticia.get("categoria", ""),
        "i": noticia.get("imagem", ""),
    }
    return "noticia.html?" + "&".join(f"{k}={quote(v)}" for k, v in q.items())


def esc(texto) -> str:
    return html.escape(texto or "")


def generate_cards_html(noticias):
    """Generate HTML for the 4 main cards (prioriza Manaus/Amazonas)"""
    html_out = ""
    for i, noticia in enumerate(noticias_priorizadas(noticias)[:4]):
        cat_class = get_category_class(noticia.get('categoria', 'amazonas'))
        link = link_noticia(noticia)
        html_out += f'''        <article class="card fade-in">
          <a class="news-link" href="{link}" target="_blank" rel="noopener">
          <img src="{noticia.get('imagem', 'https://images.unsplash.com/photo-1597733336794-12d05021d510?auto=format&fit=crop&w=600&q=80')}" alt="{esc(noticia.get('categoria', 'Notícia'))}" loading="lazy"/>
          <div class="card-body">
            <span class="pill pill-{cat_class}">{esc(noticia.get('categoria', 'Amazonas'))}</span>
            <h3>{esc(noticia.get('titulo', 'Título da Notícia'))}</h3>
            <div class="meta">Por {esc(noticia.get('autor', 'Paulo Amazonas'))} • {esc(noticia.get('hora', '10:20'))}</div>
          </div>
          </a>
        </article>'''
    return html_out


def generate_urgentes_html(noticias):
    """Generate HTML for urgent news sidebar (clicáveis)"""
    html_out = ""
    for noticia in noticias[:4]:
        link = link_noticia(noticia)
        html_out += f'''          <a class="news-link" href="{link}" target="_blank" rel="noopener">
            <div class="news-item">
              <span>{esc(noticia.get('titulo', 'Notícia urgente...'))}</span>
              <time>{esc(noticia.get('hora', '10:45'))}</time>
            </div>
          </a>'''
    html_out += '''          <a class="btn-outline" href="#">Ver Todas →</a>'''
    return html_out


def generate_mais_lidas_html(noticias):
    """Generate HTML for most read ranking (clicável)"""
    html_out = ""
    for i, noticia in enumerate(noticias[:5]):
        link = link_noticia(noticia)
        html_out += f'''          <a class="news-link" href="{link}" target="_blank" rel="noopener">
            <div class="rank-item">
              <span class="rank-num">{i+1}</span>
              <p>{esc(noticia.get('titulo', f'Notícia {i+1}'))}</p>
            </div>
          </a>'''
    html_out += '''          <a class="btn-outline" href="#">Ver Todas →</a>'''
    return html_out


def generate_ultimas_noticias_html(noticias):
    """Generate HTML for latest news section (3 stories, prioriza Manaus/Amazonas)"""
    html_out = ""
    for noticia in noticias_priorizadas(noticias)[:3]:
        cat_class = get_category_class(noticia.get('categoria', 'amazonas'))
        link = link_noticia(noticia)
        html_out += f'''        <article class="story fade-in">
          <img src="{noticia.get('imagem', 'https://images.unsplash.com/photo-1614064641938-3bbee52942c7?auto=format&fit=crop&w=700&q=80')}" alt="{esc(noticia.get('titulo', 'Notícia'))}" loading="lazy"/>
          <div>
            <span class="pill pill-{cat_class}">{esc(noticia.get('categoria', 'Amazonas'))}</span>
            <h3><a href="{link}" target="_blank" rel="noopener">{esc(noticia.get('titulo', 'Título da Notícia'))}</a></h3>
            <p>{esc(noticia.get('resumo', 'Resumo da notícia...'))}</p>
            <div class="meta">Por {esc(noticia.get('autor', 'Paulo Amazonas'))} • {esc(noticia.get('data', data_pt()))} • {esc(noticia.get('hora', '10:00'))}</div>
          </div>
        </article>'''
    return html_out


def generate_colunas_html(colunas):
    """Generate HTML for columns sidebar"""
    html_out = ""
    for coluna in colunas:
        html_out += f'''            <div class="news-item">
            <span>{esc(coluna["nome"])}<br><small style="color:var(--gray)">Por {esc(coluna["autor"])}</small></span>
          </div>'''
    html_out += '''          <a class="btn-outline" href="#">Ver Todas →</a>'''
    return html_out


def generate_empregos_html(empregos):
    """Banda de Emprego no topo da página: até 3 vagas/concursos (ou estado vazio).
    Cada item: vaga, empresa, tipo, local, salario (opcional), descricao.
    O card abre a página interna vaga.html?v=N (nada de link externo)."""
    if not empregos:
        return ('<div class="empregos-empty">💼 Novas vagas chegando em breve. '
                'Tem uma vaga ou concurso aberto? '
                '<a href="mailto:portalamznorte@gmail.com?subject=Divulgar%20vaga%20de%20emprego">'
                'Envie para o AMZ Norte</a>.</div>')
    html_out = ""
    for i, vaga in enumerate(empregos[:3]):
        meta = esc(vaga.get("tipo", "Emprego"))
        if vaga.get("salario"):
            meta += f" · {esc(vaga['salario'])}"
        local = esc(vaga.get("local", "Manaus - AM"))
        corpo = (
            f'<div class="vaga-tipo">{meta}</div>'
            f'<h3>{esc(vaga.get("vaga", vaga.get("titulo", "Vaga")))}</h3>'
            f'<p>{esc(vaga.get("empresa", vaga.get("fonte", "")))} — {local}</p>'
            + (f'<p>{esc(vaga["descricao"])}</p>' if vaga.get("descricao") else "")
        )
        corpo += ('<div class="vaga-meta"><i class="fas fa-arrow-right"></i> '
                  'Ver detalhes</div>')
        html_out += f'''        <div class="vaga-card">
          <a href="vaga.html?v={i}">
            {corpo}
          </a>
        </div>'''
    return html_out


def generate_nacint_html(noticias):
    """Seção compacta Nacional/Internacional: miniatura real + título pequeno + fonte."""
    html_out = ""
    for noticia in noticias[:6]:
        link = link_noticia(noticia)
        img = noticia.get("imagem", "")
        img_html = (f'<img src="{esc(img)}" alt="{esc(noticia.get("titulo", ""))[:40]}" loading="lazy" '
                    'onerror="this.style.display=\'none\'"/>') if img else ""
        html_out += f'''          <div class="nacint-item">
            {img_html}
            <div>
              <h4><a href="{link}" target="_blank" rel="noopener">{esc(noticia.get("titulo", ""))}</a></h4>
              <div class="nacint-fonte">{esc(noticia.get("fonte", ""))}</div>
            </div>
          </div>'''
    return html_out


def enriquecer_urgentes(news_data):
    """Preenche resumo/link/imagem/categoria dos urgentes antigos que foram
    salvos só com título (bug antigo), cruzando com as notícias completas."""
    completas = news_data.get("ultimas_noticias", []) + news_data.get("mais_lidas", [])
    por_titulo = {}
    for n in completas:
        t = (n.get("titulo") or "").strip().lower()
        if t and t not in por_titulo:
            por_titulo[t] = n
    mudou = False
    for u in news_data.get("urgentes", []):
        if u.get("resumo") or u.get("link"):
            continue  # já completo
        completo = por_titulo.get((u.get("titulo") or "").strip().lower())
        if completo:
            for k in ("resumo", "link", "imagem", "categoria", "fonte", "data", "autor"):
                if k not in u and completo.get(k):
                    u[k] = completo[k]
            mudou = True
    if mudou:
        save_news_data(news_data)
    return mudou


def update_index_html():
    """Update the index.html file with latest news from template"""
    template_path = Path("template.html")
    index_path = Path("index.html")

    if not template_path.exists():
        print("Erro: template.html não encontrado!")
        return False

    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    news_data = load_news_data()

    # Corrige urgentes antigos salvos só com título (clique abria página vazia)
    enriquecer_urgentes(news_data)

    cards_html = generate_cards_html(news_data["ultimas_noticias"])
    urgentes_html = generate_urgentes_html(news_data["urgentes"])
    mais_lidas_html = generate_mais_lidas_html(news_data["mais_lidas"])
    ultimas_noticias_html = generate_ultimas_noticias_html(news_data["ultimas_noticias"])
    colunas_html = generate_colunas_html(news_data["colunas"])
    nacionais_html = generate_nacint_html(news_data.get("nacionais", []))
    internacionais_html = generate_nacint_html(news_data.get("internacionais", []))
    empregos_html = generate_empregos_html(news_data.get("empregos", []))

    replacements = {
        '<!-- Cards will be inserted here -->': cards_html,
        '<!-- Urgentes will be inserted here -->': urgentes_html,
        '<!-- Mais Lidas will be inserted here -->': mais_lidas_html,
        '<!-- Últimas Notícias will be inserted here -->': ultimas_noticias_html,
        '<!-- Colunas will be inserted here -->': colunas_html,
        '<!-- Nacionais will be inserted here -->': nacionais_html,
        '<!-- Internacionais will be inserted here -->': internacionais_html,
        '<!-- Empregos will be inserted here -->': empregos_html,
    }

    for placeholder, content in replacements.items():
        html_content = html_content.replace(placeholder, content)

    # Data de hoje (topbar + hero)
    hoje = data_pt()
    html_content = html_content.replace(
        'Manaus, 25 de abril de 2026',
        f'Manaus, {hoje}'
    )
    html_content = re.sub(
        r'● Por [^<]*<span>•</span> [^<]+',
        f"● Por Paulo Amazonas <span>•</span> {hoje}",
        html_content, count=1,
    )

    # Hero: usa a primeira notícia priorizada (Manaus/Amazonas primeiro)
    if news_data["ultimas_noticias"]:
        primeira = noticias_priorizadas(news_data["ultimas_noticias"])[0]
        link_hero = link_noticia(primeira)
        html_content = re.sub(
            r'<h1 id="heroTitle">.*?</h1>',
            f'<h1 id="heroTitle"><a href="{link_hero}" target="_blank" rel="noopener">{esc(primeira.get("titulo", "Título Principal"))}</a></h1>',
            html_content, flags=re.S,
        )
        html_content = re.sub(
            r'<p id="heroSummary">.*?</p>',
            f'<p id="heroSummary">{esc(primeira.get("resumo", "Resumo da notícia principal."))}</p>',
            html_content, flags=re.S,
        )
        if primeira.get('imagem'):
            html_content = re.sub(
                r'(<article class="hero fade-in" id="heroArticle">\s*<img src=")[^"]*(")',
                rf'\g<1>{primeira["imagem"]}\g<2>',
                html_content, count=1,
            )

    # Ticker: texto da notícia mais recente (priorizada), clicável
    if news_data["ultimas_noticias"]:
        topo = noticias_priorizadas(news_data["ultimas_noticias"])[0]
        link_ticker = link_noticia(topo)
        html_content = re.sub(
            r'(<p id="tickerText">).*?(</p>)',
            rf'\g<1><a href="{link_ticker}" target="_blank" rel="noopener">• {esc(topo.get("titulo", ""))}</a>\g<2>',
            html_content, count=1, flags=re.S,
        )
        html_content = re.sub(
            r'(<span class="time" id="tickerTime">).*?(</span>)',
            rf'\g<1>{esc(topo.get("hora", ""))}\g<2>',
            html_content, count=1, flags=re.S,
        )

    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ Site atualizado com sucesso em {datetime.now().strftime('%H:%M:%S')}")
    print(f"   - {len(news_data['ultimas_noticias'])} últimas notícias")
    print(f"   - {len(news_data['urgentes'])} urgentes")
    print(f"   - {len(news_data['mais_lidas'])} mais lidas")
    print(f"   - {len(news_data.get('nacionais', []))} nacionais")
    print(f"   - {len(news_data.get('internacionais', []))} internacionais")
    print(f"   - {len(news_data['colunas'])} colunas")
    return True


def add_new_noticia(titulo, resumo, categoria="amazonas", autor="Paulo Amazonas", imagem=None, link=None, fonte=None, texto=None, secao=None):
    """Add a new news item to the database

    texto: texto completo da matéria (reescrito pelo AMZ Norte). Quando presente,
    a página noticia.html mostra o texto completo em vez de só o resumo.
    secao: local / nacional / internacional (opcional, p/ organização).
    """
    news_data = load_news_data()

    nova_noticia = {
        "titulo": titulo,
        "resumo": resumo,
        "categoria": categoria,
        "autor": autor,
        "data": data_pt(),
        "hora": datetime.now().strftime('%H:%M'),
        "imagem": imagem or f"https://images.unsplash.com/photo-{abs(hash(titulo)) % 1000000000}?auto=format&fit=crop&w=700&q=80"
    }
    if texto and texto.strip():
        nova_noticia["texto"] = texto.strip()
    if secao:
        nova_noticia["secao"] = secao
    if link:
        nova_noticia["link"] = link
        nova_noticia["fonte"] = fonte or link.split("//")[-1].split("/")[0].replace("www.", "")
    elif fonte:
        nova_noticia["fonte"] = fonte

    # Add to beginning of list (most recent first)
    news_data["ultimas_noticias"].insert(0, nova_noticia)
    news_data["ultimas_noticias"] = news_data["ultimas_noticias"][:50]

    # Also add to urgentes if it's breaking news (guarda a notícia completa,
    # para o clique abrir a página da notícia com resumo/foto/link)
    if categoria.lower() in ["urgente", "segurança", "política", "polícia"]:
        urgente_item = dict(nova_noticia)
        urgente_item.setdefault("hora", datetime.now().strftime('%H:%M'))
        news_data["urgentes"].insert(0, urgente_item)
        news_data["urgentes"] = news_data["urgentes"][:10]

    # Update mais lidas
    news_data["mais_lidas"].insert(0, nova_noticia)
    news_data["mais_lidas"] = news_data["mais_lidas"][:10]

    save_news_data(news_data)
    print(f"✅ Notícia adicionada: {titulo}")
    return nova_noticia


def main():
    """Main function for CLI usage"""
    import sys

    if len(sys.argv) < 2:
        print("Uso:")
        print("  python post_news.py update          # Atualiza o site com notícias existentes")
        print("  python post_news.py add \"Título\" \"Resumo\" [categoria] [autor] [imagem]  # Adiciona nova notícia")
        print("  python post_news.py demo            # Adiciona notícias de demonstração")
        return

    comando = sys.argv[1].lower()

    if comando == "update":
        update_index_html()

    elif comando == "add":
        if len(sys.argv) < 4:
            print("Erro: Título e resumo são obrigatórios")
            return

        titulo = sys.argv[2]
        resumo = sys.argv[3]
        categoria = sys.argv[4] if len(sys.argv) > 4 else "amazonas"
        autor = sys.argv[5] if len(sys.argv) > 5 else "Paulo Amazonas"
        imagem = sys.argv[6] if len(sys.argv) > 6 else None

        add_new_noticia(titulo, resumo, categoria, autor, imagem)
        update_index_html()

    elif comando == "demo":
        demo_news = [
            {
                "titulo": "Novo hospital de campanha é instalado em Manaus para atendimento de emergência",
                "resumo": "O Governo do Amazonas anunciou a instalação de um hospital de campanha na zona leste de Manaus para atender o aumento de casos de doenças respiratórias.",
                "categoria": "saúde",
                "autor": "Paulo Amazonas"
            },
            {
                "titulo": "Turismo no Amazonas cresce 25% no primeiro trimestre de 2026",
                "resumo": "Dados da Secretaria de Estado de Turismo mostram aumento significativo no número de visitantes ao estado, impulsionado pelo turismo ecológico e cultural.",
                "categoria": "economia",
                "autor": "Paulo Amazonas"
            },
            {
                "titulo": "Escolas da rede estadual recebem novos kits de ciências e biologia",
                "resumo": "O Programa Educação do Amazonas distribuiu mais de 5.000 kits educacionais para escolas de Manaus e interior, focados em experimentos práticos de ciências.",
                "categoria": "educação",
                "autor": "Paulo Amazonas"
            }
        ]

        for noticia in demo_news:
            add_new_noticia(
                noticia["titulo"],
                noticia["resumo"],
                noticia["categoria"],
                noticia["autor"]
            )

        update_index_html()
        print("✅ Notícias de demonstração adicionadas!")

    else:
        print(f"Comando desconhecido: {comando}")


if __name__ == "__main__":
    main()
