#!/usr/bin/env python3
"""
UK Cybersecurity Company Index Builder
Aggregates UK cybersecurity companies into public/data/cyber_companies.json
Schema matches public/data/companies.json with all 20 required keys.
"""

import urllib.request, re, json, time, os, sys
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(BASE_DIR, "public", "data", "cyber_companies.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
}

def clean_company_name(raw_name):
    if not raw_name: return ""
    name = raw_name.split("|")[0].split(" - ")[0].split("—")[0].strip()
    name = re.sub(r"\b(Ltd|Limited|Plc|LLP|Inc|Corporation|Corp)\.?\b", "", name, flags=re.I).strip()
    name = re.sub(r"^(Welcome to|About)\s+", "", name, flags=re.I).strip()
    name = re.sub(r"\s+", " ", name).strip()
    return name

def get_root_domain(url):
    if not url: return ""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc.split(":")[0]
    except:
        return ""

def slugify(text):
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text

def infer_location(address, postcode):
    addr_combined = f"{address} {postcode}".upper()
    if any(k in addr_combined for k in ["LONDON", "EC1", "EC2", "EC3", "EC4", "WC1", "WC2", "E1", "E14", "SW1", "SE1", "W1"]):
        return "London", address or "London, UK"
    if "CAMBRIDGE" in addr_combined or "CB" in addr_combined:
        return "Cambridge", address or "Cambridge, UK"
    if "CHELTENHAM" in addr_combined or "GL5" in addr_combined or "GLOS" in addr_combined:
        return "Cheltenham", address or "Cheltenham, UK"
    if "MANCHESTER" in addr_combined or "M1" in addr_combined or "M2" in addr_combined:
        return "Manchester", address or "Manchester, UK"
    if "BRISTOL" in addr_combined or "BS" in addr_combined:
        return "Bristol", address or "Bristol, UK"
    if "BELFAST" in addr_combined or "BT" in addr_combined:
        return "Belfast", address or "Belfast, UK"
    if "EDINBURGH" in addr_combined or "EH" in addr_combined:
        return "Edinburgh", address or "Edinburgh, UK"
    if "GLASGOW" in addr_combined or "G1" in addr_combined or "G2" in addr_combined:
        return "Glasgow", address or "Glasgow, UK"
    if "OXFORD" in addr_combined or "OX" in addr_combined:
        return "Oxford", address or "Oxford, UK"
    if "READING" in addr_combined or "RG" in addr_combined:
        return "Reading", address or "Reading, UK"
    if "BIRMINGHAM" in addr_combined or "B1" in addr_combined:
        return "Birmingham", address or "Birmingham, UK"
    if "LEEDS" in addr_combined or "LS" in addr_combined:
        return "Leeds", address or "Leeds, UK"
    return "United Kingdom (Hybrid)", address or "United Kingdom"

def infer_subsector(desc, cat, kw):
    text = f"{desc} {cat} {' '.join(kw) if isinstance(kw, list) else kw}".lower()
    if any(k in text for k in ["identity", "iam", "biometric", "passwordless", "credential", "pam"]):
        return "Identity & Access Management (IAM)"
    if any(k in text for k in ["threat intelligence", "osint", "dark web", "adversary", "recon"]):
        return "Threat Intelligence & OSINT"
    if any(k in text for k in ["detection", "ndr", "edr", "xdr", "soc", "siem", "mdr", "autonomous"]):
        return "Detection & Response (EDR/NDR/XDR)"
    if any(k in text for k in ["appsec", "application security", "devsecops", "code security", "vulnerability scan", "pentest", "penetration test"]):
        return "Application Security & Vulnerability Management"
    if any(k in text for k in ["cloud security", "cspm", "cwpp", "container", "kubernetes"]):
        return "Cloud & Container Security"
    if any(k in text for k in ["ot ", "iot", "industrial", "scada", "ics", "automotive"]):
        return "OT, IoT & Industrial Cybersecurity"
    if any(k in text for k in ["grc", "compliance", "iso 27001", "risk assessment", "supply chain"]):
        return "Governance, Risk & Compliance (GRC)"
    if any(k in text for k in ["email", "phishing", "dlp", "data loss", "human risk"]):
        return "Email Security & Human Risk Management"
    if any(k in text for k in ["crypto", "blockchain", "web3"]):
        return "Blockchain & Financial Cyber Security"
    return "Cybersecurity Software & Services"

import ssl

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

