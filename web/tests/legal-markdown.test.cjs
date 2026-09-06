const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const ts = require("typescript");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");

require.extensions[".tsx"] = (module, filename) => {
  const { outputText } = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  });
  module._compile(outputText, filename);
};
const { LegalMarkdown } = require("../components/legal-markdown.tsx");
const render = (markdown) => renderToStaticMarkup(React.createElement(LegalMarkdown, { markdown }));

test("legal source wrapping stays within one paragraph; blank lines start another", () => {
  const html = render("IZFIN; piyasa verilerini ve\r\nprojeksiyonları gösterir.\r\n\r\nEmir iletmez.");
  assert.match(html, /<p>IZFIN; piyasa verilerini ve projeksiyonları gösterir\.<\/p><p>Emir iletmez\.<\/p>/);
});

test("privacy emphasis and cookie names render as semantic inline content", () => {
  const html = render("### Veri sorumlusu\n\n- **İletişim e-postası:** Yapılandırılmayı bekliyor\n\n**30 gün** boyunca `izfin_session` kullanılır.");
  assert.match(html, /<h3>Veri sorumlusu<\/h3>/);
  assert.match(html, /<li><strong>İletişim e-postası:<\/strong> Yapılandırılmayı bekliyor<\/li>/);
  assert.match(html, /<p><strong>30 gün<\/strong> boyunca <code>izfin_session<\/code> kullanılır\.<\/p>/);
});

test("paragraph, list, and heading boundaries preserve content order without blank lines", () => {
  const html = render("Giriş\nmetni\n- Bir\n- İki\n## Sonraki bölüm\nSon\nparagraf");
  assert.match(html, /<p>Giriş metni<\/p><ul class="legal-public-list"><li>Bir<\/li><li>İki<\/li><\/ul><h2>Sonraki bölüm<\/h2><p>Son paragraf<\/p>/);
});

test("legal inline formatting keeps HTML inert and code contents literal", () => {
  const html = render("**<img src=x onerror=alert(1)>** ve `<script>**metin**</script>`");
  assert.match(html, /<strong>&lt;img src=x onerror=alert\(1\)&gt;<\/strong>/);
  assert.match(html, /<code>&lt;script&gt;\*\*metin\*\*&lt;\/script&gt;<\/code>/);
  assert.doesNotMatch(html, /<(img|script)\b/);
});

test("empty documents and unmatched markers do not lose source text", () => {
  assert.equal(render(" \n\n"), '<div class="legal-public-copy"></div>');
  assert.match(render("Eksik **işaret ve `kod"), /<p>Eksik \*\*işaret ve `kod<\/p>/);
});
