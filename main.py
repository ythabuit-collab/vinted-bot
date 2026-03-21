"""
╔═══════════════════════════════════════════════════════════════════╗
║          VINTED ALERT BOT v3 — ULTIMATE EDITION                   ║
║  Détection multi-couche : prix marché réel × état × tier marque   ║
║  Vision IA + scoring avancé + filtres anti-contrefaçon            ║
╚═══════════════════════════════════════════════════════════════════╝
 
INSTALLATION :
  pip install requests
 
CONFIGURATION :
  1. Crée un bot Telegram via @BotFather → /newbot → copie le TOKEN
  2. Envoie un msg à ton bot puis :
     https://api.telegram.org/bot<TOKEN>/getUpdates → copie l'id
  3. Clé Anthropic sur console.anthropic.com → API Keys
  4. Remplis les 3 variables ci-dessous
  5. Lance : python vinted_alert_v3.py
"""
 
import requests
import time
import base64
import json
import re
from datetime import datetime
 
# ════════════════════════════════════════════════════════════
#  ⚙️  CONFIGURATION
# ════════════════════════════════════════════════════════════
 
TELEGRAM_TOKEN    = "8611988792:AAGOJ7xDWPRJveS0jOe71NH5rWczdKwPUgI"
TELEGRAM_CHAT_ID  = "8559815820"
ANTHROPIC_API_KEY = ""
 
BUDGET_MAX       = 60     # Prix max accepté (€)
RATIO_MIN        = 2.0    # Ratio min valeur_réelle / prix_annonce
CHECK_INTERVAL   = 55     # Secondes entre chaque scan
VISION_ENABLED   = True   # Reconnaissance visuelle par IA
MIN_GAIN         = 20     # Gain net minimum après frais Vinted (€)
 
# ════════════════════════════════════════════════════════════
#  📊  COEFFICIENTS D'ÉTAT (appliqués à la valeur de revente)
#  Source : données réelles Vinted/eBay/Vestiaire
# ════════════════════════════════════════════════════════════
 
CONDITION_COEFFS = {
    # Clé Vinted          : (coeff_valeur_marché, coeff_revente)
    "neuf avec étiquette" : (1.00, 0.90),   # Neuf = valeur pleine, revente facile
    "neuf sans étiquette" : (0.90, 0.82),
    "très bon état"       : (0.75, 0.70),
    "bon état"            : (0.60, 0.55),
    "satisfaisant"        : (0.40, 0.35),
    # Fallbacks
    "neuf"                : (0.95, 0.87),
    "très bon"            : (0.75, 0.70),
    "bon"                 : (0.60, 0.55),
    "default"             : (0.65, 0.58),
}
 
# ════════════════════════════════════════════════════════════
#  🏷️  TIERS DE MARQUES
#  Définit le niveau de prix et la liquidité sur le marché
# ════════════════════════════════════════════════════════════
 
BRAND_TIERS = {
    # TIER 1 — Luxe : valeur élevée, niche, clients exigeants
    # Prix plancher d'achat conseillé : >15€ (en dessous = suspect)
    "tier1_luxury": {
        "brands": ["Moncler", "Canada Goose", "CP Company", "Stone Island", "Jacquemus", "Ami Paris"],
        "min_credible_price": 20,   # En dessous = probable contrefaçon
        "resell_platform": "Vestiaire Collective, eBay",
        "liquidity": "moyenne",
        "margin_target": 60,        # % de marge visé
    },
    # TIER 2 — Premium : forte demande, bonne liquidité
    "tier2_premium": {
        "brands": ["Ralph Lauren", "Lacoste", "Tommy Hilfiger", "A.P.C.", "Sézane", "Zadig & Voltaire", "Barbour", "Patagonia"],
        "min_credible_price": 8,
        "resell_platform": "Vinted, eBay, Depop",
        "liquidity": "bonne",
        "margin_target": 50,
    },
    # TIER 3 — Streetwear premium : très liquide, clientèle large
    "tier3_street": {
        "brands": ["Nike / Jordan", "Adidas", "The North Face", "Carhartt / WIP", "Stone Island"],
        "min_credible_price": 5,
        "resell_platform": "Vinted, StockX, Depop",
        "liquidity": "très bonne",
        "margin_target": 45,
    },
    # TIER 4 — Casual premium : volume élevé, marges correctes
    "tier4_casual": {
        "brands": ["Levis", "Wrangler", "Lee", "Dickies", "Timberland"],
        "min_credible_price": 3,
        "resell_platform": "Vinted, eBay",
        "liquidity": "très bonne",
        "margin_target": 40,
    },
}
 
