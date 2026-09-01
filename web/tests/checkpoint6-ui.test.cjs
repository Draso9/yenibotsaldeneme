const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const ts = require("typescript");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

// Execute the actual presentational components without adding a test dependency.
require.extensions[".tsx"] = (module, filename) => {
  const { outputText } = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS },
  });
  module._compile(outputText, filename);
};
const { PerformanceMobileCards } = require("../components/performance-mobile-cards.tsx");
const { MobileNavigation } = require("../components/mobile-navigation.tsx");

test("missing mobile return values stay unavailable instead of becoming zero", () => {
  for (const value of [null, undefined, "", " "]) {
    const html = renderToStaticMarkup(React.createElement(PerformanceMobileCards, {
      rows: [{ "Kâr / Zarar %": value }], variant: "active",
    }));
    assert.match(html, /K\/Z<\/small><strong>—<\/strong>/);
    assert.doesNotMatch(html, />0%/);
  }
});

test("mobile navigation exposes admin only to authorized users", () => {
  const render = (isAdmin) => renderToStaticMarkup(React.createElement(MobileNavigation, {
    pathname: "/account", isAdmin,
  }));
  assert.equal((render(false).match(/data-mobile-primary="true"/g) || []).length, 5);
  assert.doesNotMatch(render(false), /href="\/admin\/quality"/);
  assert.match(render(true), /href="\/admin\/quality"/);
  assert.match(render(false), /aria-current="page" href="\/account"/);
  assert.doesNotMatch(render(false), /\/stocks\//);
});

test("mobile cards retain secondary fields behind a disclosure", () => {
  for (const [variant, fields] of [
    ["active", ["İlk Sinyal", "İlk Alım Fiyatı", "Güncel Fiyat"]],
    ["closed", ["Maks. Kâr %", "Maks. Düşüş %", "İlk Stop", "İlk TP1", "TP1", "TP2", "TP3", "Stop"]],
  ]) {
    const html = renderToStaticMarkup(React.createElement(PerformanceMobileCards, { rows: [{}], variant }));
    assert.match(html, /<details class="performance-mobile-secondary">/);
    for (const field of fields) assert.ok(html.includes(`<dt>${field}</dt>`), field);
  }
});

test("closed card inspection passes the selected row index", () => {
  let inspected = null;
  const tree = PerformanceMobileCards({ rows: [{}, {}], variant: "closed", onInspectClosed: (index) => { inspected = index; } });
  const buttons = [];
  const visit = (node) => {
    if (!node || typeof node !== "object") return;
    if (Array.isArray(node)) return node.forEach(visit);
    if (node.type === "button") buttons.push(node);
    visit(node.props?.children);
  };
  visit(tree);
  assert.equal(buttons.length, 2);
  buttons[1].props.onClick();
  assert.equal(inspected, 1);
});
