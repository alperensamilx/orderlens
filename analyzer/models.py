from django.conf import settings
from django.db import models


class Dataset(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='datasets')
    file = models.FileField(upload_to='datasets/')
    name = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    column_mapping = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name or self.file.name

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.file.name
        super().save(*args, **kwargs)

    @property
    def is_mapped(self):
        required = {'date', 'product', 'amount'}
        return required.issubset(self.column_mapping.keys())
