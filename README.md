# 🎯 Northern Ireland Tech Radar

A fast, lightweight, zero-dependency local dashboard and role intelligence tracker for tech companies across Northern Ireland.

Built for senior professionals, candidates, and founders who want an unvarnished, real-time map of the regional technology ecosystem, company scale, ownership models, and live vacancies.

---

## 🌟 Key Features

* **Complete Regional Landscape:** Categorises companies by Scale Tier (`Startup`, `Scaleup`, `Mid-Market`, `Large Enterprise / FDI Hub`), Industry Sector, Funding / Ownership model, and Northern Ireland location.
* **Automated Role Intelligence:** Scans ATS endpoints (Ashby, Greenhouse, Lever, SmartRecruiters, custom career portals) and extracts live vacancies with 1-click direct apply links.
* **Interactive Favourites & Shortlisting:** Star (`★`) target companies to curate your shortlist, persisted in local storage.
* **Local Application Pipeline Sync:** Automatically cross-references your private job application tracking notes (stage, date applied, rejection alerts) directly inside the company profile.
* **Graceful Failsafe:** Runs completely standalone. If no application tracking directory is connected, it fails silently and gracefully with zero errors.
* **Zero External Dependencies:** Built entirely with native Node.js APIs (`http`, `fs`, `path`) and lightweight frontend styling. Starts in milliseconds.

---

## 🤖 Or Just Get Your AI Agent to Do It

If you use an AI coding assistant (such as **Google Antigravity CLI**, **Claude Code**, **Codex**, or **Cursor**), you can let your agent handle the entire setup, scanning, or customization for you:

```bash
cd ni-tech-radar
agy   # or: claude, codex, etc.
```

**Copy & paste this prompt into your agent:**
> *"Read README.md, AGENTS.md, and the codebase. Install any prerequisites if needed, verify the database schema, start the local dashboard server, and give me the localhost link to view it in my browser."*

---

## 🚀 Quick Start & Local Setup

### Prerequisites: Installing Node.js
This tool requires **Node.js v18.0.0 or higher** (no external npm packages required):
* **macOS (Homebrew):**
  ```bash
  brew install node
  ```
* **Windows:**
  Download the LTS installer from [nodejs.org](https://nodejs.org) or run via terminal:
  ```powershell
  winget install OpenJS.NodeJS.LTS
  ```
* **Linux (Ubuntu / Debian):**
  ```bash
  sudo apt update && sudo apt install nodejs npm
  ```
* **Version Check:**
  ```bash
  node -v
  ```

### 1. Launch the Dashboard
Clone or download the repository, navigate to the folder, and run:
```bash
cd ni-tech-radar
npm start
# or directly:
node server.js
```
Open your browser at: **`http://localhost:3333`** (or whichever port is displayed in your terminal output. You can also specify a custom port with `PORT=3000 npm start`).

### 2. Run the Role Scanner
To scan and refresh live job openings across career endpoints:
```bash
npm run scan
# or directly:
node scanner.js
```
*(You can also click the **"Scan for Open Product Roles"** button directly inside the web UI).*

---

## 📊 Data Architecture & Data Sources

All company intelligence is stored in clean JSON format at [`data/companies.json`](data/companies.json).

### Company Schema
```json
{
  "id": "cloudsmith",
  "name": "Cloudsmith",
  "website": "https://cloudsmith.com/",
  "careers_url": "https://cloudsmith.com/careers",
  "ats_type": "custom",
  "industry": "Cybersecurity & DevTools",
  "sub_sector": "Software Supply Chain Security & Package Management",
  "scale_tier": "Scaleup (20-100)",
  "headcount_estimate": "60-80",
  "funding_type": "VC-backed (Series A)",
  "location": "Belfast",
  "address": "4th Floor, High Street, Belfast",
  "description": "Cloud-native universal package management and software supply chain security platform.",
  "key_products": ["Cloudsmith Universal Package Management", "Software Supply Chain Trust Engine"],
  "key_people": "Glenn Bilby (CEO), Alan Carson (Co-Founder)",
  "last_checked": "2026-08-28T09:00:00Z",
  "open_roles_count": 5,
  "product_roles_count": 2,
  "active_product_roles": [
    {
      "title": "Group Product Manager, Software Supply Chain Trust",
      "location": "Belfast / Remote UK",
      "url": "https://cloudsmith.com/careers",
      "date_posted": "2026-08-20"
    }
  ]
}
```

### Example Regional Data Sources & Registries
You can seed or expand [`data/companies.json`](data/companies.json) with company data from public ecosystem sources e.g.
* **[TechIreland](https://techireland.org/)** (e.g. filter by Northern Ireland startups, scaleups, and FDI hubs).
* **[Catalyst Community](https://wearecatalyst.org/)** (e.g. tenants across Belfast Titanic Quarter, Derry/Londonderry, and Ballymena).
* **[Software NI](https://softwareni.co.uk/)** (e.g. official Northern Ireland software industry member directory).
* **[FinTech NI](https://www.fintechni.org.uk/)** (e.g. capital markets, trading tech, and regtech map).

---

## 🔄 Live Application Status Tracking & Built-in Failsafe

### How the Pipeline Connection Works
The server inspects parent or local directories for markdown application status files structured like:
```text
/applications/
  ├── 2026-08-01_AcmeCorp_HeadOfEngineering/
  │   └── application_status.md
  └── 2026-08-15_ExampleTech_DirectorOfProduct/
      └── application_status.md
```
Where `application_status.md` contains metadata lines:
```markdown
- **Company:** Acme Corp
- **Role Title:** Head of Engineering
- **Current Stage:** Applied
- **Date Applied:** 2026-08-01
```

* **When an application is found:** The dashboard displays a status badge (`✓ Applied`, `✕ Rejected`, `★ Interviewing`) on the table row and displays an in-depth alert banner inside the company's expanded accordion drawer.
* **Graceful Failsafe:** If the `/applications/` directory does not exist (e.g. when forked standalone on GitHub), `server.js` catches the missing folder and returns an empty list `[]`. The frontend seamlessly renders company data without application badges and with zero errors.

---

## 🛠️ How to Fork & Customise (e.g. For Software Engineering Roles)

You can easily adapt this radar to track software engineering, data science, cybersecurity operations, or design roles:

### 1. Update Scanner Keywords in [`scanner.js`](scanner.js)
Open [`scanner.js`](scanner.js) and update the role filter keyword array:
```javascript
// Example: Switch from Product to Software Engineering
const ENGINEERING_KEYWORDS = [
  'software engineer',
  'frontend engineer',
  'backend engineer',
  'full stack',
  'tech lead',
  'lead engineer',
  'principal engineer',
  'staff engineer',
  'engineering manager',
  'director of engineering',
  'vp of engineering',
  'cto'
];

function isTargetRole(title) {
  if (!title) return false;
  const lower = title.toLowerCase();
  return ENGINEERING_KEYWORDS.some(k => lower.includes(k));
}
```

### 2. Update Web UI Labels in [`public/index.html`](public/index.html)
* Change **"Scan for Open Product Roles"** to **"Scan for Open Engineering Roles"**.
* Change the table column header from **"Live Product Roles"** to **"Live Engineering Roles"**.
* Update the filter toggle checkbox from **"🔥 Live Product Roles"** to **"🔥 Live Engineering Roles"**.

### 3. Customise Sectors or Regional Locations
Modify the dropdown `<select>` filters in [`public/index.html`](public/index.html) and add your target cities, scale categories, or specialized sectors.
