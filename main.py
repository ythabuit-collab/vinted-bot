import requests
import time
import re
from datetime import datetime

TELEGRAM_TOKEN   = "8611988792:AAGOJ7xDWPRJveS0jOe71NH5rWczdKwPUgI"
TELEGRAM_CHAT_ID = "8559815820"

BUDGET_MAX     = 60
RATIO_MIN      = 2.5
CHECK_INTERVAL = 50
MIN_GAIN       = 40
FRESH_MINUTES  = 10

VINTED_COUNTRIES = {
    "🇫🇷 France":    "https://www.vinted.fr",
    "🇧🇪 Belgique":  "https://www.vinted.be",
    "🇳🇱 Pays-Bas":  "https://www.vinted.nl",
    "🇪🇸 Espagne":   "https://www.vinted.es",
    "🇩🇪 Allemagne": "https://www.vinted.de",
    "🇮🇹 Italie":    "https://www.vinted.it",
}

# ════════════════════════════════════════════════════════
#  ⚡  FRAÎCHEUR
# ════════════════════════════════════════════════════════

def get_freshness(item):
    try:
        ts = item.get("created_at_ts") or item.get("photo", {}).get("created_at_ts")
        if not ts: return None, "?", False
        age_min  = int((time.time() - int(ts)) / 60)
        is_fresh = age_min <= FRESH_MINUTES
        if age_min < 5:    label = f"🆕 {age_min} min — VIENT DE SORTIR"
        elif age_min < 15: label = f"🔴 {age_min} min — TRÈS RÉCENT"
        elif age_min < 60: label = f"🟠 {age_min} min"
        elif age_min < 360: label = f"🟡 {age_min // 60}h"; is_fresh = False
        else: label = f"⚪ {age_min // 60}h"; is_fresh = False
        return age_min, label, is_fresh
    except:
        return None, "?", False

# ════════════════════════════════════════════════════════
#  📊  LIQUIDITÉ
# ════════════════════════════════════════════════════════

LIQUID_SIZES = {
    "xs": 3, "s": 5, "m": 5, "l": 4, "xl": 3, "xxl": 2,
    "36": 4, "38": 5, "40": 5, "42": 4, "44": 3, "46": 2,
    "34": 3, "32": 4, "30": 4, "39": 4, "41": 5, "43": 4, "45": 2,
    "one size": 4, "unique": 4,
}
LIQUID_COLORS = {
    "noir": 5, "black": 5, "blanc": 5, "white": 5,
    "beige": 4, "cream": 4, "gris": 4, "grey": 4, "gray": 4,
    "marine": 4, "navy": 4, "bleu": 3, "blue": 3,
    "marron": 3, "brown": 3, "kaki": 3, "khaki": 3,
    "rouge": 2, "red": 2, "vert": 2, "green": 2,
    "rose": 2, "pink": 2, "jaune": 1, "orange": 1, "violet": 1,
}

def compute_liquidity(title, size_str, condition):
    score = 3.0
    for sk, sv in LIQUID_SIZES.items():
        if sk in (size_str or "").lower(): score = (score + sv) / 2; break
    for ck, cv in LIQUID_COLORS.items():
        if ck in title.lower(): score = (score + cv) / 2; break
    if condition:
        c = condition.lower()
        if any(x in c for x in ["neuf", "neu", "nuevo", "nuovo", "nieuw"]): score += 0.5
        elif any(x in c for x in ["satisfaisant", "befriedigend"]): score -= 1
    return round(min(5, max(1, score)), 1)

def liq_label(score):
    if score >= 4.5: return "⚡ Très rapide (heures)"
    elif score >= 3.5: return "🟢 Rapide (jours)"
    elif score >= 2.5: return "🟡 Moyen (semaines)"
    else: return "🔴 Lent (mois)"

# ════════════════════════════════════════════════════════
#  💰  EXTRACTION MODÈLE PRÉCIS DEPUIS LE TITRE
# ════════════════════════════════════════════════════════