def scrape_cyberdirectory():
    print("Scraping UK Cyber Directory (cyberdirectory.co)...")
    sitemap_url = "https://www.cyberdirectory.co/sitemap.xml"
    try:
        req = urllib.request.Request(sitemap_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12, context=SSL_CTX) as r:
            content = r.read().decode("utf-8")
            urls = re.findall(r"<loc>(https?://[^\s<]+)</loc>", content)
    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return []

    profile_urls = [u for u in urls if u not in ["https://www.cyberdirectory.co", "https://www.cyberdirectory.co/listing"]]
    print(f"Found {len(profile_urls)} company profiles on cyberdirectory.co")

    def fetch_profile(u):
        try:
            r = urllib.request.Request(u, headers=HEADERS)
            with urllib.request.urlopen(r, timeout=8, context=SSL_CTX) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                
                # Extract clean website link
                m_site = re.search(r"<a[^>]+href=[\"\x27](https?://(?!www\.cyberdirectory\.co)[^\s\"\x27]+)[\"\x27][^>]*>(?:(?!<\/a>)[\s\S])*?Visit Website", html, re.I)
                website = m_site.group(1).rstrip("/") if m_site else ""
                
                # Extract JSON-LD metadata
                scripts = re.findall(r"<script[^>]+type=[\"\x27]application/ld\+json[\"\x27][^>]*>(.*?)</script>", html, re.DOTALL)
                name, desc, addr, postcode, cat, kw = "", "", "", "", "", []
                for s in scripts:
                    try:
                        d = json.loads(s)
                        if d.get("@type") in ["LocalBusiness", "Organization", "Corporation"]:
                            name = d.get("name", "")
                            desc = d.get("description", "")
                            addr = d.get("address", {}).get("streetAddress", "") if isinstance(d.get("address"), dict) else ""
                            postcode = d.get("address", {}).get("postalCode", "") if isinstance(d.get("address"), dict) else ""
                            cat = d.get("category", "")
                            kw = d.get("keywords", [])
                            break
                    except:
                        pass
                
                if not name:
                    tm = re.search(r"<title>(.*?)</title>", html, re.I)
                    name = tm.group(1) if tm else u.split("/")[-1].replace("-", " ").title()
                
                clean_name = clean_company_name(name)
                if not clean_name or not website:
                    return None
                
                # Filter out solo / non-tech
                lower_desc = (desc or "").lower()
                if any(x in lower_desc for x in ["freelance", "copywriting", "graphic design", "accountancy services"]):
                    return None
                
                loc_city, loc_addr = infer_location(addr, postcode)
                sub_sec = infer_subsector(desc, cat, kw)
                
                return {
                    "id": slugify(clean_name),
                    "name": clean_name,
                    "website": website,
                    "careers_url": f"{website}/careers",
                    "ats_type": "custom",
                    "industry": "Cybersecurity & Information Security",
                    "sub_sector": sub_sec,
                    "scale_tier": "Scaleup (20-100)",
                    "headcount_estimate": "25-75",
                    "funding_type": "Privately Owned",
                    "location": loc_city,
                    "address": loc_addr,
                    "description": desc or f"{clean_name} provides specialised cybersecurity software and services in the UK.",
                    "key_products": [clean_name + " Platform"],
                    "key_people": "Executive Leadership",
                    "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                    "open_roles_count": 0,
                    "product_roles_count": 0,
                    "active_product_roles": []
                }
        except:
            return None

    with ThreadPoolExecutor(max_workers=20) as ex:
        results = list(filter(None, ex.map(fetch_profile, profile_urls)))

    print(f"Successfully scraped {len(results)} companies from cyberdirectory.co")
    return results