def get_brand_tier(brand_name):
    for tier_id, tier_data in BRAND_TIERS.items():
        if brand_name in tier_data["brands"]:
            return tier_id, tier_data
    return "tier4_casual", BRAND_TIERS["tier4_casual"]
 
# ════════════════════════════════════════════════════════════
#  🏷️  BASE DE PRIX PAR MARQUE, MODÈLE & ÉTAT
#  Prix = valeur neuf boutique (on applique ensuite les coefficients état)
# ════════════════════════════════════════════════════════════
 
BRANDS = {
 
    # ── LUXE ────────────────────────────────────────────────
    "Moncler": {
        "keywords": ["moncler"],
        "min_price": 20,
        "items": {
            "doudoune maya":      900,  "doudoune ever":      800,
            "doudoune":           850,  "gilet":              600,
            "veste":              700,  "pull":               350,
            "hoodie":             380,  "tshirt":             180,
            "polo":               200,  "bonnet":             130,
            "casquette":          140,  "écharpe":            200,
        }
    },
 
    "Canada Goose": {
        "keywords": ["canada goose"],
        "min_price": 20,
        "items": {
            "expedition":        1200,  "chilliwack":         900,
            "parka":              800,  "doudoune":           700,
            "veste":              600,  "gilet":              400,
            "pull":               250,  "tshirt":             120,
            "bonnet":             100,
        }
    },
 
    "CP Company": {
        "keywords": ["cp company", "c.p. company", "c.p company"],
        "min_price": 15,
        "items": {
            "goggle jacket":      700,  "metropolis":         800,
            "veste shell":        600,  "veste":              500,
            "hoodie goggle":      400,  "hoodie":             350,
            "sweat":              280,  "tshirt":             150,
            "polo":               160,  "bonnet":             110,
            "lunette":            100,  "pantalon":           250,
        }
    },
 
    "Stone Island": {
        "keywords": ["stone island", "stone"],
        "min_price": 15,
        "items": {
            "ghost piece":        600,  "shadow project":     700,
            "veste membrana":     500,  "veste softshell":    450,
            "veste":              400,  "hoodie":             300,
            "sweat":              250,  "pull":               220,
            "polo":               160,  "tshirt":             140,
            "cargo":              260,  "pantalon":           230,
            "bonnet":             100,  "badge":              50,
        }
    },
 
    "Jacquemus": {
        "keywords": ["jacquemus", "le chiquito", "le bambino", "la bomba"],
        "min_price": 10,
        "items": {
            "le chiquito":        550,  "le bambino":         500,
            "la bomba":           250,  "sac":                400,
            "chemise":            250,  "robe":               300,
            "pull":               250,  "veste":              400,
            "casquette":          100,  "tshirt":             120,
            "jean":               200,
        }
    },
 
    "Ami Paris": {
        "keywords": ["ami paris", "ami alexandre", "ami de coeur"],
        "min_price": 15,
        "items": {
            "pull coeur":         300,  "hoodie coeur":       350,
            "sweat coeur":        300,  "tshirt coeur":       150,
            "pull":               280,  "hoodie":             320,
            "chemise":            220,  "veste":              450,
            "manteau":            600,  "jean":               250,
            "sac":                350,  "tshirt":             130,
        }
    },
 
    # ── PREMIUM ─────────────────────────────────────────────
    "Ralph Lauren": {
        "keywords": ["ralph lauren", "polo ralph", "polo sport", "purple label", "rrl", "polo bear", "double rl"],
        "min_price": 5,
        "items": {
            "purple label veste": 600,  "purple label pull":  400,
            "rrl veste":          350,  "rrl chemise":        200,
            "polo bear":          180,  "polo 100% coton":    120,
            "polo mesh":          100,  "polo sport":         90,
            "chemise oxford":     120,  "chemise":            110,
            "hoodie":             180,  "sweat":              150,
            "pull lambswool":     180,  "pull":               140,
            "veste":              300,  "blouson":            350,
            "manteau":            500,  "doudoune":           350,
            "jean":               110,  "pantalon chino":     120,
            "tshirt":             70,   "casquette":          65,
            "écharpe":            80,
        }
    },
 
    "Lacoste": {
        "keywords": ["lacoste", "lacoste sport", "lacoste live"],
        "min_price": 5,
        "items": {
            "polo l1212":         120,  "polo slim":          100,
            "polo sport":         90,   "polo":               95,
            "chemise":            110,  "hoodie":             140,
            "sweat":              120,  "veste":              200,
            "blouson":            250,  "manteau":            350,
            "tshirt":             70,   "casquette":          55,
            "sneaker court":      110,  "sneaker":            100,
            "sac":                90,   "bermuda":            80,
        }
    },
 
    "Tommy Hilfiger": {
        "keywords": ["tommy hilfiger", "tommy jeans", "hilfiger denim"],
        "min_price": 4,
        "items": {
            "polo flag":          100,  "polo":               85,
            "chemise":            95,   "hoodie":             110,
            "sweat":              95,   "veste":              170,
            "blouson":            200,  "pull":               100,
            "doudoune":           250,  "tshirt":             55,
            "jean":               95,   "casquette":          50,
        }
    },
 
    "A.P.C.": {
        "keywords": ["apc", "a.p.c.", "a.p.c", "atelier production creation"],
        "min_price": 10,
        "items": {
            "jean new standard":  200,  "jean petit standard": 200,
            "jean":               190,  "veste":              300,
            "manteau":            500,  "pull":               220,
            "hoodie":             230,  "chemise":            180,
            "tshirt":             90,   "sac demi lune":      350,
            "sac":                300,  "blouson":            350,
        }
    },
 
    "Sézane": {
        "keywords": ["sezane", "sézane"],
        "min_price": 5,
        "items": {
            "robe":               140,  "chemise":            120,
            "pull mohair":        160,  "pull":               130,
            "veste":              200,  "manteau":            350,
            "jean":               120,  "tshirt":             65,
            "top":                70,   "sac":                180,
            "blazer":             230,  "jupe":               100,
        }
    },
 
    "Zadig & Voltaire": {
        "keywords": ["zadig", "zadig voltaire", "zadig & voltaire", "z&v"],
        "min_price": 8,
        "items": {
            "perfecto":           500,  "blouson":            450,
            "veste":              350,  "pull":               230,
            "hoodie":             200,  "chemise":            180,
            "robe":               250,  "tshirt":             90,
            "jean":               180,  "sac":                300,
            "casquette":          70,
        }
    },
 
    "Barbour": {
        "keywords": ["barbour", "barbour international"],
        "min_price": 8,
        "items": {
            "bedale":             350,  "beaufort":           380,
            "international":      320,  "ashby":              300,
            "ciré":               300,  "veste":              280,
            "blouson":            300,  "pull":               180,
            "chemise":            120,  "casquette":          70,
        }
    },
 
    "Patagonia": {
        "keywords": ["patagonia"],
        "min_price": 5,
        "items": {
            "better sweater":     180,  "retro pile":         200,
            "fleece":             160,  "synchilla":          150,
            "doudoune nano puff": 280,  "doudoune":           260,
            "veste":              230,  "pull":               150,
            "tshirt":             55,   "sac":                110,
            "casquette":          45,
        }
    },
 
    # ── STREETWEAR ──────────────────────────────────────────
    "Nike / Jordan": {
        "keywords": ["nike", "jordan", "air max", "dunk", "air force", "travis scott nike", "off white nike"],
        "min_price": 3,
        "items": {
            "jordan 1 retro high": 280, "jordan 1 low":       180,
            "jordan 3":            250, "jordan 4":           300,
            "jordan 11":           320, "jordan 6":           260,
            "dunk low":            200, "dunk high":          210,
            "air max 1":           150, "air max 90":         130,
            "air max 95":          160, "air max 97":         150,
            "air force 1":         110, "sb dunk":            200,
            "tech fleece veste":   120, "tech fleece":        100,
            "acg":                 120, "veste":              90,
            "hoodie":              70,  "sweat":              65,
            "tshirt":              40,  "short":              45,
            "casquette":           35,
        }
    },
 
    "Adidas": {
        "keywords": ["adidas", "yeezy", "superstar", "gazelle", "samba", "spezial", "originals", "adidas originals"],
        "min_price": 3,
        "items": {
            "yeezy 350 v2":       220,  "yeezy 700":          200,
            "yeezy slide":        90,   "yeezy foam runner":  100,
            "samba og":           130,  "gazelle":            110,
            "superstar":          100,  "campus":             110,
            "handball spezial":   120,  "forum low":          110,
            "forum high":         120,  "sl72":               120,
            "veste":              80,   "hoodie":             65,
            "sweat":              60,   "tshirt":             35,
            "short":              40,   "casquette":          35,
        }
    },
 
    "The North Face": {
        "keywords": ["north face", "the north face", "tnf"],
        "min_price": 4,
        "items": {
            "nuptse 700":         280,  "nuptse":             260,
            "supreme tnf":        350,  "steep tech":         400,
            "brown label":        300,  "veste gore-tex":     250,
            "veste":              180,  "doudoune":           200,
            "fleece":             130,  "pull":               110,
            "tshirt":             55,   "sac":                90,
            "casquette":          45,   "bonnet":             40,
        }
    },
 
    "Carhartt / WIP": {
        "keywords": ["carhartt", "carhartt wip", "wip"],
        "min_price": 3,
        "items": {
            "detroit jacket":     200,  "michigan jacket":    190,
            "active jacket":      180,  "og santa fe":        220,
            "veste":              160,  "hoodie":             100,
            "sweat chase":        90,   "sweat":              80,
            "work pant":          100,  "double knee":        120,
            "salopette":          140,  "chemise":            80,
            "tshirt":             55,   "bonnet":             40,
            "casquette":          45,
        }
    },
 
    # ── DENIM ───────────────────────────────────────────────
    "Levis": {
        "keywords": ["levis", "levi's", "levi strauss", "501", "levis vintage"],
        "min_price": 3,
        "items": {
            "501 vintage":        180,  "501 made in usa":    150,
            "501 90s":            120,  "501":                100,
            "502":                90,   "511":                90,
            "512":                90,   "517 bootcut":        120,
            "trucker vintage":    150,  "trucker":            110,
            "veste sherpa":       130,  "veste":              110,
            "jean":               90,   "chemise":            75,
            "hoodie":             85,   "tshirt":             45,
        }
    },
 
    "Dickies": {
        "keywords": ["dickies"],
        "min_price": 3,
        "items": {
            "eisenhower":         90,   "veste":              80,
            "salopette":          85,   "work pant 874":      75,
            "pantalon":           65,   "chemise":            55,
            "hoodie":             65,   "tshirt":             35,
        }
    },
 
    "Wrangler": {
        "keywords": ["wrangler"],
        "min_price": 3,
        "items": {
            "jean 11mwz":         120,  "jean vintage":       100,
            "jean":               80,   "veste":              95,
            "chemise":            60,   "salopette":          90,
        }
    },
 
    "Lee": {
        "keywords": ["lee cooper", "lee riders", "lee jeans"],
        "min_price": 3,
        "items": {
            "101 vintage":        120,  "jean vintage":       100,
            "jean":               75,   "veste":              90,
            "chemise":            55,
        }
    },
 
    "Timberland": {
        "keywords": ["timberland"],
        "min_price": 4,
        "items": {
            "boot 6 inch":        180,  "boot":               160,
            "veste":              130,  "pull":               80,
            "tshirt":             45,   "casquette":          40,
        }
    },
}
 
