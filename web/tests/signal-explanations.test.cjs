const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const ts = require("typescript");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

for (const extension of [".tsx", ".ts"]) require.extensions[extension] = (module, filename) => {
  const { outputText } = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS },
  });
  module._compile(outputText, filename);
};
const { ScanMobileResultList } = require("../components/scan-mobile-result-list.tsx");
const { SignalExplanation } = require("../components/signal-explanation.tsx");
const { technicalProfile, confidenceScore, isTrendCandidate } = require("../lib/signal-labels.ts");

test("historic mobile results show trend profile and a score without changing the record", () => {
  const row = { Varlık: "NVDA", "Nihai Sinyal": "TEYİT BEKLE 🟡", "Teknik Profil": "UZUN VADELİ ADAY 🌟", "Güven": "%69" };
  const before = structuredClone(row);
  const html = renderToStaticMarkup(React.createElement(ScanMobileResultList, { rows: [row], selectedTicker: "", onSelectTicker() {} }));
  assert.match(html, /TREND ADAYI/);
  assert.match(html, /69\/100/);
  assert.doesNotMatch(html, /UZUN VADELİ|%69/);
  assert.match(html, /TEYİT BEKLE/);
  assert.deepEqual(row, before);
});

test("missing mobile confidence is unavailable, while a real zero remains zero", () => {
  for (const [value, expected] of [[null, "—"], [undefined, "—"], ["", "—"], [false, "—"], [0, "0/100"]]) {
    const html = renderToStaticMarkup(React.createElement(ScanMobileResultList, { rows: [{ "Güven": value }], selectedTicker: "", onSelectTicker() {} }));
    assert.ok(html.includes(`<dt>Güven puanı</dt><dd>${expected}</dd>`));
  }
});

test("candidate membership accepts old names and leaves unrelated profiles outside", () => {
  for (const name of ["UZUN VADELİ ADAY 🌟", "Uzun Vadeli Aday", "uzun vadeli aday", "TREND ADAYI 🌟"]) {
    assert.equal(isTrendCandidate({ "Teknik Profil": name }), true);
    assert.match(technicalProfile(name), /TREND ADAYI/);
  }
  assert.equal(isTrendCandidate({ "Teknik Profil": "NÖTR" }), false);
  assert.equal(isTrendCandidate({}), false);
  for (const value of ["80", 80, "%80", "80%", "80/100", " 80/100 "]) assert.equal(confidenceScore(value), "80/100");
});

test("audit renders server supplied conditions and escapes their text", () => {
  const html = renderToStaticMarkup(React.createElement(SignalExplanation, { value: {
    available: true, seviyeler: { AL: [
      { kod: "guven", saglandi: false, metin: "Güven 69/100; gereken ≥70" },
      { kod: "trend", saglandi: true, metin: "Fiyat <eşik>" },
    ] },
  } }));
  assert.match(html, /AL · 1 eksik koşul/);
  assert.match(html.replace(/<[^>]+>/g, ""), /Eksik: Güven 69\/100; gereken ≥70/);
  assert.match(html.replace(/<[^>]+>/g, ""), /Sağlandı: Fiyat &lt;eşik&gt;/);
  assert.doesNotMatch(html, /Fiyat <eşik>/);
});

test("passing buy checks never suppress a prior risk decision", () => {
  const html = renderToStaticMarkup(React.createElement(SignalExplanation, { value: {
    available: true, oncelikli_karar: true,
    seviyeler: { AL: [{ kod: "gate", saglandi: true, metin: "Teyit" }] },
  } }));
  assert.match(html, /Öncelikli risk\/kâr koruma kararı uygulanıyor/);
  assert.match(html, /AL · Alım koşulları sağlandı/);
});

test("missing and incomplete audit data cannot claim a satisfied buy gate", () => {
  for (const value of [null, undefined, { available: false }, { available: true, seviyeler: { AL: [] } }]) {
    const html = renderToStaticMarkup(React.createElement(SignalExplanation, { value }));
    assert.doesNotMatch(html, /Alım koşulları sağlandı/);
  }
});
