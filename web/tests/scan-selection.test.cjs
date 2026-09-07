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
const originalLoad = Module._load;
Module._load = function (id, parent, isMain) {
  if (id === './auth-provider') return { useIzfinAuth: () => auth };
  return originalLoad.call(this, id, parent, isMain);
};
const { AnalysisContextProvider } = require('../components/analysis-context-provider.tsx');
const { ScanWorkspace } = require('../components/scan-workspace.tsx');
Module._load = originalLoad;
let dom, root, container, job;
const key = 'izfin:analysis-context:owner';
const json = data => new Response(JSON.stringify(data), { headers: { 'Content-Type': 'application/json' } });
test.beforeEach(() => {
  dom = new JSDOM('<div id="root"></div>', { url: 'https://izfin.test/scan' });
  global.window = dom.window;
  global.document = dom.window.document;
  global.IS_REACT_ACT_ENVIRONMENT = true;
  container = document.getElementById('root');
  root = createRoot(container);
  auth = { loading: false, user: { uid: 'owner' }, getIdToken: async () => 'test-token' };
  job = { job_id: 'saved', status: 'completed', stage: 'complete', completed: 2, total: 2,
    tickers: ['AAA', 'BBB'], projectable_tickers: ['AAA', 'BBB'],
    result: { sonuclar: [
      { Varlık: 'AAA', 'Nihai Sinyal': 'AL', 'Gelişmiş Skor': 80 },
      { Varlık: 'BBB', 'Nihai Sinyal': 'BEKLE', 'Gelişmiş Skor': 60 },
    ], basarisiz_taramalar: [], boga_sayisi: 0, alim_firsati: 1 } };
  global.fetch = async (url, init) => {
    assert.equal(init.headers.Authorization, 'Bearer test-token');
    const path = String(url).replace('/izfin-api', '');
    if (path === '/api/v1/scan/jobs') return json({ jobs: [job] });
    if (path === '/api/v1/scan/jobs/saved') return json(job);
    if (path === '/api/v1/watchlist') return json({ tickers: job.tickers, recovered: false });
    if (path === '/api/v1/scan/profiles') return json({ profiles: {} });
    if (path === '/api/v1/scan/universe') return json({ profil: 'Kendi Listem', tickers: job.tickers, secim_ozeti: { varlik_adedi: 2 } });
    if (path.startsWith('/api/v1/market/jobs/saved/stocks/') && !job.projectable_tickers.includes(path.split('/').at(-1))) {
      return new Response(JSON.stringify({ detail: 'Tarama sonucu bulunamadı.' }), { status: 404 });
    }
    if (path.startsWith('/api/v1/market/jobs/saved/stocks/')) return json({
      ticker: path.split('/').at(-1), price: 100, score: { nihai: 75 }, decision: { karar: 'BEKLE' }, action: {}, panel: {},
    });
    throw new Error(`Unexpected API request: ${path}`);
  };
});
test.afterEach(async () => {
  await act(async () => root.unmount());
  dom.window.close();
  delete global.window; delete global.document; delete global.IS_REACT_ACT_ENVIRONMENT;
});
async function render(show = true) {
  await act(async () => root.render(React.createElement(AnalysisContextProvider, null,
    show ? React.createElement(ScanWorkspace) : React.createElement('p', null, 'Diğer sekme'))));
}
function cache(ticker) { window.localStorage.setItem(key, JSON.stringify({ activeScanJobId: 'saved', selectedTicker: ticker })); }
function selected(ticker) {
  assert.equal(container.querySelector('#scan-decision-ticker')?.value, ticker);
  assert.equal(container.querySelector('.scan-decision-identity h3')?.textContent, ticker);
  assert.equal(JSON.parse(window.localStorage.getItem(key)).selectedTicker, ticker);
}
test('restores a non-first result on refresh and route return', async () => {
  cache('BBB');
  await render(); selected('BBB');
  await render(false); await render(); selected('BBB');
  await act(async () => root.unmount()); root = createRoot(container);
  await render(); selected('BBB');
});
test('a single projectable ticker must not replace a valid selected result', async () => {
  job.projectable_tickers = ['AAA'];
  cache('BBB');
  await render();
  assert.equal(JSON.parse(window.localStorage.getItem(key)).selectedTicker, 'BBB');
  assert.equal(container.querySelector('tr.is-selected .scan-result-symbol')?.textContent, 'BBB');
  assert.match(container.querySelector('.scan-decision-state[role="alert"]')?.textContent, /yüklenemedi/);
  assert.equal(container.querySelector('.scan-decision-card'), null);
});
test('selection from the table survives filters, sorting and route return', async () => {
  await render(); selected('AAA');
  await act(async () => [...container.querySelectorAll('.scan-result-symbol')].find(el => el.textContent === 'BBB').click());
  selected('BBB');
  await act(async () => [...container.querySelectorAll('.result-filter button')].find(el => el.textContent === 'AL Sinyalleri').click());
  selected('BBB');
  await act(async () => container.querySelector('th button').click()); selected('BBB');
  await render(false); await render(); selected('BBB');
});
test('missing remembered ticker falls back to the first actual result', async () => {
  cache('MISSING'); await render(); selected('AAA');
});
test('a genuine single-result scan selects its only row even without projection data', async () => {
  job.result.sonuclar = [job.result.sonuclar[1]];
  job.projectable_tickers = [];
  cache('AAA'); await render();
  assert.equal(JSON.parse(window.localStorage.getItem(key)).selectedTicker, 'BBB');
  assert.equal(container.querySelector('tr.is-selected .scan-result-symbol')?.textContent, 'BBB');
});