# ════════════════════════════════════════════════════════════
#  🚨  MOTS-CLÉS SUSPECTS (signaux de contrefaçon)
# ════════════════════════════════════════════════════════════
 
FAKE_SIGNALS = [
    "inspired", "style", "replica", "rep", "aaa", "qualité", "comme",
    "similaire", "type", "marque inconnue", "no name", "sans marque"
]
 
# ════════════════════════════════════════════════════════════
#  📡  SESSION VINTED
# ════════════════════════════════════════════════════════════
 
VINTED_SESSION = requests.Session()
VINTED_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Origin": "https://www.vinted.fr",
    "Referer": "https://www.vinted.fr/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
})
 
def init_vinted_session():
    try:
        r = VINTED_SESSION.get("https://www.vinted.fr", timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[ERREUR] Session Vinted : {e}")
        return False
 
def search_vinted(keyword, max_price=None, order="newest_first"):
    params = {
        "search_text": keyword,
        "order": order,
        "per_page": 48,
        "currency": "EUR",
    }
    if max_price:
        params["price_to"] = max_price
    try:
        r = VINTED_SESSION.get(
            "https://www.vinted.fr/api/v2/catalog/items",
            params=params,
            timeout=12
        )
        if r.status_code == 200:
            return r.json().get("items", [])
        elif r.status_code == 401:
            init_vinted_session()
            time.sleep(2)
        return []
    except Exception as e:
        print(f"  [Vinted] Erreur '{keyword}' : {e}")
        return []
 
# ════════════════════════════════════════════════════════════
#  🤖  VISION IA — Claude analyse la photo
# ════════════════════════════════════════════════════════════
 
def download_image_b64(url):
    try:
        r = requests.get(url, timeout=8, stream=True)
        if r.status_code == 200:
            content_type = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
            return base64.b64encode(r.content).decode("utf-8"), content_type
    except:
        pass
    return None, None
 
def vision_analyze(image_url, title, description, price):
    """
    Analyse visuelle de l'article via Claude.
    Retourne un dict avec brand, confidence, market_value, is_fake, item_type.
    """
    if not image_url:
        return None
 
    img_b64, media_type = download_image_b64(image_url)
    if not img_b64:
        return None
 
    brands_list = "\n".join([f"- {b}" for b in BRANDS.keys()])
 
    prompt = f"""Tu es un expert authenticité & mode — spécialiste de la revente de vêtements de marque.
 
IMAGE : article vendu {price}€ sur Vinted France
TITRE : "{title}"
DESCRIPTION : "{description[:300] if description else 'non fournie'}"
 
MISSION :
1. Identifie la marque (logo, étiquette, coupe, détails)
2. Identifie le type précis d'article
3. Évalue l'authenticité (contrefaçon probable ?)
4. Estime la valeur marché pour cet article spécifique
 
MARQUES À SURVEILLER (priorité) :
{brands_list}
 
Réponds UNIQUEMENT en JSON strict, sans markdown :
{{
  "brand": "nom exact ou null",
  "confidence": 0.85,
  "item_type": "hoodie / veste / jean / etc",
  "item_model": "modèle précis si identifiable ou null",
  "condition_visible": "neuf / très bon / bon / usé",
  "is_likely_fake": false,
  "fake_signals": [],
  "estimated_market_value": 150,
  "reasoning": "Explication 1 ligne"
}}
 
RÈGLES :
- confidence : 0.0 à 1.0 (sois conservateur, mets 0.5 si doute)
- estimated_market_value : prix de vente moyen occasion TRÈS BON ÉTAT sur Vinted/eBay
- is_likely_fake : true si coutures douteuses, logos flous/déformés, étiquette suspecte
- fake_signals : liste des éléments suspects visuels"""
 
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-opus-4-5",
                "max_tokens": 400,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img_b64,
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }]
            },
            timeout=20
        )
 
        if response.status_code == 200:
            raw = response.json()["content"][0]["text"].strip()
            # Nettoyage robuste du JSON
            raw = re.sub(r"```json|```", "", raw).strip()
            return json.loads(raw)
 
    except json.JSONDecodeError as e:
        print(f"  [Vision] JSON invalide : {e}")
    except Exception as e:
        print(f"  [Vision] Erreur : {e}")
 
    return None
 
