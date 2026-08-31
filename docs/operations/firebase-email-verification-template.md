# IZFIN Firebase E-posta Doğrulama Şablonu

Bu belge, IZFIN e-posta doğrulaması için onaylanmış production metninin canonical kaydıdır.

## Firebase Console ayarı

Firebase Console → Authentication → Templates → Email address verification bölümünde aşağıdaki konu ve gövde kullanılmalıdır. Gönderen görünen adı mümkünse **IZFIN** olarak ayarlanmalıdır.

### Konu

**IZFIN hesabınızı doğrulayın**

### Gövde

Merhaba,

IZFIN hesabınızı kullanmaya başlamak için e-posta adresinizi doğrulamanız gerekiyor.

Aşağıdaki bağlantıyı kullanarak doğrulama işlemini tamamlayabilirsiniz.

**E-posta Adresimi Doğrula**

Bu işlemi siz başlatmadıysanız bu e-postayı dikkate almayabilirsiniz.

Güvenliğiniz için doğrulama bağlantısını başkalarıyla paylaşmayın.

Teşekkürler,  
**IZFIN**  
Analyze · Predict · Invest

## Uygulama davranışı

IZFIN web istemcisi doğrulama e-postalarını ortak `sendIzfinVerificationEmail` helper'ı üzerinden gönderir. Uygulama Firebase Auth dilini Türkçe (`tr`) olarak ayarlar ve doğrulama sonrasında kullanıcıyı kalıcı production adresine döndürür:

`https://izfin-web.vercel.app/auth?verified=1`

Firebase'in yerleşik doğrulama e-postasının konu ve gövdesi istemci SDK çağrısından değiştirilemez; bu metin Firebase Console'daki Authentication email template ayarında tutulur. Bu nedenle production şablonunda değişiklik yapılırken bu dosya kaynak kabul edilmelidir.
