# yenibotsaldeneme

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