def extract_search_query(title, brand_name):
    """
    Extrait une requête de recherche précise depuis le titre Vinted.
    Garde les mots significatifs : modèle, couleur, matière, taille.
    """
    # Mots à ignorer (articles, prépositions, mots génériques)
    stop_words = {
        "le", "la", "les", "de", "du", "des", "un", "une", "en", "et",
        "avec", "pour", "très", "bon", "etat", "état", "neuf", "occasion",
        "vente", "vends", "taille", "couleur", "belle", "beau", "super",
        "the", "a", "an", "in", "of", "for", "and", "with", "size",
        "condition", "used", "new", "good", "great", "nice", "worn"
    }

    words = title.lower().split()
    significant = [w for w in words if len(w) > 2 and w not in stop_words]

    # Prend les 5 mots les plus significatifs
    query = f"{brand_name} {' '.join(significant[:5])}"
    return query.strip()

# ════════════════════════════════════════════════════════
#  💰  SOURCE 1 : EBAY — dernières ventes réelles
# ════════════════════════════════════════════════════════

ebay_cache = {}
SCRAPE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

def search_ebay(brand_name, title):
    query     = extract_search_query(title, brand_name)
    cache_key = query.lower().replace(" ", "_")[:60]
    now       = time.time()

    if cache_key in ebay_cache:
        t, d = ebay_cache[cache_key]
        if now - t < 3600: return d

    def parse_prices(html):
        prices = []
        for p in re.findall(r'([\d]+[,.][\d]{2})\s*EUR', html):
            try:
                v = float(p.replace(",", "."))
                if 5 < v < 8000: prices.append(v)
            except: pass
        return prices

    try:
        # Recherche 1 : requête précise avec titre
        params = {"_nkw": query, "LH_Sold": "1", "LH_Complete": "1", "_sop": "13", "_ipg": "60"}
        r      = requests.get("https://www.ebay.fr/sch/i.html", params=params,
                              headers=SCRAPE_HEADERS, timeout=12)
        prices = parse_prices(r.text) if r.status_code == 200 else []

        # Recherche 2 : fallback avec juste la marque + type
        if len(prices) < 5:
            item_type = _detect_type_from_title(title)
            params2   = dict(params)
            params2["_nkw"] = f"{brand_name} {item_type}".strip()
            r2 = requests.get("https://www.ebay.fr/sch/i.html", params=params2,
                              headers=SCRAPE_HEADERS, timeout=12)
            if r2.status_code == 200:
                prices += parse_prices(r2.text)

        if len(prices) < 3:
            result = (None, 0, "faible")
            ebay_cache[cache_key] = (now, result)
            return result

        prices.sort()
        cut    = max(1, len(prices) // 10)
        prices = prices[cut:-cut] if len(prices) > 10 else prices
        median = prices[len(prices) // 2]
        avg    = sum(prices) / len(prices)
        price  = round(median * 0.65 + avg * 0.35, 0)
        n      = len(prices)
        conf   = "haute" if n >= 20 else "moyenne" if n >= 8 else "faible"

        result = (price, n, conf)
        ebay_cache[cache_key] = (now, result)
        print(f"  [eBay] '{query[:35]}' → {price}€ ({n} ventes, {conf})")
        return result
    except Exception as e:
        print(f"  [eBay] Erreur: {e}")
        result = (None, 0, "faible")
        ebay_cache[cache_key] = (now, result)
        return result

def _detect_type_from_title(title):
    tl = title.lower()
    for t in ["veste", "jacket", "hoodie", "pull", "sweat", "tshirt", "t-shirt",
              "jean", "pantalon", "sac", "bag", "sneaker", "boot", "manteau",
              "polo", "chemise", "shirt", "gilet", "parka", "doudoune"]:
        if t in tl: return t
    return ""

# ════════════════════════════════════════════════════════
#  💰  SOURCE 2 : VESTIAIRE COLLECTIVE — luxe uniquement
# ════════════════════════════════════════════════════════

vestiaire_cache = {}

LUXURY_BRANDS_VESTIAIRE = [
    "Bottega Veneta", "Balenciaga", "Gucci", "Prada", "Burberry",
    "Louis Vuitton", "Dior", "Stone Island", "Ami Paris", "Jacquemus",
    "APC", "Zadig Voltaire", "Moncler", "Canada Goose", "CP Company",
    "Saint Laurent", "Celine", "Givenchy", "Valentino", "Fendi",
]

def search_vestiaire(brand_name, title):
    if brand_name not in LUXURY_BRANDS_VESTIAIRE:
        return None, 0, "non applicable"

    query     = extract_search_query(title, brand_name)
    cache_key = f"vest_{query.lower().replace(' ', '_')[:50]}"
    now       = time.time()

    if cache_key in vestiaire_cache:
        t, d = vestiaire_cache[cache_key]
        if now - t < 7200: return d

    try:
        search_url = "https://fr.vestiairecollective.com/search/"
        params     = {"q": query, "order": "price_asc"}
        r = requests.get(search_url, params=params,
                         headers=SCRAPE_HEADERS, timeout=12)

        if r.status_code != 200:
            result = (None, 0, "indisponible")
            vestiaire_cache[cache_key] = (now, result)
            return result

        # Extraction des prix
        prices_raw = re.findall(r'(\d{2,5})[,.]?\d{0,2}\s*€', r.text)
        prices = []
        for p in prices_raw:
            try:
                v = float(p)
                if 20 < v < 10000: prices.append(v)
            except: pass

        if len(prices) < 3:
            result = (None, 0, "faible")
            vestiaire_cache[cache_key] = (now, result)
            return result

        prices.sort()
        # Sur Vestiaire on prend le prix médian des 10 premiers résultats
        prices  = prices[:10]
        median  = prices[len(prices) // 2]
        result  = (round(median, 0), len(prices), "haute")
        vestiaire_cache[cache_key] = (now, result)
        print(f"  [Vestiaire] '{query[:35]}' → {median}€ ({len(prices)} résultats)")
        return result
    except Exception as e:
        print(f"  [Vestiaire] Erreur: {e}")
        result = (None, 0, "indisponible")
        vestiaire_cache[cache_key] = (now, result)
        return result

# ════════════════════════════════════════════════════════
#  💰  SOURCE 3 : STOCKX — sneakers & streetwear
# ════════════════════════════════════════════════════════

stockx_cache = {}

STOCKX_BRANDS = ["Nike Jordan", "Adidas", "Balenciaga", "Gucci", "Dior", "Louis Vuitton"]

def search_stockx(brand_name, title):
    if brand_name not in STOCKX_BRANDS:
        return None, 0, "non applicable"

    query     = extract_search_query(title, brand_name)
    cache_key = f"stx_{query.lower().replace(' ', '_')[:50]}"
    now       = time.time()

    if cache_key in stockx_cache:
        t, d = stockx_cache[cache_key]
        if now - t < 3600: return d

    try:
        # StockX search via leur page publique
        r = requests.get(
            f"https://stockx.com/search?s={requests.utils.quote(query)}",
            headers={**SCRAPE_HEADERS, "Accept-Language": "en-US,en;q=0.9"},
            timeout=12
        )

        if r.status_code != 200:
            result = (None, 0, "indisponible")
            stockx_cache[cache_key] = (now, result)
            return result

        # Extraction prix "last sale"
        prices_raw = re.findall(r'\$(\d{2,4})', r.text)
        prices = []
        for p in prices_raw:
            try:
                v = float(p) * 0.92  # Conversion USD → EUR approximative
                if 30 < v < 3000: prices.append(v)
            except: pass

        if len(prices) < 2:
            result = (None, 0, "faible")
            stockx_cache[cache_key] = (now, result)
            return result

        prices.sort()
        median = prices[len(prices) // 2]
        result = (round(median, 0), len(prices), "moyenne")
        stockx_cache[cache_key] = (now, result)
        print(f"  [StockX] '{query[:35]}' → {median}€ ({len(prices)} résultats)")
        return result
    except Exception as e:
        print(f"  [StockX] Erreur: {e}")
        result = (None, 0, "indisponible")
        stockx_cache[cache_key] = (now, result)
        return result

# ════════════════════════════════════════════════════════
#  🧠  FUSION MULTI-SOURCES + SCORE DE CONFIANCE
# ════════════════════════════════════════════════════════

def fuse_prices(ebay_data, vestiaire_data, stockx_data, catalogue_price):
    """
    Fusionne les prix de toutes les sources disponibles.
    Retourne (prix_final, score_confiance, detail_sources)
    """
    sources       = []
    prices_valid  = []
    sources_used  = []
    conf_score    = 0

    # eBay
    ebay_price, ebay_n, ebay_conf = ebay_data
    if ebay_price and ebay_conf in ("haute", "moyenne"):
        weight = 3 if ebay_conf == "haute" else 2
        prices_valid.append((ebay_price, weight))
        sources_used.append(f"eBay ({ebay_n} ventes)")
        conf_score += weight

    # Vestiaire Collective
    vest_price, vest_n, vest_conf = vestiaire_data
    if vest_price and vest_conf == "haute":
        prices_valid.append((vest_price, 3))
        sources_used.append(f"Vestiaire ({vest_n} résultats)")
        conf_score += 3

    # StockX
    stx_price, stx_n, stx_conf = stockx_data
    if stx_price and stx_conf in ("haute", "moyenne"):
        prices_valid.append((stx_price, 2))
        sources_used.append(f"StockX ({stx_n} prix)")
        conf_score += 2

    # Si aucune source externe fiable → catalogue
    if not prices_valid:
        return catalogue_price, 1, ["catalogue (prix fixe)"]

    # Moyenne pondérée
    total_weight = sum(w for _, w in prices_valid)
    weighted_avg = sum(p * w for p, w in prices_valid) / total_weight
    final_price  = round(weighted_avg, 0)

    # Score confiance max 10
    conf_score = min(10, conf_score)

    return final_price, conf_score, sources_used

def confidence_label(score):
    if score >= 7:   return "🟢 Élevée"
    elif score >= 4: return "🟡 Moyenne"
    elif score >= 2: return "🟠 Faible"
    else:            return "⚪ Catalogue"

# ════════════════════════════════════════════════════════
#  🏷️  MARQUES & CATALOGUE
# ════════════════════════════════════════════════════════

MAX_LUXURY_RATIO   = 0.30
MAX_AVG_PRICE      = 80
MIN_FEEDBACK_SCORE = 4.0

LUXURY_KEYWORDS = [
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
    "tres bon etat": 0.75, "bon etat": 0.60, "satisfaisant": 0.40,
    "neuf": 0.95, "tres bon": 0.75, "bon": 0.60,
    "neu mit etikett": 1.00, "sehr gut": 0.75, "gut": 0.60,
    "nuevo con etiqueta": 1.00, "muy bueno": 0.75, "bueno": 0.60,
    "nuovo con etichetta": 1.00, "ottimo": 0.75,
    "nieuw met label": 1.00, "zeer goed": 0.75,
    "default": 0.65,
}

BRANDS = {
    "Bottega Veneta": {
        "keywords": ["bottega veneta", "bottega"], "min_price": 20,
        "retail": {"sac jodie": 2800, "sac cassette": 3200, "sac arco": 2500,
                   "sac": 2000, "portefeuille": 800, "ceinture": 600,
                   "sneaker": 700, "pull": 900, "veste": 1500}},
    "Balenciaga": {
        "keywords": ["balenciaga"], "min_price": 15,
        "retail": {"triple s": 950, "speed trainer": 800, "track": 850,
                   "runner": 950, "sneaker": 900, "hoodie": 900,
                   "tshirt": 450, "veste": 1500, "sac": 1200}},
    "Gucci": {
        "keywords": ["gucci"], "min_price": 15,
        "retail": {"ace": 650, "sneaker": 700, "ceinture": 400,
                   "sac": 1200, "tshirt": 400, "hoodie": 900, "veste": 1800}},
    "Prada": {
        "keywords": ["prada"], "min_price": 15,
        "retail": {"sac nylon": 900, "sac": 1500, "sneaker": 800,
                   "tshirt": 400, "pull": 900, "veste": 1800}},
    "Burberry": {
        "keywords": ["burberry"], "min_price": 12,
        "retail": {"trench": 2000, "veste": 1200, "manteau": 1800,
                   "pull": 600, "tshirt": 300, "echarpe": 500, "sac": 1200}},
    "Louis Vuitton": {
        "keywords": ["louis vuitton", "lv", "vuitton"], "min_price": 20,
        "retail": {"keepall": 2000, "speedy": 1200, "neverfull": 1800,
                   "sac": 1500, "portefeuille": 700, "ceinture": 500,
                   "sneaker": 1000, "tshirt": 500, "hoodie": 1200}},
    "Dior": {
        "keywords": ["dior", "christian dior"], "min_price": 20,
        "retail": {"b23": 1100, "b22": 1200, "sneaker": 1100,
                   "sac": 2000, "tshirt": 450, "hoodie": 1200, "veste": 2500}},
    "Stone Island": {
        "keywords": ["stone island"], "min_price": 15,
        "retail": {"ghost piece": 600, "veste": 400, "hoodie": 300,
                   "sweat": 250, "pull": 220, "tshirt": 140}},
    "Ami Paris": {
        "keywords": ["ami paris", "ami de coeur"], "min_price": 15,
        "retail": {"pull": 300, "hoodie": 350, "tshirt": 130,
                   "chemise": 220, "veste": 450, "manteau": 600}},
    "Jacquemus": {
        "keywords": ["jacquemus"], "min_price": 10,
        "retail": {"le chiquito": 550, "sac": 400, "chemise": 250,
                   "robe": 300, "pull": 250, "veste": 400}},
    "APC": {
        "keywords": ["apc", "a.p.c."], "min_price": 10,
        "retail": {"jean": 190, "veste": 300, "manteau": 500,
                   "pull": 220, "hoodie": 230, "sac": 300}},
    "Ralph Lauren": {
        "keywords": ["ralph lauren", "polo ralph", "purple label", "rrl"], "min_price": 5,
        "retail": {"polo": 100, "chemise": 110, "hoodie": 180,
                   "pull": 140, "veste": 300, "tshirt": 70,
                   "purple label": 500, "rrl": 300}},
    "Lacoste": {
        "keywords": ["lacoste"], "min_price": 5,
        "retail": {"polo": 95, "chemise": 110, "hoodie": 140,
                   "veste": 200, "tshirt": 70, "sneaker": 110}},
    "Tommy Hilfiger": {
        "keywords": ["tommy hilfiger", "tommy jeans"], "min_price": 4,
        "retail": {"polo": 85, "chemise": 95, "hoodie": 110,
                   "veste": 170, "tshirt": 55, "jean": 95}},
    "Zadig Voltaire": {
        "keywords": ["zadig", "zadig voltaire"], "min_price": 8,
        "retail": {"perfecto": 500, "veste": 350, "pull": 230,
                   "hoodie": 200, "robe": 250, "tshirt": 90, "sac": 300}},
    "Sezane": {
        "keywords": ["sezane", "sézane"], "min_price": 5,
        "retail": {"robe": 140, "chemise": 120, "pull": 130,
                   "veste": 200, "manteau": 350, "jean": 120}},
    "Barbour": {
        "keywords": ["barbour"], "min_price": 8,
        "retail": {"bedale": 350, "beaufort": 380, "veste": 280, "pull": 180}},
    "Patagonia": {
        "keywords": ["patagonia"], "min_price": 5,
        "retail": {"better sweater": 180, "fleece": 160,
                   "doudoune": 260, "veste": 230, "pull": 150}},
    "Nike Jordan": {
        "keywords": ["nike", "jordan", "air max", "dunk", "air force"], "min_price": 3,
        "retail": {"jordan 1": 280, "jordan 3": 250, "jordan 4": 300,
                   "dunk low": 200, "air max 90": 130, "air max 95": 160,
                   "air force 1": 110, "tech fleece": 100,
                   "veste": 90, "hoodie": 70, "tshirt": 40}},
    "Adidas": {
        "keywords": ["adidas", "yeezy", "samba", "gazelle"], "min_price": 3,
        "retail": {"yeezy 350": 220, "yeezy 700": 200, "samba": 130,
                   "gazelle": 110, "superstar": 100, "veste": 80}},
    "The North Face": {
        "keywords": ["north face", "the north face"], "min_price": 4,
        "retail": {"nuptse": 260, "veste": 180, "doudoune": 200,
                   "fleece": 130, "pull": 110, "tshirt": 55}},
    "Carhartt": {
        "keywords": ["carhartt", "carhartt wip"], "min_price": 3,
        "retail": {"detroit": 200, "michigan": 190, "veste": 160,
                   "hoodie": 100, "sweat": 80, "tshirt": 55}},
    "Levis": {
        "keywords": ["levis", "levi's", "501"], "min_price": 3,
        "retail": {"501 vintage": 180, "501": 100, "trucker": 110,
                   "veste": 110, "jean": 90, "tshirt": 45}},
    "Timberland": {
        "keywords": ["timberland"], "min_price": 4,
        "retail": {"boot": 160, "veste": 130, "pull": 80}},
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
            "Origin": base_url, "Referer": base_url + "/",
        })
        try: s.get(base_url, timeout=10)
        except: pass
        country_sessions[base_url] = s
    return country_sessions[base_url]

def init_all_sessions():
    for country, url in VINTED_COUNTRIES.items():
        try: get_session(url); print(f"  {country} ✓")
        except Exception as e: print(f"  {country} ✗ ({e})")
        time.sleep(0.8)

def search_vinted(base_url, keyword, max_price=None):
    s = get_session(base_url)
    params = {"search_text": keyword, "order": "newest_first", "per_page": 48, "currency": "EUR"}
    if max_price: params["price_to"] = max_price
    try:
        r = s.get(f"{base_url}/api/v2/catalog/items", params=params, timeout=12)
        if r.status_code == 200: return r.json().get("items", [])
        elif r.status_code == 401: s.get(base_url, timeout=10)
        return []
    except Exception as e:
        print(f"  [{base_url.split('.')[-1]}] '{keyword}': {e}"); return []

# ════════════════════════════════════════════════════════
#  👤  ANALYSE VENDEUR
# ════════════════════════════════════════════════════════

seller_cache = {}

def analyze_seller(base_url, seller_id):
    key = f"{base_url}_{seller_id}"
    if key in seller_cache: return seller_cache[key]
    s = get_session(base_url)
    profile, items = {}, []
    try:
        r = s.get(f"{base_url}/api/v2/users/{seller_id}", timeout=10)
        if r.status_code == 200: profile = r.json().get("user", {})
        time.sleep(0.4)
        r2 = s.get(f"{base_url}/api/v2/users/{seller_id}/items",
                   params={"per_page": 20, "order": "newest_first"}, timeout=10)
        if r2.status_code == 200: items = r2.json().get("items", [])
    except:
        result = (True, 60, "profil non disponible")
        seller_cache[key] = result; return result

    if not items:
        result = (True, 60, "historique vide")
        seller_cache[key] = result; return result

    feedback  = float(profile.get("feedback_reputation", 1) or 1)
    n_items   = int(profile.get("items_count", 0) or 0)
    n_fb      = int(profile.get("positive_feedback_count", 0) or 0)
    prices, lux, norm = [], 0, 0

    for it in items:
        try:
            p = float(it.get("price", {}).get("amount", 0))
            if p > 0: prices.append(p)
            if any(kw in it.get("title", "").lower() for kw in LUXURY_KEYWORDS): lux += 1
            else: norm += 1
        except: pass

    avg_p   = sum(prices) / len(prices) if prices else 0
    lux_r   = lux / len(items) if items else 0
    score, reason = 100, []

    if feedback < MIN_FEEDBACK_SCORE:   score -= 40; reason.append(f"note {feedback}/5")
    if lux_r > MAX_LUXURY_RATIO:        score -= 50; reason.append(f"{int(lux_r*100)}% luxe")
    if avg_p > MAX_AVG_PRICE:           score -= 20; reason.append(f"prix moy. {avg_p:.0f}€")
    if n_items > 50 and n_fb < 5:       score -= 30; reason.append("peu de feedback")
    if avg_p < 30 and norm > lux * 3:   score += 10; reason.append("dressing perso ✓")

    score  = max(0, min(100, score))
    result = (score >= 50, score, " | ".join(reason) if reason else "profil OK")
    seller_cache[key] = result
    return result

# ════════════════════════════════════════════════════════
#  🧠  ÉVALUATION ARTICLE — MULTI-SOURCES
# ════════════════════════════════════════════════════════

def get_cond_coeff(cond):
    if not cond: return CONDITION_COEFFS["default"]
    c = cond.lower()
    for k, v in CONDITION_COEFFS.items():
        if k in c: return v
    return CONDITION_COEFFS["default"]

def get_catalogue_resell(title, desc, brand_data):
    text = (title + " " + (desc or "")).lower()
    best_retail, best_match = 0, None
    for mk, rp in brand_data["retail"].items():
        if all(w in text for w in mk.split()) and rp > best_retail:
            best_retail = rp; best_match = mk
    if best_retail == 0:
        vals = sorted(brand_data["retail"].values())
        best_retail = vals[len(vals) // 2]; best_match = "ref mediane"
    return best_retail * 0.50, best_retail, best_match

def evaluate_item(item, brand_name, brand_data):
    try:
        price = float(item.get("price", {}).get("amount", 0))
        title = item.get("title", "")
        desc  = item.get("description", "")
        cond  = item.get("status", "")
        size  = item.get("size_title", "?")
        city  = item.get("city", "?")

        if price == 0 or price > BUDGET_MAX: return None
        if price < brand_data.get("min_price", 3): return None
        if any(s in (title + " " + (desc or "")).lower() for s in FAKE_SIGNALS): return None

        # ── Prix catalogue (base) ──
        cat_resell, retail_price, _ = get_catalogue_resell(title, desc, brand_data)

        # ── 3 sources externes ──
        ebay_data      = search_ebay(brand_name, title)
        time.sleep(0.5)
        vestiaire_data = search_vestiaire(brand_name, title)
        time.sleep(0.3)
        stockx_data    = search_stockx(brand_name, title)
        time.sleep(0.3)

        # ── Fusion des prix ──
        fused_price, conf_score, sources_used = fuse_prices(
            ebay_data, vestiaire_data, stockx_data, cat_resell
        )

        # ── Application coefficient état ──
        coeff  = get_cond_coeff(cond)
        resell = round(fused_price * coeff, 0)
        ratio  = round(resell / price, 2) if price > 0 else 0

        if ratio < RATIO_MIN: return None

        fees = round(resell * 0.05 + 0.70, 2)
        gain = round(resell - price - fees, 0)
        if gain < MIN_GAIN: return None

        liq = compute_liquidity(title, size, cond)

        return {
            "brand":        brand_name,
            "price":        price,
            "retail":       retail_price,
            "resell":       resell,
            "gain":         gain,
            "ratio":        ratio,
            "cond":         cond,
            "size":         size,
            "city":         city,
            "sources":      sources_used,
            "conf_score":   conf_score,
            "conf_label":   confidence_label(conf_score),
            "liq":          liq,
            "liq_label":    liq_label(liq),
        }
    except Exception as e:
        print(f"  [ERREUR] {e}"); return None

# ════════════════════════════════════════════════════════
#  📲  TELEGRAM
# ════════════════════════════════════════════════════════

def send_telegram(msg, photo_url=None):
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    if photo_url:
        payload  = {"chat_id": TELEGRAM_CHAT_ID, "photo": photo_url,
                    "caption": msg[:1024], "parse_mode": "HTML"}
        endpoint = f"{base}/sendPhoto"
    else:
        payload  = {"chat_id": TELEGRAM_CHAT_ID, "text": msg,
                    "parse_mode": "HTML", "disable_web_page_preview": False}
        endpoint = f"{base}/sendMessage"
    try:
        r = requests.post(endpoint, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[ERREUR] Telegram: {e}"); return False

def format_alert(item, r, flag, s_score, s_reason, base_url, age_min, fresh_label, is_fresh):
    title  = item.get("title", "Sans titre")
    url    = f"{base_url}/items/{item.get('id', '')}"
    seller = item.get("user", {})
    s_url  = f"{base_url}/member/{seller.get('id', '')}"
    fire   = "🔥" * min(int(r["ratio"]), 5)

    if is_fresh and age_min is not None and age_min <= 5: header = f"🚨 URGENT — {fresh_label}\n"
    elif is_fresh: header = f"⚡ RÉCENT — {fresh_label}\n"
    else: header = ""

    if s_score >= 80:   badge = "🟢 Profil idéal"
    elif s_score >= 60: badge = "🟡 Profil correct"
    else:               badge = "🟠 À vérifier"

    # Sources utilisées
    sources_str = " + ".join(r["sources"]) if r["sources"] else "catalogue"

    return (
        f"{header}{fire} {flag} <b>{r['brand'].upper()}</b>\n\n"
        f"👕 <b>{title}</b>\n\n"
        f"💰 Prix demandé   : <b>{r['price']}€</b>\n"
        f"🏷️ Prix boutique  : ~{r['retail']}€\n"
        f"💵 Revente estimée: ~{r['resell']:.0f}€\n"
        f"📊 Sources        : {sources_str}\n"
        f"🎯 Confiance      : {r['conf_label']} ({r['conf_score']}/10)\n"
        f"📈 Ratio          : <b>x{r['ratio']}</b>\n"
        f"🤑 Gain net       : <b>+{r['gain']:.0f}€</b>\n\n"
        f"⚡ Liquidité      : {r['liq_label']} ({r['liq']}/5)\n"
        f"🕐 Annonce        : {fresh_label}\n"
        f"📐 Taille : {r['size']} | État : {r['cond']}\n"
        f"📍 {r['city']}\n\n"
        f"{badge} ({s_score}/100)\n"
        f"👤 <a href=\"{s_url}\">{seller.get('login','?')}</a> — {s_reason}\n\n"
        f"👉 <a href=\"{url}\">VOIR L'ANNONCE</a>\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )

# ════════════════════════════════════════════════════════
#  🔄  BOUCLE PRINCIPALE
# ════════════════════════════════════════════════════════

seen_ids = set()

def scan_country(country_name, base_url):
    found = 0
    flag  = country_name.split()[0]
    for brand_name, brand_data in BRANDS.items():
        for keyword in brand_data["keywords"]:
            items = search_vinted(base_url, keyword, max_price=BUDGET_MAX)
            for item in items:
                item_id   = item.get("id")
                unique_id = f"{base_url}_{item_id}"
                if not item_id or unique_id in seen_ids: continue
                seen_ids.add(unique_id)

                result = evaluate_item(item, brand_name, brand_data)
                if not result: continue

                seller_id = item.get("user", {}).get("id")
                if not seller_id: continue

                is_good, score, reason = analyze_seller(base_url, seller_id)
                if not is_good: continue

                age_min, fresh_label, is_fresh = get_freshness(item)
                photos    = item.get("photos", [])
                photo_url = photos[0].get("url") or photos[0].get("full_size_url") if photos else None
                msg       = format_alert(item, result, flag, score, reason,
                                         base_url, age_min, fresh_label, is_fresh)
                send_telegram(msg, photo_url=photo_url)

                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] {flag}"
                    f"{'🚨' if is_fresh else '  '} {result['brand']} | "
                    f"{item.get('title','?')[:25]} | "
                    f"{result['price']}€→{result['resell']:.0f}€ "
                    f"x{result['ratio']} +{result['gain']:.0f}€ "
                    f"conf:{result['conf_score']}/10 liq:{result['liq']}"
                )
                found += 1
                time.sleep(1)
            time.sleep(1.5)
    return found

def main():
    print("=" * 65)
    print("   VINTED BOT — MULTI-SOURCES PRIX")
    print(f"   Prix    : eBay + Vestiaire + StockX + catalogue")
    print(f"   Confiance : score /10 selon nb sources confirmées")
    print(f"   Ratio min : x{RATIO_MIN} | Gain min : +{MIN_GAIN}€")
    print(f"   Pays    : {len(VINTED_COUNTRIES)} | Marques : {len(BRANDS)}")
    print("=" * 65)

    init_all_sessions()

    send_telegram(
        f"🤖 <b>Vinted Bot — Multi-Sources activé</b>\n\n"
        f"💰 Prix vérifiés sur 3 sources :\n"
        f"• eBay (dernières ventes réelles)\n"
        f"• Vestiaire Collective (luxe)\n"
        f"• StockX (sneakers & streetwear)\n\n"
        f"🎯 Score de confiance /10 par alerte\n"
        f"🌍 6 pays | 📦 {len(BRANDS)} marques\n\n"
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
        print(f"\n══ FIN #{cycle} ══ {total} alerte(s) | eBay:{len(ebay_cache)} Vest:{len(vestiaire_cache)} STX:{len(stockx_cache)} | Next:{CHECK_INTERVAL}s")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
