#!/usr/bin/env node

/**
 * Northern Ireland Tech Radar: Role Scanner
 * Dynamically queries public ATS APIs (SmartRecruiters, Greenhouse, Ashby, Workable, Lever)
 * and updates data/companies.json with real, verified live product roles.
 */

const fs = require('fs');
const path = require('path');

const DEFAULT_DB_PATH = path.join(__dirname, 'public', 'data', 'companies.json');
const CYBER_DB_PATH = path.join(__dirname, 'public', 'data', 'cyber_companies.json');
const DB_PATH = DEFAULT_DB_PATH;

const PRODUCT_KEYWORDS = [
  'product manager',
  'head of product',
  'director of product',
  'director, product',
  'product director',
  'vp product',
  'vp of product',
  'vp, product',
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
  'product champion',
  'product specialist',
  'product marketing manager',
  'director, product marketing',
  'principal product consultant',
  'product consultant',
  'chief product officer',
  'cpo'
];

function isProductRole(title) {
  if (!title) return false;
  const lower = title.toLowerCase();
  return PRODUCT_KEYWORDS.some(keyword => lower.includes(keyword));
}

function isUkOrNiRelevant(location, company) {
  if (!location) return true;
  const loc = location.toLowerCase().trim();

  // Positive UK / NI indicators
  const ukPositives = [
    'belfast', 'derry', 'londonderry', 'northern ireland', 'antrim', 'down', 'armagh', 'tyrone', 'fermanagh',
    'uk', 'united kingdom', 'great britain', 'england', 'scotland', 'wales',
    'london', 'manchester', 'birmingham', 'edinburgh', 'glasgow', 'bristol', 'leeds', 'newcastle', 'cambridge', 'oxford', 'bath', 'knutsford',
    'homeworker---uk', 'home worker', 'remote - uk', 'uk remote', 'remote (uk)', 'uk (remote)', 'remote, uk'
  ];
  if (ukPositives.some(p => loc.includes(p))) {
    return true;
  }

  // Explicit foreign excludes (e.g. San Francisco, US states, Canada, etc.)
  const foreignExcludes = [
    'san francisco', 'california', ', ca', ' ca ', 'ca,', 'los angeles',
    'new york', 'nyc', ', ny', ' ny ', 'ny,', 'boston', ', ma', ' ma ',
    'chicago', ', il', ' il ', 'seattle', ', wa', ' wa ',
    'austin', ', tx', ' tx ', 'denver', ', co', 'colorado', 'utah', 'lehi',
    'toronto', 'vancouver', 'montreal', 'canada', 'ontario',
    'manila', 'philippines', 'buenos aires', 'argentina',
    'sydney', 'melbourne', 'australia', 'singapore', 'tokyo', 'japan',
    'india', 'bengaluru', 'bangalore', 'pune', 'hyderabad',
    'germany', 'berlin', 'munich', 'frankfurt', 'france', 'paris',
    'israel', 'tel aviv', 'ramat gan', 'herzliya', 'haifa', 'jerusalem',
    'brazil', 'sao paulo', 'netherlands', 'amsterdam', 'rijswijk',
    'united states', 'usa', 'u.s.', 'us-remote', 'us remote', 'usa remote', 'remote - us', 'remote (us)'
  ];
  if (foreignExcludes.some(f => loc.includes(f))) {
    return false;
  }

  // Generic remote or multi-location tags
  const genericTerms = ['remote', 'hybrid', 'anywhere', 'emea', 'flexible', 'locations'];
  if (genericTerms.some(g => loc.includes(g))) {
    return true;
  }

  return true;
}

async function isJobUrlLive(url) {
  if (!url) return false;
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);
    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      },
      redirect: 'follow'
    });
    clearTimeout(timeout);
    if (!res.ok) return false;
    const text = await res.text();
    const lower = text.toLowerCase();
    const closedPhrases = [
      'this job is no longer available',
      'this position has been filled',
      'job posting has expired',
      'this requisition is closed',
      'position is no longer open',
      'job no longer exists',
      'this opening is closed',
      'posting has expired'
    ];
    if (closedPhrases.some(p => lower.includes(p))) return false;
    return true;
  } catch (err) {
    return false;
  }
}

