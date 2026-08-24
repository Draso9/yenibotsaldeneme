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
