"""Find and test official career pages. Honest identity, TLS on, robots.txt obeyed, blocks reported."""
import csv, json, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

UA = "IndustryJobWatcher/0.1 (personal job-alert bot; read-only; low frequency)"
ORGS = {
 "Bank: central/state": "Bangladesh Bank|bb.org.bd;Sonali Bank|sonalibank.com.bd;Janata Bank|jb.com.bd;Agrani Bank|agranibank.org;Rupali Bank|rupalibank.com.bd;BASIC Bank|basicbanklimited.com;Bangladesh Development Bank|bdbl.com.bd;Sammilito Islami Bank|sammilitoislamibank.com;Bangladesh Krishi Bank|krishibank.org.bd;Rajshahi Krishi Unnayan Bank|rakub.org.bd;Probashi Kallyan Bank|pkb.gov.bd",
 "Bank: private": "AB Bank|abbl.com;Bangladesh Commerce Bank|bcblbd.com;Bank Asia|bankasia-bd.com;Bengal Commercial Bank|bgcb.com.bd;BRAC Bank|bracbank.com;Citizens Bank|citizensbankbd.com;City Bank|thecitybank.com;Community Bank|communitybankbd.com;Dhaka Bank|dhakabankltd.com;Dutch-Bangla Bank|dutchbanglabank.com;Eastern Bank|ebl.com.bd;IFIC Bank|ificbank.com.bd;Jamuna Bank|jamunabankbd.com;Meghna Bank|meghnabank.com.bd;Mercantile Bank|mblbd.com;Midland Bank|midlandbankbd.net;Modhumoti Bank|modhumotibank.com;Mutual Trust Bank|mutualtrustbank.com;National Bank|nblbd.com;NCC Bank|nccbank.com.bd;NRB Bank|nrbbankbd.com;NRBC Bank|nrbcommercialbank.com;ONE Bank|onebank.com.bd;Padma Bank|padmabankbd.com;Prime Bank|primebank.com.bd;Pubali Bank|pubalibangla.com;SBAC Bank|sbacbank.com;Shimanto Bank|shimantobank.com;Southeast Bank|southeastbank.com.bd;Premier Bank|premierbankplc.com;Trust Bank|trustbank.com.bd;UCB|ucb.com.bd;Uttara Bank|uttarabank-bd.com;Al-Arafah Islami Bank|al-arafahbank.com;ICB Islamic Bank|icbislamic-bd.com;Islami Bank Bangladesh|islamibankbd.com;Shahjalal Islami Bank|shahjalalbank.com.bd;Standard Bank|standardbankbd.com",
 "Bank: foreign": "Standard Chartered|sc.com/bd;HSBC Bangladesh|about.hsbc.com.bd;Citibank Bangladesh|citigroup.com;State Bank of India BD|sbi.co.in;Woori Bank BD|wooribank.com.bd;Commercial Bank of Ceylon BD|combankbd.com;Habib Bank BD|habibbank.com;National Bank of Pakistan|nbp.com.pk",
 "Finance/NBFI": "IDLC Finance|idlc.com;IPDC Finance|ipdcbd.com;LankaBangla Finance|lankabd.com;DBH Finance|dbhfinance.com;Green Delta Insurance|green-delta.com;MetLife Bangladesh|metlife.com.bd",
 "Fintech/Telecom": "bKash|bkash.com;Nagad|nagad.com.bd;Upay|upaybd.com;SSLCOMMERZ|sslcommerz.com;Grameenphone|grameenphone.com;Robi Axiata|robi.com.bd;Banglalink|banglalink.net;Teletalk|teletalk.com.bd",
 "Software/AI": "Brain Station 23|brainstation-23.com;Therap BD|therapbd.com;Enosis Solutions|enosisbd.com;SELISE|selise.ch;Cefalo|cefalo.com;BJIT|bjitgroup.com;Vivasoft|vivasoftltd.com;Kaz Software|kaz.com.bd;REVE Systems|revesoft.com;LeadSoft|leadsoft.com.bd;Riseup Labs|riseuplabs.com;Dynamic Solution Innovators|dsinnovators.com;Samsung R&D Bangladesh|research.samsung.com/srbd;Tiger IT|tigerit.com;Southtech|southtechgroup.com;DataSoft|datasoft-bd.com;Nascenia|nascenia.com;WellDev|welldev.io;Strativ|strativ.se;BitMascot|bitmascot.com;Monstarlab Bangladesh|monstar-lab.com;Orbitax|orbitax.com;Craftsmen|craftsmenltd.com;ReliSource|relisource.com;Sazim|sazim.io;Pridesys|pridesys.com;Apsis Solutions|apsissolutions.com;Streams Tech|streamstech.com;Divine IT|divineit.net;TechnoNext|technonext.com;ShellBeeHaken|shellbeehaken.com;BRAC IT|bracits.com;Ollyo|ollyo.com;weDevs|wedevs.com;Portonics|portonics.com;SSL Wireless|sslwireless.com;Augmedix|augmedix.com;Intelligent Machines|intelligentmachines.xyz;Gigatech|gigatechltd.com;Hishab|hishab.co;Synesis IT|synesisit.com.bd;Exabyting|exabyting.com;Bdtask|bdtask.com;Xpeed Studio|xpeedstudio.com;Inflectionpoint|inflectionpointbd.com",
 "Tech product/e-commerce": "Pathao|pathao.com;Chaldal|chaldal.com;ShopUp|shopup.org;Shohoz|shohoz.com;Sheba|sheba.xyz;10 Minute School|10minuteschool.com;Shikho|shikho.com;Daraz|daraz.com.bd;foodpanda BD|foodpanda.com.bd;Bongo|bongobd.com",
 "Industry/FMCG": "Unilever|careers.unilever.com;BAT Bangladesh|batbangladesh.com;Nestle Bangladesh|nestle.com.bd;Marico Bangladesh|marico.com/bangladesh;Reckitt|careers.reckitt.com;Square Group|squaregroup.com;Square Pharma|squarepharma.com.bd;ACI|aci-bd.com;Walton|waltonbd.com;PRAN-RFL|prangroup.com;Beximco|beximco.com;Renata|renata-ltd.com;Incepta|inceptapharma.com;Akij Venture|akijventure.com;Bashundhara|bashundharagroup.com;Meghna Group|meghnagroup.biz;City Group|citygroup.com.bd;Partex Star|partexstargroup.com;Transcom|transcombd.com;BSRM|bsrm.com;Summit Group|summitgroupbd.com;Berger Paints|bergerbd.com;Apex Footwear|apexfootwearltd.com;DBL Group|dbl-group.com;Epyllion|epylliongroup.com;Mohammadi Group|mohammadigroup.com;MGI|mgi.org;Runner Group|runnerbd.com;Nitol Niloy|nitolniloy.com;Kazi Farms|kazifarms.com;BRAC|brac.net;Aarong|aarong.com;Bata Bangladesh|batabd.com;International Beverages|ibplbd.com;Pran Foods|pranfoods.net",
 "Audit/Consulting": "Hoda Vasi|hodavasi.com;Rahman Rahman Huq KPMG|kpmg.com/bd;A Qasem|aqasem.com;LightCastle|lightcastlepartners.com",
}
CAREER = re.compile(r"career|careers|job|jobs|vacanc|recruit|join[-_ ]?us|work[-_ ]?with[-_ ]?us|talent|hiring|নিয়োগ|ক্যারিয়ার", re.I)
BAD = re.compile(r"career[-_ ]?(fair|tips|advice)|facebook|linkedin\.com|youtube|\.(jpg|png|zip)$", re.I)
ATS = re.compile(r"greenhouse\.io|lever\.co|workable\.com|smartrecruiters|myworkdayjobs|bamboohr|recruitee|teamtailor|ashbyhq|successfactors|taleo|icims|oraclecloud|hotjobs\.bdjobs|bdjobs\.com|skill\.jobs|erecruitment|career\.", re.I)
JOBWORD = re.compile(r"software engineer|developer|officer|trainee|intern|engineer|executive|analyst|manager|vacanc|circular|apply|deadline|position|opening|নিয়োগ", re.I)
CHALLENGE = re.compile(r"request is being verified|checking your browser|just a moment|cf-chl|verify you are human|captcha", re.I)
PATHS = ["/career", "/careers", "/jobs", "/career.php", "/en/careers"]


