# Bank & Industry Job Alert Bot

Bangladesh-er bank, software/AI company, telecom ar industry group-er career page protiti ghontay check kore. Tarpor matching job gulo Telegram-e pathay. University circular-er jonno alada bot ache: `university-job-alert`.

## Ki pathabe

Protiti ghontay shudhu **2 ta message** ashe. Agher ghontar 2 ta message nije theke muche jay.

1. **💻 Software · AI · Data · IT**: Software/AI/ML/data engineer, SQA, DevOps, IT officer.
2. **🏦 Bank · Business · Officer**: bank officer, MTO, probationary/trainee officer, marketing, finance, HR, supply chain. Eta duita bhag-e thake: "Bank & Finance" ar "Industry · Telecom · Tech company".

- Internship duita message-ei upore alada **🎓 INTERNSHIP** bhag-e thake.
- Deadline thakle je post-er deadline age shesh, sheta upore thake. 🔴 = 3 diner moddhe, 🟠 = ei shoptahe.
- Deadline chara post gulo tar niche thake, notun gulo age.
- Je post aj prothom dekha geche, tar pashe saradin **🟢 NEW** thake.
- Deadline par hole, ba company page theke post sore gele, post list theke chole jay.
- Head/Director/GM/Lead er moto senior post, ar CSE/BBA-r baire je post (production, mechanical, medical, driver) segulo dekhabe na.
- Notun kichu ashle message sound kore ashe, na ashle silent.
- Kono site 6 ghonta kaj na korle Bank message-er niche dekhabe.
- Robibar sokal 9 tar por manual checklist ashe. Je site bot porte pare na (block, bot check, robots.txt), segulo karon soho ekhane thake.

Kon company automatic ar kon gula manual, seta [career_sources.csv](career_sources.csv)-e karon shoho ache. LinkedIn nei, karon LinkedIn auto-check allow kore na.

## Setup

### 1. Notun Telegram bot

University bot-er token use korben na. Alada bot banan:

1. Telegram-e `@BotFather` khulun, `/newbot` pathan, naam din (jemon "BD Job Alert").
2. Token copy korun. Token karo sathe share korben na, code-eo rakhben na.
3. Notun bot khule `/start` pathan.

### 2. Chat ID

```powershell
pip install -r requirements.txt
```

```powershell
$env:TELEGRAM_BOT_TOKEN = Read-Host "Bot token"
```

```powershell
python watcher.py --find-chat-id
```

### 3. GitHub

1. Ei folder-er jonno ekta notun **public** repository banan, jemon `industry-job-alert`.
2. Settings > Secrets and variables > Actions-e duita secret add korun: `TELEGRAM_BOT_TOKEN` ar `TELEGRAM_CHAT_ID`.
3. Actions tab-e **Industry job watch > Run workflow** e `test-message` diye run korun.

### 4. Protiti ghontay chalano

GitHub-er nijer schedule bhorsha jogyo na. Tai university bot-er moto cron-job.org-e arekta job banan, je protiti ghontay ei repository-r `watch.yml` workflow-e `workflow_dispatch` POST pathabe.

## Local test

```powershell
python -m unittest test_watcher
```

```powershell
python watcher.py --dry-run --state $env:TEMP\industry_state.json
```

Source list notun kore banate hole `research/` folder-er script gulo use korun: `discover.py`, `render.py`, `finalize.py`, ar shesh-e `build_config.py`.
