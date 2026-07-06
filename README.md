# OrderLens

E-ticaret satıcıları için sipariş CSV export'larını (Shopify, Etsy, WooCommerce, Trendyol vb.) birkaç adımda bir satış analiz panosuna çeviren bir Django uygulaması.

Küçük bir e-ticaret satıcısı genelde siparişlerini Excel/Google Sheets'te elle karıştırıp gelir, en çok satan ürün, tekrar eden müşteri gibi soruların cevabını arar. OrderLens bu CSV'yi yükleyip birkaç saniyede bu soruların cevabını, ilgili grafiklerle birlikte veriyor.

## Özellikler

- **Sütun eşleme**: Farklı platformların farklı CSV başlıklarını (`Order Date`, `Total`, `tarih`, `tutar`...) varsaymak yerine, yüklenen dosyanın başlıklarını otomatik tahmin edip kullanıcıya onaylatan bir eşleme adımı.
- **KPI panosu**: Toplam gelir, sipariş sayısı, ortalama sepet tutarı (AOV), benzersiz müşteri sayısı, tekrar eden müşteri oranı.
- **Grafikler**: Zaman içinde gelir trendi, en çok gelir getiren ürünler, kategoriye göre gelir dağılımı, sipariş durumu (tamamlandı/iptal/iade) dağılımı.
- **REST API**: Aynı analiz verisi `GET /api/datasets/<id>/stats/` üzerinden JSON olarak da alınabilir (Django REST Framework).
- **Çok kullanıcılı**: Kayıt/giriş sistemi var, her satıcı sadece kendi yüklediği dosyaları görür.

## Ekran Görüntüleri

> `screenshots/` klasörüne eklenecek.

| Panel | Sütun Eşleme | Analiz |
|---|---|---|
| _(yakında)_ | _(yakında)_ | _(yakında)_ |

## Teknoloji

- **Backend**: Django 4.2, Django REST Framework
- **Veri işleme**: pandas
- **Grafikler**: matplotlib (sunucu tarafında render edilip base64 olarak gömülür — ayrı bir JS grafik kütüphanesi gerekmez)
- **Auth**: Django'nun yerleşik auth sistemi
- **Veritabanı**: SQLite (geliştirme ortamı)

## Kurulum

```bash
git clone <bu-repo>
cd orderlens
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

`http://127.0.0.1:8000` adresine git, bir hesap oluştur, ve `sample_data/orders.csv` dosyasını yükleyerek dene.

## Testler

```bash
python manage.py test analyzer
```

8 test: giriş zorunluluğu, kullanıcılar arası veri izolasyonu (bir satıcı başka bir satıcının verisini göremez), sütun eşleme tahmini, metrik hesaplamalarının doğruluğu, ve uçtan uca kayıt→yükleme→eşleme→analiz→API akışı.

## API Örneği

```
GET /api/datasets/1/stats/
```

```json
{
  "order_count": 45,
  "total_revenue": 51863.0,
  "aov": 1152.51,
  "total_units": 54,
  "unique_customers": 7,
  "repeat_customer_rate": 100.0,
  "top_products": [
    {"name": "Akıllı Saat", "revenue": 14994.0},
    {"name": "Spor Ayakkabı", "revenue": 9093.0}
  ],
  "category_revenue": [
    {"name": "Elektronik", "revenue": 29680.0}
  ],
  "status_counts": [
    {"name": "Tamamlandı", "count": 40},
    {"name": "İptal", "count": 3}
  ]
}
```

## Proje Yapısı

```
analyzer/
  analysis.py     # sütun eşleme tahmini, metrik hesaplama, grafik üretimi
  models.py       # Dataset modeli (owner, column_mapping)
  views.py        # auth, yükleme, eşleme, analiz view'ları
  api_views.py    # DRF API endpoint
  forms.py        # yükleme formu, dinamik sütun eşleme formu, kayıt formu
  templates/      # tüm HTML şablonları
sample_data/
  orders.csv      # denemek için gerçekçi bir örnek sipariş export'u
```

## Lisans

MIT