# ════════════════════════════════════════════════════════════
#  🧠  MOTEUR D'ÉVALUATION AVANCÉ
# ════════════════════════════════════════════════════════════
 
def get_condition_coeff(condition_str):
    """Retourne le coefficient d'état depuis le texte Vinted."""
    if not condition_str:
        return CONDITION_COEFFS["default"]
    condition_lower = condition_str.lower()
    for key, coeffs in CONDITION_COEFFS.items():
        if key in condition_lower:
            return coeffs
    return CONDITION_COEFFS["default"]
 
def estimate_from_catalog(title, description, brand_data):
    """Estime la valeur depuis la base de prix interne."""
    text = (title + " " + (description or "")).lower()
    best_value = 0
    best_match = None
    best_specificity = 0
 
    for model_key, value in brand_data["items"].items():
        words = model_key.split()
        matches = sum(1 for w in words if w in text)
        specificity = matches / len(words)
 
        if matches == len(words) and specificity > best_specificity:
            best_value = value
            best_match = model_key
            best_specificity = specificity
 
    # Fallback : valeur médiane
    if best_value == 0:
        vals = sorted(brand_data["items"].values())
        best_value = vals[len(vals) // 2]
        best_match = "référence médiane"
 
    return best_value, best_match
 
def detect_fake_in_text(title, description):
    """Détecte des signaux de contrefaçon dans le texte."""
    text = (title + " " + (description or "")).lower()
    found = [sig for sig in FAKE_SIGNALS if sig in text]
    return found
 
def evaluate_item(item, brand_name, brand_data):
    """
    Évaluation complète d'un article.
    Retourne un dict détaillé ou None si pas intéressant.
    """
    try:
        # ── Prix & données de base ──
        price_data  = item.get("price", {})
        price       = float(price_data.get("amount", 0))
        title       = item.get("title", "")
        description = item.get("description", "")
        condition   = item.get("status", "")
        size        = item.get("size_title", "?")
        city        = item.get("city", "?")
 
        # Filtres de base
        if price == 0 or price > BUDGET_MAX:
            return None
 
        # Filtre prix minimum crédible (anti-contrefaçon)
        min_price = brand_data.get("min_price", 3)
        if price < min_price:
            return None  # Trop suspect pour cette marque
 
        # Détection fake textuelle
        fake_signals_text = detect_fake_in_text(title, description)
 
        # ── Évaluation textuelle ──
        base_value, matched_model = estimate_from_catalog(title, description, brand_data)
 
        # Application du coefficient d'état
        cond_coeff_value, cond_coeff_resell = get_condition_coeff(condition)
        adjusted_value  = base_value * cond_coeff_value     # Valeur ajustée à l'état
        resell_value    = base_value * cond_coeff_resell     # Prix de revente réaliste
 
        text_ratio = round(adjusted_value / price, 2) if price > 0 else 0
 
        # ── Vision IA ──
        vision_result = None
        is_vague      = len(title.split()) <= 4 or price < brand_data.get("min_price", 3) * 3
 
        # On lance la vision si ratio prometteur ou titre vague
        if VISION_ENABLED and (text_ratio >= 1.5 or is_vague):
            photos = item.get("photos", [])
            if photos:
                img_url = (
                    photos[0].get("url") or
                    photos[0].get("full_size_url") or
                    photos[0].get("high_resolution", {}).get("url")
                )
                if img_url:
                    print(f"  [Vision] {title[:45]}...")
                    vision_result = vision_analyze(img_url, title, description, price)
 
        # ── Fusion texte + vision ──
        final_value    = adjusted_value
        final_resell   = resell_value
        detection_info = f"texte ({matched_model})"
        is_fake        = len(fake_signals_text) >= 2
 
        if vision_result:
            v_brand  = vision_result.get("brand")
            v_conf   = float(vision_result.get("confidence", 0))
            v_value  = float(vision_result.get("estimated_market_value", 0))
            v_fake   = vision_result.get("is_likely_fake", False)
            v_model  = vision_result.get("item_model", "")
            v_type   = vision_result.get("item_type", "")
            v_cond   = vision_result.get("condition_visible", "")
 
            # Contrefaçon détectée → on rejette
            if v_fake and v_conf >= 0.75:
                return None
 
            # La vision confirme ou améliore l'estimation
            if v_conf >= 0.70 and v_value > 0:
                # On prend la moyenne pondérée (vision = 60%, texte = 40%)
                final_value  = round(v_value * 0.6 + adjusted_value * 0.4, 0)
                final_resell = round(final_value * cond_coeff_resell, 0)
                model_str    = v_model or v_type or matched_model
                detection_info = f"Vision IA ({v_brand or brand_name}, {int(v_conf*100)}%, {model_str})"
 
            # La vision détecte une marque différente → on adapte
            if v_brand and v_brand != brand_name and v_conf >= 0.80 and v_brand in BRANDS:
                alt_brand_data  = BRANDS[v_brand]
                alt_value, _    = estimate_from_catalog(title, description, alt_brand_data)
                if alt_value > final_value:
                    final_value    = alt_value * cond_coeff_value
                    final_resell   = alt_value * cond_coeff_resell
                    brand_name     = v_brand
                    detection_info += f" [→ reclassé {v_brand}]"
 
        # ── Score final ──
        final_ratio = round(final_value / price, 2) if price > 0 else 0
 
        if final_ratio < RATIO_MIN:
            return None
 
        # Frais Vinted : ~5% + 0.70€ sur le prix de vente
        vinted_fees  = round(final_resell * 0.05 + 0.70, 2)
        net_gain     = round(final_resell - price - vinted_fees, 0)
 
        if net_gain < MIN_GAIN:
            return None
 
        # Tier de la marque
        tier_id, tier_data = get_brand_tier(brand_name)
 
        return {
            "brand_name":       brand_name,
            "price":            price,
            "base_value":       base_value,
            "adjusted_value":   final_value,
            "resell_value":     final_resell,
            "net_gain":         net_gain,
            "ratio":            final_ratio,
            "matched_model":    matched_model,
            "detection_info":   detection_info,
            "condition":        condition,
            "size":             size,
            "city":             city,
            "is_fake_risk":     is_fake,
            "tier":             tier_id,
            "resell_platform":  tier_data["resell_platform"],
            "vision":           vision_result,
        }
 
    except Exception as e:
        print(f"  [ERREUR] evaluate_item : {e}")
        return None
 
# ════════════════════════════════════════════════════════════
#  📲  TELEGRAM
# ════════════════════════════════════════════════════════════
 
def send_telegram(message, photo_url=None):
    base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    if photo_url:
        payload  = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": photo_url,
            "caption": message[:1024],
            "parse_mode": "HTML",
        }
        endpoint = f"{base}/sendPhoto"
    else:
        payload  = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        endpoint = f"{base}/sendMessage"
    try:
        r = requests.post(endpoint, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[ERREUR] Telegram : {e}")
        return False
 
TIER_EMOJI = {
    "tier1_luxury":  "💎",
    "tier2_premium": "⭐",
    "tier3_street":  "🔥",
    "tier4_casual":  "✅",
}
 
def format_alert(item, eval_result):
    title    = item.get("title", "Sans titre")
    item_id  = item.get("id", "")
    url      = f"https://www.vinted.fr/items/{item_id}"
 
    price         = eval_result["price"]
    adjusted_val  = eval_result["adjusted_value"]
    resell_val    = eval_result["resell_value"]
    net_gain      = eval_result["net_gain"]
    ratio         = eval_result["ratio"]
    brand_name    = eval_result["brand_name"]
    condition     = eval_result["condition"] or "?"
    size          = eval_result["size"]
    city          = eval_result["city"]
    detection     = eval_result["detection_info"]
    tier          = eval_result["tier"]
    platforms     = eval_result["resell_platform"]
    fake_risk     = eval_result["is_fake_risk"]
 
    tier_icon = TIER_EMOJI.get(tier, "✅")
    fire      = "🔥" * min(int(ratio), 5)
 
    fake_warning = "\n⚠️ <b>Vérifier l'authenticité avant achat</b>" if fake_risk else ""
 
    msg = (
        f"{fire} {tier_icon} <b>{brand_name.upper()} — BONNE AFFAIRE</b>\n\n"
        f"👕 <b>{title}</b>\n\n"
        f"💰 Prix demandé    : <b>{price}€</b>\n"
        f"📊 Valeur estimée  : ~{adjusted_val:.0f}€\n"
        f"💵 Prix revente    : ~{resell_val:.0f}€\n"
        f"📈 Ratio           : <b>x{ratio}</b>\n"
        f"🤑 Gain net estimé : <b>+{net_gain:.0f}€</b>\n\n"
        f"📐 Taille : {size} | État : {condition}\n"
        f"📍 {city}\n"
        f"🔍 Détection : {detection}\n"
        f"🛒 Revendre sur : {platforms}"
        f"{fake_warning}\n\n"
        f"👉 <a href=\"{url}\">VOIR L'ANNONCE</a>\n"
        f"⏰ {datetime.now().strftime('%H:%M:%S')}"
    )
    return msg
 
# ════════════════════════════════════════════════════════════
#  🔄  BOUCLE PRINCIPALE
# ════════════════════════════════════════════════════════════
 
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
 
                # Photo pour Telegram
                photos    = item.get("photos", [])
                photo_url = None
                if photos:
                    photo_url = (
                        photos[0].get("url") or
                        photos[0].get("full_size_url")
                    )
 
                msg = format_alert(item, result)
                send_telegram(msg, photo_url=photo_url)
 
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"{TIER_EMOJI.get(result['tier'],'✅')} {result['brand_name']} | "
                    f"{item.get('title','?')[:40]} | "
                    f"{result['price']}€ → ~{result['resell_value']:.0f}€ "
                    f"(x{result['ratio']}) | +{result['net_gain']:.0f}€ net"
                )
                found += 1
                time.sleep(1.2)
 
            time.sleep(2.5)
 
    return found
 
