import requests
import time
import re
import random
import base64
import json
from datetime import datetime

TELEGRAM_TOKEN    = "8611988792:AAGOJ7xDWPRJveS0jOe71NH5rWczdKwPUgI"
TELEGRAM_CHAT_ID  = "8559815820"
ANTHROPIC_API_KEY = ""  # Ajoute ta cle Anthropic pour activer la Vision IA

BUDGET_MAX     = 60
RATIO_MIN      = 2.0
CHECK_INTERVAL = 45
MIN_GAIN       = 20
FRESH_MINUTES  = 10

# ════════════════════════════════════════════════════════
# PROXIES ROTATIFS - protection anti-blocage
# Ajoute tes proxies ici pour ne jamais te faire bloquer
# Format: "http://user:pass@ip:port"
# Service recommande: webshare.io (gratuit jusqu a 10 proxies)
# ════════════════════════════════════════════════════════
PROXIES = []  # Laisse vide pour tourner sans proxy

def get_proxy():
    if not PROXIES:
        return None
    proxy = random.choice(PROXIES)
    return {"http": proxy, "https": proxy}

VINTED_COUNTRIES = {
    "FR": "https://www.vinted.fr",
    "BE": "https://www.vinted.be",
    "NL": "https://www.vinted.nl",
    "ES": "https://www.vinted.es",
    "DE": "https://www.vinted.de",
    "IT": "https://www.vinted.it",
}

# ════════════════════════════════════════════════════════
# MOTS-CLES VAGUES - titres sans marque mentionnee
# Les vraies pepites sont souvent mal etiquetees
# ════════════════════════════════════════════════════════
VAGUE_KEYWORDS = [
    "belle veste noire", "veste cuir noire", "veste bomber",
    "veste matelassee noire", "manteau laine noir",
    "sac cuir noir", "sac bandouliere cuir", "sac a main cuir",
    "sneakers blanches", "sneakers noires", "baskets blanches",
    "jean slim noir", "jean droit bleu", "pull cachemire",
    "pull laine merinos", "chemise oxford blanche",
    "blouson cuir noir", "parka noire", "doudoune noire",
    "hoodie gris", "sweat capuche noir", "pantalon cargo",
    "chaussures cuir marron", "mocassins cuir",
    "portefeuille cuir", "ceinture cuir noir",
    "robe noire elegante", "blazer noir", "costume gris",
    "veste blazer carreaux", "trench coat beige",
    "veste vintage", "veste retro", "veste annees 90",
    "sac vintage", "sac luxe", "sac designer",
    "chaussures designer", "sneakers rares", "kicks",
]

