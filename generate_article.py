import json, os
from pathlib import Path
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
BLOG_FILE = Path(__file__).parent / "blog.json"

PLAN = [
    {"slug": "format-video-reseaux", "titre": "Quel format vidéo pour chaque réseau ?", "mot_cle": "format vidéo", "intention": "comprendre", "landings": ["creer-video-tiktok"], "date_pub": "2026-11-01"}
]

PROMPT = """Tu es rédacteur SEO. Sujet: {titre}. Renvoie un JSON avec title, meta_description, h1, published, status, reading_time, intro, sections, faq, cta, cta_url, related_landings."""

def generate(article_plan):
    print(f"Génération de {article_plan['slug']}...")
    # Code d'appel API Anthropic ici (simplifié pour l'exemple)
    pass

if __name__ == "__main__":
    print("Script de génération IA prêt. Configure ta clé API.")