async function scanCompany(company) {
  const result = {
    ...company,
    last_checked: new Date().toISOString()
  };

  // If company has manual or verified curated roles and no automated ATS API, verify their live status
  if (company.active_product_roles && company.active_product_roles.length > 0 && (!company.ats_type || company.ats_type === 'custom' || company.ats_type === 'manual')) {
    const liveRoles = [];
    for (const role of company.active_product_roles) {
      const isLive = await isJobUrlLive(role.url);
      if (isLive) {
        liveRoles.push(role);
      } else {
        console.log(`🗑️ Removed expired/closed manual role: ${role.title} at ${company.name}`);
      }
    }
    result.active_product_roles = liveRoles;
    result.product_roles_count = liveRoles.length;
    return result;
  }

  try {
    // 1. SmartRecruiters API Handler (e.g. Version 1, Totalmobile)
    if (company.ats_type === 'smartrecruiters' || (company.careers_url && company.careers_url.includes('smartrecruiters.com')) || company.id === 'version1') {
      const companyId = company.ats_identifier || (company.id === 'version1' ? 'Version1' : null);
      if (companyId) {
        let allJobs = [];
        let offset = 0;
        const limit = 100;
        let totalFound = 0;
        do {
          const res = await fetch(`https://api.smartrecruiters.com/v1/companies/${companyId}/postings?limit=${limit}&offset=${offset}`);
          if (!res.ok) break;
          const data = await res.json();
          totalFound = data.totalFound || 0;
          const content = data.content || [];
          allJobs.push(...content);
          offset += limit;
          if (content.length === 0 || allJobs.length >= totalFound) break;
        } while (offset < totalFound && offset < 500);

        result.open_roles_count = totalFound || allJobs.length;
        const prodJobs = allJobs.filter(j => {
          if (!isProductRole(j.name)) return false;
          let loc = (j.location && j.location.city) || 'Belfast / UK Hybrid';
          return isUkOrNiRelevant(loc, company);
        });
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
          const prodJobs = allJobs.filter(j => {
            if (!isProductRole(j.title)) return false;
            const loc = (j.location ? j.location.name : '') || company.location || 'Remote / Hybrid';
            return isUkOrNiRelevant(loc, company);
          });
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
          const prodJobs = allJobs.filter(j => {
            if (!isProductRole(j.title)) return false;
            const loc = j.location || company.location || 'Remote / Hybrid';
            return isUkOrNiRelevant(loc, company);
          });
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
          const allProdJobs = allJobs.filter(j => isProductRole(j.title));
          const ukOrRemote = allProdJobs.filter(j => {
            const locStr = `${j.city || ''} ${j.country || ''} ${j.region || ''} ${j.state || ''}`.toLowerCase();
            return locStr.includes('united kingdom') || locStr.includes('uk') || locStr.includes('london') || locStr.includes('belfast') || j.telecommuting;
          });
          const prodJobs = ukOrRemote.length > 0 ? ukOrRemote : allProdJobs;
          prodJobs.sort((a, b) => {
            const aUk = `${a.city || ''} ${a.country || ''}`.toLowerCase().includes('london') || `${a.country || ''}`.toLowerCase().includes('united kingdom');
            const bUk = `${b.city || ''} ${b.country || ''}`.toLowerCase().includes('london') || `${b.country || ''}`.toLowerCase().includes('united kingdom');
            return (bUk ? 1 : 0) - (aUk ? 1 : 0);
          });
          const uniqueProdJobs = [];
          for (const j of prodJobs) {
            if (!uniqueProdJobs.some(u => u.url === j.url)) {
              uniqueProdJobs.push(j);
            }
          }
          result.product_roles_count = uniqueProdJobs.length;
          result.active_product_roles = uniqueProdJobs.map(j => ({
            title: j.title,
            location: j.city ? `${j.city}, ${j.country}` : (j.country || 'Remote / Hybrid'),
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
          const prodJobs = allJobs.filter(j => {
            if (!isProductRole(j.text)) return false;
            const loc = (j.categories && j.categories.location) || company.location || 'Remote / Hybrid';
            return isUkOrNiRelevant(loc, company);
          });
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
              location: company.location || 'Belfast / Remote UK',
              url: j.url.startsWith('http') ? j.url : new URL(j.url, targetUrl).href,
              date_posted: new Date().toISOString().split('T')[0]
            }));
            return result;
          }
        }
      } catch (ttErr) {
        console.error(`Teamtailor fetch error for ${company.name}:`, ttErr.message);
      }
    }

    // 7. Volcanic Cloud Parser (e.g. Ulster University)
    if (company.ats_type === 'volcanic' || (company.careers_url && company.careers_url.includes('volcanic.cloud'))) {
      try {
        const res = await fetch(company.careers_url, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
          }
        });
        if (res.ok) {
          const html = await res.text();
          const jobRegex = /<a[^>]+href=["'](\/job\/[^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
          const found = [];
          let jm;
          while ((jm = jobRegex.exec(html)) !== null) {
            const rawHref = jm[1];
            if (rawHref.includes('/save_job') || rawHref.includes('/apply')) continue;
            const rawText = jm[2].replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
            if (rawText && rawText.length > 3 && rawText.length < 120 && !found.some(f => f.url === rawHref)) {
              found.push({ url: rawHref, title: rawText });
            }
          }
          if (found.length > 0) {
            result.open_roles_count = found.length;
            const prodJobs = found.filter(j => isProductRole(j.title));
            result.product_roles_count = prodJobs.length;
            const urlObj = new URL(company.careers_url);
            result.active_product_roles = prodJobs.map(j => ({
              title: j.title,
              location: 'Belfast & Derry',
              url: `${urlObj.origin}${j.url}`,
              date_posted: new Date().toISOString().split('T')[0]
            }));
            return result;
          }
        }
      } catch (vErr) {
        console.error(`Volcanic fetch error for ${company.name}:`, vErr.message);
      }
    }

    // 8. BambooHR API Handler (e.g. Aflac NI)
    if (company.ats_type === 'bamboohr' || (company.careers_url && company.careers_url.includes('bamboohr.com'))) {
      try {
        let subdomain = company.ats_identifier;
        if (!subdomain && company.careers_url) {
          const match = company.careers_url.match(/https?:\/\/([^.]+)\.bamboohr\.com/);
          if (match) subdomain = match[1];
        }
        if (subdomain) {
          const res = await fetch(`https://${subdomain}.bamboohr.com/careers/list`, {
            headers: { 'Accept': 'application/json' }
          });
          if (res.ok) {
            const data = await res.json();
            const jobs = data.result || [];
            const prodJobs = jobs.filter(j => {
              if (!isProductRole(j.jobOpeningName)) return false;
              const loc = (j.location && j.location.city) || company.location || 'Belfast (Hybrid)';
              return isUkOrNiRelevant(loc, company);
            });
            result.product_roles_count = prodJobs.length;
            result.active_product_roles = prodJobs.map(j => ({
              title: j.jobOpeningName,
              location: (j.location && j.location.city) || company.location || 'Belfast (Hybrid)',
              department: j.departmentLabel || 'Digital Services',
              url: `https://${subdomain}.bamboohr.com/careers/${j.id}`,
              date_found: new Date().toISOString().split('T')[0]
            }));
            return result;
          }
        }
      } catch (bErr) {
        console.error(`BambooHR fetch error for ${company.name}:`, bErr.message);
      }
    }

    // 9. JazzHR Parser (e.g. Nisos, iManage)
    if (company.ats_type === 'jazzhr' || (company.careers_url && company.careers_url.includes('applytojob.com'))) {
      try {
        const res = await fetch(company.careers_url, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
          }
        });
        if (res.ok) {
          const html = await res.text();
          const rowRegex = /<tr[^>]*class=["']resumator_(?:even|odd)_row["'][^>]*>([\s\S]*?)<\/tr>/gi;
          let m;
          const found = [];
          const host = new URL(company.careers_url).host;
          while ((m = rowRegex.exec(html)) !== null) {
            const rowHtml = m[1];
            const linkMatch = rowHtml.match(/<a[^>]+class=["']job_title_link["'][^>]+href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/i);
            const tds = rowHtml.match(/<td[^>]*>([\s\S]*?)<\/td>/gi) || [];
            const loc = tds.length > 1 ? tds[1].replace(/<[^>]+>/g, '').trim() : (company.location || 'Belfast / Remote UK');
            if (linkMatch) {
              const rawTitle = linkMatch[2].replace(/<[^>]+>/g, '').trim();
              const jobUrl = linkMatch[1].startsWith('http') ? linkMatch[1] : `https://${host}${linkMatch[1]}`;
              if (rawTitle && !found.some(f => f.url === jobUrl)) {
                found.push({ title: rawTitle, location: loc, url: jobUrl });
              }
            }
          }
          if (found.length > 0) {
            result.open_roles_count = found.length;
            const prodJobs = found.filter(j => {
              if (!isProductRole(j.title)) return false;
              const locLower = (j.location || '').toLowerCase();
              if (locLower.includes('belfast') || locLower.includes('northern ireland') || locLower.includes('uk') || locLower.includes('united kingdom') || locLower.includes('remote') || locLower.includes('hybrid')) {
                return true;
              }
              if (locLower.includes('chicago') || locLower.includes('new york') || locLower.includes('toronto') || locLower.includes('san francisco') || locLower.includes('il') || locLower.includes('ca')) {
                return false;
              }
              return true;
            });
            result.product_roles_count = prodJobs.length;
            result.active_product_roles = prodJobs.map(j => ({
              title: j.title,
              location: j.location,
              url: j.url,
              date_posted: new Date().toISOString().split('T')[0]
            }));
            return result;
          }
        }
      } catch (jErr) {
        console.error(`JazzHR fetch error for ${company.name}:`, jErr.message);
      }
    }

    // 10. Pinpoint API Handler (e.g. NCC Group)
    if (company.ats_type === 'pinpoint' || (company.careers_url && company.careers_url.includes('pinpointhq.com'))) {
      let slug = company.ats_identifier;
      if (!slug && company.careers_url) {
        const pMatch = company.careers_url.match(/https?:\/\/([^.]+)\.pinpointhq\.com/);
        if (pMatch) slug = pMatch[1];
      }
      if (slug) {
        try {
          const res = await fetch(`https://${slug}.pinpointhq.com/postings.json`, {
            headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36' }
          });
          if (res.ok) {
            const data = await res.json();
            const allJobs = (data.data || []).filter(j => {
              const divName = (j.job && j.job.division && j.job.division.name) || '';
              return divName !== 'ACME' && !((j.benefits || '').includes('lumbersexual'));
            });
            result.open_roles_count = allJobs.length;
            const prodJobs = allJobs.filter(j => {
              if (!isProductRole(j.title)) return false;
              const loc = (j.location && (j.location.city || j.location.name)) || company.location || 'UK / Hybrid';
              return isUkOrNiRelevant(loc, company);
            });
            result.product_roles_count = prodJobs.length;
            result.active_product_roles = prodJobs.map(j => ({
              title: j.title,
              location: (j.location && (j.location.city || j.location.name)) || company.location || 'UK / Hybrid',
              url: j.url || `https://${slug}.pinpointhq.com/en/postings/${j.id}`,
              date_posted: (j.deadline_at || new Date().toISOString()).split('T')[0]
            }));
            return result;
          }
        } catch (pErr) {
          console.error(`Pinpoint fetch error for ${company.name}:`, pErr.message);
        }
      }
    }

    // 11. Workday CXS API Handler (e.g. Darktrace, Proofpoint, Kainos)
    if (company.ats_type === 'workday' || (company.careers_url && company.careers_url.includes('myworkdayjobs.com'))) {
      let host = '';
      let subdomain = '';
      let site = '';

      if (company.careers_url) {
        try {
          const u = new URL(company.careers_url);
          host = u.host;
          subdomain = u.host.split('.')[0];
          site = u.pathname.split('/').filter(Boolean)[0] || '';
        } catch (e) {}
      }

      if (!site && company.ats_identifier && company.ats_identifier.includes('/')) {
        [subdomain, site] = company.ats_identifier.split('/');
        host = `${subdomain}.myworkdayjobs.com`;
      }

      if (host && subdomain && site) {
        try {
          let allJobs = [];
          let offset = 0;
          const limit = 20;
          let total = 1;
          while (offset < total && offset < 200) {
            const wdUrl = `https://${host}/wday/cxs/${subdomain}/${site}/jobs`;
            const res = await fetch(wdUrl, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
              },
              body: JSON.stringify({ appliedFacets: {}, limit, offset, searchText: '' })
            });
            if (!res.ok) break;
            const data = await res.json();
            total = data.total || 0;
            const postings = data.jobPostings || [];
            allJobs.push(...postings);
            offset += limit;
            if (postings.length === 0) break;
          }
          if (allJobs.length > 0 || total > 0) {
            result.open_roles_count = total || allJobs.length;
            const prodJobs = allJobs.filter(j => {
              if (!isProductRole(j.title)) return false;
              const loc = j.locationsText || company.location || 'UK / Hybrid';
              return isUkOrNiRelevant(loc, company);
            });
            result.product_roles_count = prodJobs.length;
            result.active_product_roles = prodJobs.map(j => ({
              title: j.title,
              location: j.locationsText || company.location || 'UK / Hybrid',
              url: `https://${host}/${site}${j.externalPath}`,
              date_posted: (j.postedOn || new Date().toISOString()).split('T')[0]
            }));
            return result;
          }
        } catch (wdErr) {
          console.error(`Workday fetch error for ${company.name}:`, wdErr.message);
        }
      }
    }

    // 12. Comeet API Handler (e.g. Upwind Security)
    if (company.ats_type === 'comeet') {
      const uid = company.ats_identifier;
      const token = company.ats_token;
      if (uid && token) {
        try {
          const res = await fetch(`https://www.comeet.co/careers-api/2.0/company/${uid}/positions?token=${token}`);
          if (res.ok) {
            const allJobs = await res.json();
            result.open_roles_count = allJobs.length;
            const prodJobs = allJobs.filter(j => {
              if (!isProductRole(j.name)) return false;
              const locParts = [j.location?.city, j.location?.name, j.location?.country, j.workplace_type].filter(Boolean).join(', ');
              const loc = locParts || company.location || 'UK / Hybrid';
              return isUkOrNiRelevant(loc, company);
            });
            result.product_roles_count = prodJobs.length;
            result.active_product_roles = prodJobs.map(j => ({
              title: j.name,
              location: (j.location && (j.location.city || j.location.name)) || company.location || 'UK / Hybrid',
              url: j.url_active_page || j.url_comeet_hosted_page || company.careers_url,
              date_posted: (j.time_updated || new Date().toISOString()).split('T')[0]
            }));
            return result;
          }
        } catch (cErr) {
          console.error(`Comeet fetch error for ${company.name}:`, cErr.message);
        }
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

async function runScanner(targetPath = DEFAULT_DB_PATH) {
  const isCyber = targetPath.includes('cyber_companies.json');
  const label = isCyber ? 'UK Cybersecurity' : 'Northern Ireland Tech';
  console.log(`🚀 Starting ${label} Role Scanner...`);
  if (!fs.existsSync(targetPath)) {
    console.error(`Database not found at ${targetPath}`);
    process.exit(1);
  }

  const raw = fs.readFileSync(targetPath, 'utf-8');
  const companies = JSON.parse(raw);
  console.log(`Loaded ${companies.length} companies from ${path.basename(targetPath)}.`);

  const updatedCompanies = [];
  const BATCH_SIZE = 10;
  for (let i = 0; i < companies.length; i += BATCH_SIZE) {
    const chunk = companies.slice(i, i + BATCH_SIZE);
    const results = await Promise.all(chunk.map(c => scanCompany(c)));
    updatedCompanies.push(...results);
  }

  fs.writeFileSync(targetPath, JSON.stringify(updatedCompanies, null, 2), 'utf-8');
  const liveCount = updatedCompanies.reduce((acc, c) => acc + (c.product_roles_count || 0), 0);
  console.log(`✅ Scan completed. Found ${liveCount} live verified product roles across ${companies.length} companies.`);
  return { targetPath, totalCompanies: companies.length, liveCount };
}

if (require.main === module) {
  (async () => {
    if (process.argv.includes('--cyber')) {
      await runScanner(CYBER_DB_PATH);
    } else if (process.argv.includes('--all')) {
      await runScanner(DEFAULT_DB_PATH);
      await runScanner(CYBER_DB_PATH);
    } else {
      await runScanner(DEFAULT_DB_PATH);
    }
  })();
}

module.exports = { scanCompany, runScanner };
