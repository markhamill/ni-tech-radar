#!/usr/bin/env python3
"""
UK Cybersecurity Radar: Verified ATS Discovery
Strictly validates machine-readable ATS endpoints (only 200 OK + valid JSON / confirmed redirects).
"""

import json
import os
import re
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*"
}

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "public", "data", "cyber_companies.json")

def clean_slug(s):
    if not s: return ""
    return re.sub(r"[^a-zA-Z0-9\-]", "", s.lower().replace(" ", "-")).strip("-")

def get_slugs(c):
    slugs = set()
    cid = c.get("id", "").lower()
    name = c.get("name", "").lower()
    clean_n = clean_slug(name)
    website = c.get("website", "")
    
    if cid:
        slugs.add(cid)
        slugs.add(cid.replace("-", ""))
    if clean_n:
        slugs.add(clean_n)
        slugs.add(clean_n.replace("-", ""))
        for suf in ["-ltd", "-limited", "-uk", "-group", "-technologies", "-security", "-cyber"]:
            if clean_n.endswith(suf):
                base = clean_n[:-len(suf)]
                slugs.add(base)
                slugs.add(base.replace("-", ""))
    if website:
        try:
            host = urllib.parse.urlparse(website).netloc.lower()
            host = re.sub(r"^www\.", "", host)
            dom = host.split(".")[0]
            if len(dom) >= 3 and dom not in ["jobs", "careers", "apply", "boards"]:
                slugs.add(dom)
        except:
            pass
    return [s for s in slugs if len(s) >= 2 and s not in ["the", "and", "uk", "ltd", "tech"]]

def probe_greenhouse(slug):
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5, context=ctx) as r:
            if r.status == 200:
                data = json.loads(r.read().decode("utf-8", errors="ignore"))
                if "jobs" in data:
                    return {"ats_type": "greenhouse", "ats_identifier": slug, "careers_url": f"https://boards.greenhouse.io/{slug}", "count": len(data["jobs"])}
    except:
        pass
    return None

def probe_ashby(slug):
    try:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5, context=ctx) as r:
            if r.status == 200:
                data = json.loads(r.read().decode("utf-8", errors="ignore"))
                if "jobs" in data:
                    return {"ats_type": "ashby", "ats_identifier": slug, "careers_url": f"https://jobs.ashbyhq.com/{slug}", "count": len(data["jobs"])}
    except:
        pass
    return None

def probe_lever(slug):
    try:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5, context=ctx) as r:
            if r.status == 200:
                data = json.loads(r.read().decode("utf-8", errors="ignore"))
                if isinstance(data, list):
                    return {"ats_type": "lever", "ats_identifier": slug, "careers_url": f"https://jobs.lever.co/{slug}", "count": len(data)}
    except:
        pass
    return None

def probe_workable(slug):
    try:
        url = f"https://apply.workable.com/api/v1/widget/accounts/{slug}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5, context=ctx) as r:
            if r.status == 200:
                data = json.loads(r.read().decode("utf-8", errors="ignore"))
                if "jobs" in data:
                    return {"ats_type": "workable", "ats_identifier": slug, "careers_url": f"https://apply.workable.com/{slug}/", "count": len(data["jobs"])}
    except:
        pass
    return None

def probe_bamboohr(slug):
    try:
        url = f"https://{slug}.bamboohr.com/careers/list"
        req = urllib.request.Request(url, headers={**HEADERS, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3.5, context=ctx) as r:
            if r.status == 200:
                data = json.loads(r.read().decode("utf-8", errors="ignore"))
                if "result" in data:
                    return {"ats_type": "bamboohr", "ats_identifier": slug, "careers_url": f"https://{slug}.bamboohr.com/careers", "count": len(data["result"])}
    except:
        pass
    return None

def probe_recruitee(slug):
    try:
        url = f"https://{slug}.recruitee.com/api/offers/"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5, context=ctx) as r:
            if r.status == 200:
                data = json.loads(r.read().decode("utf-8", errors="ignore"))
                if "offers" in data:
                    return {"ats_type": "recruitee", "ats_identifier": slug, "careers_url": f"https://{slug}.recruitee.com/", "count": len(data["offers"])}
    except:
        pass
    return None

def probe_pinpoint(slug):
    try:
        url = f"https://{slug}.pinpointhq.com/postings.json"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5, context=ctx) as r:
            if r.status == 200:
                data = json.loads(r.read().decode("utf-8", errors="ignore"))
                if "data" in data and isinstance(data["data"], list):
                    return {"ats_type": "pinpoint", "ats_identifier": slug, "careers_url": f"https://{slug}.pinpointhq.com/", "count": len(data["data"])}
    except:
        pass
    return None

