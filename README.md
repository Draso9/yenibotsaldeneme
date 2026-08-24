# yenibotsaldeneme

## API (deneysel temel)

Mobil uygulama ve Next.js istemcisine giden geçiş için sürümlü FastAPI yüzeyi
`/api/v1` altında bulunur. Yerel olarak başlatmak için:

```powershell
.venv\Scripts\uvicorn.exe izfin_api.app:app --reload
```

Etkileşimli sözleşme dokümanı `http://127.0.0.1:8000/docs` adresindedir.
Bu ilk temel yalnızca dış sağlayıcı veya Firebase erişimi gerektirmeyen endpoint'leri
barındırır; Streamlit uygulaması bağımsız biçimde çalışmayı sürdürür.

### FastAPI deploy notları

Production API, Streamlit'ten bağımsız çalışır; Streamlit uygulaması bu geçişte
korunur ve ayrı deploy edilebilir. Uvicorn ile örnek başlatma:

    uvicorn izfin_api.runtime:create_environment_app --factory --host 0.0.0.0 --port 8000

Firebase için yalnız deploy ortamında `FIREBASE_SERVICE_ACCOUNT_JSON` veya
`FIREBASE_SERVICE_ACCOUNT_FILE` sağlayın. Sağlayıcı anahtarları (ör. `FINNHUB_API_KEY`)
runtime adapter'larına aittir; istemci API sözleşmesini değiştirmez. CORS izinlerini
deploy katmanında yalnız bilinen istemci origin'leriyle sınırlayın.

API varsayılan olarak süreç-içi rate limit uygular. `IZFIN_RATE_LIMIT_ENABLED`,
`IZFIN_RATE_LIMIT_MAX_REQUESTS` ve `IZFIN_RATE_LIMIT_WINDOW_SECONDS` ile ayarlanır.
Birden fazla replica kullanılıyorsa bu sayaçlar paylaşılmaz; ayrıca reverse proxy,
WAF veya paylaşılan bir limit altyapısı zorunludur. `/api/v1/health` ve
`/api/v1/health/ready` health probe için kullanılır. Loglar JSON biçiminde request ID
ile eşleşir; token, e-posta, request body ve export içeriği loglanmaz.