CURATED_CYBER_COMPANIES = [
    {
        "id": "darktrace",
        "name": "Darktrace",
        "website": "https://darktrace.com",
        "careers_url": "https://darktrace.com/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Detection & Response (EDR/NDR/XDR)",
        "scale_tier": "Large Enterprise / FDI Hub (500+)",
        "headcount_estimate": "2,200+",
        "funding_type": "PE-backed (Thoma Bravo)",
        "location": "Cambridge",
        "address": "Turing House, Cambridge Science Park, Milton Rd, Cambridge CB4 0GD",
        "description": "Global leader in AI-native cybersecurity, delivering autonomous threat detection, investigation, and response across network, cloud, email, and endpoints.",
        "key_products": ["Darktrace Enterprise Immune System", "Darktrace Cyber AI Analyst", "Darktrace PREVENT & HEAL"],
        "key_people": "Ed Jennings (CEO), Max Heinemeyer (CPO), Dr. Beverly McCann (VP Product)"
    },
    {
        "id": "sophos",
        "name": "Sophos",
        "website": "https://www.sophos.com",
        "careers_url": "https://sophos.wd3.myworkdayjobs.com/Sophos_Careers",
        "ats_type": "workday",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Detection & Response (EDR/NDR/XDR)",
        "scale_tier": "Large Enterprise / FDI Hub (500+)",
        "headcount_estimate": "4,500+",
        "funding_type": "PE-backed (Thoma Bravo)",
        "location": "Oxford",
        "address": "The Pentagon, Abingdon Science Park, Abingdon, OX14 3YP",
        "description": "Global cybersecurity innovator providing managed threat response (MDR) and synchronized next-gen endpoint, network, email, and cloud security.",
        "key_products": ["Sophos Intercept X", "Sophos Firewall", "Sophos Central Cloud Console", "Sophos MDR"],
        "key_people": "Joe Levy (CEO), Raja Patel (CPO)"
    },
    {
        "id": "ncc-group",
        "name": "NCC Group",
        "website": "https://www.nccgroup.com",
        "careers_url": "https://jobs.smartrecruiters.com/NCCGroup",
        "ats_type": "smartrecruiters",
        "ats_identifier": "NCCGroup",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Application Security & Vulnerability Management",
        "scale_tier": "Large Enterprise / FDI Hub (500+)",
        "headcount_estimate": "2,000+",
        "funding_type": "Public (LSE: NCC)",
        "location": "Manchester",
        "address": "XYZ Building, 2 Hardman Boulevard, Spinningfields, Manchester M3 3AQ",
        "description": "Global cyber security and software escrow resilience leader, providing penetration testing, red teaming, incident response, and software resilience solutions.",
        "key_products": ["NCC Group Software Resilience & Escrow", "Penetration Testing Services", "Managed Detection"],
        "key_people": "Mike Maddison (CEO)"
    },
    {
        "id": "snyk",
        "name": "Snyk",
        "website": "https://snyk.io",
        "careers_url": "https://boards.greenhouse.io/snyk",
        "ats_type": "greenhouse",
        "ats_identifier": "snyk",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Application Security & Vulnerability Management",
        "scale_tier": "Large Enterprise / FDI Hub (500+)",
        "headcount_estimate": "1,000+",
        "funding_type": "VC-backed (Accel, Tiger Global)",
        "location": "London",
        "address": "100 New Bridge St, London EC4V 6JA",
        "description": "Developer-first cloud-native security platform helping software-driven businesses develop fast and stay secure across code, dependencies, containers, and IaC.",
        "key_products": ["Snyk Open Source", "Snyk Code (SAST)", "Snyk Container", "Snyk IaC"],
        "key_people": "Peter McKay (CEO), Guy Podjarny (Founder)"
    },
    {
        "id": "immersive-labs",
        "name": "Immersive Labs",
        "website": "https://www.immersivelabs.com",
        "careers_url": "https://jobs.ashbyhq.com/immersivelabs",
        "ats_type": "ashby",
        "ats_identifier": "immersivelabs",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Cyber Workforce Development & Training",
        "scale_tier": "Mid-Market (100-500)",
        "headcount_estimate": "300-400",
        "funding_type": "VC-backed (Insight Partners, Summit)",
        "location": "Bristol",
        "address": "6th Floor, The Programme, All Saints' St, Bristol BS1 2LZ",
        "description": "Cyber workforce resilience platform enabling organisations to continuously measure, assess, and develop human cyber capabilities against live threats.",
        "key_products": ["Cyber Crisis Simulator", "Technical Cyber Labs", "Application Security Labs"],
        "key_people": "James Hadley (Founder & CEO)"
    },
    {
        "id": "portswigger",
        "name": "PortSwigger",
        "website": "https://portswigger.net",
        "careers_url": "https://portswigger.net/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Application Security & Vulnerability Management",
        "scale_tier": "Scaleup (100-150)",
        "headcount_estimate": "120-150",
        "funding_type": "Bootstrapped / Privately Owned",
        "location": "Knutsford",
        "address": "Victoria Buildings, 1-7 Princess St, Knutsford WA16 6BY",
        "description": "World leader in web application security software and creator of Burp Suite, the industry standard toolkit used by penetration testers worldwide.",
        "key_products": ["Burp Suite Professional", "Burp Suite Enterprise Edition", "Web Security Academy"],
        "key_people": "Dafydd Stuttard (Founder & CEO)"
    },
    {
        "id": "tessian",
        "name": "Tessian",
        "website": "https://www.tessian.com",
        "careers_url": "https://www.proofpoint.com/uk/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Email Security & Human Risk Management",
        "scale_tier": "Mid-Market (100-500)",
        "headcount_estimate": "250+",
        "funding_type": "Acquired by Proofpoint (Thoma Bravo)",
        "location": "London",
        "address": "70 Mark Lane, London EC3R 7NQ",
        "description": "Intelligent Cloud Email Security platform utilizing machine learning to protect against advanced email threats, misdirected emails, and data exfiltration.",
        "key_products": ["Tessian Guardian", "Tessian Enforcer", "Tessian Defender"],
        "key_people": "Tim Sadler (Co-Founder)"
    },
    {
        "id": "red-sift",
        "name": "Red Sift",
        "website": "https://redsift.com",
        "careers_url": "https://boards.greenhouse.io/redsift",
        "ats_type": "greenhouse",
        "ats_identifier": "redsift",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Email Security & Human Risk Management",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "80-120",
        "funding_type": "VC-backed (Highland Europe)",
        "location": "London",
        "address": "40 Artillery Lane, London E1 7LS",
        "description": "Integrated cloud security platform offering DMARC automation, brand protection, and attack surface management to stop impersonation and data breaches.",
        "key_products": ["OnDMARC", "OnINBOX", "OnDOMAIN", "Red Sift Pulse"],
        "key_people": "Rahul Powar (CEO), Randal Pinto (COO)"
    },
    {
        "id": "panaseer",
        "name": "Panaseer",
        "website": "https://panaseer.com",
        "careers_url": "https://apply.workable.com/panaseer",
        "ats_type": "workable",
        "ats_identifier": "panaseer",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Governance, Risk & Compliance (GRC)",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "60-100",
        "funding_type": "VC-backed (Notion Capital, AlbionVC)",
        "location": "London",
        "address": "25 City Road, London EC1Y 1AA",
        "description": "Continuous Controls Monitoring (CCM) platform delivering automated, trusted metrics on security posture, compliance gaps, and cyber risk across enterprise infrastructure.",
        "key_products": ["Panaseer Continuous Controls Monitoring Platform"],
        "key_people": "Jonathan Gill (CEO), Nik Whitfield (Founder)"
    },
    {
        "id": "cybersmart",
        "name": "CyberSmart",
        "website": "https://cybersmart.co.uk",
        "careers_url": "https://apply.workable.com/cybersmart",
        "ats_type": "workable",
        "ats_identifier": "cybersmart",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Governance, Risk & Compliance (GRC)",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "70-100",
        "funding_type": "VC-backed (Oxx, BGF)",
        "location": "London",
        "address": "6-8 Bonhill St, London EC2A 4BX",
        "description": "Automated SME cybersecurity and Cyber Essentials compliance platform providing 24/7 continuous device protection, policies, and cyber insurance integration.",
        "key_products": ["CyberSmart Active Protect", "CyberSmart Cyber Essentials Portal"],
        "key_people": "Jamie Akhtar (Co-Founder & CEO)"
    },
    {
        "id": "outthink",
        "name": "OutThink",
        "website": "https://outthink.io",
        "careers_url": "https://jobs.lever.co/outthink",
        "ats_type": "lever",
        "ats_identifier": "outthink",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Email Security & Human Risk Management",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "35-50",
        "funding_type": "VC-backed (AlbionVC)",
        "location": "London",
        "address": "1 Poultry, London EC2R 8EJ",
        "description": "Human Risk Management (HRM) platform combining behavioral science, sentiment analysis, and adaptive targeted security awareness training.",
        "key_products": ["OutThink Human Risk Management Platform"],
        "key_people": "Flavius Plesu (Founder & CEO)"
    },
    {
        "id": "elliptic",
        "name": "Elliptic",
        "website": "https://www.elliptic.co",
        "careers_url": "https://boards.greenhouse.io/elliptic",
        "ats_type": "greenhouse",
        "ats_identifier": "elliptic",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Blockchain & Financial Cyber Security",
        "scale_tier": "Mid-Market (100-500)",
        "headcount_estimate": "150-250",
        "funding_type": "VC-backed (Evolution Equity, SoftBank)",
        "location": "London",
        "address": "1 Fore St Ave, London EC2Y 9DT",
        "description": "Global leader in cryptoasset risk management, anti-money laundering (AML) compliance, and blockchain threat intelligence for crypto businesses and financial institutions.",
        "key_products": ["Elliptic Navigator", "Elliptic Lens", "Elliptic Forensics"],
        "key_people": "Simone Maini (CEO), Tom Robinson (Chief Scientist & Co-Founder)"
    },
    {
        "id": "garrison-technology",
        "name": "Garrison Technology",
        "website": "https://www.garrison.com",
        "careers_url": "https://jobs.lever.co/garrison",
        "ats_type": "lever",
        "ats_identifier": "garrison",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Cloud & Container Security",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "70-110",
        "funding_type": "VC-backed (BGF, Dawn Capital)",
        "location": "London",
        "address": "Level 6, 25 Finsbury Circus, London EC2M 7EE",
        "description": "Hardware-enforced web isolation and cross-domain solution delivering ultra-secure browsing by transforming active web content into raw video pixels.",
        "key_products": ["Garrison SAVI Web Isolation", "Garrison Silicon Hardsec"],
        "key_people": "David Garfield (CEO & Co-Founder)"
    },
    {
        "id": "cado-security",
        "name": "Cado Security",
        "website": "https://www.cadosecurity.com",
        "careers_url": "https://jobs.ashbyhq.com/cadosecurity",
        "ats_type": "ashby",
        "ats_identifier": "cadosecurity",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Cloud & Container Security",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "40-70",
        "funding_type": "VC-backed (Eurazeo, Ten Eleven Ventures)",
        "location": "London",
        "address": "12 Melcombe Place, London NW1 6JJ",
        "description": "Cloud-native digital forensics and incident response platform enabling security teams to rapidly investigate and respond to cyber threats across AWS, Azure, and containers.",
        "key_products": ["Cado Response Platform"],
        "key_people": "James Campbell (CEO & Co-Founder), Chris Doman (CTO & Co-Founder)"
    },
    {
        "id": "senseon",
        "name": "SenseOn",
        "website": "https://www.senseon.io",
        "careers_url": "https://jobs.ashbyhq.com/senseon",
        "ats_type": "ashby",
        "ats_identifier": "senseon",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Detection & Response (EDR/NDR/XDR)",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "60-100",
        "funding_type": "VC-backed (Octopus Ventures, MMC)",
        "location": "London",
        "address": "138-142 Holborn, London EC1N 2SW",
        "description": "Autonomous threat detection and response platform fusing telemetry across endpoints, network traffic, and cloud environments into a unified automated investigation engine.",
        "key_products": ["SenseOn Reflex Detection & Response", "SenseOn Unified Telemetry Engine"],
        "key_people": "David Atkinson (Founder & CEO)"
    },
    {
        "id": "metomic",
        "name": "Metomic",
        "website": "https://metomic.io",
        "careers_url": "https://jobs.ashbyhq.com/metomic",
        "ats_type": "ashby",
        "ats_identifier": "metomic",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Governance, Risk & Compliance (GRC)",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "40-70",
        "funding_type": "VC-backed (Evolution Equity, LocalGlobe)",
        "location": "London",
        "address": "25 Christopher St, London EC2A 2BS",
        "description": "Next-gen SaaS Data Security Posture Management (DSPM) platform detecting sensitive data, credentials, and PII across Slack, Google Drive, Jira, and GitHub.",
        "key_products": ["Metomic SaaS Data Security", "Metomic AI Guardrails"],
        "key_people": "Rich Staveley (CEO & Co-Founder)"
    },
    {
        "id": "push-security",
        "name": "Push Security",
        "website": "https://pushsecurity.com",
        "careers_url": "https://jobs.ashbyhq.com/pushsecurity",
        "ats_type": "ashby",
        "ats_identifier": "pushsecurity",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Identity & Access Management (IAM)",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "30-50",
        "funding_type": "VC-backed (Google Ventures, Decibel)",
        "location": "London",
        "address": "London, UK (Remote-first)",
        "description": "Browser-based identity threat detection and response (ITDR) platform that stops credential harvesting, session hijacking, and SaaS supply chain attacks.",
        "key_products": ["Push Browser Agent", "Push ITDR Platform"],
        "key_people": "Adam Bateman (Co-Founder & CEO)"
    },
    {
        "id": "kynd",
        "name": "KYND",
        "website": "https://www.kynd.io",
        "careers_url": "https://www.kynd.io/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Governance, Risk & Compliance (GRC)",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "35-60",
        "funding_type": "VC-backed (BGF)",
        "location": "London",
        "address": "25 Finsbury Circus, London EC2M 7EE",
        "description": "Cyber risk management and underwriting platform transforming complex cyber vulnerability data into actionable risk insights for insurers, brokers, and enterprises.",
        "key_products": ["KYND Signals", "KYND Ready", "KYND Horizon"],
        "key_people": "Andy Thomas (CEO & Founder)"
    },
    {
        "id": "risk-ledger",
        "name": "Risk Ledger",
        "website": "https://riskledger.com",
        "careers_url": "https://apply.workable.com/risk-ledger",
        "ats_type": "workable",
        "ats_identifier": "risk-ledger",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Governance, Risk & Compliance (GRC)",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "30-50",
        "funding_type": "VC-backed (Lifeline Ventures)",
        "location": "London",
        "address": "12 Melcombe Place, London NW1 6JJ",
        "description": "Social network for supply chain security risk management, helping organisations identify and remediate cybersecurity vulnerabilities across third-party vendors.",
        "key_products": ["Risk Ledger Supply Chain Risk Management Platform"],
        "key_people": "Haydn Brooks (CEO & Co-Founder)"
    },
    {
        "id": "salt-communications",
        "name": "Salt Communications",
        "website": "https://saltcommunications.com",
        "careers_url": "https://saltcommunications.com/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Email Security & Human Risk Management",
        "scale_tier": "Startup (1-20)",
        "headcount_estimate": "15-25",
        "funding_type": "Privately Owned",
        "location": "Belfast",
        "address": "Scottish Provident Building, 7 Donegall Square W, Belfast BT1 6JH",
        "description": "Government-grade encrypted voice, messaging, and file transfer platform engineered for high-consequence enterprise incident management and executive protection.",
        "key_products": ["Salt Mobile Secure App", "Salt Communications Management Console"],
        "key_people": "Joe Boyle (CEO & Co-Founder)"
    },
    {
        "id": "angoka",
        "name": "Angoka",
        "website": "https://angoka.io",
        "careers_url": "https://angoka.io/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "OT, IoT & Industrial Cybersecurity",
        "scale_tier": "Startup (1-20)",
        "headcount_estimate": "15-30",
        "funding_type": "VC-backed (Kernel Capital)",
        "location": "Belfast",
        "address": "Catalyst Innovation Centre, Queen's Rd, Belfast BT3 9DT",
        "description": "Hardware-embedded identity authentication for Machine-to-Machine (M2M) communications in connected autonomous vehicles, smart cities, and drone aviation.",
        "key_products": ["Angoka Quantum-Resilient M2M Hardware Module"],
        "key_people": "Steve Berry (Chairman), Yuri Andersson (CEO)"
    },
    {
        "id": "uleska",
        "name": "Uleska",
        "website": "https://uleska.com",
        "careers_url": "https://uleska.com/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Application Security & Vulnerability Management",
        "scale_tier": "Startup (1-20)",
        "headcount_estimate": "10-20",
        "funding_type": "VC-backed (Techstars, Crescent Capital)",
        "location": "Belfast",
        "address": "Ormeau Baths, 18 Ormeau Ave, Belfast BT2 8HS",
        "description": "Autonomous software vulnerability management and continuous DevSecOps orchestration, quantifying software security risks into real financial business impact.",
        "key_products": ["Uleska Continuous AppSec Orchestration Platform"],
        "key_people": "Gary Robinson (Founder & Chief Architect)"
    },
    {
        "id": "quorum-cyber",
        "name": "Quorum Cyber",
        "website": "https://www.quorumcyber.com",
        "careers_url": "https://www.quorumcyber.com/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Detection & Response (EDR/NDR/XDR)",
        "scale_tier": "Mid-Market (100-500)",
        "headcount_estimate": "200-300",
        "funding_type": "PE-backed (Livingbridge)",
        "location": "Edinburgh",
        "address": "Exchange Tower, 19 Canning St, Edinburgh EH3 8EH",
        "description": "Leading Microsoft Solutions Partner and Managed Detection and Response (MDR) provider, delivering 24/7 security operations (SOC) and cyber incident response.",
        "key_products": ["Clarity Portal", "Managed Detection and Response (MDR)", "Threat Intelligence"],
        "key_people": "Federico Charosky (Founder & CEO)"
    },
    {
        "id": "bridewell",
        "name": "Bridewell",
        "website": "https://www.bridewell.com",
        "careers_url": "https://www.bridewell.com/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Detection & Response (EDR/NDR/XDR)",
        "scale_tier": "Mid-Market (100-500)",
        "headcount_estimate": "150-250",
        "funding_type": "PE-backed (Charterhouse Capital)",
        "location": "Reading",
        "address": "400 Thames Valley Park Dr, Reading RG6 1PT",
        "description": "Cyber security consultancy and managed detection and response (MDR) specialist delivering 24/7 SOC monitoring, penetration testing, and GRC advisory.",
        "key_products": ["Bridewell Managed Detection and Response", "NCSC Assured CIR Services"],
        "key_people": "Anthony Young (CEO), Scott Nicholson (Co-CEO)"
    },
    {
        "id": "secarma",
        "name": "Secarma",
        "website": "https://secarma.com",
        "careers_url": "https://secarma.com/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Application Security & Vulnerability Management",
        "scale_tier": "Scaleup (20-100)",
        "headcount_estimate": "40-70",
        "funding_type": "Privately Owned",
        "location": "Manchester",
        "address": "The Sharp Project, Thorp Rd, Manchester M40 5BJ",
        "description": "Independent cyber security consultancy specialising in ethical hacking, penetration testing, cloud security audits, and red teaming.",
        "key_products": ["Penetration Testing Services", "Red Team Engagements", "Security Awareness"],
        "key_people": "Nick Davies (Managing Director)"
    },
    {
        "id": "iriusrisk",
        "name": "IriusRisk",
        "website": "https://www.iriusrisk.com",
        "careers_url": "https://boards.greenhouse.io/iriusrisk",
        "ats_type": "greenhouse",
        "ats_identifier": "iriusrisk",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Application Security & Vulnerability Management",
        "scale_tier": "Mid-Market (100-500)",
        "headcount_estimate": "150-220",
        "funding_type": "VC-backed (Paladin Capital, BrightPixel)",
        "location": "London",
        "address": "London, UK (Hybrid)",
        "description": "Industry-leading threat modeling and secure software architecture platform automating threat identification and security requirements at design time.",
        "key_products": ["IriusRisk Automated Threat Modeling Platform"],
        "key_people": "Stephen De Vries (CEO & Co-Founder)"
    },
    {
        "id": "ripjar",
        "name": "Ripjar",
        "website": "https://ripjar.com",
        "careers_url": "https://ripjar.com/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Threat Intelligence & OSINT",
        "scale_tier": "Scaleup (100-150)",
        "headcount_estimate": "100-150",
        "funding_type": "VC-backed (Longwall Ventures)",
        "location": "Cheltenham",
        "address": "Eagle Tower, Montpellier Dr, Cheltenham GL50 1TA",
        "description": "Data intelligence platform founded by former GCHQ technologists, using AI and NLP to detect financial crime, sanctions evasion, and national security cyber threats.",
        "key_products": ["Labyrinth Threat Intelligence", "Labyrinth Financial Crime & Screening"],
        "key_people": "Jeremy Annis (CEO & Co-Founder)"
    },
    {
        "id": "callsign",
        "name": "Callsign",
        "website": "https://www.callsign.com",
        "careers_url": "https://www.callsign.com/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Identity & Access Management (IAM)",
        "scale_tier": "Mid-Market (100-500)",
        "headcount_estimate": "150-250",
        "funding_type": "VC-backed (Qualcomm Ventures, Accel)",
        "location": "London",
        "address": "150 Cheapside, London EC2V 6ET",
        "description": "Digital identity and fraud prevention platform pioneering passive behavioral biometric authentication and intelligence for global financial institutions.",
        "key_products": ["Callsign Intelligence Engine", "Behavioral Biometrics Authentication"],
        "key_people": "Dr. Zia Hayat (Founder & CEO)"
    },
    {
        "id": "hack-the-box",
        "name": "Hack The Box",
        "website": "https://www.hackthebox.com",
        "careers_url": "https://apply.workable.com/hackthebox",
        "ats_type": "workable",
        "ats_identifier": "hackthebox",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Cyber Workforce Development & Training",
        "scale_tier": "Mid-Market (100-500)",
        "headcount_estimate": "250-350",
        "funding_type": "VC-backed (Carlyle, Paladin Capital)",
        "location": "Folkestone",
        "address": "Oxford House, 15-17 Mount Ephraim Rd, Tunbridge Wells / Remote UK",
        "description": "Massive global cyber readiness platform providing gamified hands-on penetration testing labs, CTF challenges, and enterprise cyber capability training.",
        "key_products": ["HTB Enterprise Platform", "HTB Academy", "HTB Battlegrounds"],
        "key_people": "Haris Pylarinos (Founder & CEO)"
    },
    {
        "id": "enclave",
        "name": "Enclave",
        "website": "https://enclave.io",
        "careers_url": "https://enclave.io/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Detection & Response (EDR/NDR/XDR)",
        "scale_tier": "Startup (1-20)",
        "headcount_estimate": "10-20",
        "funding_type": "VC-backed",
        "location": "Belfast",
        "address": "Belfast, Northern Ireland / Remote UK",
        "description": "Zero Trust Network Access (ZTNA) platform creating invisible, end-to-end encrypted overlay networks connecting cloud instances, servers, and developers.",
        "key_products": ["Enclave Zero Trust Overlay Engine"],
        "key_people": "David Murray (CEO)"
    },
    {
        "id": "goldilock",
        "name": "Goldilock",
        "website": "https://goldilock.com",
        "careers_url": "https://goldilock.com/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "OT, IoT & Industrial Cybersecurity",
        "scale_tier": "Startup (1-20)",
        "headcount_estimate": "15-25",
        "funding_type": "VC-backed",
        "location": "Wolverhampton",
        "address": "Science Park, Wolverhampton WV10 9RU",
        "description": "Hardware cyber defense system enabling physical air-gapping and instant remote connection/disconnection of critical assets without IP or internet exposure.",
        "key_products": ["Goldilock TruAirgap Remote Physical Disconnect"],
        "key_people": "Tony Hasek (Founder & CEO)"
    },
    {
        "id": "lexverify",
        "name": "Lexverify",
        "website": "https://lexverify.com",
        "careers_url": "https://lexverify.com/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Email Security & Human Risk Management",
        "scale_tier": "Startup (1-20)",
        "headcount_estimate": "10-20",
        "funding_type": "VC-backed",
        "location": "Birmingham",
        "address": "Birmingham, UK (Hybrid)",
        "description": "AI-powered continuous communication compliance tool alerting employees to data exposure, regulatory breaches, and sensitive content prior to email dispatch.",
        "key_products": ["Lexverify Real-Time Assistant"],
        "key_people": "Cristian Gherhes (CEO & Founder)"
    },
    {
        "id": "lupovis",
        "name": "Lupovis",
        "website": "https://www.lupovis.io",
        "careers_url": "https://www.lupovis.io/careers",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Detection & Response (EDR/NDR/XDR)",
        "scale_tier": "Startup (1-20)",
        "headcount_estimate": "10-20",
        "funding_type": "VC-backed",
        "location": "Glasgow",
        "address": "University of Strathclyde, George St, Glasgow G1 1RD",
        "description": "Deception technology platform that deploys AI-guided dynamic decoy networks and fake digital assets to lure, steer, and neutralize adversaries inside networks.",
        "key_products": ["Lupovis Deception Platform"],
        "key_people": "Xavier Bellekens (CEO & Founder)"
    },
    {
        "id": "rapid7-uk",
        "name": "Rapid7",
        "website": "https://www.rapid7.com",
        "careers_url": "https://rapid7.wd1.myworkdayjobs.com/Rapid7_Careers",
        "ats_type": "workday",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Application Security & Vulnerability Management",
        "scale_tier": "Large Enterprise / FDI Hub (500+)",
        "headcount_estimate": "2,500+ (300+ in UK/NI)",
        "funding_type": "Public (NASDAQ: RPD)",
        "location": "Belfast",
        "address": "Chichester House, 21-27 Chichester St, Belfast BT1 4JB",
        "description": "Global cyber security and risk management leader offering cloud-native vulnerability management (Nexpose/InsightVM), SIEM (InsightIDR), and AppSec (InsightAppSec).",
        "key_products": ["InsightVM", "InsightAppSec", "InsightIDR", "InsightConnect SOAR"],
        "key_people": "Corey Thomas (CEO)"
    },
    {
        "id": "contrast-security-uk",
        "name": "Contrast Security",
        "website": "https://www.contrastsecurity.com",
        "careers_url": "https://boards.greenhouse.io/contrastsecurity",
        "ats_type": "greenhouse",
        "ats_identifier": "contrastsecurity",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Application Security & Vulnerability Management",
        "scale_tier": "Mid-Market (100-500)",
        "headcount_estimate": "350+ (60+ in UK/NI)",
        "funding_type": "VC-backed (Warburg Pincus)",
        "location": "Belfast",
        "address": "The Boat, 49 Queen's Square, Belfast BT1 3FG",
        "description": "Code security and runtime application security (IAST & RASP) platform embedding intelligent security instrumentation directly inside running applications.",
        "key_products": ["Contrast Assess", "Contrast Protect (RASP)", "Contrast Scan (SAST)"],
        "key_people": "Rick Fitz (CEO), Jeff Williams (Co-Founder)"
    },
    {
        "id": "black-duck-uk",
        "name": "Black Duck",
        "website": "https://www.blackduck.com",
        "careers_url": "https://synopsys.wd1.myworkdayjobs.com/Synopsys_Careers",
        "ats_type": "workday",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Application Security & Vulnerability Management",
        "scale_tier": "Large Enterprise / FDI Hub (500+)",
        "headcount_estimate": "1,500+ (100+ in UK/NI)",
        "funding_type": "PE-backed (Clearlake Capital & Francisco Partners)",
        "location": "Belfast",
        "address": "City Quays 2, 2 Clarendon Rd, Belfast BT1 3FD",
        "description": "Software composition analysis (SCA) and open-source security intelligence platform tracking security vulnerabilities and license compliance across open source code.",
        "key_products": ["Black Duck SCA", "Coverity SAST", "Defensics DAST"],
        "key_people": "Jason Schmitt (CEO)"
    },
    {
        "id": "imperva-uk",
        "name": "Imperva",
        "website": "https://www.imperva.com",
        "careers_url": "https://careers.thalesgroup.com",
        "ats_type": "custom",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Application Security & Vulnerability Management",
        "scale_tier": "Large Enterprise / FDI Hub (500+)",
        "headcount_estimate": "2,000+ (100+ in UK/NI)",
        "funding_type": "Public (Acquired by Thales)",
        "location": "Belfast",
        "address": "Victoria Hall, 22-26 Victoria St, Belfast BT1 3GG",
        "description": "Comprehensive cybersecurity leader protecting critical applications, APIs, and business data from sophisticated DDoS, botnets, and API security threats.",
        "key_products": ["Imperva Cloud WAF", "Imperva API Security", "Imperva Advanced Bot Protection"],
        "key_people": "Pam Murphy (CEO)"
    },
    {
        "id": "proofpoint-uk",
        "name": "Proofpoint",
        "website": "https://www.proofpoint.com",
        "careers_url": "https://proofpoint.wd5.myworkdayjobs.com/Proofpoint_Careers",
        "ats_type": "workday",
        "industry": "Cybersecurity & Information Security",
        "sub_sector": "Email Security & Human Risk Management",
        "scale_tier": "Large Enterprise / FDI Hub (500+)",
        "headcount_estimate": "4,000+ (150+ in UK/NI)",
        "funding_type": "PE-backed (Thoma Bravo)",
        "location": "Reading",
        "address": "Reading / Belfast Tech Hub",
        "description": "Leading cybersecurity and compliance company protecting organizations against advanced phishing, email attacks, and insider threat data leakage.",
        "key_products": ["Proofpoint Email Protection", "Targeted Attack Protection (TAP)", "Enterprise DLP"],
        "key_people": "Sumit Dhawan (CEO)"
    }
]