# ════════════════════════════════════════════════════════
# TOUTES LES MARQUES DE LUXE
# ════════════════════════════════════════════════════════
BRANDS = {
    "Chanel": {
        "keywords": ["chanel"],
        "min_price": 30,
        "retail": {"sac": 3000, "veste": 2000, "pull": 800, "tshirt": 500, "ceinture": 600, "chaussure": 800, "sneaker": 700, "lunettes": 400}
    },
    "Dior": {
        "keywords": ["dior", "christian dior"],
        "min_price": 20,
        "retail": {"sac": 2000, "sneaker": 1100, "tshirt": 450, "hoodie": 1200, "veste": 2500, "ceinture": 450}
    },
    "Louis Vuitton": {
        "keywords": ["louis vuitton", "lv", "vuitton"],
        "min_price": 20,
        "retail": {"keepall": 2000, "speedy": 1200, "neverfull": 1800, "sac": 1500, "portefeuille": 700, "ceinture": 500, "sneaker": 1000}
    },
    "Hermes": {
        "keywords": ["hermes", "hermès"],
        "min_price": 50,
        "retail": {"birkin": 10000, "kelly": 8000, "sac": 3000, "ceinture": 600, "foulard": 400, "bracelet": 800}
    },
    "Saint Laurent": {
        "keywords": ["saint laurent", "ysl", "yves saint laurent"],
        "min_price": 20,
        "retail": {"sac": 1500, "veste": 2000, "sneaker": 600, "tshirt": 350, "ceinture": 400}
    },
    "Celine": {
        "keywords": ["celine", "céline"],
        "min_price": 20,
        "retail": {"sac": 1500, "veste": 1800, "tshirt": 350, "pull": 600, "sneaker": 600}
    },
    "Givenchy": {
        "keywords": ["givenchy"],
        "min_price": 15,
        "retail": {"sac": 1500, "veste": 1500, "tshirt": 350, "sneaker": 600, "hoodie": 800}
    },
    "Balenciaga": {
        "keywords": ["balenciaga"],
        "min_price": 15,
        "retail": {"triple s": 950, "speed": 800, "track": 850, "sneaker": 900, "hoodie": 900, "tshirt": 450, "veste": 1500, "sac": 1200}
    },
    "Gucci": {
        "keywords": ["gucci"],
        "min_price": 15,
        "retail": {"ace": 650, "sneaker": 700, "ceinture": 400, "sac": 1200, "tshirt": 400, "hoodie": 900, "veste": 1800}
    },
    "Prada": {
        "keywords": ["prada"],
        "min_price": 15,
        "retail": {"sac nylon": 900, "sac": 1500, "sneaker": 800, "tshirt": 400, "pull": 900, "veste": 1800}
    },
    "Bottega Veneta": {
        "keywords": ["bottega veneta", "bottega"],
        "min_price": 20,
        "retail": {"sac jodie": 2800, "sac cassette": 3200, "sac": 2000, "portefeuille": 800, "ceinture": 600, "sneaker": 700}
    },
    "Miu Miu": {
        "keywords": ["miu miu"],
        "min_price": 15,
        "retail": {"sac": 1500, "ballet": 800, "sneaker": 700, "jupe": 600, "veste": 1200, "pull": 500}
    },
    "Versace": {
        "keywords": ["versace"],
        "min_price": 15,
        "retail": {"sneaker": 600, "tshirt": 350, "veste": 1500, "sac": 1200, "ceinture": 350}
    },
    "Fendi": {
        "keywords": ["fendi"],
        "min_price": 15,
        "retail": {"baguette": 3000, "sac": 2000, "tshirt": 400, "sneaker": 700, "ceinture": 400}
    },
    "Valentino": {
        "keywords": ["valentino"],
        "min_price": 15,
        "retail": {"rockstud": 800, "sneaker": 700, "sac": 1500, "tshirt": 350, "veste": 1800}
    },
    "Dolce Gabbana": {
        "keywords": ["dolce gabbana", "dolce & gabbana", "d&g"],
        "min_price": 15,
        "retail": {"sneaker": 500, "tshirt": 300, "veste": 1200, "sac": 1000}
    },
    "Armani": {
        "keywords": ["armani", "giorgio armani", "emporio armani"],
        "min_price": 10,
        "retail": {"veste": 800, "chemise": 200, "tshirt": 120, "jean": 200, "sac": 500}
    },
    "Burberry": {
        "keywords": ["burberry"],
        "min_price": 12,
        "retail": {"trench": 2000, "veste": 1200, "manteau": 1800, "pull": 600, "tshirt": 300, "echarpe": 500, "sac": 1200}
    },
    "Loewe": {
        "keywords": ["loewe"],
        "min_price": 20,
        "retail": {"puzzle": 2500, "sac": 1500, "tshirt": 350, "pull": 600, "veste": 1200}
    },
    "Jacquemus": {
        "keywords": ["jacquemus"],
        "min_price": 10,
        "retail": {"le chiquito": 550, "sac": 400, "chemise": 250, "robe": 300, "pull": 250, "veste": 400}
    },
    "Balmain": {
        "keywords": ["balmain"],
        "min_price": 15,
        "retail": {"veste": 2000, "tshirt": 400, "jean": 500, "sneaker": 600, "sac": 1200}
    },
    "Alexander McQueen": {
        "keywords": ["alexander mcqueen", "mcqueen"],
        "min_price": 15,
        "retail": {"sneaker oversized": 500, "sneaker": 480, "sac": 1200, "veste": 1500}
    },
    "Maison Margiela": {
        "keywords": ["maison margiela", "margiela", "mm6"],
        "min_price": 15,
        "retail": {"tabi": 900, "sneaker": 600, "veste": 800, "tshirt": 250, "sac": 700}
    },
    "Acne Studios": {
        "keywords": ["acne studios"],
        "min_price": 10,
        "retail": {"veste": 500, "pull": 300, "tshirt": 150, "jean": 250, "sac": 400, "echarpe": 200}
    },
    "AMI Paris": {
        "keywords": ["ami paris", "ami de coeur"],
        "min_price": 15,
        "retail": {"pull": 300, "hoodie": 350, "tshirt": 130, "chemise": 220, "veste": 450, "manteau": 600}
    },
    "Sandro": {
        "keywords": ["sandro"],
        "min_price": 8,
        "retail": {"veste": 350, "robe": 250, "pull": 200, "chemise": 180, "jean": 200, "tshirt": 100}
    },
    "Maje": {
        "keywords": ["maje"],
        "min_price": 8,
        "retail": {"robe": 200, "veste": 300, "pull": 180, "chemise": 160, "tshirt": 90}
    },
    "Isabel Marant": {
        "keywords": ["isabel marant"],
        "min_price": 10,
        "retail": {"sneaker": 300, "veste": 600, "robe": 400, "pull": 300, "jean": 250}
    },
    "Off-White": {
        "keywords": ["off white", "off-white"],
        "min_price": 15,
        "retail": {"sneaker": 450, "tshirt": 350, "hoodie": 600, "veste": 1000, "sac": 600}
    },
    "Supreme": {
        "keywords": ["supreme"],
        "min_price": 10,
        "retail": {"hoodie box logo": 800, "tshirt box logo": 300, "hoodie": 250, "tshirt": 150, "veste": 400}
    },
    "Fear of God": {
        "keywords": ["fear of god", "essentials fog"],
        "min_price": 10,
        "retail": {"hoodie": 350, "tshirt": 150, "jean": 300, "veste": 500, "sneaker": 400}
    },
    "Rick Owens": {
        "keywords": ["rick owens"],
        "min_price": 20,
        "retail": {"sneaker ramones": 600, "sneaker": 550, "veste": 1500, "tshirt": 300}
    },
    "Amiri": {
        "keywords": ["amiri"],
        "min_price": 15,
        "retail": {"jean": 800, "tshirt": 300, "sneaker": 500, "veste": 1200, "hoodie": 600}
    },
    "Palm Angels": {
        "keywords": ["palm angels"],
        "min_price": 10,
        "retail": {"tshirt": 250, "hoodie": 450, "veste track": 600, "sneaker": 350}
    },
    "Stone Island": {
        "keywords": ["stone island"],
        "min_price": 15,
        "retail": {"ghost piece": 600, "veste": 400, "hoodie": 300, "sweat": 250, "tshirt": 140}
    },
    "CP Company": {
        "keywords": ["cp company", "c.p. company"],
        "min_price": 15,
        "retail": {"goggle jacket": 700, "veste": 500, "hoodie": 350, "sweat": 280}
    },
    "Moncler": {
        "keywords": ["moncler"],
        "min_price": 20,
        "retail": {"doudoune": 850, "gilet": 600, "veste": 700, "pull": 350, "hoodie": 380}
    },
    "Canada Goose": {
        "keywords": ["canada goose"],
        "min_price": 20,
        "retail": {"expedition": 1200, "parka": 800, "doudoune": 700, "veste": 600}
    },
    "Ralph Lauren": {
        "keywords": ["ralph lauren", "polo ralph", "purple label", "rrl"],
        "min_price": 5,
        "retail": {"polo": 100, "chemise": 110, "hoodie": 180, "pull": 140, "veste": 300, "purple label": 500}
    },
    "Tom Ford": {
        "keywords": ["tom ford"],
        "min_price": 20,
        "retail": {"parfum": 300, "lunettes": 400, "veste": 1500, "chaussure": 600}
    },
    "Nike Jordan": {
        "keywords": ["nike", "jordan", "air max", "dunk", "air force"],
        "min_price": 3,
        "retail": {"jordan 1": 280, "jordan 3": 250, "jordan 4": 300, "dunk low": 200, "air max 90": 130, "air force 1": 110}
    },
    "Adidas": {
        "keywords": ["adidas", "yeezy", "samba", "gazelle"],
        "min_price": 3,
        "retail": {"yeezy 350": 220, "yeezy 700": 200, "samba": 130, "gazelle": 110, "superstar": 100}
    },
    "New Balance": {
        "keywords": ["new balance", "nb 550", "nb 990", "nb 2002"],
        "min_price": 5,
        "retail": {"990": 200, "2002r": 180, "550": 130, "574": 100}
    },
    "Lacoste": {
        "keywords": ["lacoste"],
        "min_price": 5,
        "retail": {"polo": 95, "chemise": 110, "hoodie": 140, "veste": 200, "tshirt": 70, "sneaker": 110}
    },
    "Carhartt": {
        "keywords": ["carhartt", "carhartt wip"],
        "min_price": 3,
        "retail": {"detroit": 200, "michigan": 190, "veste": 160, "hoodie": 100}
    },
    "Levis": {
        "keywords": ["levis", "levi's", "501"],
        "min_price": 3,
        "retail": {"501 vintage": 180, "501": 100, "trucker": 110, "jean": 90}
    },
    "The North Face": {
        "keywords": ["north face", "the north face"],
        "min_price": 4,
        "retail": {"nuptse": 260, "veste": 180, "doudoune": 200, "fleece": 130}
    },
    "Barbour": {
        "keywords": ["barbour"],
        "min_price": 8,
        "retail": {"bedale": 350, "beaufort": 380, "veste": 280}
    },
    "Patagonia": {
        "keywords": ["patagonia"],
        "min_price": 5,
        "retail": {"better sweater": 180, "fleece": 160, "doudoune": 260}
    },
    "APC": {
        "keywords": ["apc", "a.p.c."],
        "min_price": 10,
        "retail": {"jean": 190, "veste": 300, "manteau": 500, "pull": 220, "sac": 300}
    },
    "Brunello Cucinelli": {
        "keywords": ["brunello cucinelli"],
        "min_price": 30,
        "retail": {"pull": 1200, "veste": 2500, "chemise": 600, "tshirt": 400}
    },
    "Vivienne Westwood": {
        "keywords": ["vivienne westwood"],
        "min_price": 10,
        "retail": {"collier": 200, "sac": 500, "veste": 600, "tshirt": 150}
    },
    "Lanvin": {
        "keywords": ["lanvin"],
        "min_price": 15,
        "retail": {"sneaker curb": 650, "sneaker": 600, "sac": 1200, "veste": 1500}
    },
    "Gallery Dept": {
        "keywords": ["gallery dept"],
        "min_price": 15,
        "retail": {"tshirt": 300, "jean": 400, "hoodie": 500, "veste": 700}
    },
    "Vetements": {
        "keywords": ["vetements"],
        "min_price": 15,
        "retail": {"hoodie": 600, "tshirt": 300, "veste": 1000}
    },
}

