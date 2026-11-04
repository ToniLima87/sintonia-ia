import feedparser
from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel

# Feeds de notícias consultados pelo coletor.
FEEDS_CONFIG = [
    {"fonte": "OpenAI Blog", "url": "https://openai.com/news/rss.xml"},
    {"fonte": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml"},
    {"fonte": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"fonte": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"fonte": "arXiv AI (Papers)", "url": "https://rss.arxiv.org/rss/cs.AI"}
]

class NoticiasBrutas(BaseModel):
    titulo: str
    link: str
    resumo: str
    data_publicacao: str
    fonte: str

def extrair_noticias(limite_por_feed: int = 5) -> List[NoticiasBrutas]:
    noticias_coletadas: List[NoticiasBrutas] = []
    
    for feed_info in FEEDS_CONFIG:
        print(f"Lendo feed: {feed_info['fonte']}...")
        parsed_feed = feedparser.parse(feed_info["url"])
        
        # Trata falhas de parse ou feeds fora do ar
        if parsed_feed.bozo and not parsed_feed.entries:
            print(f"Erro ao acessar ou ler {feed_info['fonte']}")
            continue
        for entry in parsed_feed.entries[:limite_por_feed]:
            # Normalização básica de campos 
            data_pub = entry.get("published_parsed") or entry.get("updated_parsed")
            if data_pub:
                data_pub = datetime(*data_pub[:6], tzinfo=timezone.utc)
            else:
                data_pub = datetime.now(timezone.utc)
            resumo_texto = entry.get("summary", entry.get("description", ""))
            
            noticia = NoticiasBrutas(
                titulo=entry.get("title", "Sem título"),
                link=entry.get("link", ""),
                resumo=resumo_texto,
                data_publicacao=data_pub.isoformat(),
                fonte=feed_info["fonte"]
            )
            noticias_coletadas.append(noticia)
            
    print(f"\nTotal de notícias coletadas: {len(noticias_coletadas)}")
    return noticias_coletadas

if __name__ == "__main__":
    noticias = extrair_noticias(limite_por_feed=5)
    for n in noticias[:3]:
        print(f"\n[{n.fonte}] {n.titulo}\nLink: {n.link}\nResumo: {n.resumo[:150]}...")
