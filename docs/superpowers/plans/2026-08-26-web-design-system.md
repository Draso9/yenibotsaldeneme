# IZFIN Web Tasarım Sistemi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Next.js Piyasa Merkezi'ni IZFIN'in Streamlit kökenli koyu, yoğun veri odaklı kimliğiyle tutarlı ve responsive bir web arayüzüne dönüştürmek.

**Architecture:** Ortak görsel kurallar `web/app/globals.css` içindeki token katmanında tutulacak; uygulama kabuğu yalnız navigasyon ve oturum görünürlüğünden sorumlu kalacak. Piyasa bandı ve tarama sonucu tabanlı Piyasa Merkezi mevcut API istemcilerini kullanmaya devam edecek; yeni veri sağlayıcı veya API sözleşmesi eklenmeyecek.

**Tech Stack:** Next.js 16, React 19, TypeScript 5.9, mevcut FastAPI v1 istemcisi, CSS custom properties, pytest statik web sözleşme testleri, pnpm.

**Spec:** `docs/superpowers/specs/2026-08-26-web-design-system-design.md`

## Global Constraints

- `main` değiştirilmeyecek; PR hedefi `develop` olacak.
- Streamlit uygulaması ve mevcut FastAPI sözleşmeleri korunacak.
- "Fırsat Haritası" web navigasyonunda veya Piyasa Merkezi içeriğinde yer almayacak.
- Fiyat ve piyasa durumu yalnız API'nin döndürdüğü veriyle gösterilecek; veri yoksa açık yükleniyor/erişilemiyor durumu gösterilecek.
- Yeni renkler token olarak tanımlanacak; sayfa bileşenleri yeni sabit hex renkler eklemeyecek.
- Metin ve etkileşimde klavye odağı görünür, mobil dokunma hedefi en az 44px olacak.
- Her commit öncesi ilgili testler; PR öncesi `pnpm --dir web typecheck`, `pnpm --dir web build` ve ilgili pytest testleri çalışacak.

---

## Dosya Yapısı

- `web/lib/design-foundation.ts` — token/sayfa ilkelerinin TypeScript sözleşmesi.
- `web/lib/design-foundation.contract.ts` — foundation tipinin derleme sözleşmesi.
- `web/components/app-shell.tsx` — masaüstü ve dar ekran navigasyon hiyerarşisi; erişilebilir etiketler.
- `web/components/market-strip.tsx` — API tabanlı piyasa kartlarının yüklenme/hata/veri durumları.
- `web/components/market-center.tsx` — seçili tarama sonucu için sinyal tablosu, piyasa modu ve hareketli hisseler.
- `web/app/page.tsx` — Piyasa Merkezi'nin ürün odaklı sayfa yerleşimi.
- `web/app/globals.css` — ortak tokenlar, kabuk, piyasa bandı ve responsive kurallar.
- `web/app/market-center.css` — yalnız Piyasa Merkezi'nin yerel ızgara/tablo/stil kuralları.
- `tests/test_web_design_system.py` — kaynak tabanlı tasarım sistemi, veri dürüstlüğü ve responsive sözleşmeler.

## Task 1: Tasarım tokenları ve kabuk sözleşmesi

**Files:**
- Modify: `web/lib/design-foundation.ts`
- Modify: `web/lib/design-foundation.contract.ts`
- Modify: `web/app/globals.css`
- Modify: `web/components/app-shell.tsx`
- Create: `tests/test_web_design_system.py`

**Interfaces:**
- Produces: `IZFIN_DESIGN_FOUNDATION` içinde `tokens`, `navigation` ve `breakpoints` alanları.
- Consumes: mevcut `AppShell`, `useIzfinAuth`, `usePathname` ve CSS `:root` değişkenleri.

- [x] **Step 1: Başarısız tasarım sistemi testi yaz**