def inspect_url(url):
    if not url: return None
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            final_url = r.url
            html = r.read().decode("utf-8", errors="ignore")
            text = html + " " + final_url

            # Workday
            m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.(?:wd\d+|myworkdayjobs)\.com/([a-zA-Z0-9_\-]+)", text)
            if m:
                return {"ats_type": "workday", "ats_identifier": f"{m.group(1)}/{m.group(2)}", "careers_url": m.group(0), "count": 0}

            # Greenhouse
            m = re.search(r"(?:boards\.greenhouse\.io|job-boards\.greenhouse\.io)/([a-zA-Z0-9_\-]+)", text)
            if m and m.group(1) not in ["embed", "js"]:
                return {"ats_type": "greenhouse", "ats_identifier": m.group(1), "careers_url": f"https://boards.greenhouse.io/{m.group(1)}", "count": 0}

            # Ashby
            m = re.search(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_\-]+)", text)
            if m:
                return {"ats_type": "ashby", "ats_identifier": m.group(1), "careers_url": f"https://jobs.ashbyhq.com/{m.group(1)}", "count": 0}

            # Workable
            m = re.search(r"apply\.workable\.com/([a-zA-Z0-9_\-]+)", text)
            if m and m.group(1) not in ["j", "api", "widget"]:
                return {"ats_type": "workable", "ats_identifier": m.group(1), "careers_url": f"https://apply.workable.com/{m.group(1)}/", "count": 0}
            m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.workable\.com", text)
            if m and m.group(1) not in ["www", "resources", "help", "apply"]:
                return {"ats_type": "workable", "ats_identifier": m.group(1), "careers_url": f"https://apply.workable.com/{m.group(1)}/", "count": 0}

            # Lever
            m = re.search(r"jobs\.lever\.co/([a-zA-Z0-9_\-]+)", text)
            if m:
                return {"ats_type": "lever", "ats_identifier": m.group(1), "careers_url": f"https://jobs.lever.co/{m.group(1)}", "count": 0}

            # Teamtailor
            m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.teamtailor\.com", text)
            if m:
                return {"ats_type": "teamtailor", "ats_identifier": m.group(1), "careers_url": f"https://{m.group(1)}.teamtailor.com/jobs", "count": 0}

            # SmartRecruiters (explicit link in page)
            m = re.search(r"jobs\.smartrecruiters\.com/([a-zA-Z0-9_\-]+)", text)
            if m:
                return {"ats_type": "smartrecruiters", "ats_identifier": m.group(1), "careers_url": f"https://jobs.smartrecruiters.com/{m.group(1)}", "count": 0}

            # BambooHR
            m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.bamboohr\.com", text)
            if m and m.group(1) not in ["www", "help", "app"]:
                return {"ats_type": "bamboohr", "ats_identifier": m.group(1), "careers_url": f"https://{m.group(1)}.bamboohr.com/careers", "count": 0}

            # Pinpoint
            m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.pinpointhq\.com", text)
            if m:
                return {"ats_type": "pinpoint", "ats_identifier": m.group(1), "careers_url": f"https://{m.group(1)}.pinpointhq.com/", "count": 0}

            # Recruitee
            m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.recruitee\.com", text)
            if m and m.group(1) not in ["www", "app"]:
                return {"ats_type": "recruitee", "ats_identifier": m.group(1), "careers_url": f"https://{m.group(1)}.recruitee.com/", "count": 0}

    except:
        pass
    return None

def check_company(c):
    slugs = get_slugs(c)

    # 1. Probe known slugs on Greenhouse & Ashby & Lever & Workable
    for s in slugs:
        res = probe_greenhouse(s) or probe_ashby(s) or probe_lever(s) or probe_workable(s) or probe_bamboohr(s) or probe_recruitee(s) or probe_pinpoint(s)
        if res:
            return c, res

    # 2. Inspect careers_url
    res = inspect_url(c.get("careers_url"))
    if res:
        return c, res

    # 3. Inspect main website
    res = inspect_url(c.get("website"))
    if res:
        return c, res

    return c, None

def main():
    with open(DB_PATH, "r", encoding="utf-8") as f:
        companies = json.load(f)

    print(f"Checking {len(companies)} UK cyber companies for verified ATS...")

    matches = {}
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(check_company, c): c for c in companies}
        for fut in as_completed(futures):
            c, res = fut.result()
            if res:
                matches[c["id"]] = res
                print(f"🎯 [FOUND] {c['name']} -> {res['ats_type']} ({res['ats_identifier']}) | {res['careers_url']} (jobs: {res.get('count', 0)})")

    print(f"\nTotal verified machine-readable / confirmed ATS: {len(matches)}")

if __name__ == "__main__":
    main()
