import requests
import time
import re
import random
from datetime import datetime

TELEGRAM_TOKEN   = "8611988792:AAGOJ7xDWPRJveS0jOe71NH5rWczdKwPUgI"
TELEGRAM_CHAT_ID = "8559815820"

BUDGET_MAX     = 60
RATIO_MIN      = 2.0
CHECK_INTERVAL = 45
MIN_GAIN       = 20
FRESH_MINUTES  = 10

VINTED_COUNTRIES = {
    "FR": "https://www.vinted.fr",
    "BE": "https://www.vinted.be",
    "NL": "https://www.vinted.nl",
    "ES": "https://www.vinted.es",
    "DE": "https://www.vinted.de",
    "IT": "https://www.vinted.it",
}

# ── Toutes les marques de luxe ────────────────────────
BRANDS = {
    # Luxe francais
    "Chanel": {
        "keywords": ["chanel"],
        "min_price": 30,
        "retail": {"sac": 3000, "veste": 2000, "pull": 800, "tshirt": 500, "ceinture": 600, "chaussure": 800, "sneaker": 700, "parfum": 200, "lunettes": 400, "accessoire": 300}
    },
    "Dior": {
        "keywords": ["dior", "christian dior"],
        "min_price": 20,
        "retail": {"sac": 2000, "sneaker": 1100, "b23": 1100, "b22": 1200, "tshirt": 450, "hoodie": 1200, "veste": 2500, "ceinture": 450, "portefeuille": 600}
    },
    "Louis Vuitton": {
        "keywords": ["louis vuitton", "lv", "vuitton"],
        "min_price": 20,
        "retail": {"keepall": 2000, "speedy": 1200, "neverfull": 1800, "sac": 1500, "portefeuille": 700, "ceinture": 500, "sneaker": 1000, "tshirt": 500, "hoodie": 1200}
    },
    "Hermes": {
        "keywords": ["hermes", "hermès"],
        "min_price": 50,
        "retail": {"birkin": 10000, "kelly": 8000, "constance": 6000, "sac": 3000, "ceinture": 600, "foulard": 400, "bracelet": 800, "portefeuille": 700}
    },
    "Saint Laurent": {
        "keywords": ["saint laurent", "ysl", "yves saint laurent"],
        "min_price": 20,
        "retail": {"sac": 1500, "veste": 2000, "sneaker": 600, "tshirt": 350, "ceinture": 400, "portefeuille": 500, "lunettes": 300}
    },
    "Celine": {
        "keywords": ["celine", "céline"],
        "min_price": 20,
        "retail": {"sac": 1500, "veste": 1800, "tshirt": 350, "pull": 600, "sneaker": 600, "lunettes": 300, "portefeuille": 500}
    },
    "Givenchy": {
        "keywords": ["givenchy"],
        "min_price": 15,
        "retail": {"sac": 1500, "veste": 1500, "tshirt": 350, "sneaker": 600, "hoodie": 800, "ceinture": 350}
    },
    "Balenciaga": {
        "keywords": ["balenciaga"],
        "min_price": 15,
        "retail": {"triple s": 950, "speed": 800, "track": 850, "runner": 950, "sneaker": 900, "hoodie": 900, "tshirt": 450, "veste": 1500, "sac": 1200, "casquette": 350}
    },
    "Jacquemus": {
        "keywords": ["jacquemus"],
        "min_price": 10,
        "retail": {"le chiquito": 550, "le bambino": 500, "sac": 400, "chemise": 250, "robe": 300, "pull": 250, "veste": 400, "tshirt": 120}
    },
    "Balmain": {
        "keywords": ["balmain"],
        "min_price": 15,
        "retail": {"veste": 2000, "tshirt": 400, "jean": 500, "sneaker": 600, "sac": 1200, "pull": 600}
    },
    "Lanvin": {
        "keywords": ["lanvin"],
        "min_price": 15,
        "retail": {"sneaker curb": 650, "sneaker": 600, "sac": 1200, "veste": 1500, "tshirt": 300}
    },
    "Isabel Marant": {
        "keywords": ["isabel marant"],
        "min_price": 10,
        "retail": {"sneaker": 300, "veste": 600, "robe": 400, "pull": 300, "jean": 250, "sac": 500}
    },
    "Sandro": {
        "keywords": ["sandro"],
        "min_price": 8,
        "retail": {"veste": 350, "robe": 250, "pull": 200, "chemise": 180, "jean": 200, "tshirt": 100, "sac": 300}
    },
    "Maje": {
        "keywords": ["maje"],
        "min_price": 8,
        "retail": {"robe": 200, "veste": 300, "pull": 180, "chemise": 160, "tshirt": 90, "sac": 250}
    },
    "AMI Paris": {
        "keywords": ["ami paris", "ami de coeur"],
        "min_price": 15,
        "retail": {"pull": 300, "hoodie": 350, "tshirt": 130, "chemise": 220, "veste": 450, "manteau": 600, "sac": 350}
    },
    "APC": {
        "keywords": ["apc", "a.p.c."],
        "min_price": 10,
        "retail": {"jean": 190, "veste": 300, "manteau": 500, "pull": 220, "hoodie": 230, "sac": 300}
    },
    # Luxe italien
    "Gucci": {
        "keywords": ["gucci"],
        "min_price": 15,
        "retail": {"ace": 650, "sneaker": 700, "ceinture": 400, "sac": 1200, "tshirt": 400, "hoodie": 900, "veste": 1800, "portefeuille": 450}
    },
    "Prada": {
        "keywords": ["prada"],
        "min_price": 15,
        "retail": {"sac nylon": 900, "sac": 1500, "sneaker": 800, "tshirt": 400, "pull": 900, "veste": 1800, "portefeuille": 500, "ceinture": 450}
    },
    "Bottega Veneta": {
        "keywords": ["bottega veneta", "bottega"],
        "min_price": 20,
        "retail": {"sac jodie": 2800, "sac cassette": 3200, "sac": 2000, "portefeuille": 800, "ceinture": 600, "sneaker": 700, "pull": 900, "veste": 1500}
    },
    "Miu Miu": {
        "keywords": ["miu miu"],
        "min_price": 15,
        "retail": {"sac": 1500, "ballet": 800, "sneaker": 700, "jupe": 600, "veste": 1200, "pull": 500, "tshirt": 300}
    },
    "Versace": {
        "keywords": ["versace"],
        "min_price": 15,
        "retail": {"sneaker": 600, "tshirt": 350, "veste": 1500, "sac": 1200, "ceinture": 350, "hoodie": 700}
    },
    "Fendi": {
        "keywords": ["fendi"],
        "min_price": 15,
        "retail": {"baguette": 3000, "sac": 2000, "tshirt": 400, "sneaker": 700, "ceinture": 400, "portefeuille": 500}
    },
    "Valentino": {
        "keywords": ["valentino"],
        "min_price": 15,
        "retail": {"rockstud": 800, "sneaker": 700, "sac": 1500, "tshirt": 350, "veste": 1800, "ceinture": 400}
    },
    "Dolce Gabbana": {
        "keywords": ["dolce gabbana", "dolce & gabbana", "d&g"],
        "min_price": 15,
        "retail": {"sneaker": 500, "tshirt": 300, "veste": 1200, "sac": 1000, "ceinture": 300}
    },
    "Salvatore Ferragamo": {
        "keywords": ["ferragamo", "salvatore ferragamo"],
        "min_price": 15,
        "retail": {"chaussure": 600, "sneaker": 500, "sac": 1000, "ceinture": 350, "portefeuille": 400}
    },
    "Armani": {
        "keywords": ["armani", "giorgio armani", "emporio armani"],
        "min_price": 10,
        "retail": {"veste": 800, "chemise": 200, "tshirt": 120, "jean": 200, "montre": 500, "sac": 500}
    },
    "Moschino": {
        "keywords": ["moschino"],
        "min_price": 10,
        "retail": {"tshirt": 250, "veste": 800, "sac": 700, "ceinture": 200}
    },
    "Stone Island": {
        "keywords": ["stone island"],
        "min_price": 15,
        "retail": {"ghost piece": 600, "veste": 400, "hoodie": 300, "sweat": 250, "pull": 220, "tshirt": 140}
    },
    "CP Company": {
        "keywords": ["cp company", "c.p. company"],
        "min_price": 15,
        "retail": {"goggle jacket": 700, "veste": 500, "hoodie": 350, "sweat": 280, "tshirt": 150}
    },
    "Moncler": {
        "keywords": ["moncler"],
        "min_price": 20,
        "retail": {"doudoune": 850, "gilet": 600, "veste": 700, "pull": 350, "hoodie": 380, "tshirt": 180}
    },
    "Brunello Cucinelli": {
        "keywords": ["brunello cucinelli"],
        "min_price": 30,
        "retail": {"pull": 1200, "veste": 2500, "chemise": 600, "tshirt": 400, "manteau": 3000}
    },
    "Zegna": {
        "keywords": ["zegna", "ermenegildo zegna"],
        "min_price": 20,
        "retail": {"costume": 1500, "veste": 1000, "pull": 500, "chemise": 300, "chaussure": 500}
    },
    "Tod's": {
        "keywords": ["tods", "tod's"],
        "min_price": 15,
        "retail": {"mocassin": 500, "chaussure": 450, "sac": 800, "ceinture": 250}
    },
    # Luxe britannique
    "Burberry": {
        "keywords": ["burberry"],
        "min_price": 12,
        "retail": {"trench": 2000, "veste": 1200, "manteau": 1800, "pull": 600, "tshirt": 300, "echarpe": 500, "sac": 1200}
    },
    "Alexander McQueen": {
        "keywords": ["alexander mcqueen", "mcqueen"],
        "min_price": 15,
        "retail": {"sneaker oversized": 500, "sneaker": 480, "sac": 1200, "veste": 1500, "tshirt": 300}
    },
    "Vivienne Westwood": {
        "keywords": ["vivienne westwood"],
        "min_price": 10,
        "retail": {"collier": 200, "sac": 500, "veste": 600, "tshirt": 150, "robe": 400}
    },
    "Paul Smith": {
        "keywords": ["paul smith"],
        "min_price": 8,
        "retail": {"chemise": 180, "veste": 400, "pull": 250, "tshirt": 80, "sac": 300}
    },
    "Mulberry": {
        "keywords": ["mulberry"],
        "min_price": 15,
        "retail": {"sac": 800, "portefeuille": 300, "ceinture": 200}
    },
    # Luxe nordique et belge
    "Maison Margiela": {
        "keywords": ["maison margiela", "margiela", "mm6"],
        "min_price": 15,
        "retail": {"tabi": 900, "sneaker": 600, "veste": 800, "tshirt": 250, "sac": 700}
    },
    "Acne Studios": {
        "keywords": ["acne studios", "acne"],
        "min_price": 10,
        "retail": {"veste": 500, "pull": 300, "tshirt": 150, "jean": 250, "sac": 400, "echarpe": 200}
    },
    "Dries Van Noten": {
        "keywords": ["dries van noten"],
        "min_price": 15,
        "retail": {"veste": 800, "pull": 400, "chemise": 300, "pantalon": 400}
    },
    "Raf Simons": {
        "keywords": ["raf simons"],
        "min_price": 15,
        "retail": {"sneaker": 500, "veste": 800, "tshirt": 250, "pull": 400}
    },
    # Luxe americain
    "Ralph Lauren": {
        "keywords": ["ralph lauren", "polo ralph", "purple label", "rrl"],
        "min_price": 5,
        "retail": {"polo": 100, "chemise": 110, "hoodie": 180, "pull": 140, "veste": 300, "tshirt": 70, "purple label": 500, "rrl": 300}
    },
    "Tom Ford": {
        "keywords": ["tom ford"],
        "min_price": 20,
        "retail": {"parfum": 300, "lunettes": 400, "veste": 1500, "chaussure": 600}
    },
    "Marc Jacobs": {
        "keywords": ["marc jacobs"],
        "min_price": 10,
        "retail": {"sac tote": 250, "sac": 350, "tshirt": 150, "pull": 250}
    },
    "Coach": {
        "keywords": ["coach"],
        "min_price": 10,
        "retail": {"sac": 400, "portefeuille": 200, "sneaker": 150, "ceinture": 150}
    },
    # Streetwear luxe
    "Off-White": {
        "keywords": ["off white", "off-white"],
        "min_price": 15,
        "retail": {"sneaker": 450, "tshirt": 350, "hoodie": 600, "veste": 1000, "sac": 600, "ceinture": 250}
    },
    "Supreme": {
        "keywords": ["supreme"],
        "min_price": 10,
        "retail": {"hoodie box logo": 800, "tshirt box logo": 300, "hoodie": 250, "tshirt": 150, "veste": 400, "casquette": 80}
    },
    "Fear of God": {
        "keywords": ["fear of god", "fog", "essentials"],
        "min_price": 10,
        "retail": {"hoodie": 350, "tshirt": 150, "jean": 300, "veste": 500, "sneaker": 400}
    },
    "Palm Angels": {
        "keywords": ["palm angels"],
        "min_price": 10,
        "retail": {"tshirt": 250, "hoodie": 450, "veste track": 600, "sneaker": 350}
    },
    "Amiri": {
        "keywords": ["amiri"],
        "min_price": 15,
        "retail": {"jean": 800, "tshirt": 300, "sneaker": 500, "veste": 1200, "hoodie": 600}
    },
    "Rick Owens": {
        "keywords": ["rick owens"],
        "min_price": 20,
        "retail": {"sneaker ramones": 600, "sneaker": 550, "veste": 1500, "tshirt": 300, "jean": 500}
    },
    "Vetements": {
        "keywords": ["vetements", "vêtements"],
        "min_price": 15,
        "retail": {"hoodie": 600, "tshirt": 300, "veste": 1000, "jean": 500}
    },
    "Gallery Dept": {
        "keywords": ["gallery dept"],
        "min_price": 15,
        "retail": {"tshirt": 300, "jean": 400, "hoodie": 500, "veste": 700}
    },
    # Luxe espagnol
    "Loewe": {
        "keywords": ["loewe"],
        "min_price": 20,
        "retail": {"puzzle": 2500, "sac": 1500, "tshirt": 350, "pull": 600, "veste": 1200}
    },
    # Sneakers luxe
    "Nike Jordan": {
        "keywords": ["nike", "jordan", "air max", "dunk", "air force"],
        "min_price": 3,
        "retail": {"jordan 1": 280, "jordan 3": 250, "jordan 4": 300, "dunk low": 200, "air max 90": 130, "air max 95": 160, "air force 1": 110, "tech fleece": 100, "veste": 90, "hoodie": 70, "tshirt": 40}
    },
    "Adidas": {
        "keywords": ["adidas", "yeezy", "samba", "gazelle"],
        "min_price": 3,
        "retail": {"yeezy 350": 220, "yeezy 700": 200, "samba": 130, "gazelle": 110, "superstar": 100, "veste": 80}
    },
    "New Balance": {
        "keywords": ["new balance", "nb 550", "nb 574", "nb 990", "nb 2002"],
        "min_price": 5,
        "retail": {"990": 200, "2002r": 180, "550": 130, "574": 100, "530": 90, "nb": 100}
    },
    # Autres luxe
    "Canada Goose": {
        "keywords": ["canada goose"],
        "min_price": 20,
        "retail": {"expedition": 1200, "parka": 800, "doudoune": 700, "veste": 600}
    },
    "Barbour": {
        "keywords": ["barbour"],
        "min_price": 8,
        "retail": {"bedale": 350, "beaufort": 380, "veste": 280, "pull": 180}
    },
    "Patagonia": {
        "keywords": ["patagonia"],
        "min_price": 5,
        "retail": {"better sweater": 180, "fleece": 160, "doudoune": 260, "veste": 230}
    },
    "The North Face": {
        "keywords": ["north face", "the north face"],
        "min_price": 4,
        "retail": {"nuptse": 260, "veste": 180, "doudoune": 200, "fleece": 130}
    },
    "Carhartt": {
        "keywords": ["carhartt", "carhartt wip"],
        "min_price": 3,
        "retail": {"detroit": 200, "michigan": 190, "veste": 160, "hoodie": 100, "sweat": 80}
    },
    "Lacoste": {
        "keywords": ["lacoste"],
        "min_price": 5,
        "retail": {"polo": 95, "chemise": 110, "hoodie": 140, "veste": 200, "tshirt": 70, "sneaker": 110}
    },
    "Levis": {
        "keywords": ["levis", "levi's", "501"],
        "min_price": 3,
        "retail": {"501 vintage": 180, "501": 100, "trucker": 110, "veste": 110, "jean": 90}
    },
}

