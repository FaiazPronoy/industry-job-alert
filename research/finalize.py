"""Re-test every chosen career page and write the user-facing source sheet."""
import csv, json, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import render as R

s, out = Path(sys.argv[1]), Path(sys.argv[2])
rows = json.load(open(s / "discovery.csv.json", encoding="utf-8"))
second = {r["name"]: r for r in json.load(open(s / "rendered.json", encoding="utf-8"))}
OVERRIDE = {
 "Trust Bank": "https://www.tblbd.com/trust-bank-careers/", "Premier Bank": "https://thepremierbankplc.com/career/",
 "Southeast Bank": "https://recruitment.southeastbank.com.bd/", "Shahjalal Islami Bank": "https://sjiblbd.com/career/",
 "Dutch-Bangla Bank": "https://app.dutchbanglabank.com/Online_Job", "Chaldal": "https://chaldal.com/t/Career",
 "Akij Venture": "https://akijresource.com/job-openings", "Unilever": "https://careers.unilever.com/location/bangladesh-jobs/34155/1210997/2",
 "Citibank Bangladesh": "https://jobs.citi.com/location/dhaka-division-jobs/287/1210997-1337179/3",
 "Standard Chartered": "https://jobs.standardchartered.com/search/?q=Bangladesh", "Ollyo": "https://ollyo.com/careers/",
 "Transcom": "https://www.transcombd.com/career", "Square Group": "https://squarepharma.com.bd/career_4.php",
 "UCB": "https://www.ucb.com.bd/career", "Rupali Bank": "https://www.rupalibank.com.bd/notice_jquery.php?type=20",
}
WRONG = {"Janata Bank", "10 Minute School", "Synesis IT", "State Bank of India BD", "Habib Bank BD", "National Bank of Pakistan",
         "Rahman Rahman Huq KPMG", "HSBC Bangladesh", "Reckitt", "Hoda Vasi", "Strativ", "SELISE", "MetLife Bangladesh"}
BOARDS = [("Job board", "Bdjobs Hot Jobs", "https://hotjobs.bdjobs.com/"), ("Job board", "Teletalk All Jobs", "https://alljobs.teletalk.com.bd/"),
          ("Job board", "Skill Jobs", "https://skill.jobs/")]


def choose(row):
    if row["name"] in OVERRIDE:
        return OVERRIDE[row["name"]]
    r2 = second.get(row["name"])
    if r2 and r2["state"] == "ok":
        return r2["url"]
    return row["best_url"] if row["best_state"] == "ok" else ""


def check(item):
    group, name, url, previous = item
    if not url:
        return {"group": group, "name": name, "status": "manual", "reason": previous or "career page not found", "url": "", "sample": ""}
    r = R.render(url)
    if name in WRONG:
        status, reason = "manual", "no Bangladesh-specific job page confirmed"
    elif r["state"] == "ok" and R.CAREER.search(r["final"] or url):
        status, reason = "ready", "job posts visible" if r["posts"] else "page readable, no post recognised now"
    else:
        status, reason = "manual", r["state"]
    print("checked", status, "|", name, "|", reason, flush=True)
    return {"group": group, "name": name, "status": status, "reason": reason, "url": r["final"] or url, "sample": "; ".join(r["posts"])[:140]}


items = []
for row in rows:
    r2 = second.get(row["name"])
    previous = (r2["state"] if r2 else row["best_state"]) or row["home_state"]
    items.append((row["group"], row["name"], choose(row), previous))
items += [(g, n, u, "") for g, n, u in BOARDS]
with ThreadPoolExecutor(6) as pool:
    final = list(pool.map(check, items))
out.mkdir(parents=True, exist_ok=True)
with open(out / "career_sources.csv", "w", newline="", encoding="utf-8-sig") as handle:
    writer = csv.DictWriter(handle, fieldnames=["group", "name", "status", "reason", "url", "sample"])
    writer.writeheader(); writer.writerows(final)
json.dump(final, open(out / "sources.candidates.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("total", len(final), "ready", sum(r["status"] == "ready" for r in final), "with visible posts", sum(r["reason"] == "job posts visible" for r in final))
for group in dict.fromkeys(r["group"] for r in final):
    g = [r for r in final if r["group"] == group]
    print(f"\n## {group}: ready {sum(r['status'] == 'ready' for r in g)}/{len(g)}")
    print("READY:", ", ".join(r["name"] + ("" if r["reason"] == "job posts visible" else "*") for r in g if r["status"] == "ready"))
    print("MANUAL:", ", ".join(f"{r['name']} ({r['reason']})" for r in g if r["status"] == "manual"))
print("\nCHECK OVERRIDES")
for r in final:
    if r["name"] in OVERRIDE or r["group"] == "Job board":
        print(r["name"], "|", r["status"], r["reason"], "|", r["url"][:75], "|", r["sample"][:70])