# ════════════════════════════════════════════════════════════
#  🚀  MAIN
# ════════════════════════════════════════════════════════════
 
def main():
    print("=" * 70)
    print("   VINTED ALERT BOT v3 — ULTIMATE EDITION")
    print(f"   Budget      : 0 – {BUDGET_MAX}€")
    print(f"   Ratio min   : x{RATIO_MIN}")
    print(f"   Gain min    : +{MIN_GAIN}€ net")
    print(f"   Vision IA   : {'✅ Activée' if VISION_ENABLED else '❌ Désactivée'}")
    print(f"   Marques     : {len(BRANDS)} marques | {sum(len(v['items']) for v in BRANDS.values())} références prix")
    print(f"   Intervalle  : {CHECK_INTERVAL}s")
    print("=" * 70)
 
    # Vérification config
    if "COLLE" in TELEGRAM_TOKEN:
        print("\n❌  Configure TELEGRAM_TOKEN + TELEGRAM_CHAT_ID + ANTHROPIC_API_KEY\n")
        print("   Telegram :")
        print("     1. @BotFather → /newbot → copie le token")
        print("     2. Envoie un msg à ton bot puis va sur :")
        print("        https://api.telegram.org/bot<TOKEN>/getUpdates")
        print("     3. Copie le champ 'id'\n")
        print("   Anthropic (pour la Vision IA) :")
        print("     → console.anthropic.com → API Keys → Create Key\n")
        return
 
    global VISION_ENABLED
    if VISION_ENABLED and "COLLE" in ANTHROPIC_API_KEY:
        print("⚠️  Clé Anthropic manquante → Vision IA désactivée\n")
        VISION_ENABLED = False
 
    print("\n[INFO] Connexion Vinted...")
    ok = init_vinted_session()
    print(f"[INFO] Session {'OK ✓' if ok else 'ERREUR'}\n")
 
    # Message Telegram de démarrage
    tiers_summary = (
        "💎 Luxe : Moncler, Canada Goose, CP Company, Stone Island...\n"
        "⭐ Premium : Ralph Lauren, Lacoste, Sézane, Barbour...\n"
        "🔥 Street : Nike, Adidas, TNF, Carhartt...\n"
        "✅ Casual : Levis, Dickies, Wrangler..."
    )
    send_telegram(
        f"🤖 <b>Vinted Alert Bot v3 démarré !</b>\n\n"
        f"⚙️ Budget : 0–{BUDGET_MAX}€ | Ratio min : x{RATIO_MIN} | Gain min : +{MIN_GAIN}€\n"
        f"🔍 Vision IA : {'✅' if VISION_ENABLED else '❌'}\n\n"
        f"<b>{len(BRANDS)} marques surveillées :</b>\n{tiers_summary}\n\n"
        f"🟢 En chasse — scan toutes les {CHECK_INTERVAL}s..."
    )
 
    cycle = 0
    while True:
        cycle += 1
        t_start = time.time()
        print(f"\n── SCAN #{cycle} ─── {datetime.now().strftime('%H:%M:%S')} ──────────────")
        found = scan_all()
        elapsed = round(time.time() - t_start, 1)
        print(f"── FIN #{cycle} ─── {found} alerte(s) en {elapsed}s | Prochain dans {CHECK_INTERVAL}s")
        time.sleep(CHECK_INTERVAL)
 
if __name__ == "__main__":
    main()
