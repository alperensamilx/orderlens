import io

import pandas as pd
from celery import shared_task
from django.utils import timezone

from . import analysis
from .models import AnalysisResult, Dataset


@shared_task
def run_analysis(dataset_id):
    try:
        dataset = Dataset.objects.get(pk=dataset_id)
    except Dataset.DoesNotExist:
        return

    result, _ = AnalysisResult.objects.get_or_create(dataset=dataset)
    result.status = AnalysisResult.PROCESSING
    result.save(update_fields=['status'])

    try:
        df = pd.read_csv(io.StringIO(dataset.content))
        normalized = analysis.normalize_dataframe(df, dataset.column_mapping)

        if normalized.empty:
            result.status = AnalysisResult.FAILED
            result.error_message = (
                'Eşlediğin tarih ve tutar sütunlarında geçerli veri bulunamadı. '
                'Lütfen sütun eşlemesini kontrol et.'
            )
            result.save(update_fields=['status', 'error_message'])
            return

        result.metrics = analysis.compute_metrics(normalized)
        result.charts = {
            'revenue_trend': analysis.build_revenue_trend_chart(normalized),
            'top_products': analysis.build_top_products_chart(normalized),
            'category': analysis.build_category_chart(normalized),
            'status': analysis.build_status_chart(normalized),
        }
        result.status = AnalysisResult.DONE
        result.computed_at = timezone.now()
        result.error_message = ''
        result.save()
    except Exception as exc:
        result.status = AnalysisResult.FAILED
        result.error_message = str(exc)
        result.save(update_fields=['status', 'error_message'])
