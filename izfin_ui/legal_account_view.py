"""Pure legal/account presentation models for the Streamlit and future web shells."""

from __future__ import annotations

from datetime import datetime
import html


def yasal_url(public_url: str, tur: str) -> str:
    return f"{str(public_url or '').rstrip('/')}/?legal={str(tur or '').strip()}"


def _document_intro_html(*, number: str, kicker: str, title: str, copy: str, version: str) -> str:
    return f"""
    <section class="iz-legal-document-intro">
      <div class="iz-legal-doc-number">{html.escape(number)}</div>
      <div class="iz-legal-doc-copy">
        <span>{html.escape(kicker)}</span>
        <h2>{html.escape(title)}</h2>
        <p>{html.escape(copy)}</p>
      </div>
      <div class="iz-legal-version">{html.escape(str(version))}</div>
    </section>
    """


def gizlilik_sayfa_paketi_hazirla(
    *,
    kapida: bool,
    privacy_version: str,
    data_controller_name: str,
    contact_email: str,
    data_controller_address: str,
    log_retention_days: int,
) -> dict[str, object]:
    alanlar = {
        "IZFIN_DATA_CONTROLLER_NAME": data_controller_name,
        "IZFIN_CONTACT_EMAIL": contact_email,
        "IZFIN_DATA_CONTROLLER_ADDRESS": data_controller_address,
    }
    eksikler = [name for name, value in alanlar.items() if not str(value or "").strip()]
    warning = None
    if eksikler:
        warning = (
            "Bu geliştirme ortamında veri sorumlusu kimlik/iletişim alanları henüz "
            "tamamlanmadı. Herkese açık yayından önce Streamlit Secrets içindeki "
            f"{', '.join(eksikler)} değerleri doldurulmalıdır."
        )

    veri_sorumlusu = data_controller_name or "Yapılandırılmayı bekliyor"
    iletisim = contact_email or "Yapılandırılmayı bekliyor"
    adres = data_controller_address or "Yapılandırılmayı bekliyor"
    markdown = f"""
### 1. Veri sorumlusu

- **Veri sorumlusu:** {veri_sorumlusu}
- **İletişim e-postası:** {iletisim}
- **Başvuru adresi:** {adres}

### 2. İşlenen veriler

IZFIN; hesap oluşturma ve hizmeti sunma kapsamında e-posta adresi, Firebase kullanıcı
kimliği (UID), hesap oluşturma/son giriş zamanı, yasal metin sürüm kayıtları, kişisel
izleme listesi, kullanıcının oluşturduğu sinyal ve performans takip kayıtları ile sınırlı
teknik hata kayıtlarını işler. Google ile girişte Google parolası IZFIN'e ulaşmaz ve
IZFIN tarafından saklanmaz.

### 3. İşleme amaçları

Bu veriler hesabın doğrulanması, oturumun sürdürülmesi, kişisel listenin ve takip
geçmişinin saklanması, güvenliğin sağlanması, hataların giderilmesi ve hizmet kalitesinin
ölçülmesi amaçlarıyla kullanılır. Veriler reklam profili oluşturmak veya IZFIN dışı
otomatik yatırım işlemi gerçekleştirmek için kullanılmaz.

### 4. Toplama yöntemi ve hukuki sebep

Veriler kayıt/giriş formları, Google OAuth, Firebase Authentication, kullanıcı işlemleri
ve uygulama teknik logları üzerinden elektronik ortamda elde edilir. İşleme faaliyetleri;
hizmet sözleşmesinin kurulması ve ifası, hukuki yükümlülüklerin yerine getirilmesi ve
uygulama güvenliğinin sağlanmasına yönelik meşru menfaatler kapsamında yürütülür.
Gerekli olduğu durumlarda ayrıca açık rıza istenir; aydınlatma metni açık rıza yerine geçmez.

### 5. Hizmet sağlayıcılar ve aktarım

Kimlik ve kullanıcı verileri Firebase/Google Cloud altyapısında; uygulama Streamlit Cloud
altyapısında işlenebilir. Hata izleme etkinleştirildiğinde Sentry'ye kimlik, cookie ve
yetkilendirme başlıkları gönderilmez. Piyasa verisi isteklerinde Finnhub ve Yahoo Finance
gibi veri sağlayıcıları kullanılabilir; kullanıcı e-postası bu piyasa verisi isteklerine
eklenmez. Bu sağlayıcıların yurt dışındaki altyapıları kullanılabileceğinden, production
yayın öncesinde gerekli aktarım mekanizmaları veri sorumlusu tarafından ayrıca
tamamlanmalıdır.

### 6. Saklama ve silme

Hesap, kişisel liste ve takip kayıtları hesap aktif olduğu sürece veya mevzuatın gerekli
kıldığı süre boyunca saklanır. Teknik hata kayıtları varsayılan olarak en fazla
**{log_retention_days} gün** tutulacak şekilde yapılandırılmalıdır. Kullanıcı,
uygulamadaki **Gizlilik & Hesap** bölümünden verilerini indirebilir ve hesabını kalıcı
olarak silebilir. Yasal saklama zorunluluğu bulunmayan kullanıcı belgeleri silme işlemiyle
birlikte kaldırılır.

### 7. Çerezler

`izfin_session` çerezi yalnızca kullanıcı "Beni hatırla" seçeneğini kullandığında güvenli
oturumu sürdürmek için kullanılır. Reklam veya üçüncü taraf pazarlama çerezi kullanılmaz.

### 8. İlgili kişinin hakları

KVKK kapsamındaki kişiler; verilerinin işlenip işlenmediğini öğrenme, bilgi talep etme,
amacına uygun kullanılıp kullanılmadığını öğrenme, aktarılan tarafları bilme, düzeltme,
silme/yok etme ve kanuni şartları varsa zararın giderilmesini talep etme haklarına
sahiptir. Talepler yukarıdaki iletişim kanalından veri sorumlusuna iletilebilir.
"""
    return {
        "intro_html": _document_intro_html(
            number="02",
            kicker="VERİ ŞEFFAFLIĞI",
            title="KVKK Aydınlatma Metni",
            copy="Hangi verilerin neden işlendiğini, nerede saklandığını ve haklarınızı inceleyin.",
            version=privacy_version,
        ) if kapida else None,
        "title": None if kapida else "Gizlilik ve KVKK Aydınlatma Metni",
        "caption": None if kapida else f"Metin sürümü: {privacy_version}",
        "warning": warning,
        "markdown": markdown,
        "info": (
            "Bu metin uygulamanın teknik veri akışına göre hazırlanmış yayın taslağıdır. "
            "Production öncesinde veri sorumlusu bilgileri ve hukuki dayanaklar yetkili bir "
            "hukuk uzmanı tarafından doğrulanmalıdır."
        ),
    }