def robots_ok(session, cache, url):
    p = urlparse(url); origin = f"{p.scheme}://{p.netloc}"
    if origin not in cache:
        rp = None
        try:
            r = session.get(origin + "/robots.txt", timeout=(6, 10))
            if r.status_code == 200 and "html" not in r.headers.get("Content-Type", "").lower():
                rp = RobotFileParser(); rp.parse(r.text.splitlines())
        except requests.RequestException:
            pass
        cache[origin] = rp
    return cache[origin].can_fetch(UA, url) if cache[origin] else True


def get(session, cache, url):
    row = {"url": url, "state": "", "http": "", "final": "", "title": "", "chars": 0, "jobwords": 0, "soup": None}
    try:
        if not robots_ok(session, cache, url):
            row["state"] = "robots_disallowed"; return row
        r = session.get(url, timeout=(8, 18), allow_redirects=True)
    except requests.exceptions.SSLError:
        row["state"] = "cert_error"; return row
    except requests.exceptions.Timeout:
        row["state"] = "timeout"; return row
    except requests.RequestException:
        row["state"] = "conn_error"; return row
    row["http"], row["final"] = r.status_code, r.url
    if r.status_code in (401, 403, 429):
        row["state"] = "blocked"; return row
    if r.status_code >= 400:
        row["state"] = "not_found" if r.status_code in (404, 410) else "server_error"; return row
    if "html" not in r.headers.get("Content-Type", "html").lower():
        row["state"] = "document"; return row
    text = r.text[:3_000_000]
    if CHALLENGE.search(text[:20000]):
        row["state"] = "bot_check"; return row
    soup = BeautifulSoup(text, "html.parser")
    row["title"] = " ".join((soup.title.get_text(" ") if soup.title else "").split())[:70]
    links = BeautifulSoup(text, "html.parser")
    for t in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        t.decompose()
    body = " ".join(soup.get_text(" ").split())
    row.update(chars=len(body), jobwords=len(JOBWORD.findall(body)), soup=links)
    if re.search(r"\b404\b|page not found", row["title"], re.I):
        row["state"] = "soft_404"
    else:
        row["state"] = "needs_browser" if len(body) < 250 else "ok"
    return row


