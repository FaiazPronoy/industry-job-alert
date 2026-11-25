"""Second pass: render unresolved sites. Blocked, bot-checked and robots-disallowed sites are left for manual checks."""
import json, re, sys, threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import Error as PlaywrightError, sync_playwright

UA = "IndustryJobWatcher/0.1 (personal job-alert bot; read-only; low frequency)"
EXTRA = {
 "Sammilito Islami Bank": ["https://www.sibl-bd.com/", "https://sammilitoislamibank.com.bd/"],
 "Modhumoti Bank": ["https://www.modhumotibankplc.com/career", "https://modhumotibankltd.com/career"],
 "Nitol Niloy": ["https://www.nitolniloygroup.com/career"],
 "Shahjalal Islami Bank": ["https://www.sjiblbd.com/career", "https://sjibl.com.bd/career"],
 "Trust Bank": ["https://www.tblbd.com/career", "https://tblbd.com/careers"],
 "Al-Arafah Islami Bank": ["https://www.aibl.com.bd/career", "https://aibl.com.bd/careers"],
 "Woori Bank BD": ["https://www.wooribank.com/bd"],
 "Commercial Bank of Ceylon BD": ["https://www.combank.net/bangladesh", "https://www.combank.lk/careers"],
 "HSBC Bangladesh": ["https://www.about.hsbc.com.bd/careers", "https://www.hsbc.com/careers"],
 "LankaBangla Finance": ["https://www.lankabangla.com/career/", "https://lankabangla.com/careers/"],
 "Dutch-Bangla Bank": ["https://www.dutchbanglabank.com/career/career.html", "https://app.dutchbanglabank.com/Online_Job"],
 "Premier Bank": ["https://www.premierbankplc.com/careers", "https://premierbankplc.com/page/career"],
 "Grameenphone": ["https://www.grameenphone.com/about/career", "https://www.grameenphone.com/careers"],
 "Upay": ["https://www.upaybd.com/careers"],
 "Robi Axiata": ["https://www.robi.com.bd/en/corporate/career", "https://careers.robi.com.bd/"],
 "Banglalink": ["https://www.banglalink.net/en/about-us/career", "https://career.banglalink.net/"],
 "LeadSoft": ["https://leadsoft.com.bd/careers", "https://leadsoft.com.bd/career-opportunities"],
 "Tiger IT": ["https://www.tigerit.com/careers"], "Orbitax": ["https://orbitax.com/careers", "https://www.orbitax.com/careers"],
 "Intelligent Machines": ["https://intelligentmachines.xyz/careers"], "Hishab": ["https://hishab.co/careers", "https://www.hishab.co/"],
 "Sheba": ["https://www.sheba.xyz/careers"], "Shohoz": ["https://www.shohoz.com/careers"],
 "foodpanda BD": ["https://careers.foodpanda.com/"], "Beximco": ["https://www.beximco.com/careers"],
 "Kazi Farms": ["https://www.kazifarms.com/careers"], "Runner Group": ["https://www.runnerbd.com/careers"],
 "Summit Group": ["https://www.summit-bd.com/career", "https://summitpowerinternational.com/careers/"],
 "Inflectionpoint": ["https://www.inflectionpoint.com.bd/"], "International Beverages": ["https://www.ibplbd.net/career"],
 "SELISE": ["https://selisegroup.com/careers/", "https://career.selisegroup.com/"], "Strativ": ["https://strativ.se/career", "https://www.strativ.se/careers"],
 "Exabyting": ["https://exabyting.com/join-our-team/"], "Janata Bank": ["https://www.jb.com.bd/career", "https://www.jb.com.bd/home/career"],
 "Rupali Bank": ["https://www.rupalibank.com.bd/notice_jquery.php?type=20"], "10 Minute School": ["https://10minuteschool.com/careers/"],
 "Synesis IT": ["https://synesisitltd.com/career/"], "Ollyo": ["https://ollyo.com/careers/"], "Reckitt": ["https://careers.reckitt.com/search/?q=Bangladesh"],
 "Standard Chartered": ["https://jobs.standardchartered.com/search/?q=Bangladesh"], "Citibank Bangladesh": ["https://jobs.citi.com/location/bangladesh-jobs/287/1210997/2"],
 "Rahman Rahman Huq KPMG": ["https://kpmg.com/bd/en/careers.html"], "Hoda Vasi": ["https://www.hodavasi.com/career"],
 "Habib Bank BD": ["https://habibbank.com/careers/"], "National Bank of Pakistan": ["https://www.nbp.com.pk/careers/index.aspx"],
 "State Bank of India BD": ["https://bank.sbi/web/careers"],
}
SUSPECT = {"Janata Bank", "Rupali Bank", "10 Minute School", "Synesis IT", "Ollyo", "SELISE", "Strativ", "Exabyting", "Reckitt", "Standard Chartered",
           "Citibank Bangladesh", "Rahman Rahman Huq KPMG", "Hoda Vasi", "Therap BD", "UCB", "Unilever"}
STOP = {"blocked", "bot_check", "robots_disallowed", "cert_error"}
RETRY = {"needs_browser", "not_found", "timeout", "conn_error", "server_error", "soft_404", ""}
CAREER = re.compile(r"career|jobs?\b|vacanc|recruit|join[-_ ]?us|join-our|hiring|openings|নিয়োগ", re.I)
BAD = re.compile(r"facebook|linkedin\.com|youtube|career[-_ ]?(fair|tips)|\.(jpg|png|zip)$", re.I)
POST = re.compile(r"software|developer|engineer|\bai\b|machine learning|data|qa\b|devops|officer|trainee|\bmto\b|intern|executive|analyst|"
                  r"manager|associate|marketing|finance|accounts|\bhr\b|supply chain|কর্মকর্তা|নিয়োগ", re.I)
