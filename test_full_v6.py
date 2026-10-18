# test_full_v6.py
import os, re, time, requests, pandas as pd
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()
AVALAI_KEY = os.getenv("AVALAI_API_KEY")
INPUT = "salons_unmatched.csv"
OUTPUT = "salons_search_results_v6.csv"
URL = "https://api.avalai.ir/v1/search/serper-search"
MAX_ROWS = None   # None = کل لیست

if not AVALAI_KEY:
    raise SystemExit("❌ AVALAI_API_KEY در .env نیست.")

session = requests.Session()
session.mount("https://", HTTPAdapter(max_retries=Retry(
    total=5, backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["POST"],
)))

NON_TEHRAN = [
    "کرمانشاه", "kermanshah", "ارومیه", "urmia", "دورود", "doroud",
    "شهرری", "شهر ری", "shahre rey", "شیراز", "shiraz", "اصفهان", "isfahan",
    "قم", "qom", "تبریز", "tabriz", "سمنان", "semnan", "چابهار", "chabahar",
    "رشت", "rasht", "یزد", "yazd", "کرج", "karaj", "مشهد", "mashhad",
    "اهواز", "ahvaz", "کرمان", "kerman", "شوش", "shush", "بندرعباس",
    "گرگان", "ساری", "بابل", "آمل", "قزوین", "زنجان", "همدان",
    "خرم آباد", "بروجرد", "ایلام", "سنندج", "اراک", "بوشهر",
    "بیرجند", "زاهدان", "خسروشاه", "داراب", "میانه", "صومعه سرا",
    "sowmeh", "sowme", "khosrowshah", "darab", "miyaneh",
    "کیش", "kish", "دزفول", "dezful", "مهاباد", "mahabad",
    "سقز", "saqqez", "مریوان", "marivan", "بانه", "baneh",
    "جهرم", "jahrom", "فسا", "fasa", "لار", "بندر دیر", "bandar dir",
    "لاهیجان", "lahijan", "جاجرم", "jajarm", "دامغان", "damghan",
    "بجنورد", "bojnord", "سبزوار", "sabzevar", "نیشابور", "neyshabur",
    "کاشان", "kashan", "نجف آباد", "najafabad", "شهرکرد", "shahrekord",
    "یاسوج", "yasuj", "دهدشت", "dehdasht", "گچساران", "gachsaran",
    "برازجان", "borazjan", "مراغه", "maragheh", "مرند", "marand",
    "خوی", "khoy", "میاندوآب", "miandoab", "بوکان", "bukan",
    "ابهر", "abhar", "تاکستان", "takestan",
    "اسلامشهر", "eslamshahr", "پرند", "parand", "اندیشه", "andisheh",
    "ملارد", "malard", "واوان", "vavan", "مهرشهر", "mehrshahr",
    "یاغچیان", "yaghchian", "پاکدشت", "pakdasht", "شهریار", "shahriyar",
    "ورامین", "varamin", "قرچک", "qarchak", "رباط کریم",
    "باغستان", "baghestan", "صفادشت", "safadasht", "رودهن", "roudehen",
    "بومهن", "boumehen", "پردیس", "pardis", "لواسان", "lavasan",
    "فشم", "fasham", "میگون", "meygoon", "شمشک", "shemashak",
    "دماوند", "damavand", "فیروزکوه", "firouzkuh",
]

MEN_PATTERNS = [
    r"(?<![\w])barbershop(?![\w])", r"(?<![\w])barber(?![\w])",
    r"(?<![\w])پیرایش(?![\w])", r"(?<![\w])فید(?![\w])",
    r"(?<![\w])کات مردانه(?![\w])", r"(?<![\w])سالن مردانه(?![\w])",
    r"(?<![\w])آرایشگاه مردانه(?![\w])", r"(?<![\w])پسرانه(?![\w])",
    r"(?<![\w])مردانه(?![\w])", r"(?<![\w])high\s*fade(?![\w])",
    r"(?<![\w])buzz\s*cut(?![\w])",
]
SHOP_PATTERNS = [
    r"به سراسر ایران", r"(?<![\w])عمده(?![\w])",
    r"(?<![\w])پخش(?![\w])", r"(?<![\w])نمایندگی(?![\w])",
    r"محصولات سالنی", r"(?<![\w])تیشرت(?![\w])",
    r"(?<![\w])collection(?![\w])",
]
AD_PATTERNS = [
    r"(?<![\w])استخدام(?![\w])", r"همکاری به صورت",
    r"(?<![\w])اجاره(?![\w])", r"(?<![\w])اگهی(?![\w])",
    r"(?<![\w])صندلی(?![\w])", r"نیرو خدماتی",
]

