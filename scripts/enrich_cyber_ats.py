#!/usr/bin/env python3
"""
Enrich UK Cyber Companies with Machine-Readable ATS configurations.
Probes:
- Greenhouse (boards-api.greenhouse.io)
- Ashby (api.ashbyhq.com)
- Lever (api.lever.co)
- Workable (apply.workable.com widget)
- Pinpoint (*.pinpointhq.com/postings.json)
- BambooHR (*.bamboohr.com/careers/list)
- Recruitee (*.recruitee.com/api/offers/)
- Teamtailor (*.teamtailor.com/jobs)
- Workday (*.myworkdayjobs.com CXS API)
- SmartRecruiters (with verified jobs)
Also parses company websites for career links and ATS redirects/iframes.
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

def get_candidate_slugs(c):
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
        for suf in ["-ltd", "-limited", "-uk", "-group", "-technologies", "-technology", "-security", "-cyber", "-solutions", "-systems"]:
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
    return [s for s in slugs if len(s) >= 2 and s not in ["the", "and", "uk", "ltd", "tech", "group", "cyber"]]

def probe_greenhouse(slug):
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=3.5, context=ctx) as r:
            if r.status == 200:
                data = json.loads(r.read().decode("utf-8", errors="ignore"))
                if "jobs" in data:
                    return {
                        "ats_type": "greenhouse",
                        "ats_identifier": slug,
                        "careers_url": f"https://boards.greenhouse.io/{slug}",
                        "open_roles_count": len(data["jobs"])
                    }
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
                    return {
                        "ats_type": "ashby",
                        "ats_identifier": slug,
                        "careers_url": f"https://jobs.ashbyhq.com/{slug}",
                        "open_roles_count": len(data["jobs"])
                    }
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
                    return {
                        "ats_type": "lever",
                        "ats_identifier": slug,
                        "careers_url": f"https://jobs.lever.co/{slug}",
                        "open_roles_count": len(data)
                    }
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
                    return {
                        "ats_type": "workable",
                        "ats_identifier": slug,
                        "careers_url": f"https://apply.workable.com/{slug}/",
                        "open_roles_count": len(data["jobs"])
                    }
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
                    return {
                        "ats_type": "bamboohr",
                        "ats_identifier": slug,
                        "careers_url": f"https://{slug}.bamboohr.com/careers",
                        "open_roles_count": len(data["result"])
                    }
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
                    return {
                        "ats_type": "pinpoint",
                        "ats_identifier": slug,
                        "careers_url": f"https://{slug}.pinpointhq.com/",
                        "open_roles_count": len(data["data"])
                    }
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
                    return {
                        "ats_type": "recruitee",
                        "ats_identifier": slug,
                        "careers_url": f"https://{slug}.recruitee.com/",
                        "open_roles_count": len(data["offers"])
                    }
    except:
        pass
    return None

def extract_ats_from_text(text, fallback_careers_url=None):
    if not text: return None

    # Workday
    m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.(?:wd\d+|myworkdayjobs)\.com/([a-zA-Z0-9_\-]+)", text)
    if m:
        subdomain = m.group(1)
        site = m.group(2)
        try:
            wd_url = f"https://{subdomain}.myworkdayjobs.com/wday/cxs/{subdomain}/{site}/jobs"
            payload = json.dumps({"appliedFacets": {}, "limit": 10, "offset": 0, "searchText": ""}).encode("utf-8")
            req = urllib.request.Request(wd_url, data=payload, headers={"Content-Type": "application/json", "User-Agent": HEADERS["User-Agent"]})
            with urllib.request.urlopen(req, timeout=4, context=ctx) as r:
                if r.status == 200:
                    d = json.loads(r.read().decode("utf-8", errors="ignore"))
                    return {
                        "ats_type": "workday",
                        "ats_identifier": f"{subdomain}/{site}",
                        "careers_url": f"https://{subdomain}.myworkdayjobs.com/{site}",
                        "open_roles_count": d.get("total", 0)
                    }
        except:
            pass
        return {
            "ats_type": "workday",
            "ats_identifier": f"{subdomain}/{site}",
            "careers_url": f"https://{subdomain}.myworkdayjobs.com/{site}",
            "open_roles_count": 0
        }

    # Greenhouse
    m = re.search(r"(?:boards\.greenhouse\.io|job-boards\.greenhouse\.io)/([a-zA-Z0-9_\-]+)", text)
    if m and m.group(1) not in ["embed", "js", "v1"]:
        slug = m.group(1)
        res = probe_greenhouse(slug)
        if res: return res
        return {
            "ats_type": "greenhouse",
            "ats_identifier": slug,
            "careers_url": f"https://boards.greenhouse.io/{slug}",
            "open_roles_count": 0
        }

    # Ashby
    m = re.search(r"jobs\.ashbyhq\.com/([a-zA-Z0-9_\-]+)", text)
    if m:
        slug = m.group(1)
        res = probe_ashby(slug)
        if res: return res
        return {
            "ats_type": "ashby",
            "ats_identifier": slug,
            "careers_url": f"https://jobs.ashbyhq.com/{slug}",
            "open_roles_count": 0
        }

    # Workable
    m = re.search(r"apply\.workable\.com/([a-zA-Z0-9_\-]+)", text)
    if m and m.group(1) not in ["j", "api", "widget"]:
        slug = m.group(1)
        res = probe_workable(slug)
        if res: return res
        return {
            "ats_type": "workable",
            "ats_identifier": slug,
            "careers_url": f"https://apply.workable.com/{slug}/",
            "open_roles_count": 0
        }

    # Lever
    m = re.search(r"jobs\.lever\.co/([a-zA-Z0-9_\-]+)", text)
    if m:
        slug = m.group(1)
        res = probe_lever(slug)
        if res: return res
        return {
            "ats_type": "lever",
            "ats_identifier": slug,
            "careers_url": f"https://jobs.lever.co/{slug}",
            "open_roles_count": 0
        }

    # Pinpoint
    m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.pinpointhq\.com", text)
    if m:
        slug = m.group(1)
        res = probe_pinpoint(slug)
        if res: return res

    # BambooHR
    m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.bamboohr\.com", text)
    if m and m.group(1) not in ["www", "help", "app"]:
        slug = m.group(1)
        res = probe_bamboohr(slug)
        if res: return res

    # Teamtailor
    m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.teamtailor\.com", text)
    if m:
        slug = m.group(1)
        return {
            "ats_type": "teamtailor",
            "ats_identifier": slug,
            "careers_url": f"https://{slug}.teamtailor.com/jobs",
            "open_roles_count": 0
        }

    # Recruitee
    m = re.search(r"https?://([a-zA-Z0-9_\-]+)\.recruitee\.com", text)
    if m and m.group(1) not in ["www", "app"]:
        slug = m.group(1)
        res = probe_recruitee(slug)
        if res: return res

    # SmartRecruiters (only if confirmed with postings)
    m = re.search(r"jobs\.smartrecruiters\.com/([a-zA-Z0-9_\-]+)", text)
    if m:
        slug = m.group(1)
        try:
            sr_url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=5"
            req = urllib.request.Request(sr_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=3.5, context=ctx) as r:
                if r.status == 200:
                    d = json.loads(r.read().decode("utf-8", errors="ignore"))
                    total = d.get("totalFound", 0)
                    if total > 0:
                        return {
                            "ats_type": "smartrecruiters",
                            "ats_identifier": slug,
                            "careers_url": f"https://jobs.smartrecruiters.com/{slug}",
                            "open_roles_count": total
                        }
        except:
            pass

    return None

def crawl_company_site(company):
    website = company.get("website", "")
    if not website: return None
    try:
        req = urllib.request.Request(website, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
            final_home = r.url
            html = r.read().decode("utf-8", errors="ignore")
            
            # Check homepage HTML directly for ATS URLs
            res = extract_ats_from_text(html)
            if res: return res

            # Look for careers links on homepage
            matches = re.findall(r'<a[^>]+href=[\"\']([^\"\']+)[\"\'][^>]*>([\s\S]*?)<\/a>', html, re.IGNORECASE)
            career_urls = []
            for href, text in matches:
                clean_t = re.sub(r"<[^>]+>", "", text).strip().lower()
                href_l = href.lower()
                if any(w in clean_t for w in ["career", "job", "vacanc", "work with us", "join us", "join our team"]) or any(w in href_l for w in ["/career", "/job", "/vacanc"]):
                    full_u = urllib.parse.urljoin(final_home, href)
                    if full_u not in career_urls and not full_u.endswith(("#", ".pdf", ".jpg", ".png")):
                        career_urls.append(full_u)

            # Check up to 2 career URLs found
            for cu in career_urls[:2]:
                res = extract_ats_from_text(cu)
                if res: return res

                try:
                    creq = urllib.request.Request(cu, headers=HEADERS)
                    with urllib.request.urlopen(creq, timeout=5, context=ctx) as cr:
                        c_final = cr.url
                        res = extract_ats_from_text(c_final)
                        if res: return res

                        chtml = cr.read().decode("utf-8", errors="ignore")
                        res = extract_ats_from_text(chtml, fallback_careers_url=cu)
                        if res: return res
                except:
                    pass
    except:
        pass
    return None

def verify_company(c):
    # 1. Probe known slugs across all standard ATS APIs
    slugs = get_candidate_slugs(c)
    for s in slugs:
        res = (
            probe_greenhouse(s) or
            probe_ashby(s) or
            probe_lever(s) or
            probe_pinpoint(s) or
            probe_bamboohr(s) or
            probe_recruitee(s) or
            probe_workable(s)
        )
        if res:
            return c, res

    # 2. Check careers_url in metadata
    res = extract_ats_from_text(c.get("careers_url", ""))
    if res:
        return c, res

    # 3. Crawl company website
    res = crawl_company_site(c)
    if res:
        return c, res

    return c, None

def main():
    print("Reading cyber_companies.json...")
    with open(DB_PATH, "r", encoding="utf-8") as f:
        companies = json.load(f)

    print(f"Analyzing and validating ATS for {len(companies)} UK cybersecurity companies...")

    discovered = {}
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(verify_company, c): c for c in companies}
        for fut in as_completed(futures):
            c, res = fut.result()
            if res:
                discovered[c["id"]] = res
                print(f"🎯 [{res['ats_type'].upper()}] {c['name']} -> ID: {res['ats_identifier']} | {res['careers_url']} ({res.get('open_roles_count', 0)} jobs)")

    print(f"\n==========================================")
    print(f"Total Verified Machine-Readable ATS Found: {len(discovered)} / {len(companies)}")
    print(f"==========================================")

    updated_count = 0
    for c in companies:
        cid = c["id"]
        if cid in discovered:
            meta = discovered[cid]
            c["ats_type"] = meta["ats_type"]
            c["ats_identifier"] = meta["ats_identifier"]
            if meta.get("careers_url"):
                c["careers_url"] = meta["careers_url"]
            if "open_roles_count" in meta and meta["open_roles_count"] > 0:
                c["open_roles_count"] = meta["open_roles_count"]
            updated_count += 1

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(companies, f, indent=2, ensure_ascii=False)

    print(f"Successfully saved {updated_count} updated company records into {DB_PATH}.")

if __name__ == "__main__":
    main()