CHALLENGE = re.compile(r"request is being verified|checking your browser|just a moment|cf-chl|verify you are human|captcha", re.I)
local = threading.local()
lock = threading.Lock()
robots = {}


def allowed(url):
    p = urlparse(url); origin = f"{p.scheme}://{p.netloc}"
    with lock:
        if origin in robots:
            rp = robots[origin]
            return rp.can_fetch(UA, url) if rp else True
    rp = None
    try:
        r = requests.get(origin + "/robots.txt", headers={"User-Agent": UA}, timeout=(5, 8))
        if r.status_code == 200 and "html" not in r.headers.get("Content-Type", "").lower():
            rp = RobotFileParser(); rp.parse(r.text.splitlines())
    except requests.RequestException:
        pass
    with lock:
        robots[origin] = rp
    return rp.can_fetch(UA, url) if rp else True


def render(url):
    out = {"url": url, "state": "", "final": "", "title": "", "chars": 0, "posts": [], "links": []}
    if not allowed(url):
        out["state"] = "robots_disallowed"; return out
    if not hasattr(local, "ctx"):
        local.pw = sync_playwright().start(); local.browser = local.pw.chromium.launch()
        local.ctx = local.browser.new_context(user_agent=UA, timezone_id="Asia/Dhaka")
    page = local.ctx.new_page()
    try:
        response = page.goto(url, wait_until="domcontentloaded", timeout=22000)
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except PlaywrightError:
            pass
        html = page.content(); status = response.status if response else 0; out["final"] = page.url
    except PlaywrightError as error:
        text = str(error)
        out["state"] = "cert_error" if "CERT" in text else "dns_error" if "NAME_NOT" in text else "timeout" if "Timeout" in text else "conn_error"
        return out
    finally:
        page.close()
    if status in (401, 403, 429):
        out["state"] = "blocked"; return out
    if status >= 400:
        out["state"] = "not_found" if status in (404, 410) else "server_error"; return out
    if CHALLENGE.search(html[:20000]):
        out["state"] = "bot_check"; return out
    soup = BeautifulSoup(html, "html.parser")
    out["title"] = " ".join((soup.title.get_text(" ") if soup.title else "").split())[:60]
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ").split())[:50]
        try:
            link = urljoin(out["final"], a["href"].strip()).split("#")[0]
        except ValueError:
            continue
        if link.startswith("http") and (CAREER.search(text) or CAREER.search(urlparse(link).path + urlparse(link).netloc)) and not BAD.search(link):
            out["links"].append(link)
    out["links"] = list(dict.fromkeys(out["links"]))[:4]
    for t in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        t.decompose()
    lines = [" ".join(x.split()) for x in soup.get_text("\n").split("\n")]
    lines = [x for x in lines if x]
    out["chars"] = sum(map(len, lines))
    out["posts"] = list(dict.fromkeys(x for x in lines if 6 <= len(x) <= 70 and len(x.split()) <= 9 and POST.search(x)))[:4]
    if re.search(r"\b404\b|not found|under construction", out["title"] + " " + " ".join(lines[:6]), re.I):
        out["state"] = "soft_404"
    else:
        out["state"] = "ok" if out["chars"] >= 150 else "empty"
    return out


def inspect(row):
    urls = list(dict.fromkeys(EXTRA.get(row["name"], []) + ([row["best_url"]] if row["best_url"] else [])))[:3]
    results, seen = [], set()
    for url in urls:
        r = render(url); results.append(r); seen.add(url)
    if not any(r["state"] == "ok" and CAREER.search(r["final"]) for r in results):
        home = render(row["home"]) if row["home"] not in seen else None
        pool = (home["links"] if home and home["state"] == "ok" else []) + [l for r in results for l in r["links"]]
        for link in [l for l in dict.fromkeys(pool) if l not in seen][:2]:
            results.append(render(link)); seen.add(link)
    good = [r for r in results if r["state"] == "ok" and CAREER.search(r["final"])]
    good.sort(key=lambda r: (len(r["posts"]), r["chars"]), reverse=True)
    pick = good[0] if good else (results[0] if results else {"state": "none", "final": "", "url": "", "posts": [], "title": ""})
    return {"group": row["group"], "name": row["name"], "state": pick["state"], "url": pick.get("final") or pick.get("url"), "title": pick.get("title"),
            "posts": pick.get("posts", []), "tried": [f"{r['state']}:{r['url']}" for r in results]}


if __name__ == "__main__":
    rows = json.load(open(sys.argv[1], encoding="utf-8"))
    todo = [r for r in rows if r["name"] in SUSPECT or r["best_state"] in RETRY or r["best_state"] == "document"]
    todo = [r for r in todo if r["best_state"] not in STOP or r["name"] in EXTRA and r["best_state"] == "cert_error" and False]
    print("rendering", len(todo), flush=True)
    with ThreadPoolExecutor(6) as pool:
        out = list(pool.map(inspect, todo))
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    for r in out:
        print(("OK " if r["state"] == "ok" else "?? ") + r["name"], "|", r["state"], "|", (r["url"] or "")[:80], "|", "; ".join(r["posts"])[:95])