def kullanim_kosullari_paketi_hazirla(*, kapida: bool, terms_version: str) -> dict[str, object]:
    return {
        "intro_html": _document_intro_html(
            number="01",
            kicker="HİZMET ÇERÇEVESİ",
            title="Kullanım Koşulları",
            copy="Platformun kapsamını, finansal risk sınırlarını ve hesap sorumluluklarını inceleyin.",
            version=terms_version,
        ) if kapida else None,
        "title": None if kapida else "IZFIN Kullanım Koşulları",
        "caption": None if kapida else f"Koşul sürümü: {terms_version}",
        "markdown": """
### 1. Hizmetin kapsamı

IZFIN; piyasa verilerini, teknik göstergeleri, tarama sonuçlarını, projeksiyonları ve
geçmiş dönem testlerini bir araya getiren bir araştırma ve karar destek uygulamasıdır.
Aracı kurum değildir; emir iletmez, portföy yönetmez ve kullanıcı adına işlem yapmaz.

### 2. Yatırım tavsiyesi değildir

Uygulamadaki skor, sinyal, hedef, stop, projeksiyon ve backtest sonuçları yatırım
tavsiyesi, kesin getiri veya zarar etmeme garantisi değildir. Kullanıcı, yatırım
kararlarından ve bu kararların sonuçlarından kendisi sorumludur. Gerektiğinde yetkili
bir yatırım danışmanından görüş alınmalıdır.

### 3. Veri ve model sınırlamaları

Piyasa verileri gecikebilir, eksik olabilir veya sağlayıcılar arasında farklılık
gösterebilir. Teknik seviyeler; haber, bilanço, likidite, piyasa boşluğu ve olağanüstü
koşullarla geçersiz hale gelebilir. Geçmiş performans gelecekteki sonucu göstermez.
Backtestlerde komisyon, vergi, spread ve gerçek emir kayması ayrıca belirtilmedikçe
modellenmez.

### 4. Hesap güvenliği ve kabul edilebilir kullanım

Kullanıcı hesap bilgilerini korumalı, yetkisiz erişimi bildirmeli ve uygulamayı hukuka
aykırı, yanıltıcı, sistemi aşırı yükleyici veya üçüncü kişilerin haklarını ihlal edici
biçimde kullanmamalıdır. Otomatik veri kazıma, erişim kontrollerini aşma ve hizmeti
bozacak yoğun istek gönderme yasaktır.

### 5. Hizmetin sürekliliği

Bakım, veri sağlayıcı kesintisi, kota, güvenlik veya mücbir sebepler nedeniyle hizmet
geçici olarak yavaşlayabilir ya da durabilir. Güvenliği veya mevzuata uyumu korumak için
özellikler değiştirilebilir veya hesap erişimi sınırlandırılabilir.

### 6. Fikri haklar ve değişiklikler

IZFIN'e ait marka, arayüz, analiz mantığı ve özgün içerikler izin olmadan ticari olarak
kopyalanamaz. Koşullar önemli değişikliklerde yeni sürüm numarasıyla sunulur; kullanıcıdan
yeniden kabul istenebilir.

### 7. Hesabın sona ermesi

Kullanıcı hesabını uygulama içinden kalıcı olarak silebilir. Silme öncesinde verilerin
indirilmesi kullanıcının sorumluluğundadır. Kötüye kullanım veya hukuki zorunluluk halinde
hesap erişimi askıya alınabilir.
""",
    }


