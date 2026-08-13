# 🤖 Automação de Postagem para AMZ Norte

Este diretório contém um sistema de automação para gerenciar e publicar notícias no site AMZ Norte.

## 🆕 Buscador automático → site (a cada 5 min)

O `busca_noticias.py` (em `PROGRAMAÇÃO\publicação automatica`) roda a cada 5 min
(tarefa Windows `AMZNorteBusca5min`) e publica **todas** as notícias novas no site:

- **Tudo entra** (local + nacional + internacional) com **teto diário** (padrão
  50/dia — env `AMZ_MAX_POSTS_DIA`) e até 5 por rodada (`AMZ_MAX_POSTS_RODADA`)
- **Texto completo**: extrai a matéria original e **reescreve por IA** (alterando
  as palavras, mantendo os fatos). O texto completo aparece na página da matéria
- **Imagem**: foto real do RSS/og:image; quando não existe, gera **imagem por IA**
  (Pollinations) relacionada ao tema
- **1 deploy por rodada**: salva tudo e faz um único `git push` + Netlify
- Ajustes rápidos no `.env` do pipeline: `AMZ_MAX_POSTS_DIA`, `AMZ_MAX_POSTS_RODADA`,
  `AMZ_MAX_HORAS` (frescor da notícia)

Publicação manual continua igual: `python publicar.py "Título" "Resumo" --cat X
--img URL --link URL --texto "texto completo"` (a flag `--texto` é opcional).

## �� 📁 Estrutura dos Arquivos

- `index.html` - O site principal do AMZ Norte
- `post_news.py` - Script Python para automatizar a postagem de notícias
- `news_data.json` - Banco de dados JSON com as notícias (gerado automaticamente)

## �� 🚀 Como Usar

## 🚀 Como Usar

### 0. Postar notícia de forma simples (recomendado) 🆕

O comando `publicar.py` faz tudo sozinho: salva a notícia, atualiza o site, faz
git push e publica no Netlify.

**Modo assistente (pergunta tudo):**
```bash
python publicar.py
```
Ou dê dois cliques em `postar-noticia.bat` (na pasta `site noticia -amz noticia`).

**Modo one-liner:**
```bash
python publicar.py "Título da notícia" "Resumo aqui" --cat politica
python publicar.py "Título" "Resumo" --cat seguranca --img https://.../foto.jpg --urgente
```

**Gerenciamento:**
```bash
python publicar.py --listar          # lista as notícias
python publicar.py --remover 3       # remove a de número 3
python publicar.py --atualizar       # só regenera o index.html
python publicar.py "Título" "Resumo" --no-publicar   # testa sem publicar
```

### 1. Atualizar o site com notícias existentes
```bash
python post_news.py update
```

### 2. Adicionar uma nova notícia
```bash
python post_news.py add "Título da Notícia" "Resumo da notícia aqui" [categoria] [autor] [imagem_url]
```

Exemplo:
```bash
python post_news.py add "Nova descoberta na Amazônia" "Cientistas encontram nova espécie de planta na região do Alto Rio Negro" ciência "Paulo Amazonas"
```

### 3. Adicionar notícias de demonstração
```bash
python post_news.py demo
```

### 4. Fazer deploy automático para Netlify
Após atualizar as notícias, faça o commit e push:
```bash
git add .
git commit -m "Nova notícia: [título da notícia]"
git push
```

O Netlify fará o deploy automaticamente quando detectar mudanças no branch main.

## �� 🔧 Configuração

O script cria automaticamente um arquivo `news_data.json` com a seguinte estrutura:

```json
{
  "ultimas_noticias": [...],
  "mais_lidas": [...],
  "urgentes": [...],
  "colunas": [...]
}
```

## �� 🎯 Funcionalidades

- � ✅ Atualização automática das seções do site
- � ✅ Integração com o Netlify para deploy contínuo
- � ✅ Suporte a categorias de notícias (segurança, política, economia, meio ambiente, etc.)
- � ✅ Geração automática de imagens via Unsplash (quando não fornecida)
- � ✅ Manutenção de histórico de notícias
- � ✅ Destaque para notícias urgentes e mais lidas

## �� 📋 Próximos Passos Sugeridos

1. Criar interface web para postagem de notícias
2. Integrar com APIs de redes sociais para auto-postagem
3. Adicionar sistema de comentários
4. Implementar newsletter automática
5. Adicionar analytics de visualização

---
*Desenvolvido para AMZ Norte - Notícias do Amazonas*
*Autor: Paulo Amazonas*