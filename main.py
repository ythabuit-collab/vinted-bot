import requests
import time
from datetime import datetime

TELEGRAM_TOKEN   = "8611988792:AAGOJ7xDWPRJveS0jOe71NH5rWczdKwPUgI"
TELEGRAM_CHAT_ID = "8559815820"

BUDGET_MAX     = 60
RATIO_MIN      = 2.5
CHECK_INTERVAL = 55
MIN_GAIN       = 40

# ── Pays surveillés ───────────────────────────────────────
VINTED_COUNTRIES = {
    "🇫🇷 France":      "https://www.vinted.fr",
    "🇧🇪 Belgique":    "https://www.vinted.be",
    "🇳🇱 Pays-Bas":    "https://www.vinted.nl",
    "🇪🇸 Espagne":     "https://www.vinted.es",
    "🇩🇪 Allemagne":   "https://www.vinted.de",
    "🇮🇹 Italie":      "https://www.vinted.it",
}

# Mots-clés traduits par pays pour les marques non-anglophones
KEYWORD_TRANSLATIONS = {
    "veste":    {"de": "jacke",    "es": "chaqueta", "it": "giacca",   "nl": "jas"},
    "hoodie":   {"de": "hoodie",   "es": "sudadera",  "it": "felpa",    "nl": "hoodie"},
    "pull":     {"de": "pullover", "es": "jersey",    "it": "maglione", "nl": "trui"},
    "manteau":  {"de": "mantel",   "es": "abrigo",    "it": "cappotto", "nl": "jas"},
    "sac":      {"de": "tasche",   "es": "bolso",     "it": "borsa",    "nl": "tas"},
}

# ── Seuils analyse vendeur ────────────────────────────────
MAX_LUXURY_RATIO  = 0.30
MAX_AVG_PRICE     = 80
MIN_FEEDBACK_SCORE= 4.0

LUXURY_BRAND_KEYWORDS = [
    "bottega", "balenciaga", "gucci", "prada", "burberry",
    "louis vuitton", "lv", "vuitton", "dior", "christian dior",
    "stone island", "cp company", "moncler", "canada goose",
    "off white", "supreme", "ami paris", "jacquemus", "celine",
    "saint laurent", "ysl", "givenchy", "valentino", "versace",
    "fendi", "loewe", "acne studios", "maison margiela", "margiela",
    "rick owens", "fear of god", "essentials", "kenzo", "isabel marant",
]

CONDITION_COEFFS = {
    "neuf avec etiquette": 1.00, "neuf sans etiquette": 0.90,
    "tres bon etat": 0.75,       "bon etat": 0.60,
    "satisfaisant": 0.40,        "neuf": 0.95,
    "tres bon": 0.75,            "bon": 0.60,
    # Allemand
    "neu mit etikett": 1.00,     "neu ohne etikett": 0.90,
    "sehr gut": 0.75,            "gut": 0.60,
    "befriedigend": 0.40,
    # Espagnol
    "nuevo con etiqueta": 1.00,  "nuevo sin etiqueta": 0.90,
    "muy bueno": 0.75,           "bueno": 0.60,
    # Italien
    "nuovo con etichetta": 1.00, "ottimo": 0.75,
    "buono": 0.60,
    # Néerlandais
    "nieuw met label": 1.00,     "zeer goed": 0.75,
    "goed": 0.60,
    "default": 0.65,
}

