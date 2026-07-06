import pandas as pd
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import analysis
from .models import Dataset


class DatasetStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            dataset = Dataset.objects.get(pk=pk, owner=request.user)
        except Dataset.DoesNotExist:
            raise NotFound('Dataset bulunamadı.')

        if not dataset.is_mapped:
            raise ValidationError('Bu dataset için sütun eşlemesi henüz yapılmamış.')

        df = pd.read_csv(dataset.file.path)
        normalized = analysis.normalize_dataframe(df, dataset.column_mapping)

        if normalized.empty:
            raise ValidationError('Eşlenen sütunlarda geçerli veri bulunamadı.')

        return Response(analysis.compute_metrics(normalized))
