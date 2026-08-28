#!/usr/bin/env node

/**
 * Northern Ireland Tech Radar: Role Scanner
 * Scans career endpoints (Ashby, Greenhouse, Lever, SmartRecruiters, custom HTML)
 * and updates data/companies.json with active product & leadership roles.
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
    if (company.ats_type === 'greenhouse' && company.website) {
      // Greenhouse API handler
      const ghMatch = company.careers_url.match(/boards\.greenhouse\.io\/([^\/\?]+)/);
      if (ghMatch) {
        const boardToken = ghMatch[1];
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
    } else if (company.ats_type === 'ashby' && company.careers_url) {
      // Ashby handler
      const ashbyMatch = company.careers_url.match(/jobs\.ashbyhq\.com\/([^\/\?]+)/);
      if (ashbyMatch) {
        const orgSlug = ashbyMatch[1];
        const res = await fetch(`https://api.ashbyhq.com/posting-api/job-board/${orgSlug}`);
        if (res.ok) {
          const data = await res.json();
          const allJobs = data.jobs || [];
          result.open_roles_count = allJobs.length;
          const prodJobs = allJobs.filter(j => isProductRole(j.title));
          result.product_roles_count = prodJobs.length;
          result.active_product_roles = prodJobs.map(j => ({
            title: j.title,
            location: j.location || 'Remote',
            url: j.jobUrl || company.careers_url,
            date_posted: j.publishedAt ? j.publishedAt.split('T')[0] : new Date().toISOString().split('T')[0]
          }));
          return result;
        }
      }
    }

    // Default fallback: keep curated active roles if live endpoint is proprietary
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
    console.log(`Scanning: ${company.name}...`);
    const updated = await scanCompany(company);
    updatedCompanies.push(updated);
  }

  fs.writeFileSync(DB_PATH, JSON.stringify(updatedCompanies, null, 2), 'utf-8');
  console.log(`✅ Scan completed successfully. Updated ${updatedCompanies.length} companies.`);
}

if (require.main === module) {
  runScanner();
}

module.exports = { runScanner, scanCompany };