# ── Mots interdits — anti-arnaque ─────────────────────
FAKE_SIGNALS = [
    "replica", "rep ", "aaa", "inspired", "no name",
    "contrefacon", "contrefaçon", "fake", "copie",
    "imitation", "style", "inspired by", "pokemon",
    "carte", "card", "sticker", "poster", "print",
    "cadre", "tableau", "photo", "figurine", "jouet",
    "toy", "lego", "manga", "livre", "book", "dvd",
    "parfum generique", "non authentique",
]

# ── Mots qui confirment que c est un vrai vetement ──
CLOTHING_SIGNALS = [
    "taille", "size", "xl", "xxl", "xs", " s ", " m ", " l ",
    "veste", "jacket", "hoodie", "pull", "tshirt", "t-shirt",
    "jean", "pantalon", "robe", "chemise", "manteau", "blouson",
    "sac", "bag", "chaussure", "sneaker", "boots", "mocassin",
    "ceinture", "portefeuille", "lunettes", "casquette", "bonnet",
    "echarpe", "parfum", "montre",
]

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

MAX_LUXURY_RATIO   = 0.30
MAX_AVG_PRICE      = 80
MIN_FEEDBACK_SCORE = 4.0

LUXURY_KEYWORDS = [
    "chanel", "dior", "louis vuitton", "hermes", "gucci", "prada",
    "bottega", "miu miu", "versace", "fendi", "valentino", "celine",
    "saint laurent", "ysl", "balenciaga", "givenchy", "loewe",
    "off white", "supreme", "stone island", "moncler", "canada goose",
    "burberry", "ami paris", "jacquemus", "rick owens", "vetements",
    "amiri", "fear of god", "palm angels", "gallery dept", "margiela",
    "acne studios", "balmain", "sandro", "maje", "isabel marant",
    "vivienne westwood", "alexander mcqueen", "tom ford",
]