```python
def test_design_system_declares_tokens_and_product_navigation():
    foundation = _read("web/lib/design-foundation.ts")
    shell = _read("web/components/app-shell.tsx")
    css = _read("web/app/globals.css")

    for token in ("--iz-bg", "--iz-surface", "--iz-accent", "--iz-positive", "--iz-negative", "--iz-warning"):
        assert token in css
    assert "tokens:" in foundation
    assert "breakpoints:" in foundation
    assert '"Fırsat Haritası"' not in shell
```

- [x] **Step 2: Testin önce başarısız olduğunu doğrula**

Run: `python -m pytest tests/test_web_design_system.py::test_design_system_declares_tokens_and_product_navigation -v`
Expected: FAIL; yeni `--iz-*` tokenları ve foundation alanları henüz yok.

- [x] **Step 3: En küçük token ve kabuk düzenlemesini uygula**

```ts
export const IZFIN_DESIGN_FOUNDATION = {
  theme: "command-center",
  density: "compact",
  responsive: true,
  tokens: ["iz-bg", "iz-surface", "iz-accent", "iz-positive", "iz-negative", "iz-warning"],
  breakpoints: { tablet: 1100, compact: 860, mobile: 600 },
  navigation: ["Piyasa Merkezi", "Akıllı Tarama", "Projeksiyon", "Performans", "Strateji Lab", "Hesap"],
} as const;
```

CSS'te mevcut değerleri geriye uyumlu takma adlarla `--iz-*` tokenlarına bağla.
`AppShell` içindeki mevcut altı ürün navigasyonunu koru. `860px` altında marka
üstte kalırken navigasyon ekranın altında sabit, yatay taşma yapmayan ve
klavye ile erişilebilir bir çubuğa dönüşür; `aria-label` değeri "Ana
navigasyon" olarak kalır. `600px` altında etiketler kısa biçimde görünür ama
her bağlantının erişilebilir adı tam ürün adıdır.

- [x] **Step 4: İlgili testi geçir**

Run: `python -m pytest tests/test_web_design_system.py::test_design_foundation_exposes_shared_tokens_and_responsive_navigation -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add web/lib/design-foundation.ts web/lib/design-foundation.contract.ts web/app/globals.css web/components/app-shell.tsx tests/test_web_design_system.py
git commit -m "feat(web): establish IZFIN design tokens"
```

## Task 2: Dürüst piyasa bandı kartları

**Files:**
- Modify: `web/components/market-strip.tsx`
- Modify: `web/components/market-strip.contract.ts`
- Modify: `web/app/globals.css`
- Modify: `tests/test_web_design_system.py`

**Interfaces:**
- Consumes: `fetchMarketStrip(): Promise<MarketStripResponse>` ve `MarketStripResponse.items`.
- Produces: veri kaynağı, tazelik ve hata durumunu metinle açıklayan `MarketStrip`.

- [x] **Step 1: Başarısız piyasa bandı testi yaz**

```python
def test_market_strip_exposes_freshness_and_error_state_without_fake_quotes():
    source = _read("web/components/market-strip.tsx")
    assert 'aria-label="Piyasa özeti"' in source
    assert "Piyasa verisi şu anda alınamıyor" in source
    assert "Veri hazırlanıyor" in source
    assert "Array.from({ length: 5 }" not in source
```

- [x] **Step 2: Testin önce başarısız olduğunu doğrula**

Run: `python -m pytest tests/test_web_design_system.py::test_market_strip_reports_loading_and_error_without_fake_quotes -v`
Expected: FAIL; mevcut hata durumunda `null` döner ve skeleton sahte kart hissi verir.

- [x] **Step 3: En küçük piyasa bandı düzenlemesini uygula**

`MarketStrip` hata durumunda görünür ama kompakt bir açıklama gösterir.
Yüklenirken yalnız "Veri hazırlanıyor" metni ile belirsiz değerler gösterir;
üretilmiş fiyat/değişim kullanmaz. Başarılı kartlarda `ad`, `fiyat`, `deg`,
`kaynak`, `durum` ve tazelik metni mevcut API alanlarından gelir. Negatif,
pozitif ve nötr yön ayrı CSS sınıflarıyla ifade edilir.

