#!/usr/bin/env python3
"""
UK Cybersecurity Radar: ATS API Discovery & Validator
Systematically checks all companies in cyber_companies.json to uncover
machine-readable ATS endpoints (Greenhouse, Ashby, Workable, Lever, Teamtailor,
SmartRecruiters, BambooHR, Pinpoint, Recruitee, JazzHR, Workday).
"""

import json
import os
import re
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "public", "data", "cyber_companies.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_slug(s):
    if not s:
        return ""
    return re.sub(r"[^a-zA-Z0-9\-]", "", s.lower().replace(" ", "-")).strip("-")

def get_slug_candidates(company):
    candidates = set()
    name = company.get("name", "").lower()
    cid = company.get("id", "").lower()
    website = company.get("website", "")
    careers = company.get("careers_url", "")
    
    # 1. Direct ID & variations
    if cid:
        candidates.add(cid)
        candidates.add(cid.replace("-", ""))
        candidates.add(cid.replace("cyber", "").replace("-", "").strip())
        candidates.add(cid.replace("security", "").replace("-", "").strip())
    
    # 2. Name variations
    clean_n = clean_slug(name)
    if clean_n:
        candidates.add(clean_n)
        candidates.add(clean_n.replace("-", ""))
        for suffix in ["-ltd", "-limited", "-uk", "-group", "-technologies", "-security", "-cyber"]:
            if clean_n.endswith(suffix):
                stripped = clean_n[:-len(suffix)]
                candidates.add(stripped)
                candidates.add(stripped.replace("-", ""))

    # 3. Domain variations
    for u in [website, careers]:
        if u:
            try:
                host = urllib.parse.urlparse(u).netloc.lower()
                host = re.sub(r"^www\.", "", host)
                dom_name = host.split(".")[0]
                if len(dom_name) >= 3 and dom_name not in ["jobs", "careers", "apply", "boards"]:
                    candidates.add(dom_name)
            except Exception:
                pass

    return [c for c in candidates if len(c) >= 2 and c not in ["the", "and", "uk", "ltd"]]

