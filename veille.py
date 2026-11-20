import json, os, re, smtplib, ssl
from email.message import EmailMessage
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

KEYWORDS = [r"\bsoc\b", r"\bgrc\b", r"\biam\b", r"\bcti\b", r"\bciso\b", r"\brssi\b",
            r"cyber", r"s[ée]curit", r"security", r"pentest", r"audit", r"devsecops",
            r"threat", r"vuln[ée]rabilit", r"\bcert\b", r"d[ée]tection", r"conformit"]
EXCLUDE = [r"s[ée]curit[ée] sociale", r"agent de s[ée]curit", r"\bsst\b", r"incendie"]

SOURCES = [
    {"name": "Synetis", "type": "html", "url": "https://www.synetis.com/carriere/offres-emplois/"},
    {"name": "Almond", "type": "html", "url": "https://careers.almond.eu/jobs"},
    {"name": "Advens", "type": "smartrecruiters", "id": "ADVENS"},
    {"name": "Orange Cyberdefense", "type": "html", "url": "https://jobs.orangecyberdefense.com/fr"},
    {"name": "I-TRACING", "type": "html", "url": "https://i-tracing.com/fr/offres-emploi/"},
    {"name": "Intrinsec", "type": "html", "url": "https://www.intrinsec.com/offres-emploi/"},
    {"name": "Sekoia.io", "type": "html", "url": "https://careers.sekoia.com/jobs"},
    {"name": "EGERIE", "type": "html", "url": "https://www.welcometothejungle.com/fr/companies-v1/egerie/jobs"},
    {"name": "Gatewatcher", "type": "html", "url": "https://www.welcometothejungle.com/fr/companies-v1/gatewatcher/jobs"},
    {"name": "Sopra Steria", "type": "html", "url": "https://careers.soprasteria.fr/posts/recrutement"},
    {"name": "Wavestone", "type": "html", "url": "https://www.wavestone.com/fr/carrieres/nos-offres/"},
    {"name": "Capgemini", "type": "html", "url": "https://www.capgemini.com/fr-fr/carrieres/rejoignez-nous/nos-offres-demploi/?page=1&size=11&country_code=fr-fr"},
    {"name": "Accenture", "type": "html", "url": "https://www.accenture.com/fr-fr/careers/jobsearch"},
    {"name": "Deloitte", "type": "html", "url": "https://www.deloitte.com/fr/fr/careers/content/job/results.html"},
    {"name": "EY", "type": "html", "url": "https://eyglobal.yello.co/job_boards/c1riT--B2O-KySgYWsZO1Q?locale=en"},
    {"name": "PwC jeunes diplômés", "type": "html", "url": "https://carrieres.pwc.fr/fr/jeunes-diplomes-offres.html"},
    {"name": "PwC stages", "type": "html", "url": "https://carrieres.pwc.fr/fr/stage-offres.html"},
    {"name": "KPMG", "type": "html", "url": "https://emplois.kpmg.fr/recherche-d%27offres?acm=ALL&alrpm=ALL&ascf=[%7B%22key%22:%22custom_fields.CareerLevel%22,%22value%22:%22Jeunes+dipl%C3%B4m%C3%A9s%22%7D]"},
    {"name": "Atos", "type": "html", "url": "https://jobs.atos.net/search/?createNewAlert=false&q=&locationsearch=&optionsFacetsDD_country=&optionsFacetsDD_city=&optionsFacetsDD_customfield2="},
    {"name": "Inetum", "type": "html", "url": "https://www.inetum.com/fr/fr/careers/jobs.html?list-b4837029c4_page=1"},
    {"name": "BNP Paribas", "type": "html", "url": "https://group.bnpparibas/emploi-carriere/toutes-offres-emploi"},
]

UA = {"User-Agent": "Mozilla/5.0"}

def fetch(src):
    t = src["type"]
    if t == "smartrecruiters":
        r = requests.get(f"https://api.smartrecruiters.com/v1/companies/{src['id']}/postings?limit=100", headers=UA, timeout=30)
        return [(j["name"], f"https://jobs.smartrecruiters.com/{src['id']}/{j['id']}") for j in r.json().get("content", [])]
    if t == "html":
        r = requests.get(src["url"], headers=UA, timeout=30)
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for a in soup.find_all("a", href=True):
            txt = a.get_text(" ", strip=True)
            if 8 < len(txt) < 150:
                out.append((txt, urljoin(src["url"], a["href"])))
        return out
    return []

def is_cyber(title):
    t = title.lower()
    return any(re.search(k, t) for k in KEYWORDS) and not any(re.search(e, t) for e in EXCLUDE)

def send(new):
    body = "\n\n".join(f"[{n}] {t}\n{u}" for n, t, u in new)
    msg = EmailMessage()
    msg["Subject"] = f"{len(new)} nouvelle(s) offre(s) cyber"
    msg["From"] = os.environ["GMAIL_USER"]
    msg["To"] = os.environ["MAIL_TO"]
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
        s.send_message(msg)

def main():
    first_run = not os.path.exists("seen.json")
    seen = set(json.load(open("seen.json"))) if not first_run else set()
    new = []
    for src in SOURCES:
        try:
            items = fetch(src)
            cyber = [(t, u) for t, u in items if is_cyber(t)]
            print(f"{src['name']}: {len(items)} liens, {len(cyber)} cyber")
            for title, url in cyber:
                if url not in seen:
                    seen.add(url)
                    new.append((src["name"], title, url))
        except Exception as e:
            print(f"Erreur {src['name']}: {e}")
    json.dump(sorted(seen), open("seen.json", "w"), indent=1)
    if new and not first_run:
        send(new)
    print(f"{len(new)} nouvelles offres (premier passage : {first_run})")

main()
