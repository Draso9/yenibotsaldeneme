const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const test = require('node:test');
const ts = require('typescript');
const React = require('react');
const { JSDOM } = require('jsdom');
const { createRoot } = require('react-dom/client');
const { act } = React;

for (const extension of ['.ts', '.tsx']) {
  require.extensions[extension] = (module, filename) => {
    const { outputText } = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
      compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true },
    });
    module._compile(outputText, filename);
  };
}
let auth;
let route;
const replacements = [];
const router = { replace: (href) => replacements.push(href) };
const originalLoad = Module._load;
// External Firebase session and Next router only; React, context persistence,
// components and API request/response handling remain real.
Module._load = function (id, parent, isMain) {
  if (id === './auth-provider') return { useIzfinAuth: () => auth };
  if (id === 'next/navigation') return {
    usePathname: () => route.pathname,
    useSearchParams: () => route.searchParams,
    useRouter: () => router,
  };
  return originalLoad.call(this, id, parent, isMain);
};
const { AnalysisContextProvider } = require('../components/analysis-context-provider.tsx');
const { StockDetailPage } = require('../components/stock-detail-page.tsx');
const { AppShell } = require('../components/app-shell.tsx');
Module._load = originalLoad;

const historyItem = (job_id, status = 'completed') => ({ job_id, status, stage: status, completed: status === 'completed' ? 2 : 0, total: 2, tickers: ['AAA', 'BBB'] });
const detail = (ticker, price) => ({ ticker, price, score: { nihai: 75 }, decision: { karar: 'BEKLE' }, action: { profile: 'BOĞA' }, panel: {} });
let dom, root, container, calls, responses, history;
const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });

test.beforeEach(() => {
  dom = new JSDOM('<div id="root"></div>', { url: 'https://izfin.test/stocks/BBB' });
  global.window = dom.window;
  global.document = dom.window.document;
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.getElementById('root');
  root = createRoot(container);
  auth = { loading: false, user: { uid: 'owner', email: 'owner@example.test', emailVerified: true }, getIdToken: async () => 'test-token', logout: async () => {} };
  route = new URL('https://izfin.test/stocks/BBB?job_id=old%2Fjob&source=scan');
  replacements.length = 0;
  calls = [];
  history = [historyItem('running', 'running'), historyItem('latest'), historyItem('old/job')];
  responses = new Map([
    ['/api/v1/market/jobs/old%2Fjob/stocks/BBB', () => json(detail('BBB', 101))],
    ['/api/v1/market/jobs/latest/stocks/BBB', () => json(detail('BBB', 202))],
    ['/api/v1/market/jobs/latest/stocks/AAA', () => json(detail('AAA', 303))],
  ]);
  global.fetch = async (url, init) => {
    const path = String(url).replace('/izfin-api', '');
    calls.push({ path, authorization: init.headers.Authorization });
    if (path === '/api/v1/scan/jobs') return json({ jobs: history });
    if (path.endsWith('/health/ready/durable')) return json({ ready: true });
    if (path.endsWith('/account/bootstrap')) return json({});
    if (path.endsWith('/legal/consent')) return json({ accepted: true });
    return responses.get(path)?.() ?? json({ error: { message: 'Bulunamadı' } }, 404);
  };
});
test.afterEach(async () => {
  await act(async () => root.unmount());
  dom.window.close();
  delete global.window;
  delete global.document;
  delete global.IS_REACT_ACT_ENVIRONMENT;
});
function cache(value) { window.localStorage.setItem('izfin:analysis-context:owner', JSON.stringify(value)); }
function stored() { return JSON.parse(window.localStorage.getItem('izfin:analysis-context:owner')); }
async function render(jobId = '', ticker = 'BBB', shell = false) {
  await act(async () => {
    const page = React.createElement(StockDetailPage, { jobId, ticker });
    root.render(React.createElement(AnalysisContextProvider, null, shell ? React.createElement(AppShell, null, page) : page));
  });
}
const projection = () => container.querySelector('.projection-cta')?.getAttribute('href');

test('contextual sidebar link preserves the explicit scan query', async () => {
  await render('old/job', 'BBB', true);
  assert.equal(container.querySelector('.contextual-nav-item')?.getAttribute('aria-current'), 'page');
  assert.equal(container.querySelector('.contextual-nav-item')?.getAttribute('href'), '/stocks/BBB?job_id=old%2Fjob&source=scan');
});

test('missing query restores the owned remembered completed scan and exact ticker', async () => {
  cache({ activeScanJobId: 'old/job', selectedTicker: 'AAA' });
  await render();
  assert.match(container.textContent, /101/);
  assert.equal(projection(), '/projection?job_id=old%2Fjob&ticker=BBB');
  assert.equal(stored().selectedTicker, 'BBB');
  assert.equal(stored().lastVisitedAnalysisRoute, '/stocks/BBB?job_id=old%2Fjob');
  assert.ok(replacements.includes('/stocks/BBB?job_id=old%2Fjob'));
  assert.ok(calls.filter(c => c.path.includes('/market/jobs/')).every(c => c.authorization === 'Bearer test-token'));
});

test('running or stale remembered scan recovers the latest completed scan', async () => {
  cache({ activeScanJobId: 'running', selectedTicker: 'AAA' });
  await render();
  assert.match(container.textContent, /202/);
  assert.equal(projection(), '/projection?job_id=latest&ticker=BBB');
  assert.ok(!calls.some(c => c.path.includes('/market/jobs/running/')));
});

