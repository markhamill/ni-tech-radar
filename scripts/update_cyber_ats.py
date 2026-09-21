import json

path = "/workspaces/AI-Workspace/Projects/job-applications/ni-tech-radar/public/data/cyber_companies.json"

with open(path, "r", encoding="utf-8") as f:
    companies = json.load(f)

ats_updates = {
    "hack-the-box": {
        "ats_type": "workable",
        "ats_identifier": "hack-the-box-ltd",
        "careers_url": "https://apply.workable.com/hack-the-box-ltd/"
    },
    "contrast-security-uk": {
        "ats_type": "ashby",
        "ats_identifier": "contrast-security",
        "careers_url": "https://jobs.ashbyhq.com/contrast-security"
    },
    "senseon": {
        "ats_type": "workable",
        "ats_identifier": "senseon",
        "careers_url": "https://apply.workable.com/senseon/"
    },
    "bridewell": {
        "ats_type": "workable",
        "ats_identifier": "bridewell",
        "careers_url": "https://apply.workable.com/bridewell/"
    },
    "callsign": {
        "ats_type": "workable",
        "ats_identifier": "callsign",
        "careers_url": "https://apply.workable.com/callsign/"
    },
    "portswigger": {
        "ats_type": "workable",
        "ats_identifier": "portswigger",
        "careers_url": "https://apply.workable.com/portswigger/"
    },
    "cybersmart": {
        "ats_type": "workable",
        "ats_identifier": "cybersmart",
        "careers_url": "https://apply.workable.com/cybersmart/"
    },
    "metomic": {
        "ats_type": "workable",
        "ats_identifier": "metomic",
        "careers_url": "https://apply.workable.com/metomic/"
    },
    "cybercube": {
        "ats_type": "ashby",
        "ats_identifier": "cybcube",
        "careers_url": "https://jobs.ashbyhq.com/cybcube"
    },
    "immersivelabs": {
        "ats_type": "ashby",
        "ats_identifier": "immersivelabs",
        "careers_url": "https://jobs.ashbyhq.com/immersivelabs"
    }
}

updated_count = 0
for c in companies:
    cid = c.get("id")
    if cid in ats_updates:
        c.update(ats_updates[cid])
        updated_count += 1
    elif c.get("name") == "Hack The Box":
        c.update(ats_updates["hack-the-box"])
        updated_count += 1

with open(path, "w", encoding="utf-8") as f:
    json.dump(companies, f, indent=2)

print(f"Updated {updated_count} companies with verified ATS identifiers")