FAKE_SIGNALS = [
    "replica", "rep ", "aaa", "inspired", "no name", "contrefacon",
    "fake", "copie", "imitation", "pokemon", "carte", "card",
    "sticker", "poster", "figurine", "jouet", "toy", "lego",
    "manga", "livre", "book", "dvd", "cadre", "tableau",
]

CLOTHING_SIGNALS = [
    "taille", "size", "xl", "xxl", "xs", " s ", " m ", " l ",
    "veste", "jacket", "hoodie", "pull", "tshirt", "t-shirt",
    "jean", "pantalon", "robe", "chemise", "manteau", "blouson",
    "sac", "bag", "chaussure", "sneaker", "boots", "mocassin",
    "ceinture", "portefeuille", "lunettes", "casquette", "bonnet",
    "echarpe", "parfum", "montre", "bracelet", "collier",
]

ALL_BRAND_NAMES = list(BRANDS.keys())

CONDITION_COEFFS = {
    "neuf avec etiquette": 1.00, "neuf sans etiquette": 0.90,
    "tres bon etat": 0.75, "bon etat": 0.60, "satisfaisant": 0.40,
    "neuf": 0.95, "tres bon": 0.75, "bon": 0.60,
    "neu mit etikett": 1.00, "sehr gut": 0.75, "gut": 0.60,
    "nuevo con etiqueta": 1.00, "muy bueno": 0.75, "bueno": 0.60,
    "nuovo con etichetta": 1.00, "ottimo": 0.75,
    "nieuw met label": 1.00, "zeer goed": 0.75,
    "default": 0.65,
}

