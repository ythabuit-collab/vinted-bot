import requests
import time
import json
from datetime import datetime

TELEGRAM_TOKEN    = "8611988792:AAGOJ7xDWPRJveS0jOe71NH5rWczdKwPUgI"
TELEGRAM_CHAT_ID  = "8559815820"

BUDGET_MAX      = 60
RATIO_MIN       = 4.0
CHECK_INTERVAL  = 55
MIN_GAIN        = 50

CONDITION_COEFFS = {
    "neuf avec etiquette" : 1.00,
    "neuf sans etiquette" : 0.90,
    "tres bon etat"       : 0.75,
    "bon etat"            : 0.60,
    "satisfaisant"        : 0.40,
    "neuf"                : 0.95,
    "tres bon"            : 0.75,
    "bon"                 : 0.60,
    "default"             : 0.65,
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
            "sneaker": 800, "tshirt": 400, "polo": 500,
            "pull": 900, "veste": 1800, "casquette": 350,
            "portefeuille": 500, "ceinture": 450,
        }
    },
    "Burberry": {
        "keywords": ["burberry"],
        "min_price": 12,
        "retail": {
            "trench": 2000, "veste": 1200, "manteau": 1800,
            "pull": 600, "chemise": 500, "polo": 400,
            "tshirt": 300, "echarpe": 500, "sac": 1200,
            "hoodie": 600, "casquette": 300,
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
            "ceinture": 450, "portefeuille": 600,
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
        "keywords": ["sezane", "sÃ©zane"],
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

FAKE_SIGNALS = ["replica", "rep", "aaa", "inspired", "no name"]

VINTED_SESSION = requests.Session()
VINTED_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Origin": "https://www.vinted.fr",
    "Referer": "https://www.vinted.fr/",
})

def init_vinted_session():
    try:
        VINTED_SESSION.get("https://www.vinted.fr", timeout=10)
        return True
    except Exception as e:
        print(f"[ERREUR] Session : {e}")
        return False

def search_vinted(keyword, max_price=None):
    params = {"search_text": keyword, "order": "newest_first", "per_page": 48, "currency": "EUR"}
    if max_price:
        params["price_to"] = max_price
    try:
        r = VINTED_SESSION.get("https://www.vinted.fr/api/v2/catalog/items", params=params, timeout=12)
        if r.status_code == 200:
            return r.json().get("items", [])
        elif r.status_code == 401:
            init_vinted_session()
        return []
    except Exception as e:
        print(f"  [Vinted] '{keyword}' : {e}")
        return []

def get_condition_coeff(condition_str):
    if not condition_str:
        return CONDITION_COEFFS["default"]
    c = condition_str.lower()
    for key, coeff in CONDITION_COEFFS.items():
        if key in c:
            return coeff
    return CONDITION_COEFFS["default"]

def estimate_resell_value(title, description, brand_data):
    text = (title + " " + (description or "")).lower()
    best_retail = 0
    best_match  = None
    for model_key, retail_price in brand_data["retail"].items():
        words = model_key.split()
        if all(w in text for w in words) and retail_price > best_retail:
            best_retail = retail_price
            best_match  = model_key
    if best_retail == 0:
        vals = sorted(brand_data["retail"].values())
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
        print(f"  [ERREUR] : {e}")
        return None

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

def format_alert(item, result):
    title   = item.get("title", "Sans titre")
    url     = f"https://www.vinted.fr/items/{item.get('id', '')}"
    fire    = "ð¥" * min(int(result["ratio"]), 5)
    msg = (
        f"{fire} <b>{result['brand_name'].upper()}</b>\n\n"
        f"ð <b>{title}</b>\n\n"
        f"ð° Prix demandÃ©   : <b>{result['price']}â¬</b>\n"
        f"ð·ï¸ Prix boutique  : ~{result['retail_price']}â¬\n"
        f"ðµ Revente estimÃ©e: ~{result['resell_value']:.0f}â¬\n"
        f"ð Ratio          : <b>x{result['ratio']}</b>\n"
        f"ð¤ Gain net       : <b>+{result['net_gain']:.0f}â¬</b>\n\n"
        f"ð Taille : {result['size']} | Ãtat : {result['condition']}\n"
        f"ð {result['city']}\n\n"
        f"ð <a href=\"{url}\">VOIR L'ANNONCE</a>\n"
        f"â° {datetime.now().strftime('%H:%M:%S')}"
    )
    return msg

seen_ids = set()

def scan_all():
    found = 0
    for brand_name, brand_data in BRANDS.items():
        for keyword in brand_data["keywords"]:
            items = search_vinted(keyword, max_price=BUDGET_MAX)
            for item in items:
                item_id = item.get("id")
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                result = evaluate_item(item, brand_name, brand_data)
                if not result:
                    continue
                photos    = item.get("photos", [])
                photo_url = photos[0].get("url") or photos[0].get("full_size_url") if photos else None
                send_telegram(format_alert(item, result), photo_url=photo_url)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ð¥ {result['brand_name']} | {item.get('title','?')[:40]} | {result['price']}â¬ â ~{result['resell_value']:.0f}â¬ (x{result['ratio']}) | +{result['net_gain']:.0f}â¬")
                found += 1
                time.sleep(1)
        time.sleep(2)
    return found

def main():
    print("=" * 55)
    print("   VINTED ALERT BOT â MODE STRICT")
    print(f"   Ratio min : x{RATIO_MIN} | Gain min : +{MIN_GAIN}â¬")
    print(f"   Revente   : 50% prix boutique Ã coeff Ã©tat")
    print(f"   Marques   : {len(BRANDS)}")
    print("=" * 55)
    init_vinted_session()
    send_telegram(
        f"ð¤ <b>Vinted Bot â Mode Strict activÃ©</b>\n\n"
        f"âï¸ Ratio min : x{RATIO_MIN} | Gain min : +{MIN_GAIN}â¬\n"
        f"ðµ Revente = 50% prix boutique\n"
        f"â Bottega, Gucci, Balenciaga, Prada, Dior, LV, Burberry...\n\n"
        f"ð¢ En chasse..."
    )
    cycle = 0
    while True:
        cycle += 1
        print(f"\nââ SCAN #{cycle} ââ {datetime.now().strftime('%H:%M:%S')} ââ")
        found = scan_all()
        print(f"ââ FIN #{cycle} ââ {found} alerte(s) | Prochain dans {CHECK_INTERVAL}s")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