def yasal_onay_paketi_hazirla(*, terms_version: str, privacy_version: str) -> dict[str, str]:
    return {
        "hero_html": """
        <section class="iz-legal-hero">
          <div class="iz-legal-hero-top">
            <span class="iz-legal-kicker">IZFIN · GÜVEN &amp; ŞEFFAFLIK</span>
            <span class="iz-legal-status"><i></i> GÜNCEL ONAY GEREKLİ</span>
          </div>
          <h1>Hesabınız için şeffaf ve güvenli bir başlangıç</h1>
          <p>IZFIN'i kullanmaya devam etmeden önce hizmet çerçevesini ve kişisel veri
          bilgilendirmesini inceleyin. Belgeler birbirinden ayrı ve sürümlü olarak kaydedilir.</p>
          <div class="iz-legal-steps">
            <div><b>01</b><span><strong>Koşulları inceleyin</strong><small>Hizmet ve risk sınırları</small></span></div>
            <div><b>02</b><span><strong>Veri akışını görün</strong><small>KVKK ve saklama bilgisi</small></span></div>
            <div><b>03</b><span><strong>Güvenle devam edin</strong><small>Sürümlü onay kaydı</small></span></div>
          </div>
        </section>
        """,
        "approval_html": f"""
        <section class="iz-legal-approval-marker">
          <div>
            <span>SON ADIM</span>
            <h3>Belgeleri okuduğunuzu doğrulayın</h3>
            <p>Aydınlatma metninin sunulması açık rıza değildir; iki kayıt ayrı tutulur.</p>
          </div>
          <div class="iz-legal-approval-versions">
            <span>KOŞUL · {html.escape(str(terms_version))}</span>
            <span>KVKK · {html.escape(str(privacy_version))}</span>
          </div>
        </section>
        """,
    }


def hesap_sidebar_html(email: str | None) -> str:
    email_safe = html.escape(str(email or ""))
    return (
        f'<div class="iz-account-chip"><b>{email_safe}</b>'
        "<span>Kişisel IZFIN hesabı · listeleriniz ve takip verileriniz size özeldir</span></div>"
    )


def veri_export_dosya_adi(now: datetime) -> str:
    return f"izfin-verilerim-{now.strftime('%Y%m%d')}.json"
