# 🎯 Northern Ireland Tech Radar

A fast, lightweight, zero-dependency local dashboard and role intelligence tracker for tech companies across Northern Ireland.

Built for senior professionals, candidates, and founders who want an unvarnished, real-time map of the regional technology ecosystem, company scale, ownership models, and live vacancies.

---

## 🌟 Key Features

* **Complete Regional Landscape:** Categorises companies by Scale Tier (`Startup`, `Scaleup`, `Mid-Market`, `Large Enterprise / FDI Hub`), Industry Sector, Funding / Ownership model, and Northern Ireland location.
* **Automated Role Intelligence:** Scans ATS endpoints (Greenhouse, Ashby, SmartRecruiters, Workable, Lever, Teamtailor, BambooHR, Pinpoint, Volcanic, and custom career portals) and extracts live vacancies with 1-click direct apply links.
* **Light & Dark Mode Themes:** Full tokenised palette with automatic OS preference detection and smooth top-bar toggle.
* **3-State Column Sorting:** Sort any table column in ascending, descending, or natural cleared order (including numeric role counts and ordinal scale tiers).
* **Zero-Shift KPI Filters:** Top-level metrics cards double as 1-click filter toggles with reflow-safe CSS rings.
* **Mobile-First Responsive Design:** Automatically transitions to a touch-friendly native card list with 1-tap expandable drawers on mobile devices.
* **Interactive Favourites & Shortlisting:** Star (`★`) target companies to curate your shortlist, persisted in local storage.
* **Local Application Pipeline Sync:** Automatically cross-references private job application notes with token-boundary matching.
* **Zero External Dependencies:** Built entirely with native Node.js APIs (`http`, `fs`, `path`) and lightweight vanilla frontend code. Starts in milliseconds.

---

## 🤖 Or Just Get Your AI Agent to Do It

If you use an AI coding assistant (such as **Google Antigravity CLI**, **Claude Code**, **Codex**, or **Cursor**), you can let your agent handle the entire setup, scanning, or customisation for you:

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
*(You can also click the **"Scan for Open Product Roles"** button directly inside the local web UI).*

---

## 📊 Data Architecture & Data Sources

All company intelligence is stored in clean JSON format at [`public/data/companies.json`](public/data/companies.json).

### Company Schema
```json
{
  "id": "cloudsmith",
  "name": "Cloudsmith",
  "website": "https://cloudsmith.com/",
  "careers_url": "https://careers.cloudsmith.com/jobs",
  "ats_type": "teamtailor",
  "ats_identifier": "cloudsmith",
  "industry": "Cybersecurity & DevTools",
  "sub_sector": "Software Supply Chain Security & Package Management",
  "scale_tier": "Scaleup (20-100)",
  "headcount_estimate": "60-80",
  "funding_type": "VC-backed (Series A)",
  "location": "Belfast",
  "address": "4th Floor, High Street, Belfast",
  "description": "Cloud-native universal package management and software supply chain security platform.",
  "key_products": ["Cloudsmith Universal Package Management", "Software Supply Chain Trust Engine"],
  "last_checked": "2026-08-29T10:00:00Z",
  "open_roles_count": 5,
  "product_roles_count": 1,
  "active_product_roles": [
    {
      "title": "Group Product Manager, Software Supply Chain Trust",
      "location": "Belfast / Remote UK",
      "url": "https://careers.cloudsmith.com/jobs/7830987-group-product-manager-software-supply-chain-trust",
      "date_found": "2026-08-29"
    }
  ]
}
```

