# IZFIN

Güncel durum ve sıradaki işler için önce [IZFIN_MASTER_STATUS.md](IZFIN_MASTER_STATUS.md)
dosyasındaki **Latest verified handoff** bölümünü okuyun. Eski planlar ve checkpoint
kanıtları tarihsel kayıtlardır; güncel branch/PR durumunu GitHub üzerinden doğrulayın.
Geliştirme `develop` tabanlı ayrı branch ve PR üzerinden yürür; `main` değiştirilmez.

## API

Mobil uygulama ve Next.js istemcisine giden geçiş için sürümlü FastAPI yüzeyi
`/api/v1` altında bulunur. Yerel olarak başlatmak için:

```powershell
.venv\Scripts\uvicorn.exe izfin_api.main:app --reload
```

Etkileşimli sözleşme dokümanı `http://127.0.0.1:8000/docs` adresindedir.
Production giriş noktası ortam değişkenlerinden Firebase, Finnhub, CORS ve istek
sınırı ayarlarını oluşturur. Önemli ayarlar:

- `IZFIN_CORS_ORIGINS`: Virgülle ayrılmış Next.js/web origin listesi.
- `IZFIN_RATE_LIMIT_REQUESTS`: Pencere başına istemci istek sınırı (varsayılan 120).
- `IZFIN_RATE_LIMIT_WINDOW_SECONDS`: Sınır penceresi (varsayılan 60 saniye).
- `FIREBASE_SERVICE_ACCOUNT_JSON` veya `FIREBASE_SERVICE_ACCOUNT_FILE`.
- `FINNHUB_API_KEY`.

Her yanıtta `X-Request-ID` bulunur; hata yanıtları web ve mobil istemcilerin
paylaşabileceği kararlı bir `error` sözleşmesi döndürür. Streamlit uygulaması
bağımsız biçimde çalışmayı sürdürür.

## Next.js web istemcisi

Yeni web arayüzü `web/` altında bulunur; Streamlit uygulamasını değiştirmez.
İlk kurulumda `web/.env.example` dosyasını `web/.env.local` olarak kopyalayıp
gerekirse API adresini değiştirin. Node.js 24+ ve pnpm ile:

```powershell
pnpm --dir web install
pnpm --dir web dev
```

İstemci varsayılan olarak Cloud Run'daki canlı IZFIN API adresini kullanır.
Giriş, kişisel liste, Akıllı Tarama, Detaylı Analiz, Projeksiyon, Performans ve
Strateji Lab ekranları bu istemcide bulunur. Streamlit davranış ve tasarım
referansıdır. Tamamlanan geçiş işleri, kabul kanıtları ve yayın öncesi açık işler
ana durum dosyasında ayrıştırılır.

### Container ile çalıştırma

API platformdan bağımsız bir container olarak da başlatılabilir:

```powershell
docker build -t izfin-api .
docker run --rm -p 8000:8000 --env-file .env izfin-api
```

`FIREBASE_SERVICE_ACCOUNT_JSON` sağlandığında scan-job durumları Firestore'daki
`izfin_scan_jobs` koleksiyonunda saklanır. Tamamlanmış işler uygulama yeniden
başlasa da sorgulanabilir; yeniden başlatma sırasında çalışan bir iş güvenli
biçimde `failed/interrupted` durumuna alınır. Mevcut backend Cloud Run üzerinde çalışır; container giriş noktası başka bir
ASGI container platformunda da kullanılabilir.
