import requests
import time
import re
from datetime import datetime

TELEGRAM_TOKEN   = "8611988792:AAGOJ7xDWPRJveS0jOe71NH5rWczdKwPUgI"
TELEGRAM_CHAT_ID = "8559815820"

BUDGET_MAX     = 60
RATIO_MIN      = 2.5
CHECK_INTERVAL = 55
MIN_GAIN       = 40

# ════════════════════════════════════════════════════════
#  🌍  PAYS VINTED
# ════════════════════════════════════════════════════════

VINTED_COUNTRIES = {
    "🇫🇷 France":    "https://www.vinted.fr",
    "🇧🇪 Belgique":  "https://www.vinted.be",
    "🇳🇱 Pays-Bas":  "https://www.vinted.nl",
    "🇪🇸 Espagne":   "https://www.vinted.es",
    "🇩🇪 Allemagne": "https://www.vinted.de",
    "🇮🇹 Italie":    "https://www.vinted.it",
}

# ════════════════════════════════════════════════════════
#  📊  SCORE LIQUIDITÉ
#  Estime la vitesse de revente (1-5 étoiles)
# ════════════════════════════════════════════════════════

# Tailles les plus liquides sur Vinted/eBay (données marché)
LIQUID_SIZES = {
    "xs": 3, "s": 5, "m": 5, "l": 4, "xl": 3, "xxl": 2,
    "36": 4, "38": 5, "40": 5, "42": 4, "44": 3, "46": 2,
    "34": 3, "32": 4, "30": 4, "28": 3,
    "39": 4, "40": 5, "41": 5, "42": 4, "43": 4, "44": 3, "45": 2,
    "one size": 4, "unique": 4,
}

# Couleurs les plus liquides
LIQUID_COLORS = {
    "noir": 5, "black": 5, "blanc": 5, "white": 5,
    "beige": 4, "crème": 4, "cream": 4, "gris": 4, "grey": 4, "gray": 4,
    "marine": 4, "navy": 4, "bleu": 3, "blue": 3,
    "marron": 3, "brown": 3, "kaki": 3, "khaki": 3,
    "rouge": 2, "red": 2, "vert": 2, "green": 2,
    "rose": 2, "pink": 2, "jaune": 1, "yellow": 1,
    "orange": 1, "violet": 1, "purple": 1,
}

def compute_liquidity_score(title, size_str, condition):
    """
    Calcule un score de liquidité de 1 à 5.
    5 = se revend en quelques heures
    1 = peut rester des semaines
    """
    score = 3  # Base

    # Score taille
    size_lower = (size_str or "").lower().strip()
    for size_key, size_score in LIQUID_SIZES.items():
        if size_key in size_lower:
            score = (score + size_score) / 2
            break

    # Score couleur (depuis le titre)
    title_lower = title.lower()
    for color, color_score in LIQUID_COLORS.items():
        if color in title_lower:
            score = (score + color_score) / 2
            break

    # Bonus état
    if condition:
        c = condition.lower()
        if "neuf" in c or "neu" in c or "nuevo" in c or "nuovo" in c:
            score += 0.5
        elif "satisfaisant" in c or "befriedigend" in c:
            score -= 1

    return round(min(5, max(1, score)), 1)

def liquidity_label(score):
    if score >= 4.5:
        return "⚡ Très rapide (heures)"
    elif score >= 3.5:
        return "🟢 Rapide (jours)"
    elif score >= 2.5:
        return "🟡 Moyen (semaines)"
    else:
        return "🔴 Lent (mois)"

# ════════════════════════════════════════════════════════
#  💰  PRIX EBAY EN TEMPS RÉEL
#  Scrape les dernières ventes eBay pour avoir le vrai prix marché
# ════════════════════════════════════════════════════════

ebay_cache = {}  # Cache 6h pour éviter trop de requêtes

EBAY_SESSION = requests.Session()
EBAY_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
})