LUXURY_KEYWORDS = [
    "chanel", "dior", "louis vuitton", "hermes", "gucci", "prada",
    "bottega", "miu miu", "versace", "fendi", "valentino", "celine",
    "saint laurent", "ysl", "balenciaga", "givenchy", "loewe",
    "off white", "supreme", "stone island", "moncler", "canada goose",
    "burberry", "ami paris", "jacquemus", "rick owens",
    "amiri", "fear of god", "palm angels", "margiela",
    "acne studios", "balmain", "sandro", "maje", "isabel marant",
    "vivienne westwood", "alexander mcqueen", "tom ford",
]

MAX_LUXURY_RATIO   = 0.30
MAX_AVG_PRICE      = 80
MIN_FEEDBACK_SCORE = 4.0

# ════════════════════════════════════════════════════════
# VISION IA - Reconnaissance marque depuis photo
# ════════════════════════════════════════════════════════

vision_cache = {}

def analyze_photo_with_ai(img_url, title, price):
    if not ANTHROPIC_API_KEY or not img_url:
        return None

    cache_key = img_url[:80]
    if cache_key in vision_cache:
        return vision_cache[cache_key]

    try:
        img_r = requests.get(img_url, timeout=8)
        if img_r.status_code != 200:
            return None

        img_b64 = base64.b64encode(img_r.content).decode("utf-8")
        media_type = img_r.headers.get("Content-Type", "image/jpeg").split(";")[0]

        brands_list = "\n".join(["- " + b for b in ALL_BRAND_NAMES[:30]])

        prompt = (
            "Tu es un expert en mode et luxe. Analyse cette photo d un article vendu "
            + str(price) + "EUR sur Vinted.\n\n"
            + "Titre de l annonce: " + title + "\n\n"
            + "MISSION:\n"
            + "1. Identifie la marque depuis le logo, les details, la coupe\n"
            + "2. Identifie le type d article\n"
            + "3. Estime si c est authentique\n"
            + "4. Estime la valeur marche\n\n"
            + "Marques prioritaires:\n" + brands_list + "\n\n"
            + "Reponds UNIQUEMENT en JSON sans markdown:\n"
            + '{"brand": "nom ou null", "confidence": 0.0, "item_type": "type", "is_fake": false, "market_value": 0, "reason": "explication courte"}'
        )

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-opus-4-5",
                "max_tokens": 300,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            },
            timeout=20
        )

        if response.status_code == 200:
            raw = response.json()["content"][0]["text"].strip()
            raw = re.sub(r"```json|```", "", raw).strip()
            result = json.loads(raw)
            vision_cache[cache_key] = result
            return result

    except Exception as e:
        print("Vision error: " + str(e))

    return None

