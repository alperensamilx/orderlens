from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AnalysisResult, Dataset
from .serializers import AnalysisStatusSerializer, DatasetStatsSerializer


class DatasetStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={
            200: DatasetStatsSerializer,
            202: AnalysisStatusSerializer,
            422: AnalysisStatusSerializer,
        },
        description=(
            'Returns cached sales analytics for a dataset. Analysis runs asynchronously '
            '(Celery) after column mapping is saved, so this may return 202 while it '
            'is still being computed — poll again shortly.'
        ),
    )
    def get(self, request, pk):
        try:
            dataset = Dataset.objects.get(pk=pk, owner=request.user)
        except Dataset.DoesNotExist:
            raise NotFound('Dataset bulunamadı.')

        if not dataset.is_mapped:
            raise ValidationError('Bu dataset için sütun eşlemesi henüz yapılmamış.')

        result = AnalysisResult.objects.filter(dataset=dataset).first()

        if result is None or result.status in (AnalysisResult.PENDING, AnalysisResult.PROCESSING):
            payload = {'status': result.status if result else AnalysisResult.PENDING,
                       'detail': 'Analysis is still being generated, try again shortly.'}
            return Response(AnalysisStatusSerializer(payload).data, status=status.HTTP_202_ACCEPTED)

        if result.status == AnalysisResult.FAILED:
            payload = {'status': result.status, 'detail': result.error_message}
            return Response(AnalysisStatusSerializer(payload).data, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(DatasetStatsSerializer(result.metrics).data)
