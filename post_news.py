#!/usr/bin/env python3
"""
Script para automatizar postagem de notícias no site AMZ Norte
Usa template.html como base e preenche com dados do news_data.json
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

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

def generate_cards_html(noticias):
    """Generate HTML for the 4 main cards"""
    html = ""
    for i, noticia in enumerate(noticias[:4]):
        cat_class = get_category_class(noticia.get('categoria', 'amazonas'))
        html += f'''        <article class="card fade-in">
          <img src="{noticia.get('imagem', 'https://images.unsplash.com/photo-1597733336794-12d05021d510?auto=format&fit=crop&w=600&q=80')}" alt="{noticia.get('categoria', 'Notícia').title()}"/>
          <div class="card-body">
            <span class="pill pill-{cat_class}">{noticia.get('categoria', 'Amazonas').title()}</span>
            <h3>{noticia.get('titulo', 'Título da Notícia')}</h3>
            <div class="meta">Por {noticia.get('autor', 'Paulo Amazonas')} • {noticia.get('hora', '10:20')}</div>
          </div>
        </article>'''
    return html

def generate_urgentes_html(noticias):
    """Generate HTML for urgent news sidebar"""
    html = ""
    for noticia in noticias[:4]:
        html += f'''          <div class="news-item">
            <span>{noticia.get('titulo', 'Notícia urgente...')}</span>
            <time>{noticia.get('hora', '10:45')}</time>
          </div>'''
    html += '''          <a class="btn-outline" href="#">Ver Todas →</a>'''
    return html

def generate_mais_lidas_html(noticias):
    """Generate HTML for most read ranking"""
    html = ""
    for i, noticia in enumerate(noticias[:5]):
        html += f'''          <div class="rank-item">
            <span class="rank-num">{i+1}</span>
            <p>{noticia.get('titulo', f'Notícia {i+1}')}</p>
          </div>'''
    html += '''          <a class="btn-outline" href="#">Ver Todas →</a>'''
    return html

def generate_ultimas_noticias_html(noticias):
    """Generate HTML for latest news section (3 stories)"""
    html = ""
    for noticia in noticias[:3]:
        cat_class = get_category_class(noticia.get('categoria', 'amazonas'))
        html += f'''        <article class="story fade-in">
          <img src="{noticia.get('imagem', 'https://images.unsplash.com/photo-1614064641938-3bbee52942c7?auto=format&fit=crop&w=700&q=80')}" alt="{noticia.get('titulo', 'Notícia')}"/>
          <div>
            <span class="pill pill-{cat_class}">{noticia.get('categoria', 'Amazonas').title()}</span>
            <h3>{noticia.get('titulo', 'Título da Notícia')}</h3>
            <p>{noticia.get('resumo', 'Resumo da notícia...')}</p>
            <div class="meta">Por {noticia.get('autor', 'Paulo Amazonas')} • {noticia.get('data', datetime.now().strftime('%d de %B de %Y'))} • {noticia.get('hora', '10:00')}</div>
          </div>
        </article>'''
    return html

def generate_colunas_html(colunas):
    """Generate HTML for columns sidebar"""
    html = ""
    for coluna in colunas:
        html += f'''            <div class="news-item">
            <span>{coluna["nome"]}<br><small style="color:var(--gray)">Por {coluna["autor"]}</small></span>
          </div>'''
    html += '''          <a class="btn-outline" href="#">Ver Todas →</a>'''
    return html

def update_index_html():
    """Update the index.html file with latest news from template"""
    template_path = Path("template.html")
    index_path = Path("index.html")
    
    if not template_path.exists():
        print("Erro: template.html não encontrado!")
        return False
    
    # Load template
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Load news data
    news_data = load_news_data()
    
    # Generate all HTML sections
    cards_html = generate_cards_html(news_data["ultimas_noticias"])
    urgentes_html = generate_urgentes_html(news_data["urgentes"])
    mais_lidas_html = generate_mais_lidas_html(news_data["mais_lidas"])
    ultimas_noticias_html = generate_ultimas_noticias_html(news_data["ultimas_noticias"])
    colunas_html = generate_colunas_html(news_data["colunas"])
    
    # Replace placeholders in template
    replacements = {
        '<!-- Cards will be inserted here -->': cards_html,
        '<!-- Urgentes will be inserted here -->': urgentes_html,
        '<!-- Mais Lidas will be inserted here -->': mais_lidas_html,
        '<!-- Últimas Notícias will be inserted here -->': ultimas_noticias_html,
        '<!-- Colunas will be inserted here -->': colunas_html,
    }
    
    for placeholder, content in replacements.items():
        html_content = html_content.replace(placeholder, content)
    
    # Update current date
    hoje = datetime.now().strftime('%d de %B de %Y')
    html_content = html_content.replace(
        'Manaus, 25 de abril de 2026',
        f'Manaus, {hoje}'
    )
    
    # Update hero with first news if available
    if news_data["ultimas_noticias"]:
        primeira = news_data["ultimas_noticias"][0]
        # Update hero title
        html_content = re.sub(
            r'<h1 id="heroTitle">.*?</h1>',
            f'<h1 id="heroTitle">{primeira.get("titulo", "Título Principal")}</h1>',
            html_content
        )
        # Update hero summary
        html_content = re.sub(
            r'<p id="heroSummary">.*?</p>',
            f'<p id="heroSummary">{primeira.get("resumo", "Resumo da notícia principal.")}</p>',
            html_content
        )
        # Update hero image
        if primeira.get('imagem'):
            html_content = re.sub(
                r'<article class="hero fade-in" id="heroArticle">\s*<img src="[^"]*"',
                f'<article class="hero fade-in" id="heroArticle">\n        <img src="{primeira["imagem"]}"',
                html_content
            )
    
    # Write updated HTML
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Site atualizado com sucesso em {datetime.now().strftime('%H:%M:%S')}")
    print(f"   - {len(news_data['ultimas_noticias'])} últimas notícias")
    print(f"   - {len(news_data['urgentes'])} urgentes")
    print(f"   - {len(news_data['mais_lidas'])} mais lidas")
    print(f"   - {len(news_data['colunas'])} colunas")
    return True

def add_new_noticia(titulo, resumo, categoria="amazonas", autor="Paulo Amazonas", imagem=None):
    """Add a new news item to the database"""
    news_data = load_news_data()
    
    nova_noticia = {
        "titulo": titulo,
        "resumo": resumo,
        "categoria": categoria,
        "autor": autor,
        "data": datetime.now().strftime('%d de %B de %Y'),
        "hora": datetime.now().strftime('%H:%M'),
        "imagem": imagem or f"https://images.unsplash.com/photo-{abs(hash(titulo)) % 1000000000}?auto=format&fit=crop&w=700&q=80"
    }
    
    # Add to beginning of list (most recent first)
    news_data["ultimas_noticias"].insert(0, nova_noticia)
    news_data["ultimas_noticias"] = news_data["ultimas_noticias"][:50]
    
    # Also add to urgentes if it's breaking news
    if categoria.lower() in ["urgente", "segurança", "política", "polícia"]:
        news_data["urgentes"].insert(0, {
            "titulo": titulo,
            "hora": datetime.now().strftime('%H:%M')
        })
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
        # Add some demo news
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