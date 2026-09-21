import urllib.request
import re
import json

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

targets = [
    ("Red Sift", "https://redsift.com/careers"),
    ("Snyk", "https://snyk.io/careers/"),
    ("Hack The Box", "https://www.hackthebox.com/careers"),
    ("SenseOn", "https://www.senseon.io/careers"),
    ("Push Security", "https://pushsecurity.com/careers"),
    ("Metomic", "https://metomic.io/careers"),
    ("Cado Security", "https://www.cadosecurity.com/careers/"),
    ("Elliptic", "https://www.elliptic.co/careers"),
    ("IriusRisk", "https://www.iriusrisk.com/careers"),
    ("Panaseer", "https://panaseer.com/careers/"),
    ("CyberSmart", "https://cybersmart.co.uk/careers/"),
    ("OutThink", "https://outthink.io/careers/"),
    ("KYND", "https://www.kynd.io/careers"),
    ("Risk Ledger", "https://riskledger.com/careers"),
    ("Quorum Cyber", "https://www.quorumcyber.com/careers/"),
    ("Bridewell", "https://www.bridewell.com/careers"),
    ("Secarma", "https://secarma.com/careers/"),
    ("Ripjar", "https://ripjar.com/careers/"),
    ("Callsign", "https://www.callsign.com/careers/"),
    ("Salt Communications", "https://saltcommunications.com/careers/"),
    ("Angoka", "https://angoka.io/careers/"),
    ("Uleska", "https://uleska.com/careers/"),
    ("PortSwigger", "https://portswigger.net/careers")
]

for name, url in targets:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            final_url = resp.url
            html = resp.read().decode("utf-8", errors="ignore")
            combined = html + " " + final_url
            
            ats_list = []
            m_ashby = re.search(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_\-]+)", combined)
            if m_ashby: ats_list.append(f"ashby: {m_ashby.group(1)}")
            
            m_gh = re.search(r"(?:boards\.greenhouse\.io|job-boards\.greenhouse\.io)/([a-zA-Z0-9_\-]+)", combined)
            if m_gh: ats_list.append(f"greenhouse: {m_gh.group(1)}")
            
            m_lever = re.search(r"jobs\.lever\.co/([a-zA-Z0-9_\-]+)", combined)
            if m_lever: ats_list.append(f"lever: {m_lever.group(1)}")
            
            m_workable = re.search(r"apply\.workable\.com/([a-zA-Z0-9_\-]+)", combined)
            if m_workable: ats_list.append(f"workable: {m_workable.group(1)}")
            
            m_sr = re.search(r"jobs\.smartrecruiters\.com/([a-zA-Z0-9_\-]+)", combined)
            if m_sr: ats_list.append(f"smartrecruiters: {m_sr.group(1)}")
            
            status = ", ".join(ats_list) if ats_list else "custom"
            print(f"{name} -> {status}")
    except Exception as e:
        print(f"{name} -> Error: {e}")
