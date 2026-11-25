"""Turn the verified source sheet into the bot's sources.json."""
import json
from pathlib import Path

here = Path(__file__).parent
sheet = json.load(open(here.parent / "sources.candidates.json", encoding="utf-8"))
discovery = {r["name"]: r for r in json.load(open(here / "discovery.csv.json", encoding="utf-8"))}
rendered = {r["name"] for r in json.load(open(here / "rendered.json", encoding="utf-8")) if r["state"] == "ok"}

SECTOR = {"Bank: central/state": "Govt bank", "Bank: private": "Bank", "Bank: foreign": "Foreign bank",
          "Finance/NBFI": "Finance", "Fintech/Telecom": "Telecom", "Software/AI": "Software",
          "Tech product/e-commerce": "Tech", "Industry/FMCG": "Industry", "Audit/Consulting": "Audit"}
# Readable, but the sheet's last pass marked them manual (a timeout or a strict URL check).
# The bot retries every hour and lists them under "check kora jachhe na" if they keep failing.
FORCE_READY = {
    "Rupali Bank": "https://www.rupalibank.com.bd/notice_jquery.php?type=20",
    "City Bank": "https://www.citybankplc.com/p/careers",
    "Jamuna Bank": "https://jamunabankbd.com/careers/",
    "Modhumoti Bank": "https://www.modhumotibankplc.com/career/",
    "IDLC Finance": "https://apps.idlc.com/career",
}
REASONS = {"bot_check": "site bot check dekhay", "blocked": "site bot block kore", "robots_disallowed": "site auto-check allow kore na",
           "cert_error": "site-er certificate somossa", "not_found": "career page pawa jayni", "timeout": "site response dey na",
           "conn_error": "site-e connect hoy na", "dns_error": "domain kaj kore na", "empty": "page khali ashe",
           "soft_404": "career page pawa jayni", "server_error": "site-e error"}

orgs, backups = [], []
for row in sheet:
    name, info = row["name"], discovery.get(row["name"], {})
    if row["group"] == "Job board":
        if row["status"] == "ready":
            backups.append({"name": name, "urls": [row["url"]], "monitor_urls": [row["url"]]})
        continue
    url = FORCE_READY.get(name) or row["url"]
    ready = name in FORCE_READY or row["status"] == "ready"
    org = {"name": name, "sector": SECTOR[row["group"]], "urls": [url or info.get("home") or ""],
           "monitor_urls": [url] if ready else [], "browser_urls": [url] if ready and name in rendered else [],
           "status": "Ready" if ready else "Manual"}
    if not ready:
        org["note"] = REASONS.get(row["reason"], row["reason"])
    if not org["urls"][0]:
        org["urls"] = []
    orgs.append(org)

json.dump({"organisations": orgs, "backup_sources": backups}, open(here.parent / "sources.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("orgs", len(orgs), "ready", sum(o["status"] == "Ready" for o in orgs), "browser", sum(bool(o["browser_urls"]) for o in orgs),
      "backups", [b["name"] for b in backups])
