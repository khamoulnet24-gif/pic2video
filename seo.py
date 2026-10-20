# Configuration SEO centralisée
BASE_URL = "https://pics2video.com"
SITE_NAME = "Pics2Video"
OG_IMAGE = f"{BASE_URL}/static/og-image.png"

LANDINGS = {
    "creer-video-tiktok": {
        "ratio": "9:16", "quality": "1080",
        "title": "Créer une vidéo TikTok avec photos et musique (gratuit) — Pics2Video",
        "meta_description": "Transformez vos photos et votre musique en vidéo TikTok verticale 9:16 en 10 secondes. Recadrage automatique sur les visages, sans logiciel à installer.",
        "h1": "Créer une vidéo TikTok avec vos photos et votre musique",
        "intro": "Uploadez vos photos, ajoutez votre son, choisissez le format 9:16 et téléchargez votre TikTok en quelques secondes. Le recadrage intelligent centre automatiquement chaque photo sur les visages.",
        "sections": [
            {"h2": "Pourquoi créer un TikTok à partir de photos ?", "body": ["Les diaporamas photos cartonnent sur TikTok : ils racontent une histoire, affichent une esthétique soignée et retiennent l'attention grâce à la musique.", "Pics2Video résout le problème du format : chaque image est recadrée sur le visage ou le sujet principal, puis animée d'un léger zoom."]},
            {"h2": "Comment ça marche en 3 étapes", "list": ["Déposez vos photos (JPG, PNG, jusqu'à 20 images)", "Ajoutez votre musique (MP3, WAV)", "Téléchargez votre vidéo 9:16 en 1080x1920"]}
        ],
        "faq": [
            ("Quel format pour TikTok ?", "Le format vertical 9:16 en 1080x1920 est le standard TikTok. Pics2Video le génère automatiquement avec recadrage intelligent."),
            ("Puis-je ajouter des transitions ?", "Un fondu doux de 0,4 seconde est appliqué entre chaque photo, avec un effet zoom lent type Ken Burns.")
        ],
        "related": ["video-instagram-reels", "video-portrait-instagram"]
    },
    "video-instagram-reels": {
        "ratio": "9:16", "quality": "1080",
        "title": "Créer une vidéo Instagram Reels avec musique — Pics2Video",
        "meta_description": "Faites un Reel Instagram à partir de vos photos et d'une musique en 9:16, en 10 secondes. Sans montage, sans app à télécharger.",
        "h1": "Créer un Reel Instagram à partir de vos photos",
        "intro": "Photos + musique = Reel Instagram parfait en 9:16. Recadrage automatique sur les visages pour un rendu pro.",
        "sections": [{"h2": "Format recommandé", "body": ["9:16 en 1080x1920. C'est le format natif d'Instagram Reels."]}],
        "faq": [("Quel format pour les Reels ?", "9:16 en 1080x1920 pour occuper tout l'écran.")],
        "related": ["creer-video-tiktok", "video-portrait-instagram"]
    },
    "diaporama-youtube": {
        "ratio": "16:9", "quality": "1080",
        "title": "Créer un diaporama musical YouTube en HD — Pics2Video",
        "meta_description": "Générez un diaporama vidéo 16:9 en 1080p ou 4K pour YouTube avec vos photos et votre musique. Rapide, gratuit, sans logiciel.",
        "h1": "Diaporama musical pour YouTube en HD",
        "intro": "Créez un diaporama vidéo professionnel au format 16:9 (1920x1080 ou 4K), synchronisé sur votre musique.",
        "sections": [{"h2": "Résolution", "body": ["1080p (1920x1080) suffit pour la majorité des chaînes. Choisissez 4K pour un rendu maximal."]}],
        "faq": [("La musique est-elle synchronisée ?", "Oui, la durée totale de la vidéo est calée exactement sur la durée de votre piste audio.")],
        "related": ["diaporama-mariage", "diaporama-anniversaire"]
    },
    # Ajoute ici les autres landings (Mariage, Anniversaire, etc.)
}

BLOG = {} # Sera chargé depuis blog.json

def software_app_jsonld():
    return {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": SITE_NAME, "url": BASE_URL}

def faq_jsonld(faq_pairs):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq_pairs]}

def article_jsonld(article, url):
    return {"@context": "https://schema.org", "@type": "Article", "headline": article["title"], "url": url}
