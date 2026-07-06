import base64
import io

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

CANONICAL_FIELDS = ['date', 'product', 'amount', 'quantity', 'customer', 'category', 'status']
REQUIRED_FIELDS = ['date', 'product', 'amount']

FIELD_LABELS = {
    'date': 'Sipariş Tarihi',
    'product': 'Ürün Adı',
    'amount': 'Tutar (satır geliri)',
    'quantity': 'Adet',
    'customer': 'Müşteri (e-posta/isim)',
    'category': 'Kategori',
    'status': 'Sipariş Durumu',
}

_KEYWORDS = {
    'date': ['date', 'tarih', 'created'],
    'product': ['product', 'item', 'ürün', 'urun', 'title'],
    'amount': ['amount', 'total', 'price', 'tutar', 'fiyat', 'revenue', 'gelir'],
    'quantity': ['qty', 'quantity', 'adet', 'miktar'],
    'customer': ['customer', 'email', 'müşteri', 'musteri', 'buyer'],
    'category': ['category', 'kategori', 'type'],
    'status': ['status', 'durum', 'state'],
}


def detect_column_mapping(columns):
    mapping = {}
    used = set()
    for field in CANONICAL_FIELDS:
        for col in columns:
            if col in used:
                continue
            lowered = str(col).lower()
            if any(keyword in lowered for keyword in _KEYWORDS[field]):
                mapping[field] = col
                used.add(col)
                break
    return mapping


def normalize_dataframe(df, mapping):
    rename = {source: field for field, source in mapping.items() if source}
    normalized = df.rename(columns=rename)
    keep = [field for field in CANONICAL_FIELDS if field in normalized.columns]
    normalized = normalized[keep].copy()

    normalized['date'] = pd.to_datetime(normalized['date'], errors='coerce')
    normalized['amount'] = pd.to_numeric(normalized['amount'], errors='coerce')
    if 'quantity' in normalized.columns:
        normalized['quantity'] = pd.to_numeric(normalized['quantity'], errors='coerce')

    return normalized.dropna(subset=['date', 'amount'])


def compute_metrics(df):
    metrics = {
        'order_count': int(len(df)),
        'total_revenue': round(float(df['amount'].sum()), 2),
        'aov': round(float(df['amount'].mean()), 2) if len(df) else 0,
    }

    if 'quantity' in df.columns:
        metrics['total_units'] = int(df['quantity'].sum())

    if 'customer' in df.columns:
        customer_counts = df['customer'].dropna().value_counts()
        total_customers = int(customer_counts.shape[0])
        metrics['unique_customers'] = total_customers
        repeat_customers = int((customer_counts > 1).sum())
        metrics['repeat_customer_rate'] = round(100 * repeat_customers / total_customers, 1) if total_customers else 0

    top_products = df.groupby('product')['amount'].sum().sort_values(ascending=False).head(10)
    metrics['top_products'] = [
        {'name': str(name), 'revenue': round(float(value), 2)} for name, value in top_products.items()
    ]

    if 'category' in df.columns:
        category_revenue = df.groupby('category')['amount'].sum().sort_values(ascending=False)
        metrics['category_revenue'] = [
            {'name': str(name), 'revenue': round(float(value), 2)} for name, value in category_revenue.items()
        ]

    if 'status' in df.columns:
        status_counts = df['status'].dropna().value_counts()
        metrics['status_counts'] = [
            {'name': str(name), 'count': int(value)} for name, value in status_counts.items()
        ]

    return metrics


def _fig_to_base64(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode('utf-8')


def build_revenue_trend_chart(df):
    if df.empty:
        return None

    span_days = (df['date'].max() - df['date'].min()).days
    freq = 'D' if span_days <= 60 else ('W' if span_days <= 365 else 'M')
    trend = df.set_index('date')['amount'].resample(freq).sum()

    fig, ax = plt.subplots(figsize=(8, 4))
    trend.plot(ax=ax, color='#4f46e5', marker='o')
    ax.set_title('Zaman İçinde Gelir')
    ax.set_ylabel('Gelir')
    fig.tight_layout()
    return _fig_to_base64(fig)


def build_top_products_chart(df, top_n=8):
    top = df.groupby('product')['amount'].sum().sort_values(ascending=False).head(top_n)
    if top.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 4))
    top.plot(kind='barh', ax=ax, color='#818cf8')
    ax.set_xlabel('Gelir')
    ax.set_title('En Çok Gelir Getiren Ürünler')
    ax.invert_yaxis()
    fig.tight_layout()
    return _fig_to_base64(fig)


def build_category_chart(df):
    if 'category' not in df.columns:
        return None
    revenue = df.groupby('category')['amount'].sum().sort_values(ascending=False)
    if revenue.empty:
        return None

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(revenue.values, labels=revenue.index, autopct='%1.0f%%')
    ax.set_title('Kategoriye Göre Gelir Dağılımı')
    fig.tight_layout()
    return _fig_to_base64(fig)


def build_status_chart(df):
    if 'status' not in df.columns:
        return None
    counts = df['status'].dropna().value_counts()
    if counts.empty:
        return None

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(counts.values, labels=counts.index, autopct='%1.0f%%')
    ax.set_title('Sipariş Durumu Dağılımı')
    fig.tight_layout()
    return _fig_to_base64(fig)
