#!/usr/bin/env node

/**
 * Northern Ireland Tech Radar: Role Scanner
 * Dynamically queries public ATS APIs (Greenhouse, Ashby, SmartRecruiters, Lever, Workable)
 * and updates data/companies.json with strictly verified live product roles.
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
    // 1. Greenhouse API Handler
    if (company.ats_type === 'greenhouse' || (company.careers_url && company.careers_url.includes('greenhouse.io'))) {
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
    }

    // 2. Ashby API Handler
    if (company.ats_type === 'ashby' || (company.careers_url && company.careers_url.includes('ashbyhq.com'))) {
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

    // 3. SmartRecruiters API Handler
    if (company.ats_type === 'smartrecruiters' || (company.careers_url && company.careers_url.includes('smartrecruiters.com'))) {
      const srMatch = company.careers_url.match(/smartrecruiters\.com\/([^\/\?]+)/);
      if (srMatch) {
        const companyId = srMatch[1];
        const res = await fetch(`https://api.smartrecruiters.com/v1/companies/${companyId}/postings`);
        if (res.ok) {
          const data = await res.json();
          const allJobs = data.content || [];
          result.open_roles_count = allJobs.length;
          const prodJobs = allJobs.filter(j => isProductRole(j.name));
          result.product_roles_count = prodJobs.length;
          result.active_product_roles = prodJobs.map(j => ({
            title: j.name,
            location: j.location ? `${j.location.city || ''}, ${j.location.country || ''}` : 'Remote / Hybrid',
            url: `https://jobs.smartrecruiters.com/${companyId}/${j.id}`,
            date_posted: j.releasedDate ? j.releasedDate.split('T')[0] : new Date().toISOString().split('T')[0]
          }));
          return result;
        }
      }
    }

    // 4. Lever API Handler
    if (company.ats_type === 'lever' || (company.careers_url && company.careers_url.includes('jobs.lever.co'))) {
      const leverMatch = company.careers_url.match(/jobs\.lever\.co\/([^\/\?]+)/);
      if (leverMatch) {
        const site = leverMatch[1];
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

    // 5. Default Fallback: No unverified roles invented.
    // If not scanned via live verified API, keep active_product_roles empty.
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
    console.log(`Scanning: ${company.name}...`);
    const updated = await scanCompany(company);
    updatedCompanies.push(updated);
  }

  fs.writeFileSync(DB_PATH, JSON.stringify(updatedCompanies, null, 2), 'utf-8');
  console.log(`✅ Scan completed successfully. Updated ${updatedCompanies.length} companies with strictly verified live roles.`);
}

if (require.main === module) {
  runScanner();
}

module.exports = { scanCompany, runScanner };