- [x] **Step 4: İlgili testleri geçir**

Run: `python -m pytest tests/test_web_design_system.py::test_market_strip_reports_loading_and_error_without_fake_quotes tests/test_api_market_strip.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add web/components/market-strip.tsx web/components/market-strip.contract.ts web/app/globals.css tests/test_web_design_system.py
git commit -m "feat(web): polish live market strip states"
```

## Task 3: Piyasa Merkezi sinyal ve günlük hareketler alanı

**Files:**
- Modify: `web/components/market-center.tsx`
- Modify: `web/components/market-center.contract.tsx`
- Modify: `web/app/market-center.css`
- Modify: `tests/test_web_design_system.py`

**Interfaces:**
- Consumes: `MarketCenterResponse.top_signals`, `.movers`, `.decision`, `.metrics` ve `fetchMarketStockDetail`.
- Produces: sinyal satırları, seçili hisse özeti ve `Günlük Büyük Hareketler` paneli; hiçbir yeni API çağrısı veya endpoint eklemez.

- [x] **Step 1: Başarısız Piyasa Merkezi testi yaz**

```python
def test_market_center_has_signal_columns_and_daily_movers_without_opportunity_map():
    source = _read("web/components/market-center.tsx")
    assert "Listende dikkat çekenler" in source
    assert "IZFIN kararı" in source
    assert "Günlük Büyük Hareketler" in source
    assert "Fırsat Haritası" not in source
```

- [x] **Step 2: Testin önce başarısız olduğunu doğrula**

Run: `python -m pytest tests/test_web_design_system.py::test_market_center_prioritizes_personal_signals_and_daily_movers -v`
Expected: FAIL; mevcut bileşen başlıkları yeni hiyerarşiyi sunmaz.

- [x] **Step 3: En küçük Piyasa Merkezi düzenlemesini uygula**

`top_signals` verisini masaüstünde sembol/fiyat/karar/skor/güven/yön başlıklı
erişilebilir satırlara dönüştür. Mevcut API'de kategorik yükselen-düşen-hacim
alanı olmadığından `movers` listesini "Günlük Büyük Hareketler" altında tek
tarafsız "Hareketliler" görünümüyle göster. Kategorik sekme veya uydurma
yükseliş/düşüş bilgisi oluşturma.

Seçili hisse kartı mevcut `fetchMarketStockDetail` çağrısını korur. Hata ve
boş durumlar yalnız ilgili panelde kalır; kartların hiçbiri sahte karar ya da
fiyat kullanmaz.

- [x] **Step 4: İlgili testleri geçir**

Run: `python -m pytest tests/test_web_design_system.py::test_market_center_prioritizes_personal_signals_and_daily_movers tests/test_api_market_center.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add web/components/market-center.tsx web/components/market-center.contract.tsx web/app/market-center.css tests/test_web_design_system.py
git commit -m "feat(web): redesign market center signals"
```

## Task 4: Ana sayfa hiyerarşisi ve küçük ekran görünümü

**Files:**
- Modify: `web/app/page.tsx`
- Modify: `web/app/globals.css`
- Modify: `web/app/market-center.css`
- Modify: `tests/test_web_design_system.py`
- Modify: `tests/test_web_release_surface.py`

**Interfaces:**
- Consumes: `MarketStrip`, `Dashboard`, `ScanWorkspace`, `AccountCenter` ve `MarketCenterPanel`in mevcut yerleştirme noktası.
- Produces: Piyasa bandının üstte, oturum/tarama alanlarının ana karar akışında olduğu; 600px ve 860px kırılımlarında okunabilir ana sayfa.