STOPWORDS = {
    "سالن", "زیبایی", "آرایشگاه", "آرایش", "خدمات", "تخصصی", "مرکز",
    "بانو", "خانم", "باشگاه", "تهران", "خیابان", "بلوار", "پلاک",
    "طبقه", "واحد", "شرقی", "غربی", "شمالی", "جنوبی", "کوچه",
    "the", "and", "of", "by", "ir", "tehran", "official", "vip",
    "beauty", "salon", "beautysalon",
}
NAME_NOISE = r"سالن|زیبایی|آرایشگاه|آرایش|خدمات|تخصصی|مرکز|بانو|خانم|باشگاه|و"

# ✅ جدید: تبدیل ارقام فارسی/عربی به لاتین
DIGIT_TRANS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


def to_ascii_digits(s):
    return str(s).translate(DIGIT_TRANS)


def norm_text(s):
    s = str(s).lower()
    s = s.replace("ي", "ی").replace("ك", "ک")
    s = s.replace("آ", "ا").replace("أ", "ا").replace("إ", "ا").replace("ة", "ه")
    return re.sub(r"\s+", " ", s)


def norm_digits(s):
    # ✅ اصلاح‌شده: اول ارقام فارسی/عربی به لاتین، بعد فقط نگه‌داشتن رقم‌ها
    return re.sub(r"\D", "", to_ascii_digits(s))


def phone_variants(phone):
    d = norm_digits(phone)
    out = set()
    if len(d) >= 10:
        out.add(d[-10:])
        out.add("0" + d[-10:])
    return out


def tokenize(text):
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", norm_text(text))
    toks = re.findall(r"[a-z0-9\u0600-\u06FF]+", text)
    return {t for t in toks if t not in STOPWORDS and len(t) > 2}


def clean_name(name):
    s = re.sub(NAME_NOISE, " ", norm_text(name))
    return re.sub(r"\s+", " ", s).strip()


def has_any_pattern(text, patterns):
    for pat in patterns:
        if re.search(pat, text):
            return pat
    return None


def text_has_city(text, city):
    pattern = (
        r"(?<![\u0600-\u06FF\u200cA-Za-z])"
        + re.escape(city.lower())
        + r"(?![\u0600-\u06FF\u200cA-Za-z])"
    )
    return bool(re.search(pattern, text.lower()))