BRANDS = {
    "Bottega Veneta": {
        "keywords": ["bottega veneta", "bottega"],
        "min_price": 20,
        "retail": {
            "sac jodie": 2800, "sac cassette": 3200, "sac arco": 2500,
            "sac pouch": 2200, "sac": 2000, "portefeuille": 800,
            "ceinture": 600, "sneaker": 700, "pull": 900,
            "veste": 1500, "manteau": 2000,
        }
    },
    "Balenciaga": {
        "keywords": ["balenciaga"],
        "min_price": 15,
        "retail": {
            "triple s": 950, "speed trainer": 800, "track": 850,
            "runner": 950, "sneaker": 900, "hoodie": 900,
            "sweat": 800, "tshirt": 450, "veste": 1500,
            "sac": 1200, "casquette": 350,
        }
    },
    "Gucci": {
        "keywords": ["gucci"],
        "min_price": 15,
        "retail": {
            "ace": 650, "sneaker": 700, "ceinture": 400,
            "sac": 1200, "polo": 500, "tshirt": 400,
            "hoodie": 900, "veste": 1800, "casquette": 350,
            "portefeuille": 450,
        }
    },
    "Prada": {
        "keywords": ["prada"],
        "min_price": 15,
        "retail": {
            "sac nylon": 900, "sac re-nylon": 1200, "sac": 1500,
            "sneaker": 800, "tshirt": 400, "pull": 900,
            "veste": 1800, "casquette": 350, "portefeuille": 500,
        }
    },
    "Burberry": {
        "keywords": ["burberry"],
        "min_price": 12,
        "retail": {
            "trench": 2000, "veste": 1200, "manteau": 1800,
            "pull": 600, "chemise": 500, "tshirt": 300,
            "echarpe": 500, "sac": 1200, "hoodie": 600,
        }
    },
    "Louis Vuitton": {
        "keywords": ["louis vuitton", "lv", "vuitton"],
        "min_price": 20,
        "retail": {
            "keepall": 2000, "speedy": 1200, "neverfull": 1800,
            "sac": 1500, "portefeuille": 700, "ceinture": 500,
            "sneaker": 1000, "pull": 900, "tshirt": 500,
            "hoodie": 1200, "veste": 2000, "casquette": 400,
        }
    },
    "Dior": {
        "keywords": ["dior", "christian dior"],
        "min_price": 20,
        "retail": {
            "b23": 1100, "b22": 1200, "sneaker": 1100,
            "sac": 2000, "tshirt": 450, "hoodie": 1200,
            "pull": 900, "veste": 2500, "casquette": 400,
        }
    },
    "Stone Island": {
        "keywords": ["stone island"],
        "min_price": 15,
        "retail": {
            "ghost piece": 600, "veste": 400, "hoodie": 300,
            "sweat": 250, "pull": 220, "polo": 160,
            "tshirt": 140, "bonnet": 100,
        }
    },
    "Ami Paris": {
        "keywords": ["ami paris", "ami de coeur"],
        "min_price": 15,
        "retail": {
            "pull": 300, "hoodie": 350, "sweat": 300,
            "tshirt": 130, "chemise": 220, "veste": 450,
            "manteau": 600, "sac": 350,
        }
    },
    "Jacquemus": {
        "keywords": ["jacquemus"],
        "min_price": 10,
        "retail": {
            "le chiquito": 550, "le bambino": 500, "sac": 400,
            "chemise": 250, "robe": 300, "pull": 250, "veste": 400,
        }
    },
    "APC": {
        "keywords": ["apc", "a.p.c."],
        "min_price": 10,
        "retail": {
            "jean": 190, "veste": 300, "manteau": 500,
            "pull": 220, "hoodie": 230, "chemise": 180, "sac": 300,
        }
    },
    "Ralph Lauren": {
        "keywords": ["ralph lauren", "polo ralph", "purple label", "rrl"],
        "min_price": 5,
        "retail": {
            "polo": 100, "chemise": 110, "hoodie": 180,
            "pull": 140, "veste": 300, "blouson": 350,
            "tshirt": 70, "purple label": 500, "rrl": 300,
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
            "veste": 170, "pull": 100, "tshirt": 55, "jean": 95,
        }
    },
    "Zadig Voltaire": {
        "keywords": ["zadig", "zadig voltaire"],
        "min_price": 8,
        "retail": {
            "perfecto": 500, "blouson": 450, "veste": 350,
            "pull": 230, "hoodie": 200, "robe": 250,
            "tshirt": 90, "sac": 300,
        }
    },
    "Sezane": {
        "keywords": ["sezane", "sézane"],
        "min_price": 5,
        "retail": {
            "robe": 140, "chemise": 120, "pull": 130,
            "veste": 200, "manteau": 350, "jean": 120, "sac": 180,
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
            "better sweater": 180, "fleece": 160, "doudoune": 260,
            "veste": 230, "pull": 150, "tshirt": 55,
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
        "retail": {
            "boot": 160, "veste": 130, "pull": 80,
        }
    },
}

FAKE_SIGNALS = ["replica", "rep", "aaa", "inspired", "no name", "contrefacon"]

# ── Sessions par pays ─────────────────────────────────────
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
    print("[INFO] Initialisation des sessions par pays...")
    for country, base_url in VINTED_COUNTRIES.items():
        try:
            s = get_session(base_url)
            print(f"  {country} ✓")
        except Exception as e:
            print(f"  {country} ✗ ({e})")
        time.sleep(1)

def search_vinted_country(base_url, keyword, max_price=None):
    session = get_session(base_url)
    params  = {
        "search_text": keyword,
        "order":       "newest_first",
        "per_page":    48,
        "currency":    "EUR",
    }
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
        print(f"  [{base_url}] '{keyword}' : {e}")
        return []

# ── Analyse vendeur ───────────────────────────────────────
seller_cache = {}

def is_luxury_title(title):
    t = title.lower()
    return any(kw in t for kw in LUXURY_BRAND_KEYWORDS)

def analyze_seller(base_url, seller_id):
    cache_key = f"{base_url}_{seller_id}"
    if cache_key in seller_cache:
        return seller_cache[cache_key]

    session = get_session(base_url)
    profile = {}
    items   = []

    try:
        r = session.get(f"{base_url}/api/v2/users/{seller_id}", timeout=10)
        if r.status_code == 200:
            profile = r.json().get("user", {})
        time.sleep(0.5)
        r2 = session.get(f"{base_url}/api/v2/users/{seller_id}/items",
                         params={"per_page": 20, "order": "newest_first"}, timeout=10)
        if r2.status_code == 200:
            items = r2.json().get("items", [])
    except Exception as e:
        print(f"  [Vendeur] {seller_id}: {e}")
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

    prices       = []
    luxury_count = 0
    normal_count = 0

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

    avg_price     = sum(prices) / len(prices) if prices else 0
    luxury_ratio  = luxury_count / len(items) if items else 0

    score  = 100
    reason = []

    if feedback_score < MIN_FEEDBACK_SCORE:
        score -= 40
        reason.append(f"note {feedback_score}/5")

    if luxury_ratio > MAX_LUXURY_RATIO:
        score -= 50
        reason.append(f"{int(luxury_ratio*100)}% luxe dans son profil")

    if avg_price > MAX_AVG_PRICE:
        score -= 20
        reason.append(f"prix moyen {avg_price:.0f}€")

    if total_items > 50 and feedback_count < 5:
        score -= 30
        reason.append(f"{total_items} articles, peu de feedback")

    if avg_price < 30 and normal_count > luxury_count * 3:
        score += 10
        reason.append("dressing perso ✓")

    score      = max(0, min(100, score))
    is_good    = score >= 50
    reason_str = " | ".join(reason) if reason else "profil OK"

    result = (is_good, score, reason_str)
    seller_cache[cache_key] = result
    return result

# ── Évaluation article ────────────────────────────────────
def get_condition_coeff(condition_str):
    if not condition_str:
        return CONDITION_COEFFS["default"]
    c = condition_str.lower()
    for key, coeff in CONDITION_COEFFS.items():
        if key in c:
            return coeff
    return CONDITION_COEFFS["default"]

def estimate_resell_value(title, description, brand_data):
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

def evaluate_item(item, brand_name, brand_data):
    try:
        price       = float(item.get("price", {}).get("amount", 0))
        title       = item.get("title", "")
        description = item.get("description", "")
        condition   = item.get("status", "")

        if price == 0 or price > BUDGET_MAX:
            return None
        if price < brand_data.get("min_price", 3):
            return None

        text = (title + " " + (description or "")).lower()
        if any(s in text for s in FAKE_SIGNALS):
            return None

        resell_base, retail_price, matched_model = estimate_resell_value(title, description, brand_data)
        coeff        = get_condition_coeff(condition)
        resell_value = round(resell_base * coeff, 0)
        ratio        = round(resell_value / price, 2) if price > 0 else 0

        if ratio < RATIO_MIN:
            return None

        vinted_fees = round(resell_value * 0.05 + 0.70, 2)
        net_gain    = round(resell_value - price - vinted_fees, 0)

        if net_gain < MIN_GAIN:
            return None

        return {
            "brand_name":   brand_name,
            "price":        price,
            "retail_price": retail_price,
            "resell_value": resell_value,
            "net_gain":     net_gain,
            "ratio":        ratio,
            "condition":    condition,
            "size":         item.get("size_title", "?"),
            "city":         item.get("city", "?"),
        }
    except Exception as e:
        print(f"  [ERREUR] evaluate_item : {e}")
        return None

# ── Telegram ──────────────────────────────────────────────
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

def format_alert(item, result, country_flag, seller_score, seller_reason, base_url):
    title     = item.get("title", "Sans titre")
    item_id   = item.get("id", "")
    url       = f"{base_url}/items/{item_id}"
    seller    = item.get("user", {})
    s_name    = seller.get("login", "?")
    s_url     = f"{base_url}/member/{seller.get('id', '')}"
    fire      = "🔥" * min(int(result["ratio"]), 5)

    if seller_score >= 80:
        profile_badge = "🟢 Profil idéal"
    elif seller_score >= 60:
        profile_badge = "🟡 Profil correct"
    else:
        profile_badge = "🟠 À vérifier"

    msg = (
        f"{fire} {country_flag} <b>{result['brand_name'].upper()}</b>\n\n"
        f"👕 <b>{title}</b>\n\n"
        f"💰 Prix demandé   : <b>{result['price']}€</b>\n"
        f"🏷️ Prix boutique  : ~{result['retail_price']}€\n"
        f"💵 Revente estimée: ~{result['resell_value']:.0f}€\n"
        f"📈 Ratio          : <b>x{result['ratio']}</b>\n"
        f"🤑 Gain net       : <b>+{result['net_gain']:.0f}€</b>\n\n"
        f"📐 Taille : {result['size']} | État : {result['condition']}\n"
        f"📍 {result['city']}\n\n"
        f"{profile_badge} ({seller_score}/100)\n"
        f"👤 <a href=\"{s_url}\">{s_name}</a> — {seller_reason}\n\n"
        f"👉 <a href=\"{url}\">VOIR L'ANNONCE</a>\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    return msg

# ── Boucle principale ─────────────────────────────────────
seen_ids = set()

def scan_country(country_name, base_url):
    found = 0
    flag  = country_name.split()[0]  # Ex: "🇫🇷"

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

                seller    = item.get("user", {})
                seller_id = seller.get("id")
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
                    f"{result['brand_name']} | {item.get('title','?')[:35]} | "
                    f"{result['price']}€ → ~{result['resell_value']:.0f}€ "
                    f"(x{result['ratio']}) | +{result['net_gain']:.0f}€ | {score}/100"
                )
                found += 1
                time.sleep(1)

            time.sleep(1.5)
    return found

def main():
    print("=" * 62)
    print("   VINTED ALERT BOT — MULTI-PAYS")
    print(f"   Pays       : {', '.join([c.split()[0] for c in VINTED_COUNTRIES])}")
    print(f"   Ratio min  : x{RATIO_MIN} | Gain min : +{MIN_GAIN}€")
    print(f"   Revente    : 50% prix boutique × coeff état")
    print(f"   Marques    : {len(BRANDS)}")
    print("=" * 62)

    init_all_sessions()

    send_telegram(
        f"🤖 <b>Vinted Bot — Multi-Pays activé !</b>\n\n"
        f"🌍 Pays scannés : FR 🇫🇷 BE 🇧🇪 NL 🇳🇱 ES 🇪🇸 DE 🇩🇪 IT 🇮🇹\n"
        f"⚙️ Ratio : x{RATIO_MIN} | Gain min : +{MIN_GAIN}€\n"
        f"👤 Filtre vendeur actif\n"
        f"📦 {len(BRANDS)} marques surveillées\n\n"
        f"🟢 En chasse sur 6 pays..."
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
            print(f"  {country_name} → {found} alerte(s)")
            time.sleep(3)
        print(f"\n══ FIN #{cycle} ══ {total} alerte(s) total | Cache : {len(seller_cache)} vendeurs | Prochain dans {CHECK_INTERVAL}s")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