def test_api_slug(slug):
    """Probes standard public ATS APIs with a slug candidate."""
    # 1. Greenhouse
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                jobs = data.get("jobs", [])
                return {
                    "ats_type": "greenhouse",
                    "ats_identifier": slug,
                    "careers_url": f"https://boards.greenhouse.io/{slug}",
                    "jobs_count": len(jobs)
                }
    except Exception:
        pass

    # 2. Ashby
    try:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                jobs = data.get("jobs", [])
                return {
                    "ats_type": "ashby",
                    "ats_identifier": slug,
                    "careers_url": f"https://jobs.ashbyhq.com/{slug}",
                    "jobs_count": len(jobs)
                }
    except Exception:
        pass

    # 3. Workable
    try:
        url = f"https://apply.workable.com/api/v1/widget/accounts/{slug}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                jobs = data.get("jobs", [])
                return {
                    "ats_type": "workable",
                    "ats_identifier": slug,
                    "careers_url": f"https://apply.workable.com/{slug}/",
                    "jobs_count": len(jobs)
                }
    except Exception:
        pass

    # 4. Lever
    try:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                if isinstance(data, list):
                    return {
                        "ats_type": "lever",
                        "ats_identifier": slug,
                        "careers_url": f"https://jobs.lever.co/{slug}",
                        "jobs_count": len(data)
                    }
    except Exception:
        pass

    # 5. SmartRecruiters
    try:
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                total = data.get("totalFound", 0)
                return {
                    "ats_type": "smartrecruiters",
                    "ats_identifier": slug,
                    "careers_url": f"https://jobs.smartrecruiters.com/{slug}",
                    "jobs_count": total
                }
    except Exception:
        pass

    # 6. Recruitee
    try:
        url = f"https://{slug}.recruitee.com/api/offers/"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                offers = data.get("offers", [])
                return {
                    "ats_type": "recruitee",
                    "ats_identifier": slug,
                    "careers_url": f"https://{slug}.recruitee.com/",
                    "jobs_count": len(offers)
                }
    except Exception:
        pass

    # 7. Pinpoint
    try:
        url = f"https://{slug}.pinpointhq.com/postings.json"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                jobs = data.get("data", [])
                return {
                    "ats_type": "pinpoint",
                    "ats_identifier": slug,
                    "careers_url": f"https://{slug}.pinpointhq.com/",
                    "jobs_count": len(jobs)
                }
    except Exception:
        pass

    # 8. BambooHR
    try:
        url = f"https://{slug}.bamboohr.com/careers/list"
        req = urllib.request.Request(url, headers={**HEADERS, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                jobs = data.get("result", [])
                return {
                    "ats_type": "bamboohr",
                    "ats_identifier": slug,
                    "careers_url": f"https://{slug}.bamboohr.com/careers",
                    "jobs_count": len(jobs)
                }
    except Exception:
        pass

    return None

def inspect_page_html(url):
    """Fetches careers page HTML and searches for embedded ATS signatures and links."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as resp:
            final_url = resp.url
            html = resp.read().decode("utf-8", errors="ignore")
            combined = html + " " + final_url

            # Workday
            m_wd = re.search(r"https?://([a-zA-Z0-9_\-]+)\.(?:wd\d+|myworkdayjobs)\.com/([a-zA-Z0-9_\-]+)", combined)
            if m_wd:
                return {
                    "ats_type": "workday",
                    "ats_identifier": f"{m_wd.group(1)}/{m_wd.group(2)}",
                    "careers_url": m_wd.group(0),
                    "jobs_count": 0
                }

            # Greenhouse
            m_gh = re.search(r"(?:boards\.greenhouse\.io|job-boards\.greenhouse\.io)/([a-zA-Z0-9_\-]+)", combined)
            if m_gh:
                slug = m_gh.group(1)
                return {
                    "ats_type": "greenhouse",
                    "ats_identifier": slug,
                    "careers_url": f"https://boards.greenhouse.io/{slug}",
                    "jobs_count": 0
                }
            m_gh_script = re.search(r"boards-api\.greenhouse\.io/v1/boards/([a-zA-Z0-9_\-]+)", combined)
            if m_gh_script:
                slug = m_gh_script.group(1)
                return {
                    "ats_type": "greenhouse",
                    "ats_identifier": slug,
                    "careers_url": f"https://boards.greenhouse.io/{slug}",
                    "jobs_count": 0
                }

            # Ashby
            m_ashby = re.search(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_\-]+)", combined)
            if m_ashby:
                slug = m_ashby.group(1)
                return {
                    "ats_type": "ashby",
                    "ats_identifier": slug,
                    "careers_url": f"https://jobs.ashbyhq.com/{slug}",
                    "jobs_count": 0
                }

            # Workable
            m_workable = re.search(r"apply\.workable\.com/([a-zA-Z0-9_\-]+)", combined)
            if m_workable:
                slug = m_workable.group(1)
                return {
                    "ats_type": "workable",
                    "ats_identifier": slug,
                    "careers_url": f"https://apply.workable.com/{slug}/",
                    "jobs_count": 0
                }
            m_w_sub = re.search(r"https?://([a-zA-Z0-9_\-]+)\.workable\.com", combined)
            if m_w_sub and m_w_sub.group(1) not in ["www", "resources", "help", "apply"]:
                slug = m_w_sub.group(1)
                return {
                    "ats_type": "workable",
                    "ats_identifier": slug,
                    "careers_url": f"https://apply.workable.com/{slug}/",
                    "jobs_count": 0
                }

            # Lever
            m_lever = re.search(r"jobs\.lever\.co/([a-zA-Z0-9_\-]+)", combined)
            if m_lever:
                slug = m_lever.group(1)
                return {
                    "ats_type": "lever",
                    "ats_identifier": slug,
                    "careers_url": f"https://jobs.lever.co/{slug}",
                    "jobs_count": 0
                }

            # Teamtailor
            m_tt = re.search(r"https?://([a-zA-Z0-9_\-]+)\.teamtailor\.com", combined)
            if m_tt:
                slug = m_tt.group(1)
                return {
                    "ats_type": "teamtailor",
                    "ats_identifier": slug,
                    "careers_url": f"https://{slug}.teamtailor.com/jobs",
                    "jobs_count": 0
                }
            if "teamtailor" in html.lower() and "careers." in final_url:
                return {
                    "ats_type": "teamtailor",
                    "ats_identifier": urllib.parse.urlparse(final_url).netloc,
                    "careers_url": final_url,
                    "jobs_count": 0
                }

            # SmartRecruiters
            m_sr = re.search(r"jobs\.smartrecruiters\.com/([a-zA-Z0-9_\-]+)", combined)
            if m_sr:
                slug = m_sr.group(1)
                return {
                    "ats_type": "smartrecruiters",
                    "ats_identifier": slug,
                    "careers_url": f"https://jobs.smartrecruiters.com/{slug}",
                    "jobs_count": 0
                }

            # BambooHR
            m_bamboo = re.search(r"https?://([a-zA-Z0-9_\-]+)\.bamboohr\.com", combined)
            if m_bamboo:
                slug = m_bamboo.group(1)
                return {
                    "ats_type": "bamboohr",
                    "ats_identifier": slug,
                    "careers_url": f"https://{slug}.bamboohr.com/careers",
                    "jobs_count": 0
                }

            # Pinpoint
            m_pinpoint = re.search(r"https?://([a-zA-Z0-9_\-]+)\.pinpointhq\.com", combined)
            if m_pinpoint:
                slug = m_pinpoint.group(1)
                return {
                    "ats_type": "pinpoint",
                    "ats_identifier": slug,
                    "careers_url": f"https://{slug}.pinpointhq.com/",
                    "jobs_count": 0
                }

            # Recruitee
            m_recruitee = re.search(r"https?://([a-zA-Z0-9_\-]+)\.recruitee\.com", combined)
            if m_recruitee:
                slug = m_recruitee.group(1)
                return {
                    "ats_type": "recruitee",
                    "ats_identifier": slug,
                    "careers_url": f"https://{slug}.recruitee.com/",
                    "jobs_count": 0
                }

            # Breezy HR
            m_breezy = re.search(r"https?://([a-zA-Z0-9_\-]+)\.breezy\.hr", combined)
            if m_breezy:
                slug = m_breezy.group(1)
                return {
                    "ats_type": "breezy",
                    "ats_identifier": slug,
                    "careers_url": f"https://{slug}.breezy.hr/",
                    "jobs_count": 0
                }

            # JazzHR
            m_jazz = re.search(r"https?://([a-zA-Z0-9_\-]+)\.applytojob\.com", combined)
            if m_jazz:
                slug = m_jazz.group(1)
                return {
                    "ats_type": "jazzhr",
                    "ats_identifier": slug,
                    "careers_url": f"https://{slug}.applytojob.com/",
                    "jobs_count": 0
                }

    except Exception:
        pass
    return None

def process_company(company):
    # Check existing validated ATS first
    curr_ats = company.get("ats_type")
    if curr_ats and curr_ats not in ["custom", "manual"]:
        slug = company.get("ats_identifier") or clean_slug(company.get("name"))
        probe = test_api_slug(slug)
        if probe:
            return company, probe

    slugs = get_slug_candidates(company)
    
    # Step 1: Direct API Slug probing
    for slug in slugs:
        res = test_api_slug(slug)
        if res:
            return company, res

    # Step 2: HTML Page Inspection on careers_url
    careers_url = company.get("careers_url")
    if careers_url:
        res = inspect_page_html(careers_url)
        if res:
            return company, res

    # Step 3: HTML Page Inspection on main website
    website = company.get("website")
    if website and website != careers_url:
        res = inspect_page_html(website)
        if res:
            return company, res

    return company, None

def main():
    if not os.path.exists(DB_PATH):
        print(f"File not found: {DB_PATH}")
        return

    with open(DB_PATH, "r", encoding="utf-8") as f:
        companies = json.load(f)

    print(f"Loaded {len(companies)} companies from cyber_companies.json. Starting multi-threaded ATS validation...")

    results = {}

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(process_company, c): c for c in companies}
        for future in as_completed(futures):
            c, found = future.result()
            cid = c["id"]
            if found:
                results[cid] = found
                print(f"🎯 [MATCH] {c['name']} -> {found['ats_type']} ({found.get('ats_identifier')})")

    print(f"\n==================================================")
    print(f"Scan complete. Found machine-readable ATS for {len(results)} companies!")
    print(f"==================================================\n")

    updated_count = 0
    for c in companies:
        cid = c["id"]
        if cid in results:
            found = results[cid]
            c["ats_type"] = found["ats_type"]
            c["ats_identifier"] = found["ats_identifier"]
            if found.get("careers_url") and not c.get("careers_url", "").startswith("https://boards.greenhouse.io"):
                c["careers_url"] = found["careers_url"]
            updated_count += 1

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)

    print(f"Updated cyber_companies.json with {updated_count} confirmed ATS configurations.")

if __name__ == "__main__":
    main()
