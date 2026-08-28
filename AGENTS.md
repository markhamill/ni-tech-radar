# AGENTS.md: Developer & AI Assistant Guidelines

## 1. Project Mission & Overview
The **Northern Ireland Tech Radar** is a local, lightweight, zero-dependency intelligence tracker that catalogues tech companies across Northern Ireland, monitors their careers portals for active job vacancies, and cross-references private job application pipeline statuses.

This project is built to run standalone on a user's machine or be deployed as an open-source tool for regional tech communities.

---

## 2. Architecture & File Structure

```text
ni-tech-radar/
├── data/
│   └── companies.json    # The canonical JSON database of companies and cached vacancies
├── public/
│   └── index.html        # Interactive SPA frontend (Tailwind CDN, FontAwesome, Vanilla JS)
├── scanner.js            # Automated role scraper querying ATS APIs & career portals
├── server.js             # Zero-dependency local Node.js HTTP server & API endpoints
├── package.json          # npm start / npm run scan script definitions
├── README.md             # End-user setup, fork, and customization documentation
└── AGENTS.md             # Agentic guidelines for maintaining and extending the repo
```

---

## 3. Strict Rules & Constraints for AI Agents

1. **Zero External NPM Dependencies:**
   * The backend server (`server.js`) and scraper (`scanner.js`) must strictly use native Node.js built-ins (`http`, `fs`, `path`, `url`, native `fetch`).
   * Do NOT install external Express, Axios, Cheerio, or heavy dependencies unless explicitly instructed by the user. Keep it runnable with pure `node server.js`.
2. **British English Spelling:**
   * Use British English everywhere in documentation and UI text (e.g. `favourite`, `optimise`, `categorise`, `prioritised`, `specialised`, `organisation`).
3. **Punctuation Rules:**
   * Do NOT use em dashes anywhere in text. Use standard hyphens, colons, or commas for separation.
4. **Data Schema Immutability:**
   * Whenever adding or updating records in `data/companies.json`, ensure all mandatory keys are preserved: `id`, `name`, `website`, `careers_url`, `industry`, `scale_tier`, `funding_type`, `location`, `description`, `product_roles_count`, and `active_product_roles`.
5. **Application Status Failsafe:**
   * `server.js` includes an optional integration with a parent `/applications/` directory. All file reads must remain wrapped in try-catch blocks with graceful fallbacks. The application must run without crashing even if the `/applications/` folder does not exist.

---

## 4. How to Extend & Modify

### A. Adding New ATS Parsers to `scanner.js`
When adding support for a new ATS (e.g. Lever, Workday, SmartRecruiters):
1. Detect ATS type via `company.ats_type` or regex pattern matching on `company.careers_url`.
2. Query the platform's public JSON API endpoint (e.g. `https://api.lever.co/v0/postings/<org>`).
3. Filter role titles using `isTargetRole(title)`.
4. Return normalized `{ title, location, url, date_posted }` objects.

### B. Switching Target Role Disciplines
To fork or adapt this dashboard for different skillsets (e.g. Software Engineering or Data Science):
1. **In `scanner.js`:** Update `PRODUCT_KEYWORDS` with the relevant domain titles.
2. **In `public/index.html`:** Update UI headers, metric labels, and the filter checkbox from *"Live Product Roles"* to the target discipline (e.g. *"Live Engineering Roles"*).
3. **In `data/companies.json`:** Update the count and active role array keys if renaming.

### C. Batch Ingesting Companies
When importing companies from directories (TechIreland, Catalyst, Software NI):
* Verify company ID format (`lowercase-hyphenated`).
* Normalise scale tier to: `Startup (1-20)`, `Scaleup (20-100)`, `Mid-Market (100-500)`, or `Large Enterprise / FDI Hub (500+)`.
* Ensure every entry has a valid `website` and `careers_url`.