def inspect(item):
    group, name, target = item
    session = requests.Session(); session.headers.update({"User-Agent": UA, "Accept": "text/html,*/*"}); cache = {}
    home = None
    for base in (f"https://www.{target}", f"https://{target}"):
        if target.startswith(("careers.", "about.", "research.")) and "www." in base:
            continue
        home = get(session, cache, base)
        if home["state"] in ("ok", "needs_browser", "soft_404"):
            break
    out = {"group": group, "name": name, "domain": target, "home_state": home["state"], "home": home["final"] or base,
           "best_url": "", "best_state": "", "best_chars": 0, "best_jobwords": 0, "ats": "", "candidates": ""}
    found = []
    if home.get("soup") is not None:
        for a in home["soup"].find_all("a", href=True):
            text = " ".join(a.get_text(" ").split())[:60]
            try:
                url = urljoin(home["final"], a["href"].strip()).split("#")[0]
            except ValueError:
                continue
            if url.startswith("http") and (CAREER.search(text) or CAREER.search(urlparse(url).path + urlparse(url).netloc)) and not BAD.search(url + " " + text):
                found.append(url)
    root = f"{urlparse(home['final'] or base).scheme}://{urlparse(home['final'] or base).netloc}"
    found = list(dict.fromkeys(found))[:6]
    if not found:
        found = [root + p for p in PATHS]
    out["ats"] = " ".join(u for u in found if ATS.search(urlparse(u).netloc))[:200]
    results = []
    for url in found:
        time.sleep(0.5)
        results.append(get(session, cache, url))
    good = [r for r in results if r["state"] in ("ok", "needs_browser", "document")]
    good.sort(key=lambda r: (bool(CAREER.search(r["final"] or r["url"])), r["jobwords"], r["chars"]), reverse=True)
    pick = good[0] if good else (results[0] if results else None)
    if pick:
        out.update(best_url=pick["final"] or pick["url"], best_state=pick["state"], best_chars=pick["chars"], best_jobwords=pick["jobwords"])
    out["candidates"] = " ".join(f"{r['state']}:{r['final'] or r['url']}" for r in results)[:700]
    return out


if __name__ == "__main__":
    items = [(g, *entry.split("|")) for g, block in ORGS.items() for entry in block.split(";")]
    with ThreadPoolExecutor(10) as pool:
        rows = list(pool.map(inspect, items))
    with open(sys.argv[1], "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    json.dump(rows, open(sys.argv[1] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("orgs", len(rows))
    for group in ORGS:
        g = [r for r in rows if r["group"] == group]
        ready = [r for r in g if r["best_state"] == "ok" and CAREER.search(r["best_url"])]
        print(f"\n## {group}: {len(ready)}/{len(g)} ready")
        for r in g:
            mark = "OK " if r in ready else "?? "
            print(mark, r["name"], "|home", r["home_state"], "|", r["best_state"], r["best_jobwords"], r["best_url"][:85])