# ════════════════════════════════════════════════════════
# LEBONCOIN - Source supplementaire
# ════════════════════════════════════════════════════════

lbc_session = requests.Session()
lbc_session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "api_key": "ba0c2dad52b3049b3b7f3d29fa4e6bafe76cce35",
})

lbc_seen = set()

def search_leboncoin(keyword, max_price=None):
    items = []
    try:
        payload = {
            "filters": {
                "category": {"id": "2"},
                "keywords": {"text": keyword},
                "location": {},
                "ranges": {},
            },
            "limit": 30,
            "sort_by": "time",
            "sort_order": "desc",
        }
        if max_price:
            payload["filters"]["ranges"]["price"] = {"max": max_price}

        r = lbc_session.post(
            "https://api.leboncoin.fr/finder/search",
            json=payload, timeout=12
        )

        if r.status_code == 200:
            data = r.json()
            ads = data.get("ads", [])
            for ad in ads:
                try:
                    ad_id  = str(ad.get("list_id", ""))
                    title  = ad.get("subject", "")
                    price_raw = ad.get("price", [0])
                    price  = float(price_raw[0]) if price_raw else 0
                    url    = ad.get("url", "")
                    imgs   = ad.get("images", {}).get("urls_large", [])
                    img    = imgs[0] if imgs else ""
                    city   = ad.get("location", {}).get("city", "?")
                    ts     = ad.get("first_publication_date", "")

                    if price == 0 or price > BUDGET_MAX:
                        continue
                    if ad_id in lbc_seen:
                        continue
                    lbc_seen.add(ad_id)

                    items.append({
                        "id":       ad_id,
                        "title":    title,
                        "price":    price,
                        "url":      url,
                        "img_url":  img,
                        "city":     city,
                        "ts":       ts,
                        "source":   "Leboncoin",
                    })
                except:
                    continue

        time.sleep(random.uniform(1.5, 2.5))

    except Exception as e:
        print("LBC error: " + str(e))

    return items

# ════════════════════════════════════════════════════════
# SESSIONS VINTED avec proxies rotatifs
# ════════════════════════════════════════════════════════

country_sessions = {}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
]

def get_session(base_url):
    if base_url not in country_sessions:
        s = requests.Session()
        s.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Origin": base_url,
            "Referer": base_url + "/",
        })
        proxies = get_proxy()
        if proxies:
            s.proxies.update(proxies)
        try:
            s.get(base_url, timeout=10)
        except:
            pass
        country_sessions[base_url] = s
    return country_sessions[base_url]

def init_all_sessions():
    for country, url in VINTED_COUNTRIES.items():
        try:
            get_session(url)
            print("  " + country + " OK")
        except Exception as e:
            print("  " + country + " ERREUR: " + str(e))
        time.sleep(0.8)

def search_vinted(base_url, keyword, max_price=None):
    # Rotation User-Agent a chaque requete pour eviter le blocage
    s = get_session(base_url)
    s.headers.update({"User-Agent": random.choice(USER_AGENTS)})

    params = {"search_text": keyword, "order": "newest_first", "per_page": 48, "currency": "EUR"}
    if max_price:
        params["price_to"] = max_price
    try:
        proxies = get_proxy()
        r = s.get(
            base_url + "/api/v2/catalog/items",
            params=params, timeout=12,
            proxies=proxies if proxies else None
        )
        if r.status_code == 200:
            return r.json().get("items", [])
        elif r.status_code == 401:
            s.get(base_url, timeout=10)
        elif r.status_code == 429:
            print("  Rate limited - pause 30s")
            time.sleep(30)
        return []
    except Exception as e:
        print("  Vinted error: " + str(e))
        return []