### Example Regional Data Sources & Registries
You can seed or expand [`public/data/companies.json`](public/data/companies.json) with company data from public ecosystem sources e.g.
* **[TechIreland](https://techireland.org/)** (e.g. filter by Northern Ireland startups, scaleups, and FDI hubs).
* **[Catalyst Community](https://wearecatalyst.org/)** (e.g. tenants across Belfast Titanic Quarter, Derry/Londonderry, and Ballymena).
* **[Software NI](https://softwareni.co.uk/)** (e.g. official Northern Ireland software industry member directory).
* **[FinTech NI](https://www.fintechni.org.uk/)** (e.g. capital markets, trading tech, and regtech map).

Or ask your coding agent or AI tool to find new sources relevant to your own search preferences, and import them into `public/data/companies.json`.

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

## 🔒 Dual Architecture & Security Hardening

This project uses an air-gapped architecture designed for a two-way workflow:

1. **Local Mode (Admin & Data Gathering):**
   * Run locally with `npm start` on your machine (`localhost:3333`).
   * Gives you the full command center: one-click live ATS scrapers, add/edit company modals, star favourites, and private application pipeline synchronisation.
   * **Same-Origin API Isolation (v1.5.1):** Zero wildcard CORS headers. The local server communicates strictly on the same origin, preventing external sites open in other browser tabs from querying or triggering `/api/scan` on localhost.
   * **DOM Output Sanitisation (v1.5.1):** All dynamic company names, descriptions, locations, and vacancy titles pass through `escapeHtml()` and URL encoders before insertion into the DOM to guard against cross-site scripting (XSS).
2. **Public Deployed Mode (Zero-Risk Public Directory):**
   * Deploy the static `public/` folder to Vercel, GitHub Pages, or Netlify.
   * The client automatically evaluates `isLocalEnvironment() === false` and strictly hides all admin buttons, scraper triggers, and private application tracking via CSS and JavaScript.
   * **Zero Cloud Writing & Zero Leakage:** The public static host contains no Node backend, Python scripts, or API endpoints, making it impossible for public visitors to trigger scraper jobs or access private career tracking files.

### Feature Comparison Matrix:

| Feature | 💻 Local Mode (`localhost`) | 🌐 Deployed State (Vercel / GitHub Pages / Public Host) |
| :--- | :--- | :--- |
| **Data Source** | Local server API (`/api/companies`) with fallback | Static JSON file (`./data/companies.json`) |
| **"Scan" Button** | **Visible & Active** (Triggers local scrapers) | **Completely Hidden / Invisible** |
| **"Add Company" Form** | **Visible & Active** (Saves to local database) | **Completely Hidden / Invisible** |
| **Personal Application Tracker** | **Visible & Synchronised** (from `/applications/`) | **Completely Hidden / Invisible** |
| **Starred Favourites** | **Visible & Active** (Local storage) | **Completely Hidden / Invisible** |
| **Light & Dark Theme Switch** | **Live & Visible** (Persisted in local storage) | **Live & Visible** (Persisted in local storage) |
| **3-State Column Sorting** | **Live & Active** (Asc / Desc / Clear) | **Live & Active** (Asc / Desc / Clear) |
| **Catalogue Updated Timestamp** | Synchronised to latest local scan timestamp | **Live & Visible** (Catalogue date from static JSON) |
| **Mobile Experience** | Native cards with responsive drawers | Native cards with responsive drawers |

---

## 🚀 Public Deployment Guide

Because the application is built with **zero-dependency vanilla HTML5/JavaScript**, it requires zero build steps or compilation.

### Option A: Deploying to Vercel (Recommended)

1. Push your repository to **GitHub**.
2. Go to **[Vercel.com](https://vercel.com)** and log in with your GitHub account.
3. Click **"Add New..."** &rarr; **"Project"** and import this repository.
4. In the project configuration:
   * **Framework Preset:** Other (or leave Default).
   * **Root Directory:** `./` (the pre-configured [`vercel.json`](vercel.json) handles routing to `public/` automatically).
5. Click **"Deploy"**. Your site is live on a custom `*.vercel.app` domain in seconds!
6. Whenever you commit and push updates to `main` (such as new companies or scan results), Vercel automatically redeploys.

### Option B: Deploying to GitHub Pages (GitHub Actions)

A pre-configured GitHub Actions workflow is included at [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml).

1. Go to your GitHub repository **Settings** &rarr; **Pages**.
2. Under **Build and deployment** &rarr; **Source**, select **GitHub Actions**.
3. Push to `main`. GitHub Actions will automatically bundle `public/` and deploy your site live in seconds!

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
Modify the dropdown `<select>` filters in [`public/index.html`](public/index.html) and add your target cities, scale categories, or specialised sectors.
