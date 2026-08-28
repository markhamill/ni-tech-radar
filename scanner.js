#!/usr/bin/env node

/**
 * Northern Ireland Tech Radar: Role Scanner
 * Dynamically queries public ATS APIs (SmartRecruiters, Greenhouse, Ashby, Workable, Lever)
 * and updates data/companies.json with real, verified live product roles.
 */

const fs = require('fs');
const path = require('path');

const DB_PATH = path.join(__dirname, 'data', 'companies.json');

const PRODUCT_KEYWORDS = [
  'product manager',
  'head of product',
  'director of product',
  'vp product',
  'vice president, product',
  'vice president of product',
  'group product manager',
  'principal product manager',
  'principal product owner',
  'senior product manager',
  'staff product manager',
  'lead product manager',
  'product lead',
  'product owner',
  'chief product officer',
  'cpo'
];

function isProductRole(title) {
  if (!title) return false;
  const lower = title.toLowerCase();
  return PRODUCT_KEYWORDS.some(keyword => lower.includes(keyword));
}

async function scanCompany(company) {
  const result = {
    ...company,
    last_checked: new Date().toISOString()
  };

  try {
    // 1. SmartRecruiters API Handler (e.g. Version 1, Totalmobile)
    if (company.ats_type === 'smartrecruiters' || (company.careers_url && company.careers_url.includes('smartrecruiters.com')) || company.id === 'version1') {
      const companyId = company.ats_identifier || (company.id === 'version1' ? 'Version1' : null);
      if (companyId) {
        const res = await fetch(`https://api.smartrecruiters.com/v1/companies/${companyId}/postings?limit=100`);
        if (res.ok) {
          const data = await res.json();
          const allJobs = data.content || [];
          result.open_roles_count = data.totalFound || allJobs.length;
          const prodJobs = allJobs.filter(j => isProductRole(j.name));
          result.product_roles_count = prodJobs.length;
          result.active_product_roles = prodJobs.map(j => {
            let loc = 'Belfast / UK Hybrid';
            if (j.location && j.location.city) loc = j.location.city;
            return {
              title: j.name,
              location: loc,
              url: `https://jobs.smartrecruiters.com/${companyId}/${j.id}`,
              date_posted: j.releasedDate ? j.releasedDate.split('T')[0] : new Date().toISOString().split('T')[0]
            };
          });
          return result;
        }
      }
    }

    // 2. Greenhouse API Handler (e.g. Slice, Contrast Security, iManage, Bazaarvoice, Nisos, Benchling)
    if (company.ats_type === 'greenhouse' || (company.careers_url && company.careers_url.includes('greenhouse.io'))) {
      let boardToken = company.ats_identifier;
      if (!boardToken && company.careers_url) {
        const ghMatch = company.careers_url.match(/boards\.greenhouse\.io\/([^\/\?]+)/);
        if (ghMatch) boardToken = ghMatch[1];
      }

      if (boardToken) {
        const res = await fetch(`https://boards-api.greenhouse.io/v1/boards/${boardToken}/jobs`);
        if (res.ok) {
          const data = await res.json();
          const allJobs = data.jobs || [];
          result.open_roles_count = allJobs.length;
          const prodJobs = allJobs.filter(j => isProductRole(j.title));
          result.product_roles_count = prodJobs.length;
          result.active_product_roles = prodJobs.map(j => ({
            title: j.title,
            location: j.location ? j.location.name : 'Remote / Hybrid',
            url: j.absolute_url || company.careers_url,
            date_posted: j.updated_at ? j.updated_at.split('T')[0] : new Date().toISOString().split('T')[0]
          }));
          return result;
        }
      }
    }

    // 3. Ashby API Handler (e.g. Cloudsmith, iVerify)
    if (company.ats_type === 'ashby' || (company.careers_url && company.careers_url.includes('ashbyhq.com'))) {
      let orgSlug = company.ats_identifier;
      if (!orgSlug && company.careers_url) {
        const ashbyMatch = company.careers_url.match(/jobs\.ashbyhq\.com\/([^\/\?]+)/);
        if (ashbyMatch) orgSlug = ashbyMatch[1];
      }
      if (orgSlug) {
        const res = await fetch(`https://api.ashbyhq.com/posting-api/job-board/${orgSlug}`);
        if (res.ok) {
          const data = await res.json();
          const allJobs = data.jobs || [];
          result.open_roles_count = allJobs.length;
          const prodJobs = allJobs.filter(j => isProductRole(j.title));
          result.product_roles_count = prodJobs.length;
          result.active_product_roles = prodJobs.map(j => ({
            title: j.title,
            location: j.location || 'Remote / Hybrid',
            url: j.jobUrl || company.careers_url,
            date_posted: j.publishedAt ? j.publishedAt.split('T')[0] : new Date().toISOString().split('T')[0]
          }));
          return result;
        }
      }
    }

    // 4. Workable API Handler (e.g. Learning Pool, Datactics, Locate a Locum)
    if (company.ats_type === 'workable' || (company.careers_url && company.careers_url.includes('apply.workable.com'))) {
      let accountSlug = company.ats_identifier;
      if (!accountSlug && company.careers_url) {
        const wMatch = company.careers_url.match(/apply\.workable\.com\/([^\/\?]+)/);
        if (wMatch) accountSlug = wMatch[1];
      }
      if (accountSlug) {
        const res = await fetch(`https://apply.workable.com/api/v1/widget/accounts/${accountSlug}`);
        if (res.ok) {
          const data = await res.json();
          const allJobs = data.jobs || [];
          result.open_roles_count = allJobs.length;
          const prodJobs = allJobs.filter(j => isProductRole(j.title));
          result.product_roles_count = prodJobs.length;
          result.active_product_roles = prodJobs.map(j => ({
            title: j.title,
            location: j.city ? `${j.city}, ${j.country}` : 'Remote / Hybrid',
            url: j.url || company.careers_url,
            date_posted: j.published_on || new Date().toISOString().split('T')[0]
          }));
          return result;
        }
      }
    }

    // 5. Lever API Handler
    if (company.ats_type === 'lever' || (company.careers_url && company.careers_url.includes('jobs.lever.co'))) {
      let site = company.ats_identifier;
      if (!site && company.careers_url) {
        const leverMatch = company.careers_url.match(/jobs\.lever\.co\/([^\/\?]+)/);
        if (leverMatch) site = leverMatch[1];
      }
      if (site) {
        const res = await fetch(`https://api.lever.co/v0/postings/${site}?mode=json`);
        if (res.ok) {
          const allJobs = await res.json();
          result.open_roles_count = allJobs.length;
          const prodJobs = allJobs.filter(j => isProductRole(j.text));
          result.product_roles_count = prodJobs.length;
          result.active_product_roles = prodJobs.map(j => ({
            title: j.text,
            location: j.categories && j.categories.location ? j.categories.location : 'Remote / Hybrid',
            url: j.hostedUrl || company.careers_url,
            date_posted: j.createdAt ? new Date(j.createdAt).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]
          }));
          return result;
        }
      }
    }

    // 6. Teamtailor Parser (e.g. Cloudsmith)
    if (company.ats_type === 'teamtailor' || (company.careers_url && company.careers_url.includes('careers.')) || company.id === 'cloudsmith') {
      const targetUrl = (company.careers_url && company.careers_url.endsWith('/jobs')) ? company.careers_url : `${company.careers_url.replace(/\/$/, '')}/jobs`;
      try {
        const res = await fetch(targetUrl);
        if (res.ok) {
          const html = await res.text();
          const jobRegex = /<a[^>]+href="([^"]*\/jobs\/(\d+)-([^"]+))"[^>]*>([\s\S]*?)<\/a>/gi;
          const found = [];
          let jm;
          while ((jm = jobRegex.exec(html)) !== null) {
            const rawText = jm[4].replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
            if (rawText && !found.some(f => f.id === jm[2])) {
              found.push({ id: jm[2], url: jm[1], title: rawText });
            }
          }
          if (found.length > 0) {
            result.open_roles_count = found.length;
            const prodJobs = found.filter(j => isProductRole(j.title));
            result.product_roles_count = prodJobs.length;
            result.active_product_roles = prodJobs.map(j => ({
              title: j.title,
              location: 'Belfast / Remote UK',
              url: j.url.startsWith('http') ? j.url : `https://careers.cloudsmith.com${j.url}`,
              date_posted: new Date().toISOString().split('T')[0]
            }));
            return result;
          }
        }
      } catch (ttErr) {
        console.error(`Teamtailor fetch error for ${company.name}:`, ttErr.message);
      }
    }

    // Retain existing active roles if manually verified or if scraper didn't run
    if (!result.active_product_roles) {
      result.active_product_roles = [];
      result.product_roles_count = 0;
    }
    return result;
  } catch (err) {
    console.error(`Error scanning ${company.name}:`, err.message);
    return result;
  }
}

async function runScanner() {
  console.log('🚀 Starting Northern Ireland Tech Radar Scanner...');
  if (!fs.existsSync(DB_PATH)) {
    console.error(`Database not found at ${DB_PATH}`);
    process.exit(1);
  }

  const raw = fs.readFileSync(DB_PATH, 'utf-8');
  const companies = JSON.parse(raw);
  console.log(`Loaded ${companies.length} companies from database.`);

  const updatedCompanies = [];
  for (const company of companies) {
    const updated = await scanCompany(company);
    updatedCompanies.push(updated);
  }

  fs.writeFileSync(DB_PATH, JSON.stringify(updatedCompanies, null, 2), 'utf-8');
  const liveCount = updatedCompanies.reduce((acc, c) => acc + (c.product_roles_count || 0), 0);
  console.log(`✅ Scan completed. Found ${liveCount} live verified product roles across NI companies.`);
}

if (require.main === module) {
  runScanner();
}

module.exports = { scanCompany, runScanner };