def get_freshness(item, source="vinted"):
    try:
        if source == "leboncoin":
            return None, "recente", True

        ts = item.get("created_at_ts") or item.get("photo", {}).get("created_at_ts")
        if not ts:
            return None, "?", False
        age_min = int((time.time() - int(ts)) / 60)
        is_fresh = age_min <= FRESH_MINUTES
        if age_min < 5:
            label = str(age_min) + "min VIENT DE SORTIR"
        elif age_min < 15:
            label = str(age_min) + "min TRES RECENT"
        elif age_min < 60:
            label = str(age_min) + "min"
        else:
            label = str(age_min // 60) + "h"
            is_fresh = False
        return age_min, label, is_fresh
    except:
        return None, "?", False

def is_real_clothing(title, description):
    text = (title + " " + (description or "")).lower()
    has_fake = any(sig in text for sig in FAKE_SIGNALS)
    if has_fake:
        return False
    has_clothing = any(sig in text for sig in CLOTHING_SIGNALS)
    return has_clothing

def get_cond_coeff(cond):
    if not cond:
        return CONDITION_COEFFS["default"]
    c = cond.lower()
    for k, v in CONDITION_COEFFS.items():
        if k in c:
            return v
    return CONDITION_COEFFS["default"]

def get_resell_value(title, desc, brand_data):
    text = (title + " " + (desc or "")).lower()
    best_retail, best_match = 0, None
    for mk, rp in brand_data["retail"].items():
        if all(w in text for w in mk.split()) and rp > best_retail:
            best_retail = rp
            best_match = mk
    if best_retail == 0:
        vals = sorted(brand_data["retail"].values())
        best_retail = vals[len(vals) // 2]
        best_match = "ref mediane"
    return best_retail * 0.50, best_retail, best_match

seller_cache = {}

def analyze_seller(base_url, seller_id):
    key = base_url + "_" + str(seller_id)
    if key in seller_cache:
        return seller_cache[key]
    s = get_session(base_url)
    profile, items = {}, []
    try:
        r = s.get(base_url + "/api/v2/users/" + str(seller_id), timeout=10)
        if r.status_code == 200:
            profile = r.json().get("user", {})
        time.sleep(0.4)
        r2 = s.get(base_url + "/api/v2/users/" + str(seller_id) + "/items",
                   params={"per_page": 20, "order": "newest_first"}, timeout=10)
        if r2.status_code == 200:
            items = r2.json().get("items", [])
    except:
        result = (True, 60, "profil non disponible")
        seller_cache[key] = result
        return result

    if not items:
        result = (True, 60, "historique vide")
        seller_cache[key] = result
        return result

    feedback = float(profile.get("feedback_reputation", 1) or 1)
    n_items = int(profile.get("items_count", 0) or 0)
    n_fb = int(profile.get("positive_feedback_count", 0) or 0)
    prices, lux, norm = [], 0, 0

    for it in items:
        try:
            p = float(it.get("price", {}).get("amount", 0))
            if p > 0:
                prices.append(p)
            if any(kw in it.get("title", "").lower() for kw in LUXURY_KEYWORDS):
                lux += 1
            else:
                norm += 1
        except:
            pass

    avg_p = sum(prices) / len(prices) if prices else 0
    lux_r = lux / len(items) if items else 0
    score, reason = 100, []

    if feedback < MIN_FEEDBACK_SCORE:
        score -= 40
        reason.append("note " + str(feedback) + "/5")
    if lux_r > MAX_LUXURY_RATIO:
        score -= 50
        reason.append(str(int(lux_r*100)) + "% luxe")
    if avg_p > MAX_AVG_PRICE:
        score -= 20
        reason.append("prix moy " + str(round(avg_p)) + "EUR")
    if n_items > 50 and n_fb < 5:
        score -= 30
        reason.append("peu de feedback")
    if avg_p < 30 and norm > lux * 3:
        score += 10
        reason.append("dressing perso")

    score = max(0, min(100, score))
    result = (score >= 50, score, " | ".join(reason) if reason else "profil OK")
    seller_cache[key] = result
    return result

def evaluate_item(item, brand_name, brand_data, source="vinted"):
    try:
        if source == "vinted":
            price = float(item.get("price", {}).get("amount", 0))
            title = item.get("title", "")
            desc  = item.get("description", "")
            cond  = item.get("status", "")
            size  = item.get("size_title", "?")
            city  = item.get("city", "?")
        else:
            price = float(item.get("price", 0))
            title = item.get("title", "")
            desc  = ""
            cond  = "?"
            size  = "?"
            city  = item.get("city", "?")

        if price == 0 or price > BUDGET_MAX:
            return None
        if price < brand_data.get("min_price", 3):
            return None
        if not is_real_clothing(title, desc):
            return None

        # Vision IA pour les titres vagues ou suspects
        vision_result = None
        photos = item.get("photos", [])
        img_url = photos[0].get("url") or photos[0].get("full_size_url") if photos else item.get("img_url", "")

        is_vague = len(title.split()) <= 4 or not any(
            kw.lower() in title.lower() for kw in brand_data["keywords"]
        )

        if ANTHROPIC_API_KEY and is_vague and img_url:
            vision_result = analyze_photo_with_ai(img_url, title, price)
            if vision_result:
                if vision_result.get("is_fake") and vision_result.get("confidence", 0) >= 0.75:
                    return None
                # Reclassification si Vision detecte une autre marque
                detected = vision_result.get("brand")
                conf = float(vision_result.get("confidence", 0))
                if detected and detected != brand_name and conf >= 0.80 and detected in BRANDS:
                    brand_name = detected
                    brand_data = BRANDS[detected]

        resell_base, retail_price, matched = get_resell_value(title, desc, brand_data)

        # Prix Vision IA plus precis si disponible
        if vision_result and vision_result.get("market_value", 0) > 0:
            v_conf = float(vision_result.get("confidence", 0))
            v_val  = float(vision_result.get("market_value", 0))
            if v_conf >= 0.70:
                resell_base = (v_val * 0.5 * 0.6 + resell_base * 0.4)

        coeff  = get_cond_coeff(cond)
        resell = round(resell_base * coeff, 0)
        ratio  = round(resell / price, 2) if price > 0 else 0

        if ratio < RATIO_MIN:
            return None

        fees = round(resell * 0.05 + 0.70, 2)
        gain = round(resell - price - fees, 0)

        if gain < MIN_GAIN:
            return None

        liq = 3.0
        for sk, sv in [("xs",3),("s",5),("m",5),("l",4),("xl",3),("xxl",2)]:
            if sk in (size or "").lower():
                liq = (liq + sv) / 2
                break
        for ck, cv in [("noir",5),("black",5),("blanc",5),("white",5),("beige",4),("gris",4)]:
            if ck in title.lower():
                liq = (liq + cv) / 2
                break

        vision_badge = ""
        if vision_result and vision_result.get("brand"):
            v_conf = int(float(vision_result.get("confidence", 0)) * 100)
            vision_badge = " [Vision IA: " + vision_result["brand"] + " " + str(v_conf) + "%]"

        return {
            "brand":        brand_name + vision_badge,
            "price":        price,
            "retail":       retail_price,
            "resell":       resell,
            "gain":         gain,
            "ratio":        ratio,
            "cond":         cond,
            "size":         size,
            "city":         city,
            "img_url":      img_url,
            "liq":          round(liq, 1),
            "source_site":  source,
        }
    except Exception as e:
        print("evaluate error: " + str(e))
        return None

def send_telegram(msg, photo_url=None):
    base = "https://api.telegram.org/bot" + TELEGRAM_TOKEN
    if photo_url:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": photo_url, "caption": msg[:1024]}
        endpoint = base + "/sendPhoto"
    else:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "disable_web_page_preview": False}
        endpoint = base + "/sendMessage"
    try:
        r = requests.post(endpoint, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print("Telegram error: " + str(e))
        return False

def format_alert(item, result, flag, s_score, s_reason, base_url, age_min, fresh_label, is_fresh, source="vinted"):
    title = item.get("title", "?")
    if source == "vinted":
        url = base_url + "/items/" + str(item.get("id", ""))
        seller = item.get("user", {})
        s_name = seller.get("login", "?")
        s_url  = base_url + "/member/" + str(seller.get("id", ""))
        seller_line = s_name + " - " + s_reason + " (" + str(s_score) + "/100)\n"
    else:
        url = item.get("url", "")
        seller_line = "Leboncoin - " + result["city"] + "\n"

    fire = "F" * min(int(result["ratio"]), 5)
    urgent = "URGENT " if is_fresh and age_min is not None and age_min <= 5 else ""
    recent = "RECENT " if is_fresh and (age_min is None or age_min > 5) else ""

    msg = (
        urgent + recent + fire + " " + flag + " " + result["brand"].upper() + "\n\n"
        + "[" + result["source_site"].upper() + "] " + title + "\n\n"
        + "Prix: " + str(result["price"]) + "EUR\n"
        + "Boutique: ~" + str(result["retail"]) + "EUR\n"
        + "Revente: ~" + str(result["resell"]) + "EUR\n"
        + "Ratio: x" + str(result["ratio"]) + "\n"
        + "Gain: +" + str(result["gain"]) + "EUR\n\n"
        + "Liquidite: " + str(result["liq"]) + "/5\n"
        + "Annonce: " + fresh_label + "\n"
        + "Taille: " + result["size"] + " | Etat: " + result["cond"] + "\n\n"
        + seller_line
        + "VOIR: " + url + "\n"
        + datetime.now().strftime("%H:%M:%S")
    )
    return msg

seen_ids = set()

def scan_vinted_country(country, base_url):
    found = 0
    all_keywords = []

    # Keywords par marque
    for brand_name, brand_data in BRANDS.items():
        for kw in brand_data["keywords"]:
            all_keywords.append((kw, brand_name, brand_data))

    # Keywords vagues (titres sans marque)
    for vague_kw in VAGUE_KEYWORDS:
        all_keywords.append((vague_kw, None, None))

    for keyword, brand_name, brand_data in all_keywords:
        items = search_vinted(base_url, keyword, max_price=BUDGET_MAX)

        for item in items:
            item_id   = item.get("id")
            unique_id = base_url + "_" + str(item_id)
            if not item_id or unique_id in seen_ids:
                continue
            seen_ids.add(unique_id)

            # Si keyword vague, on tente la Vision IA pour identifier la marque
            if brand_name is None:
                if not ANTHROPIC_API_KEY:
                    continue
                photos  = item.get("photos", [])
                img_url = photos[0].get("url") or photos[0].get("full_size_url") if photos else ""
                if not img_url:
                    continue
                vision = analyze_photo_with_ai(img_url, item.get("title",""), float(item.get("price",{}).get("amount",0)))
                if not vision or not vision.get("brand") or float(vision.get("confidence",0)) < 0.75:
                    continue
                detected = vision.get("brand")
                if detected not in BRANDS:
                    continue
                brand_name = detected
                brand_data = BRANDS[detected]

            result = evaluate_item(item, brand_name, brand_data, source="vinted")
            if not result:
                continue

            seller_id = item.get("user", {}).get("id")
            if not seller_id:
                continue

            is_good, score, reason = analyze_seller(base_url, seller_id)
            if not is_good:
                continue

            age_min, fresh_label, is_fresh = get_freshness(item)
            msg = format_alert(item, result, country, score, reason, base_url, age_min, fresh_label, is_fresh, "vinted")
            send_telegram(msg, photo_url=result.get("img_url"))
            print(
                datetime.now().strftime("%H:%M:%S")
                + " " + ("URGENT " if is_fresh else "")
                + country + " " + result["brand"] + " | "
                + item.get("title","?")[:30] + " | "
                + str(result["price"]) + "->" + str(result["resell"])
                + " x" + str(result["ratio"]) + " +" + str(result["gain"])
            )
            found += 1
            time.sleep(1)

        time.sleep(1.5)
    return found

def scan_leboncoin():
    found = 0
    all_lbc_keywords = []

    for brand_name, brand_data in BRANDS.items():
        for kw in brand_data["keywords"]:
            all_lbc_keywords.append((kw, brand_name, brand_data))

    sample = random.sample(all_lbc_keywords, min(15, len(all_lbc_keywords)))

    for keyword, brand_name, brand_data in sample:
        items = search_leboncoin(keyword, max_price=BUDGET_MAX)
        for item in items:
            result = evaluate_item(item, brand_name, brand_data, source="leboncoin")
            if not result:
                continue

            age_min, fresh_label, is_fresh = get_freshness(item, source="leboncoin")
            msg = format_alert(item, result, "LBC", 70, "Leboncoin", "", age_min, fresh_label, is_fresh, "leboncoin")
            send_telegram(msg, photo_url=result.get("img_url"))
            print(
                datetime.now().strftime("%H:%M:%S")
                + " LBC " + result["brand"] + " | "
                + item.get("title","?")[:30] + " | "
                + str(result["price"]) + "->" + str(result["resell"])
                + " x" + str(result["ratio"]) + " +" + str(result["gain"])
            )
            found += 1
            time.sleep(1)
        time.sleep(2)

    return found

def main():
    print("VINTED BOT PRO")
    print(str(len(BRANDS)) + " marques | 6 pays + Leboncoin")
    print("Vision IA: " + ("ON" if ANTHROPIC_API_KEY else "OFF - ajoute ta cle Anthropic"))
    print("Proxies: " + str(len(PROXIES)) + " (ajoute des proxies pour plus de securite)")
    print("Budget: " + str(BUDGET_MAX) + "EUR | Ratio: x" + str(RATIO_MIN) + " | Gain: +" + str(MIN_GAIN) + "EUR")

    init_all_sessions()

    send_telegram(
        "Vinted Bot PRO demarre!\n\n"
        + str(len(BRANDS)) + " marques luxe\n"
        + "6 pays Vinted + Leboncoin\n"
        + "Titres vagues surveilles\n"
        + "Vision IA: " + ("ON" if ANTHROPIC_API_KEY else "OFF") + "\n"
        + "Proxies: " + str(len(PROXIES)) + "\n\n"
        + "En chasse..."
    )

    cycle = 0
    while True:
        cycle += 1
        total = 0
        print("SCAN #" + str(cycle) + " " + datetime.now().strftime("%H:%M:%S"))

        for country, base_url in VINTED_COUNTRIES.items():
            found = scan_vinted_country(country, base_url)
            total += found
            time.sleep(3)

        lbc_found = scan_leboncoin()
        total += lbc_found
        print("LBC: " + str(lbc_found) + " alertes")

        print("FIN #" + str(cycle) + " - " + str(total) + " alertes | Next: " + str(CHECK_INTERVAL) + "s")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