def search_avalai(query):
    try:
        r = session.post(
            URL,
            headers={
                "Authorization": f"Bearer {AVALAI_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            json={"query": query, "max_results": 10, "gl": "ir", "hl": "fa", "autocorrect": False},
            timeout=45,
        )
        if r.status_code != 200:
            print(f"⚠️ HTTP {r.status_code}: {r.text[:150]}")
            return None
        data = r.json()
        return data.get("results") or data.get("organic") or []
    except Exception as e:
        print(f"⚠️ خطای اتصال: {e}")
        return None


def extract_username(res):
    link = res.get("link") or res.get("url") or ""
    m = re.search(
        r"instagram\.com/(?!p/|reel/|explore/|tv/|stories/)([a-zA-Z0-9_.]+)",
        link,
    )
    if m:
        u = m.group(1).lower()
        if u not in {"p", "reel", "explore", "tv", "stories", "popular"}:
            return u
    title = res.get("title", "")
    m = re.search(r"@([a-zA-Z0-9_.]+)", title)
    return m.group(1).lower() if m else ""


def extract_all_phones(text):
    # ✅ با to_ascii_digits: ارقام فارسی و عربی هم شناسایی می‌شوند
    digits = norm_digits(text)
    found = set()
    for m in re.finditer(r"0?9\d{9}", digits):
        found.add(m.group(0)[-10:])
    for m in re.finditer(r"0?21\d{8}", digits):
        found.add(m.group(0)[-10:])
    return found


def score_result(salon_name, salon_phone, salon_address, res):
    username = extract_username(res)
    if not username:
        return "", "Low", "no_username"

    title = res.get("title") or ""
    snippet = res.get("snippet") or ""
    raw = title + " " + snippet + " " + username
    text = norm_text(raw)
    text_pat = text.replace("_", " ").replace(".", " ")
    user_lower = username.lower()

    for bad in NON_TEHRAN:
        if text_has_city(text, bad):
            return username, "Reject", f"bad_city:{bad}"

    pat = has_any_pattern(text_pat, MEN_PATTERNS)
    if pat:
        return username, "Reject", f"men:{pat}"
    pat = has_any_pattern(text_pat, SHOP_PATTERNS)
    if pat:
        return username, "Reject", f"shop:{pat}"
    pat = has_any_pattern(text_pat, AD_PATTERNS)
    if pat:
        return username, "Reject", f"ad:{pat}"

    # ✅ حالا با ارقام فارسی هم کار می‌کند
    phones_in_text = extract_all_phones(raw)
    my_phones = phone_variants(salon_phone)
    phone_match = bool(phones_in_text & my_phones)
    phone_conflict = bool(phones_in_text) and not phone_match

    name_clean = clean_name(salon_name)
    name_in_text = bool(name_clean) and len(name_clean) > 3 and name_clean in text

    name_tokens = tokenize(salon_name)
    user_tokens = tokenize(username.replace(".", " ").replace("_", " "))
    text_tokens = tokenize(title + " " + snippet)
    common_user = name_tokens & user_tokens
    common_text = name_tokens & text_tokens

    addr_tokens = tokenize(salon_address)
    addr_match = bool(addr_tokens & text_tokens)

    has_beauty = any(k in user_lower for k in ["salon", "beauty", "beautysalon"])

    # 🟢 High
    if phone_match and (name_in_text or common_text or has_beauty):
        return username, "High", f"phone+name:{name_in_text};addr:{addr_match}"
    if name_in_text and (addr_match or has_beauty) and not phone_conflict:
        return username, "High", f"name+addr:{addr_match};beauty:{has_beauty}"
    if common_user and (phone_match or has_beauty) and not phone_conflict:
        return username, "High", f"user_tokens:{','.join(common_user)}"

    # 🟡 Medium
    if phone_match:
        return username, "Medium", "phone_only"
    if name_in_text and phone_conflict:
        return username, "Medium", "name+phone_conflict"
    if name_in_text:
        return username, "Medium", "name_only"
    if common_text and addr_match:
        return username, "Medium", "text_tokens+addr"
    if phones_in_text and has_beauty:
        return username, "Medium", "phones_in_text+beauty"

    # 🟠 Low
    if has_beauty:
        return username, "Low", "beauty_only"
    return username, "Low", "no_signal"


def blank_row(salon):
    return {
        "salon_id": str(salon["id"]),
        "salon_name": salon["name"],
        "salon_phone": salon["phone"],
        "salon_address": salon["address"],
        "query_used": "",
        "found_username": "",
        "found_url": "",
        "title": "",
        "snippet": "",
        "confidence": "",
        "reason": "",
        "status": "",
        "provider": "avalai",
    }


df = pd.read_csv(INPUT, encoding="utf-8-sig")
if MAX_ROWS is not None:
    df = df.head(MAX_ROWS)

print(f"📊 کل رکوردهای این اجرا: {len(df)}")

done = set()
if os.path.exists(OUTPUT):
    prev = pd.read_csv(OUTPUT, encoding="utf-8-sig")
    if "salon_id" in prev.columns:
        done = set(prev["salon_id"].astype(str))
    print(f"↩️ {len(done)} رکورد قبلاً انجام شده")

for i, row in df.iterrows():
    if str(row["id"]) in done:
        continue

    rec = blank_row(row)
    name = str(row["name"]).strip()

    q1 = f'"{name}" site:instagram.com'
    res1 = search_avalai(q1)
    time.sleep(1.2)

    best = None
    if res1:
        for r in res1:
            u, conf, reason = score_result(row["name"], row["phone"], row["address"], r)
            if not u:
                continue
            rank = {"High": 3, "Medium": 2, "Low": 1, "Reject": 0}[conf]
            if best is None or rank > best[0]:
                best = (rank, u, conf, reason, r, q1)

    if best and best[0] >= 2:
        _, u, conf, reason, r, q = best
        rec.update({
            "query_used": q,
            "found_username": u,
            "found_url": r.get("link") or r.get("url") or "",
            "title": r.get("title", ""),
            "snippet": r.get("snippet", ""),
            "confidence": conf,
            "reason": reason,
            "status": "found" if conf == "High" else "needs_review",
        })
    else:
        found_via_phone = None
        for pv in sorted(phone_variants(row["phone"])):
            q2 = f'"{pv}" site:instagram.com'
            res2 = search_avalai(q2)
            time.sleep(1.2)
            if not res2:
                continue
            for r in res2:
                u, conf, reason = score_result(row["name"], row["phone"], row["address"], r)
                if u and conf in ("High", "Medium"):
                    found_via_phone = (u, conf, reason + ";via_phone", r, q2)
                    break
            if found_via_phone:
                break

        if found_via_phone:
            u, conf, reason, r, q = found_via_phone
            rec.update({
                "query_used": q,
                "found_username": u,
                "found_url": r.get("link") or r.get("url") or "",
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "confidence": conf,
                "reason": reason,
                "status": "found" if conf == "High" else "needs_review",
            })
        elif best:
            _, u, conf, reason, r, q = best
            rec.update({
                "query_used": q,
                "found_username": u,
                "found_url": r.get("link") or r.get("url") or "",
                "title": r.get("title", ""),
                "snippet": r.get("snippet", ""),
                "confidence": conf,
                "reason": reason,
                "status": "needs_review",
            })
        else:
            rec["status"] = "not_found"

    pd.DataFrame([rec]).to_csv(
        OUTPUT,
        mode="a",
        header=not os.path.exists(OUTPUT),
        index=False,
        encoding="utf-8-sig",
    )

    icon = {"High": "🟢", "Medium": "🟡", "Low": "🟠", "Reject": "🔴"}.get(rec["confidence"], "❌")
    print(f"[{i+1}/{len(df)}] {icon} {name[:35]:<35} → @{rec['found_username'] or '-'}  ({rec['confidence'] or 'not_found'})")

print("\n✅ تمام شد. خروجی:", OUTPUT)