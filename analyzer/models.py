from django.conf import settings
from django.db import models


class Dataset(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='datasets')
    # Stored as text in the DB rather than a FileField on local/ephemeral disk —
    # Render's free web dyno wipes its filesystem on every deploy, but the
    # (Postgres) database persists, so this is what actually survives redeploys.
    content = models.TextField()
    name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    column_mapping = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

    @property
    def is_mapped(self):
        required = {'date', 'product', 'amount'}
        return required.issubset(self.column_mapping.keys())


class AnalysisResult(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    DONE = 'done'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (DONE, 'Done'),
        (FAILED, 'Failed'),
    ]

    dataset = models.OneToOneField(Dataset, on_delete=models.CASCADE, related_name='analysis_result')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    metrics = models.JSONField(default=dict, blank=True)
    charts = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    computed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.dataset} — {self.status}'