country_sessions = {}

def get_session(base_url):
    if base_url not in country_sessions:
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Origin": base_url,
            "Referer": base_url + "/",
        })
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
    s = get_session(base_url)
    params = {"search_text": keyword, "order": "newest_first", "per_page": 48, "currency": "EUR"}
    if max_price:
        params["price_to"] = max_price
    try:
        r = s.get(base_url + "/api/v2/catalog/items", params=params, timeout=12)
        if r.status_code == 200:
            return r.json().get("items", [])
        elif r.status_code == 401:
            s.get(base_url, timeout=10)
        return []
    except Exception as e:
        print("  Vinted error: " + str(e))
        return []

def get_freshness(item):
    try:
        ts = item.get("created_at_ts") or item.get("photo", {}).get("created_at_ts")
        if not ts:
            return None, "?", False
        age_min = int((time.time() - int(ts)) / 60)
        is_fresh = age_min <= FRESH_MINUTES
        if age_min < 5:
            label = str(age_min) + " min - VIENT DE SORTIR"
        elif age_min < 15:
            label = str(age_min) + " min - TRES RECENT"
        elif age_min < 60:
            label = str(age_min) + " min"
        else:
            label = str(age_min // 60) + "h"
            is_fresh = False
        return age_min, label, is_fresh
    except:
        return None, "?", False

def is_real_clothing(title, description):
    text = (title + " " + (description or "")).lower()
    # Verifie qu il y a au moins un signal vetement
    has_clothing = any(signal in text for signal in CLOTHING_SIGNALS)
    # Verifie qu il n y a pas de signal fake
    has_fake = any(signal in text for signal in FAKE_SIGNALS)
    return has_clothing and not has_fake

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
    best_retail = 0
    best_match = None
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

def evaluate_item(item, brand_name, brand_data):
    try:
        price = float(item.get("price", {}).get("amount", 0))
        title = item.get("title", "")
        desc = item.get("description", "")
        cond = item.get("status", "")
        size = item.get("size_title", "?")
        city = item.get("city", "?")

        if price == 0 or price > BUDGET_MAX:
            return None
        if price < brand_data.get("min_price", 3):
            return None

        # Verification que c est un vrai vetement/accessoire
        if not is_real_clothing(title, desc):
            return None

        resell_base, retail_price, matched = get_resell_value(title, desc, brand_data)
        coeff = get_cond_coeff(cond)
        resell = round(resell_base * coeff, 0)
        ratio = round(resell / price, 2) if price > 0 else 0

        if ratio < RATIO_MIN:
            return None

        fees = round(resell * 0.05 + 0.70, 2)
        gain = round(resell - price - fees, 0)

        if gain < MIN_GAIN:
            return None

        liq_score = 3.0
        size_lower = (size or "").lower()
        for sk, sv in [("xs",3),("s",5),("m",5),("l",4),("xl",3),("xxl",2)]:
            if sk in size_lower:
                liq_score = (liq_score + sv) / 2
                break
        for ck, cv in [("noir",5),("black",5),("blanc",5),("white",5),("beige",4),("gris",4)]:
            if ck in title.lower():
                liq_score = (liq_score + cv) / 2
                break

        return {
            "brand": brand_name,
            "price": price,
            "retail": retail_price,
            "resell": resell,
            "gain": gain,
            "ratio": ratio,
            "cond": cond,
            "size": size,
            "city": city,
            "liq": round(liq_score, 1),
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

def format_alert(item, result, flag, s_score, s_reason, base_url, age_min, fresh_label, is_fresh):
    title = item.get("title", "Sans titre")
    url = base_url + "/items/" + str(item.get("id", ""))
    seller = item.get("user", {})
    s_name = seller.get("login", "?")
    s_url = base_url + "/member/" + str(seller.get("id", ""))
    fire = "F" * min(int(result["ratio"]), 5)

    if is_fresh and age_min is not None and age_min <= 5:
        header = "URGENT - " + fresh_label + "\n"
    elif is_fresh:
        header = "RECENT - " + fresh_label + "\n"
    else:
        header = ""

    if s_score >= 80:
        badge = "Profil ideal"
    elif s_score >= 60:
        badge = "Profil correct"
    else:
        badge = "A verifier"

    msg = (
        header
        + fire + " " + flag + " " + result["brand"].upper() + "\n\n"
        + title + "\n\n"
        + "Prix demande: " + str(result["price"]) + "EUR\n"
        + "Prix boutique: ~" + str(result["retail"]) + "EUR\n"
        + "Revente estimee: ~" + str(result["resell"]) + "EUR\n"
        + "Ratio: x" + str(result["ratio"]) + "\n"
        + "Gain net: +" + str(result["gain"]) + "EUR\n\n"
        + "Liquidite: " + str(result["liq"]) + "/5\n"
        + "Annonce: " + fresh_label + "\n"
        + "Taille: " + result["size"] + " | Etat: " + result["cond"] + "\n"
        + "Ville: " + result["city"] + "\n\n"
        + badge + " (" + str(s_score) + "/100)\n"
        + s_name + " - " + s_reason + "\n\n"
        + "VOIR: " + url + "\n"
        + datetime.now().strftime("%H:%M:%S")
    )
    return msg

seen_ids = set()

def scan_country(country, base_url):
    found = 0
    for brand_name, brand_data in BRANDS.items():
        for keyword in brand_data["keywords"]:
            items = search_vinted(base_url, keyword, max_price=BUDGET_MAX)
            for item in items:
                item_id = item.get("id")
                unique_id = base_url + "_" + str(item_id)
                if not item_id or unique_id in seen_ids:
                    continue
                seen_ids.add(unique_id)

                result = evaluate_item(item, brand_name, brand_data)
                if not result:
                    continue

                seller_id = item.get("user", {}).get("id")
                if not seller_id:
                    continue

                is_good, score, reason = analyze_seller(base_url, seller_id)
                if not is_good:
                    continue

                age_min, fresh_label, is_fresh = get_freshness(item)
                photos = item.get("photos", [])
                photo_url = photos[0].get("url") or photos[0].get("full_size_url") if photos else None
                msg = format_alert(item, result, country, score, reason, base_url, age_min, fresh_label, is_fresh)
                send_telegram(msg, photo_url=photo_url)

                urgency = "URGENT " if is_fresh else ""
                print(
                    datetime.now().strftime("%H:%M:%S") + " " + urgency
                    + country + " " + result["brand"] + " | "
                    + item.get("title", "?")[:30] + " | "
                    + str(result["price"]) + "EUR->" + str(result["resell"]) + "EUR "
                    + "x" + str(result["ratio"]) + " +" + str(result["gain"]) + "EUR"
                )
                found += 1
                time.sleep(1)
            time.sleep(1.5)
    return found

def main():
    print("VINTED BOT - " + str(len(BRANDS)) + " marques de luxe")
    print("Budget max: " + str(BUDGET_MAX) + "EUR")
    print("Ratio min: x" + str(RATIO_MIN))
    print("Gain min: +" + str(MIN_GAIN) + "EUR")
    print("Fraicheur: <" + str(FRESH_MINUTES) + " min")
    print("Pays: " + str(len(VINTED_COUNTRIES)))

    init_all_sessions()

    send_telegram(
        "Vinted Bot demarre!\n\n"
        + str(len(BRANDS)) + " marques luxe surveillees\n"
        + "Budget max: " + str(BUDGET_MAX) + "EUR\n"
        + "Ratio min: x" + str(RATIO_MIN) + "\n"
        + "Gain min: +" + str(MIN_GAIN) + "EUR\n"
        + "Fraicheur: <" + str(FRESH_MINUTES) + " min\n"
        + "6 pays: FR BE NL ES DE IT\n\n"
        + "En chasse..."
    )

    cycle = 0
    while True:
        cycle += 1
        total = 0
        print("SCAN #" + str(cycle) + " " + datetime.now().strftime("%H:%M:%S"))
        for country, base_url in VINTED_COUNTRIES.items():
            found = scan_country(country, base_url)
            total += found
            time.sleep(3)
        print("FIN #" + str(cycle) + " - " + str(total) + " alertes | Next: " + str(CHECK_INTERVAL) + "s")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