def search_ebay_sold(brand_name, item_title, item_type=""):
    """
    Cherche les dernières ventes eBay pour estimer le prix réel.
    Retourne (prix_median, nb_ventes, confiance)
    """
    # Clé de cache : marque + type article
    cache_key = f"{brand_name}_{item_type}".lower().replace(" ", "_")
    now       = time.time()

    if cache_key in ebay_cache:
        cached_time, cached_data = ebay_cache[cache_key]
        if now - cached_time < 21600:  # Cache 6 heures
            return cached_data

    # Construction requête eBay
    query = f"{brand_name} {item_type}".strip()
    # eBay France — articles vendus récemment
    url = "https://www.ebay.fr/sch/i.html"
    params = {
        "_nkw":    query,
        "LH_Sold": "1",       # Seulement les vendus
        "LH_Complete": "1",   # Annonces terminées
        "_sop":    "13",      # Tri par date récente
        "_ipg":    "60",      # 60 résultats
        "LH_ItemCondition": "3000",  # Occasion
    }

    try:
        r = EBAY_SESSION.get(url, params=params, timeout=12)
        if r.status_code != 200:
            return _ebay_fallback(cache_key)

        # Extraction des prix avec regex
        # eBay affiche les prix vendus en vert avec la classe s-item__price
        prices_raw = re.findall(
            r'class="s-item__price"[^>]*>\s*(?:<[^>]+>)*\s*([\d\s]+[,.][\d]{2})\s*EUR',
            r.text
        )

        # Fallback regex plus large
        if len(prices_raw) < 3:
            prices_raw = re.findall(
                r'([\d]+[,.][\d]{2})\s*EUR',
                r.text
            )

        prices = []
        for p_str in prices_raw:
            try:
                p = float(p_str.replace(" ", "").replace(",", "."))
                if 5 < p < 5000:  # Filtre valeurs aberrantes
                    prices.append(p)
            except:
                pass

        if len(prices) < 3:
            return _ebay_fallback(cache_key)

        # Tri et suppression des outliers (5% bas et haut)
        prices.sort()
        cut     = max(1, len(prices) // 20)
        prices  = prices[cut:-cut] if len(prices) > 10 else prices

        median  = prices[len(prices) // 2]
        avg     = sum(prices) / len(prices)
        # On prend la moyenne pondérée médiane/moyenne
        result_price = round((median * 0.6 + avg * 0.4), 0)
        nb_ventes    = len(prices)

        # Confiance basée sur nombre de ventes
        if nb_ventes >= 20:
            confiance = "haute"
        elif nb_ventes >= 8:
            confiance = "moyenne"
        else:
            confiance = "faible"

        result = (result_price, nb_ventes, confiance)
        ebay_cache[cache_key] = (now, result)
        print(f"  [eBay] {query} → {result_price}€ ({nb_ventes} ventes, confiance {confiance})")
        return result

    except Exception as e:
        print(f"  [eBay] Erreur '{query}': {e}")
        return _ebay_fallback(cache_key)

def _ebay_fallback(cache_key):
    """Retourne None si eBay inaccessible — on utilisera le prix catalogue."""
    result = (None, 0, "indisponible")
    ebay_cache[cache_key] = (time.time(), result)
    return result

# ════════════════════════════════════════════════════════
#  🏷️  MARQUES & PRIX CATALOGUE (fallback si eBay KO)
# ════════════════════════════════════════════════════════

MAX_LUXURY_RATIO   = 0.30
MAX_AVG_PRICE      = 80
MIN_FEEDBACK_SCORE = 4.0

LUXURY_BRAND_KEYWORDS = [
    "bottega", "balenciaga", "gucci", "prada", "burberry",
    "louis vuitton", "lv", "vuitton", "dior", "christian dior",
    "stone island", "cp company", "moncler", "canada goose",
    "off white", "supreme", "ami paris", "jacquemus", "celine",
    "saint laurent", "ysl", "givenchy", "valentino", "versace",
    "fendi", "loewe", "acne studios", "maison margiela",
    "rick owens", "fear of god", "kenzo", "isabel marant",
]

CONDITION_COEFFS = {
    "neuf avec etiquette": 1.00, "neuf sans etiquette": 0.90,
    "tres bon etat": 0.75,       "bon etat": 0.60,
    "satisfaisant": 0.40,        "neuf": 0.95,
    "tres bon": 0.75,            "bon": 0.60,
    "neu mit etikett": 1.00,     "sehr gut": 0.75, "gut": 0.60,
    "nuevo con etiqueta": 1.00,  "muy bueno": 0.75, "bueno": 0.60,
    "nuovo con etichetta": 1.00, "ottimo": 0.75,
    "nieuw met label": 1.00,     "zeer goed": 0.75,
    "default": 0.65,
}

BRANDS = {
    "Bottega Veneta": {
        "keywords": ["bottega veneta", "bottega"],
        "min_price": 20,
        "retail": {
            "sac jodie": 2800, "sac cassette": 3200, "sac arco": 2500,
            "sac": 2000, "portefeuille": 800, "ceinture": 600,
            "sneaker": 700, "pull": 900, "veste": 1500,
        }
    },
    "Balenciaga": {
        "keywords": ["balenciaga"],
        "min_price": 15,
        "retail": {
            "triple s": 950, "speed trainer": 800, "track": 850,
            "runner": 950, "sneaker": 900, "hoodie": 900,
            "tshirt": 450, "veste": 1500, "sac": 1200,
        }
    },
    "Gucci": {
        "keywords": ["gucci"],
        "min_price": 15,
        "retail": {
            "ace": 650, "sneaker": 700, "ceinture": 400,
            "sac": 1200, "tshirt": 400, "hoodie": 900, "veste": 1800,
        }
    },
    "Prada": {
        "keywords": ["prada"],
        "min_price": 15,
        "retail": {
            "sac nylon": 900, "sac": 1500, "sneaker": 800,
            "tshirt": 400, "pull": 900, "veste": 1800,
        }
    },
    "Burberry": {
        "keywords": ["burberry"],
        "min_price": 12,
        "retail": {
            "trench": 2000, "veste": 1200, "manteau": 1800,
            "pull": 600, "tshirt": 300, "echarpe": 500, "sac": 1200,
        }
    },
    "Louis Vuitton": {
        "keywords": ["louis vuitton", "lv", "vuitton"],
        "min_price": 20,
        "retail": {
            "keepall": 2000, "speedy": 1200, "neverfull": 1800,
            "sac": 1500, "portefeuille": 700, "ceinture": 500,
            "sneaker": 1000, "tshirt": 500, "hoodie": 1200,
        }
    },
    "Dior": {
        "keywords": ["dior", "christian dior"],
        "min_price": 20,
        "retail": {
            "b23": 1100, "b22": 1200, "sneaker": 1100,
            "sac": 2000, "tshirt": 450, "hoodie": 1200, "veste": 2500,
        }
    },
    "Stone Island": {
        "keywords": ["stone island"],
        "min_price": 15,
        "retail": {
            "ghost piece": 600, "veste": 400, "hoodie": 300,
            "sweat": 250, "pull": 220, "tshirt": 140,
        }
    },
    "Ami Paris": {
        "keywords": ["ami paris", "ami de coeur"],
        "min_price": 15,
        "retail": {
            "pull": 300, "hoodie": 350, "tshirt": 130,
            "chemise": 220, "veste": 450, "manteau": 600,
        }
    },
    "Jacquemus": {
        "keywords": ["jacquemus"],
        "min_price": 10,
        "retail": {
            "le chiquito": 550, "sac": 400, "chemise": 250,
            "robe": 300, "pull": 250, "veste": 400,
        }
    },
    "APC": {
        "keywords": ["apc", "a.p.c."],
        "min_price": 10,
        "retail": {
            "jean": 190, "veste": 300, "manteau": 500,
            "pull": 220, "hoodie": 230, "sac": 300,
        }
    },
    "Ralph Lauren": {
        "keywords": ["ralph lauren", "polo ralph", "purple label", "rrl"],
        "min_price": 5,
        "retail": {
            "polo": 100, "chemise": 110, "hoodie": 180,
            "pull": 140, "veste": 300, "tshirt": 70,
            "purple label": 500, "rrl": 300,
        }
    },
    "Lacoste": {
        "keywords": ["lacoste"],
        "min_price": 5,
        "retail": {
            "polo": 95, "chemise": 110, "hoodie": 140,
            "veste": 200, "tshirt": 70, "sneaker": 110,
        }
    },
    "Tommy Hilfiger": {
        "keywords": ["tommy hilfiger", "tommy jeans"],
        "min_price": 4,
        "retail": {
            "polo": 85, "chemise": 95, "hoodie": 110,
            "veste": 170, "tshirt": 55, "jean": 95,
        }
    },
    "Zadig Voltaire": {
        "keywords": ["zadig", "zadig voltaire"],
        "min_price": 8,
        "retail": {
            "perfecto": 500, "veste": 350, "pull": 230,
            "hoodie": 200, "robe": 250, "tshirt": 90, "sac": 300,
        }
    },
    "Sezane": {
        "keywords": ["sezane", "sézane"],
        "min_price": 5,
        "retail": {
            "robe": 140, "chemise": 120, "pull": 130,
            "veste": 200, "manteau": 350, "jean": 120,
        }
    },
    "Barbour": {
        "keywords": ["barbour"],
        "min_price": 8,
        "retail": {
            "bedale": 350, "beaufort": 380, "veste": 280, "pull": 180,
        }
    },
    "Patagonia": {
        "keywords": ["patagonia"],
        "min_price": 5,
        "retail": {
            "better sweater": 180, "fleece": 160,
            "doudoune": 260, "veste": 230, "pull": 150,
        }
    },
    "Nike Jordan": {
        "keywords": ["nike", "jordan", "air max", "dunk", "air force"],
        "min_price": 3,
        "retail": {
            "jordan 1": 280, "jordan 3": 250, "jordan 4": 300,
            "dunk low": 200, "air max 90": 130, "air max 95": 160,
            "air force 1": 110, "tech fleece": 100,
            "veste": 90, "hoodie": 70, "tshirt": 40,
        }
    },
    "Adidas": {
        "keywords": ["adidas", "yeezy", "samba", "gazelle"],
        "min_price": 3,
        "retail": {
            "yeezy 350": 220, "yeezy 700": 200, "samba": 130,
            "gazelle": 110, "superstar": 100, "veste": 80,
        }
    },
    "The North Face": {
        "keywords": ["north face", "the north face"],
        "min_price": 4,
        "retail": {
            "nuptse": 260, "veste": 180, "doudoune": 200,
            "fleece": 130, "pull": 110, "tshirt": 55,
        }
    },
    "Carhartt": {
        "keywords": ["carhartt", "carhartt wip"],
        "min_price": 3,
        "retail": {
            "detroit": 200, "michigan": 190, "veste": 160,
            "hoodie": 100, "sweat": 80, "tshirt": 55,
        }
    },
    "Levis": {
        "keywords": ["levis", "levi's", "501"],
        "min_price": 3,
        "retail": {
            "501 vintage": 180, "501": 100, "trucker": 110,
            "veste": 110, "jean": 90, "tshirt": 45,
        }
    },
    "Timberland": {
        "keywords": ["timberland"],
        "min_price": 4,
        "retail": {"boot": 160, "veste": 130, "pull": 80},
    },
}

FAKE_SIGNALS = ["replica", "rep", "aaa", "inspired", "no name", "contrefacon"]

# ════════════════════════════════════════════════════════
#  📡  SESSIONS VINTED
# ════════════════════════════════════════════════════════

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
    for country, base_url in VINTED_COUNTRIES.items():
        try:
            get_session(base_url)
            print(f"  {country} ✓")
        except Exception as e:
            print(f"  {country} ✗ ({e})")
        time.sleep(0.8)

def search_vinted_country(base_url, keyword, max_price=None):
    session = get_session(base_url)
    params  = {"search_text": keyword, "order": "newest_first", "per_page": 48, "currency": "EUR"}
    if max_price:
        params["price_to"] = max_price
    try:
        r = session.get(f"{base_url}/api/v2/catalog/items", params=params, timeout=12)
        if r.status_code == 200:
            return r.json().get("items", [])
        elif r.status_code == 401:
            session.get(base_url, timeout=10)
        return []
    except Exception as e:
        print(f"  [{base_url.split('.')[2]}] '{keyword}': {e}")
        return []

# ════════════════════════════════════════════════════════
#  👤  ANALYSE VENDEUR
# ════════════════════════════════════════════════════════

seller_cache = {}

def is_luxury_title(title):
    t = title.lower()
    return any(kw in t for kw in LUXURY_BRAND_KEYWORDS)

def analyze_seller(base_url, seller_id):
    cache_key = f"{base_url}_{seller_id}"
    if cache_key in seller_cache:
        return seller_cache[cache_key]

    session = get_session(base_url)
    profile, items = {}, []

    try:
        r = session.get(f"{base_url}/api/v2/users/{seller_id}", timeout=10)
        if r.status_code == 200:
            profile = r.json().get("user", {})
        time.sleep(0.4)
        r2 = session.get(f"{base_url}/api/v2/users/{seller_id}/items",
                         params={"per_page": 20, "order": "newest_first"}, timeout=10)
        if r2.status_code == 200:
            items = r2.json().get("items", [])
    except:
        result = (True, 60, "profil non disponible")
        seller_cache[cache_key] = result
        return result

    if not items:
        result = (True, 60, "historique vide")
        seller_cache[cache_key] = result
        return result

    feedback_score = float(profile.get("feedback_reputation", 1) or 1)
    total_items    = int(profile.get("items_count", 0) or 0)
    feedback_count = int(profile.get("positive_feedback_count", 0) or 0)

    prices, luxury_count, normal_count = [], 0, 0
    for it in items:
        try:
            p = float(it.get("price", {}).get("amount", 0))
            if p > 0:
                prices.append(p)
            if is_luxury_title(it.get("title", "")):
                luxury_count += 1
            else:
                normal_count += 1
        except:
            pass

    avg_price    = sum(prices) / len(prices) if prices else 0
    luxury_ratio = luxury_count / len(items) if items else 0

    score, reason = 100, []

    if feedback_score < MIN_FEEDBACK_SCORE:
        score -= 40
        reason.append(f"note {feedback_score}/5")
    if luxury_ratio > MAX_LUXURY_RATIO:
        score -= 50
        reason.append(f"{int(luxury_ratio*100)}% luxe")
    if avg_price > MAX_AVG_PRICE:
        score -= 20
        reason.append(f"prix moy. {avg_price:.0f}€")
    if total_items > 50 and feedback_count < 5:
        score -= 30
        reason.append("peu de feedback")
    if avg_price < 30 and normal_count > luxury_count * 3:
        score += 10
        reason.append("dressing perso ✓")

    score      = max(0, min(100, score))
    reason_str = " | ".join(reason) if reason else "profil OK"
    result     = (score >= 50, score, reason_str)
    seller_cache[cache_key] = result
    return result

# ════════════════════════════════════════════════════════
#  🧠  ÉVALUATION ARTICLE (avec prix eBay temps réel)
# ════════════════════════════════════════════════════════

def get_condition_coeff(condition_str):
    if not condition_str:
        return CONDITION_COEFFS["default"]
    c = condition_str.lower()
    for key, coeff in CONDITION_COEFFS.items():
        if key in c:
            return coeff
    return CONDITION_COEFFS["default"]

def get_catalogue_resell(title, description, brand_data):
    text        = (title + " " + (description or "")).lower()
    best_retail = 0
    best_match  = None
    for model_key, retail_price in brand_data["retail"].items():
        words = model_key.split()
        if all(w in text for w in words) and retail_price > best_retail:
            best_retail = retail_price
            best_match  = model_key
    if best_retail == 0:
        vals        = sorted(brand_data["retail"].values())
        best_retail = vals[len(vals) // 2]
        best_match  = "ref mediane"
    return best_retail * 0.50, best_retail, best_match

def detect_item_type(title, brand_data):
    """Détecte le type d'article depuis le titre pour la requête eBay."""
    title_lower = title.lower()
    for model_key in brand_data["retail"].keys():
        words = model_key.split()
        if all(w in title_lower for w in words):
            return model_key
    # Fallback types génériques
    for t in ["veste", "hoodie", "pull", "tshirt", "jean", "sac", "sneaker", "boot"]:
        if t in title_lower:
            return t
    return ""

def evaluate_item(item, brand_name, brand_data):
    try:
        price       = float(item.get("price", {}).get("amount", 0))
        title       = item.get("title", "")
        description = item.get("description", "")
        condition   = item.get("status", "")
        size        = item.get("size_title", "?")
        city        = item.get("city", "?")

        if price == 0 or price > BUDGET_MAX:
            return None
        if price < brand_data.get("min_price", 3):
            return None

        text = (title + " " + (description or "")).lower()
        if any(s in text for s in FAKE_SIGNALS):
            return None

        # ── Valeur catalogue (fallback) ──
        catalogue_resell, retail_price, matched_model = get_catalogue_resell(title, description, brand_data)

        # ── Prix eBay en temps réel ──
        item_type  = detect_item_type(title, brand_data)
        ebay_price, nb_ventes, confiance = search_ebay_sold(brand_name, title, item_type)
        time.sleep(0.3)

        # ── Fusion : eBay prioritaire si confiance suffisante ──
        if ebay_price and confiance in ("haute", "moyenne"):
            resell_base  = ebay_price
            price_source = f"eBay ({nb_ventes} ventes, {confiance})"
        else:
            resell_base  = catalogue_resell
            price_source = "catalogue"

        # Ajustement état
        coeff        = get_condition_coeff(condition)
        resell_value = round(resell_base * coeff, 0)
        ratio        = round(resell_value / price, 2) if price > 0 else 0

        if ratio < RATIO_MIN:
            return None

        vinted_fees = round(resell_value * 0.05 + 0.70, 2)
        net_gain    = round(resell_value - price - vinted_fees, 0)

        if net_gain < MIN_GAIN:
            return None

        # ── Score liquidité ──
        liq_score = compute_liquidity_score(title, size, condition)

        return {
            "brand_name":   brand_name,
            "price":        price,
            "retail_price": retail_price,
            "resell_value": resell_value,
            "net_gain":     net_gain,
            "ratio":        ratio,
            "condition":    condition,
            "size":         size,
            "city":         city,
            "price_source": price_source,
            "liq_score":    liq_score,
            "liq_label":    liquidity_label(liq_score),
        }
    except Exception as e:
        print(f"  [ERREUR] evaluate_item : {e}")
        return None

# ════════════════════════════════════════════════════════
#  📲  TELEGRAM
# ════════════════════════════════════════════════════════

def send_telegram(message, photo_url=None):
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    if photo_url:
        payload  = {"chat_id": TELEGRAM_CHAT_ID, "photo": photo_url, "caption": message[:1024], "parse_mode": "HTML"}
        endpoint = f"{base}/sendPhoto"
    else:
        payload  = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML", "disable_web_page_preview": False}
        endpoint = f"{base}/sendMessage"
    try:
        r = requests.post(endpoint, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[ERREUR] Telegram : {e}")
        return False

def format_alert(item, result, flag, seller_score, seller_reason, base_url):
    title   = item.get("title", "Sans titre")
    url     = f"{base_url}/items/{item.get('id', '')}"
    seller  = item.get("user", {})
    s_name  = seller.get("login", "?")
    s_url   = f"{base_url}/member/{seller.get('id', '')}"
    fire    = "🔥" * min(int(result["ratio"]), 5)

    if seller_score >= 80:   profile_badge = "🟢 Profil idéal"
    elif seller_score >= 60: profile_badge = "🟡 Profil correct"
    else:                    profile_badge = "🟠 À vérifier"

    msg = (
        f"{fire} {flag} <b>{result['brand_name'].upper()}</b>\n\n"
        f"👕 <b>{title}</b>\n\n"
        f"💰 Prix demandé   : <b>{result['price']}€</b>\n"
        f"🏷️ Prix boutique  : ~{result['retail_price']}€\n"
        f"💵 Revente estimée: ~{result['resell_value']:.0f}€\n"
        f"📊 Source prix    : {result['price_source']}\n"
        f"📈 Ratio          : <b>x{result['ratio']}</b>\n"
        f"🤑 Gain net       : <b>+{result['net_gain']:.0f}€</b>\n\n"
        f"⚡ Liquidité      : {result['liq_label']} ({result['liq_score']}/5)\n"
        f"📐 Taille : {result['size']} | État : {result['condition']}\n"
        f"📍 {result['city']}\n\n"
        f"{profile_badge} ({seller_score}/100)\n"
        f"👤 <a href=\"{s_url}\">{s_name}</a> — {seller_reason}\n\n"
        f"👉 <a href=\"{url}\">VOIR L'ANNONCE</a>\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    return msg

# ════════════════════════════════════════════════════════
#  🔄  BOUCLE PRINCIPALE
# ════════════════════════════════════════════════════════

seen_ids = set()

def scan_country(country_name, base_url):
    found = 0
    flag  = country_name.split()[0]

    for brand_name, brand_data in BRANDS.items():
        for keyword in brand_data["keywords"]:
            items = search_vinted_country(base_url, keyword, max_price=BUDGET_MAX)
            for item in items:
                item_id   = item.get("id")
                unique_id = f"{base_url}_{item_id}"
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

                photos    = item.get("photos", [])
                photo_url = photos[0].get("url") or photos[0].get("full_size_url") if photos else None
                msg       = format_alert(item, result, flag, score, reason, base_url)
                send_telegram(msg, photo_url=photo_url)

                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] {flag} 🔥 "
                    f"{result['brand_name']} | {item.get('title','?')[:30]} | "
                    f"{result['price']}€ → {result['resell_value']:.0f}€ "
                    f"(x{result['ratio']}) +{result['net_gain']:.0f}€ "
                    f"liq:{result['liq_score']} src:{result['price_source'][:8]}"
                )
                found += 1
                time.sleep(1)
            time.sleep(1.5)
    return found

def main():
    print("=" * 65)
    print("   VINTED ALERT BOT — MULTI-PAYS + EBAY + LIQUIDITÉ")
    print(f"   Ratio min  : x{RATIO_MIN} | Gain min : +{MIN_GAIN}€")
    print(f"   Prix       : eBay temps réel (fallback catalogue)")
    print(f"   Liquidité  : score taille + couleur + état")
    print(f"   Vendeur    : filtre profil actif")
    print(f"   Pays       : {len(VINTED_COUNTRIES)} pays")
    print(f"   Marques    : {len(BRANDS)}")
    print("=" * 65)

    print("\n[INFO] Init sessions Vinted...")
    init_all_sessions()

    send_telegram(
        f"🤖 <b>Vinted Bot Ultimate — B+C activés</b>\n\n"
        f"💰 Prix eBay en temps réel\n"
        f"⚡ Score liquidité taille/couleur\n"
        f"🌍 6 pays : FR BE NL ES DE IT\n"
        f"👤 Filtre profil vendeur\n"
        f"⚙️ Ratio x{RATIO_MIN} | Gain min +{MIN_GAIN}€\n\n"
        f"🟢 En chasse..."
    )

    cycle = 0
    while True:
        cycle += 1
        total = 0
        print(f"\n══ SCAN #{cycle} ══ {datetime.now().strftime('%H:%M:%S')} ══")
        for country_name, base_url in VINTED_COUNTRIES.items():
            print(f"\n  {country_name}...")
            found  = scan_country(country_name, base_url)
            total += found
            time.sleep(3)
        print(f"\n══ FIN #{cycle} ══ {total} alerte(s) | eBay cache: {len(ebay_cache)} | Vendeurs: {len(seller_cache)} | Prochain: {CHECK_INTERVAL}s")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
