#!/usr/bin/env python3
"""
Script para automatizar postagem de notícias no site AMZ Norte
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
        # Default news structure
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

def generate_news_html(news_data):
    """Generate HTML content for news sections"""
    
    # Generate Últimas Notícias
    ultimas_noticias_html = ""
    for i, noticia in enumerate(news_data["ultimas_noticias"][:3]):  # Show top 3
        ultimas_noticias_html += f'''
        <article class="story fade-in">
            <img src="{noticia.get('imagem', 'https://images.unsplash.com/photo-1614064641938-3bbee52942c7?auto=format&fit=crop&w=700&q=80')}" alt="{noticia.get('titulo', 'Notícia')}"/>
            <div>
                <span class="pill pill-{noticia.get('categoria', 'verde')}">{noticia.get('categoria', 'Amazonas').title()}</span>
                <h3>{noticia.get('titulo', 'Título da Notícia')}</h3>
                <p>{noticia.get('resumo', 'Resumo da notícia...')}</p>
                <div class="meta">Por {noticia.get('autor', 'Paulo Amazonas')} • {noticia.get('data', datetime.now().strftime('%d de %B de %Y'))} • {noticia.get('hora', '10:00')}</div>
            </div>
        </article>'''

    # Generate Mais Lidas ranking
    mais_lidas_html = ""
    for i, noticia in enumerate(news_data["mais_lidas"][:5]):
        mais_lidas_html += f'''
        <div class="rank-item">
            <span class="rank-num">{i+1}</span>
            <p>{noticia.get('titulo', f'Notícia {i+1}')}</p>
        </div>'''

    # Generate Urgentes
    urgentes_html = ""
    for noticia in news_data["urgentes"][:4]:
        urgentes_html += f'''
        <div class="news-item">
            <span>{noticia.get('titulo', 'Notícia urgente...')}</span>
            <time>{noticia.get('hora', '10:00')}</time>
        </div>'''

    # Generate Colunas
    colunas_html = ""
    for coluna in news_data["colunas"]:
        colunas_html += f'''
        <div class="news-item">
            <span>{coluna["nome"]}<br><small style="color:var(--gray)">Por {coluna["autor"]}</small></span>
        </div>'''

    return ultimas_noticias_html, mais_lidas_html, urgentes_html, colunas_html

def update_index_html():
    """Update the index.html file with latest news"""
    index_path = Path("index.html")
    
    if not index_path.exists():
        print("Erro: index.html não encontrado!")
        return False
    
    # Load current news data
    news_data = load_news_data()
    
    # Generate HTML sections
    ultimas_noticias_html, mais_lidas_html, urgentes_html, colunas_html = generate_news_html(news_data)
    
    # Read current HTML
    with open(index_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Replace sections
    # Replace Últimas Notícias stories
    html_content = re.sub(
        r'(<!-- ÚLTIMAS NOTÍCIAS -->.*?<div class="content-columns">.*?<div>)(.*?)(</div>)',
        rf'\1{ultimas_noticias_html}\3',
        html_content,
        flags=re.DOTALL
    )
    
    # Replace Mais Lidas ranking
    html_content = re.sub(
        r'(<div class="box-title green"><i class="fas fa-fire"></i> Mais Lidas</div>.*?<div class="news-list">)(.*?)(</div>)',
        rf'\1{mais_lidas_html}\3',
        html_content,
        flags=re.DOTALL
    )
    
    # Replace Urgentes
    html_content = re.sub(
        r'(<div class="box-title red"><i class="fas fa-bolt"></i> Urgente</div>.*?<div class="news-list">)(.*?)(</div>)',
        rf'\1{urgentes_html}\3',
        html_content,
        flags=re.DOTALL
    )
    
    # Replace Colunas
    html_content = re.sub(
        r'(<div class="box-title green"><i class="fas fa-pen-fancy"></i> Colunas</div>.*?<div class="news-list">)(.*?)(</div>)',
        rf'\1{colunas_html}\3',
        html_content,
        flags=re.DOTALL
    )
    
    # Update date in header
    hoje = datetime.now().strftime('%d de %B de %Y')
    html_content = re.sub(
        r'(<strong style="color:#e2e8f0">).*?(</strong>)',
        rf'\1Manaus, {hoje}\2',
        html_content
    )
    
    # Write updated HTML
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"��✅ Site atualizado com sucesso em {datetime.now().strftime('%H:%M:%S')}")
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
        "imagem": imagem or f"https://images.unsplash.com/photo-{hash(titulo) % 1000000000}?auto=format&fit=crop&w=700&q=80"
    }
    
    # Add to beginning of list (most recent first)
    news_data["ultimas_noticias"].insert(0, nova_noticia)
    
    # Keep only last 50 news items
    news_data["ultimas_noticias"] = news_data["ultimas_noticias"][:50]
    
    # Also add to urgentes if it's breaking news
    if categoria.lower() in ["urgente", "segurança", "política"]:
        news_data["urgentes"].insert(0, {
            "titulo": titulo,
            "hora": datetime.now().strftime('%H:%M')
        })
        news_data["urgentes"] = news_data["urgentes"][:10]  # Keep only 10 urgent
    
    # Update mais lidas (simulate by adding to top)
    news_data["mais_lidas"].insert(0, nova_noticia)
    news_data["mais_lidas"] = news_data["mais_lidas"][:10]  # Keep only top 10
    
    save_news_data(news_data)
    print(f"��✅ Notícia adicionada: {titulo}")
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
        
        news_data = load_news_data()
        for noticia in demo_news:
            add_noticia = add_new_noticia(
                noticia["titulo"],
                noticia["resumo"],
                noticia["categoria"],
                noticia["autor"]
            )
        
        update_index_html()
        print("��✅ Notícias de demonstração adicionadas!")
    
    else:
        print(f"Comando desconhecido: {comando}")

if __name__ == "__main__":
    main()