- [x] **Step 1: Başarısız responsive/hiyerarşi testi yaz**

```python
def test_homepage_uses_product_market_hierarchy_and_mobile_touch_targets():
    page = _read("web/app/page.tsx")
    css = _read("web/app/globals.css")
    assert "Piyasa Merkezi" in page
    assert "Sistem durumunu aç" not in page
    assert "min-height: 44px" in css
    assert "@media (max-width: 600px)" in css
```

- [x] **Step 2: Testin önce başarısız olduğunu doğrula**

Run: `python -m pytest tests/test_web_design_system.py::test_homepage_removes_internal_health_shortcut_and_keeps_mobile_targets -v`
Expected: FAIL; mevcut ana sayfada geliştirici odaklı sistem durumu bağlantısı vardır.

- [x] **Step 3: En küçük ana sayfa ve responsive düzenlemesini uygula**

Ana sayfadaki geliştirici odaklı sağlık bağlantısını kaldır; kullanıcıyı
Akıllı Tarama ve kişisel sinyaller akışına yönlendiren tek birincil eylemi
koru. `MarketStrip` en üstte kalır. CSS'te masaüstü tablo yoğunluğunu
korurken 860px altında kartlar tek sütuna iner, 600px altında metin taşmaz ve
etkileşimli öğeler en az 44px olur. Mevcut diğer sayfaların rotası veya
Streamlit dosyaları değiştirilmez.

- [x] **Step 4: İlgili testleri geçir**

Run: `python -m pytest tests/test_web_design_system.py tests/test_web_release_surface.py tests/test_web_stage5_parity.py -v`
Expected: PASS.

- [x] **Step 5: Commit**

```bash
git add web/app/page.tsx web/app/globals.css web/app/market-center.css tests/test_web_design_system.py tests/test_web_release_surface.py
git commit -m "feat(web): refine market center responsive layout"
```

## Task 5: Entegrasyon doğrulaması ve PR hazırlığı

**Files:**
- Modify: `docs/superpowers/specs/2026-08-26-web-design-system-design.md` (yalnız uygulama sırasında gerçek kapsam değişirse)
- Modify: `docs/superpowers/plans/2026-08-26-web-design-system.md` (tamamlanan kutuları işaretle)

**Interfaces:**
- Consumes: Task 1–4 web kaynakları ve mevcut CI iş akışı.
- Produces: `develop` hedefli, test kanıtları olan PR.

- [ ] **Step 1: Uygulama testlerini çalıştır**

Run: `python -m pytest tests/test_web_design_system.py tests/test_web_release_surface.py tests/test_web_stage5_parity.py tests/test_api_market_strip.py tests/test_api_market_center.py -v`
Expected: PASS.

- [ ] **Step 2: TypeScript kontrolünü çalıştır**

Run: `pnpm --dir web typecheck`
Expected: PASS, TypeScript diagnostics yok.

- [ ] **Step 3: Production build çalıştır**

Run: `pnpm --dir web build`
Expected: PASS, Next.js build tamamlanır.

- [ ] **Step 4: Değişiklik kapsamını kontrol et**

Run: `git diff origin/develop...HEAD --check && git diff --name-only origin/develop...HEAD`
Expected: whitespace hatası yok; `app2.py` ve Streamlit kaynakları listede yok.

- [ ] **Step 5: Planı güncelle ve commit et**

```bash
git add docs/superpowers/specs/2026-08-26-web-design-system-design.md docs/superpowers/plans/2026-08-26-web-design-system.md
git commit -m "docs: record web design system verification"
```

- [ ] **Step 6: PR aç ve CI sonucu bekle**

PR: `feat/web-design-system` → `develop`
Expected: GitHub Web Quality ve Python Quality işleri yeşil.

- [ ] **Step 7: Yalnız CI yeşilse merge et ve develop CI'ı doğrula**

Expected: PR merge sonrası `develop` iş akışı yeşil; `main` değişmez.
