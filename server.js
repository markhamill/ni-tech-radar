const http = require('http');
const fs = require('fs');
const path = require('path');
const { runScanner } = require('./scanner');

const PORT = process.env.PORT || 3333;
const DEFAULT_DB_PATH = path.join(__dirname, 'public', 'data', 'companies.json');
const CYBER_DB_PATH = path.join(__dirname, 'public', 'data', 'cyber_companies.json');
const DB_PATH = DEFAULT_DB_PATH;
const PUBLIC_DIR = path.join(__dirname, 'public');
const APPLICATIONS_DIR = path.join(__dirname, '..', 'applications');

function getDbPath(dataset) {
  if (dataset === 'cyber' || dataset === 'cybersecurity') {
    return CYBER_DB_PATH;
  }
  return DEFAULT_DB_PATH;
}

function readJsonBody(req) {
  return new Promise(resolve => {
    let data = '';
    req.on('data', chunk => { data += chunk; });
    req.on('end', () => {
      if (!data.trim()) return resolve({});
      try {
        resolve(JSON.parse(data));
      } catch (err) {
        resolve({});
      }
    });
  });
}

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

function normalize(str) {
  return (str || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function getTrackedApplications() {
  const apps = [];
  try {
    if (!fs.existsSync(APPLICATIONS_DIR)) return apps;

    const folders = fs.readdirSync(APPLICATIONS_DIR, { withFileTypes: true });
    for (const dirent of folders) {
      if (!dirent.isDirectory()) continue;
      const statusPath = path.join(APPLICATIONS_DIR, dirent.name, 'application_status.md');
      if (!fs.existsSync(statusPath)) continue;

      try {
        const content = fs.readFileSync(statusPath, 'utf-8');
        const companyMatch = content.match(/\*\*Company:\*\*\s*(.*)/i);
        const roleMatch = content.match(/\*\*Role Title:\*\*\s*(.*)/i);
        const stageMatch = content.match(/\*\*Current Stage:\*\*\s*(.*)/i);
        const dateMatch = content.match(/\*\*Date Applied:\*\*\s*(.*)/i);
        const compensationMatch = content.match(/\*\*Estimated Compensation:\*\*\s*(.*)/i);

        if (companyMatch) {
          apps.push({
            folder: dirent.name,
            company: companyMatch[1].trim(),
            role_title: roleMatch ? roleMatch[1].trim() : 'Product Leader',
            current_stage: stageMatch ? stageMatch[1].trim() : 'Discovered',
            date_applied: dateMatch ? dateMatch[1].trim() : '',
            compensation: compensationMatch ? compensationMatch[1].trim() : ''
          });
        }
      } catch (e) {
        // Silently skip corrupted or locked single status files
      }
    }
  } catch (err) {
    // Graceful fallback if applications directory is inaccessible or missing
  }
  return apps;
}

function getTokens(str) {
  return (str || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter(t => t.length > 0);
}

function matchCompanyApplications(companyName, companyId, trackedApps) {
  const normName = normalize(companyName);
  const normId = normalize(companyId);
  const nameTokens = getTokens(companyName);
  const idTokens = getTokens(companyId.replace(/-/g, ' '));

  return trackedApps.filter(app => {
    const normApp = normalize(app.company);
    if (!normApp) return false;

    // 1. Exact match
    if (normApp === normName || normApp === normId) return true;

    // 2. Prefix match if name is sufficiently distinctive
    if (normApp.length >= 4 && (normName.startsWith(normApp) || normApp.startsWith(normName))) return true;

    // 3. Token-based match
    const appTokens = getTokens(app.company);
    const primaryToken = appTokens.find(t => !['the', 'inc', 'ltd', 'limited', 'group', 'uk', 'ni', 'technologies', 'technology', 'systems'].includes(t));
    if (primaryToken && primaryToken.length >= 3) {
      if (nameTokens.includes(primaryToken) || idTokens.includes(primaryToken)) {
        if (appTokens.length > 1) {
          const secondToken = appTokens[1];
          if (nameTokens.includes(secondToken) || idTokens.includes(secondToken)) return true;
        } else {
          return true;
        }
      }
    }

    return false;
  });
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;

  // API: Get companies enriched with live local application tracking
  if (req.method === 'GET' && (pathname === '/api/companies' || pathname === '/api/cyber-companies')) {
    const requestedDataset = pathname === '/api/cyber-companies' ? 'cyber' : (url.searchParams.get('dataset') || 'ni');
    const targetDbPath = getDbPath(requestedDataset);

    try {
      if (!fs.existsSync(targetDbPath)) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: `Database file not found for dataset '${requestedDataset}'` }));
        return;
      }
      const data = fs.readFileSync(targetDbPath, 'utf-8');
      const companies = JSON.parse(data);
      const trackedApps = getTrackedApplications();

      const enriched = companies.map(c => {
        const matchedApps = matchCompanyApplications(c.name, c.id, trackedApps);
        return {
          ...c,
          tracked_applications: matchedApps
        };
      });

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(enriched));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Failed to read database', details: err.message }));
    }
    return;
  }

  // API: Trigger scanner
  if (req.method === 'POST' && pathname === '/api/scan') {
    try {
      const body = await readJsonBody(req);
      const requestedDataset = body.dataset || url.searchParams.get('dataset') || 'ni';

      // Always reload fresh scanner module
      delete require.cache[require.resolve('./scanner')];
      const { runScanner } = require('./scanner');

      if (requestedDataset === 'all') {
        await runScanner(DEFAULT_DB_PATH);
        await runScanner(CYBER_DB_PATH);
      } else {
        const targetDbPath = getDbPath(requestedDataset);
        await runScanner(targetDbPath);
      }

      const returnDbPath = getDbPath(requestedDataset);
      const data = fs.readFileSync(returnDbPath, 'utf-8');
      const companies = JSON.parse(data);
      const trackedApps = getTrackedApplications();
      const enriched = companies.map(c => ({
        ...c,
        tracked_applications: matchCompanyApplications(c.name, c.id, trackedApps)
      }));

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'success', message: 'Scan completed', dataset: requestedDataset, data: enriched }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Failed to run scanner', details: err.message }));
    }
    return;
  }

  // API: Add new company
  if (req.method === 'POST' && pathname === '/api/companies') {
    try {
      const body = await readJsonBody(req);
      const newCompany = body;
      const targetDataset = body.dataset || url.searchParams.get('dataset') || 'ni';
      const targetDbPath = getDbPath(targetDataset);

      if (!newCompany.id || !newCompany.name) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Missing required company id or name' }));
        return;
      }
      const companies = JSON.parse(fs.readFileSync(targetDbPath, 'utf-8'));
      companies.push({
        ...newCompany,
        last_checked: new Date().toISOString(),
        active_product_roles: newCompany.active_product_roles || [],
        open_roles_count: newCompany.open_roles_count || 0,
        product_roles_count: newCompany.product_roles_count || 0
      });
      fs.writeFileSync(targetDbPath, JSON.stringify(companies, null, 2), 'utf-8');
      res.writeHead(201, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'success', data: newCompany }));
    } catch (err) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid JSON payload', details: err.message }));
    }
    return;
  }

  // Static File Serving
  let filePath = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);
  const ext = path.extname(filePath).toLowerCase();

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      filePath = path.join(PUBLIC_DIR, 'index.html');
    }

    fs.readFile(filePath, (readErr, content) => {
      if (readErr) {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('404 Not Found');
        return;
      }
      res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'text/html' });
      res.end(content);
    });
  });
});

server.listen(PORT, () => {
  console.log(`\n=============================================================`);
  console.log(`🌟 Northern Ireland Tech Radar is running locally!`);
  console.log(`🔗 Dashboard URL: http://localhost:${PORT}`);
  console.log(`=============================================================\n`);
});
