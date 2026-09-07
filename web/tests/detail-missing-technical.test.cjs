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
      compilerOptions: {
        jsx: ts.JsxEmit.ReactJSX,
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        esModuleInterop: true,
      },
    });
    module._compile(outputText, filename);
  };
}

const selected = [];
const auth = {
  loading: false,
  user: { uid: 'owner', email: 'owner@example.test', emailVerified: true },
  getIdToken: async () => 'test-token',
};
const analysisContext = {
  contextReady: true,
  activeScanJobId: 'job-1',
  setActiveScan: () => {},
  setSelectedTicker: (ticker) => selected.push(ticker),
  setLastVisitedAnalysisRoute: () => {},
};
const router = { replace: () => {} };
const originalLoad = Module._load;
Module._load = function (id, parent, isMain) {
  if (id === './auth-provider') return { useIzfinAuth: () => auth };
  if (id === './analysis-context-provider') return { useAnalysisContext: () => analysisContext };
  if (id === 'next/navigation') return { useRouter: () => router };
  return originalLoad.call(this, id, parent, isMain);
};
const { StockDetailPage } = require('../components/stock-detail-page.tsx');
Module._load = originalLoad;

test('missing technical panel explains the data gap without asking the user to reselect the same stock', async () => {
  const dom = new JSDOM('<div id="root"></div>', { url: 'https://izfin.test/stocks/BBB?job_id=job-1' });
  global.window = dom.window;
  global.document = dom.window.document;
  global.IS_REACT_ACT_ENVIRONMENT = true;
  selected.length = 0;
  const calls = [];
  global.fetch = async (url) => {
    calls.push(String(url));
    return new Response(JSON.stringify({ detail: 'Tarama sonucu bulunamadı.' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    });
  };

  const container = document.getElementById('root');
  const root = createRoot(container);
  try {
    await act(async () => {
      root.render(React.createElement(StockDetailPage, { jobId: 'job-1', ticker: 'BBB' }));
    });

    const alert = container.querySelector('[role="alert"]');
    assert.ok(alert);
    assert.match(alert.textContent, /teknik.*veri.*hazır değil/i);
    assert.doesNotMatch(alert.textContent, /yeniden seç/i);
    assert.ok(container.querySelector('a[href="/scan#scan-result"]'));
    assert.deepEqual(selected, []);
    assert.ok(calls.some((url) => url.endsWith('/izfin-api/api/v1/market/jobs/job-1/stocks/BBB')));
  } finally {
    await act(async () => root.unmount());
    dom.window.close();
    delete global.window;
    delete global.document;
    delete global.IS_REACT_ACT_ENVIRONMENT;
    delete global.fetch;
  }
});