def main():
    print("=" * 60)
    print("Starting UK Cybersecurity Company Index Builder")
    print("=" * 60)
    
    scraped_companies = scrape_cyberdirectory()
    
    # Merge and deduplicate by root domain
    company_map = {}
    
    # 1. First seed curated high-priority employers
    for c in CURATED_CYBER_COMPANIES:
        domain = get_root_domain(c["website"])
        c_entry = {
            **c,
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
            "open_roles_count": 0,
            "product_roles_count": 0,
            "active_product_roles": []
        }
        if "ats_identifier" not in c_entry:
            c_entry["ats_identifier"] = ""
        company_map[domain] = c_entry
    
    print(f"Loaded {len(company_map)} curated market leaders and scaleups.")
    
    # 2. Merge in scraped directory entries
    merged_count = 0
    new_count = 0
    for sc in scraped_companies:
        domain = get_root_domain(sc["website"])
        if not domain:
            continue
        
        if domain in company_map:
            # Enrich existing entry if scraped description is longer
            if len(sc.get("description", "")) > len(company_map[domain].get("description", "")):
                company_map[domain]["description"] = sc["description"]
            merged_count += 1
        else:
            # Ensure proper ID uniqueness
            base_id = sc["id"]
            if any(e["id"] == base_id for e in company_map.values()):
                sc["id"] = f"{base_id}-{domain.split('.')[0]}"
            if "ats_identifier" not in sc:
                sc["ats_identifier"] = ""
            company_map[domain] = sc
            new_count += 1
            
    all_companies = sorted(list(company_map.values()), key=lambda x: x["name"].lower())
    
    # Verify all 20 keys on every object
    REQUIRED_KEYS = [
        "id", "name", "website", "careers_url", "ats_type", "ats_identifier",
        "industry", "sub_sector", "scale_tier", "headcount_estimate", "funding_type",
        "location", "address", "description", "key_products", "key_people",
        "last_checked", "open_roles_count", "product_roles_count", "active_product_roles"
    ]
    
    for c in all_companies:
        for k in REQUIRED_KEYS:
            if k not in c:
                if k == "key_products": c[k] = [c["name"] + " Security Platform"]
                elif k == "active_product_roles": c[k] = []
                elif k in ["open_roles_count", "product_roles_count"]: c[k] = 0
                else: c[k] = ""
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_companies, f, indent=2)
        
    print(f"\nSuccessfully generated {OUTPUT_PATH}")
    print(f"Total Unique UK Cybersecurity Companies: {len(all_companies)}")
    print(f"  - Merged existing: {merged_count}")
    print(f"  - Newly ingested from directory: {new_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