test('an explicit job wins over remembered and latest history', async () => {
  cache({ activeScanJobId: 'latest', selectedTicker: 'AAA' });
  await render('old/job');
  assert.match(container.textContent, /101/);
  assert.equal(projection(), '/projection?job_id=old%2Fjob&ticker=BBB');
});

test('foreign explicit job errors without overwriting valid persisted selection or falling back', async () => {
  history = history.filter(item => item.status === 'completed');
  cache({ activeScanJobId: 'old/job', selectedTicker: 'AAA', lastVisitedAnalysisRoute: '/scan' });
  await render('foreign');
  assert.ok(container.querySelector('[role="alert"]'));
  assert.equal(projection(), undefined);
  assert.equal(stored().activeScanJobId, 'old/job');
  assert.equal(stored().selectedTicker, 'AAA');
  assert.equal(stored().lastVisitedAnalysisRoute, '/scan');
  assert.ok(!calls.some(c => c.path.includes('/market/jobs/old%2Fjob/')));
});

test('no completed scan offers a scan return without sending an empty detail request', async () => {
  history = [historyItem('running', 'running')];
  await render();
  assert.match(container.textContent, /tamamlanmış.*tarama/i);
  assert.ok(container.querySelector('a[href="/scan#scan-result"]'));
  assert.ok(!container.querySelector('.detail-status:not([role="alert"])'));
  assert.ok(!calls.some(c => c.path.includes('/market/jobs/')));
});

test('missing requested ticker never substitutes the remembered ticker', async () => {
  cache({ activeScanJobId: 'latest', selectedTicker: 'AAA' });
  await render('', 'MISSING');
  assert.ok(container.querySelector('[role="alert"]'));
  assert.equal(projection(), undefined);
  assert.equal(stored().selectedTicker, 'AAA');
  assert.ok(!calls.some(c => c.path.endsWith('/stocks/AAA')));
});

test('token acquisition failure exits loading and does not publish unverified context', async () => {
  auth.getIdToken = async () => null;
  cache({ activeScanJobId: 'old/job', selectedTicker: 'AAA' });
  await render('latest');
  assert.ok(container.querySelector('[role="alert"]'));
  assert.equal(stored().selectedTicker, 'AAA');
});

test('late response from a previous route cannot replace the new stock or selection', async () => {
  let finishOld;
  responses.set('/api/v1/market/jobs/old%2Fjob/stocks/BBB', () => new Promise(resolve => { finishOld = resolve; }));
  await render('old/job');
  await render('latest', 'AAA');
  assert.match(container.textContent, /303/);
  await act(async () => finishOld(json(detail('BBB', 101))));
  assert.doesNotMatch(container.textContent, /101/);
  assert.equal(stored().selectedTicker, 'AAA');
  assert.equal(projection(), '/projection?job_id=latest&ticker=AAA');
});


test('switching accounts clears the old detail immediately while the new request is pending', async () => {
  await render('old/job');
  assert.match(container.textContent, /101/);
  let finish;
  responses.set('/api/v1/market/jobs/old%2Fjob/stocks/BBB', () => new Promise(resolve => { finish = resolve; }));
  auth = { ...auth, user: { ...auth.user, uid: 'other-owner' } };
  await render('old/job');
  assert.doesNotMatch(container.textContent, /101/);
  assert.equal(projection(), undefined);
  await act(async () => finish(json({ error: { message: 'Bulunamadı' } }, 404)));
  assert.ok(container.querySelector('[role="alert"]'));
  assert.equal(stored().selectedTicker, 'BBB');
  const other = JSON.parse(window.localStorage.getItem('izfin:analysis-context:other-owner'));
  assert.equal(other.selectedTicker, '');
});

test('an explicit unfinished scan is not replaced with an older successful result', async () => {
  responses.set('/api/v1/market/jobs/running/stocks/BBB', () => json({ error: { message: 'Henüz tamamlanmadı' } }, 409));
  await render('running');
  assert.ok(container.querySelector('[role="alert"]'));
  assert.equal(projection(), undefined);
  assert.ok(!calls.some(c => c.path.includes('/market/jobs/latest/')));
});

test('refresh after recovery uses the canonical job even if newer history arrives', async () => {
  history = [historyItem('old/job')];
  await render();
  const canonical = replacements.at(-1);
  assert.equal(canonical, '/stocks/BBB?job_id=old%2Fjob');
  await act(async () => root.unmount());
  root = createRoot(container);
  history = [historyItem('latest'), historyItem('old/job')];
  await render(new URL(canonical, 'https://izfin.test').searchParams.get('job_id'));
  assert.match(container.textContent, /101/);
  assert.equal(projection(), '/projection?job_id=old%2Fjob&ticker=BBB');
});

test('provider history refresh cannot switch the remembered scan during recovery', async () => {
  cache({ activeScanJobId: 'old/job', selectedTicker: 'BBB' });
  const realFetch = global.fetch;
  let historyCalls = 0, finishHistory, finishOld;
  global.fetch = (url, init) => {
    if (String(url).endsWith('/api/v1/scan/jobs') && ++historyCalls === 1) {
      return new Promise(resolve => { finishHistory = resolve; });
    }
    return realFetch(url, init);
  };
  responses.set('/api/v1/market/jobs/old%2Fjob/stocks/BBB', () => new Promise(resolve => { finishOld = resolve; }));
  await render();
  await act(async () => finishHistory(json({ jobs: history })));
  await act(async () => finishOld(json(detail('BBB', 101))));
  assert.equal(projection(), '/projection?job_id=old%2Fjob&ticker=BBB');
  assert.equal(replacements.at(-1), '/stocks/BBB?job_id=old%2Fjob');
});
