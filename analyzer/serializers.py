from rest_framework import serializers


class ProductRevenueSerializer(serializers.Serializer):
    name = serializers.CharField()
    revenue = serializers.FloatField()


class StatusCountSerializer(serializers.Serializer):
    name = serializers.CharField()
    count = serializers.IntegerField()


class DatasetStatsSerializer(serializers.Serializer):
    order_count = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    aov = serializers.FloatField(help_text='Average order value')
    total_units = serializers.IntegerField(required=False)
    unique_customers = serializers.IntegerField(required=False)
    repeat_customer_rate = serializers.FloatField(required=False, help_text='Percentage, e.g. 33.3')
    top_products = ProductRevenueSerializer(many=True)
    category_revenue = ProductRevenueSerializer(many=True, required=False)
    status_counts = StatusCountSerializer(many=True, required=False)


class AnalysisStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['pending', 'processing', 'done', 'failed'])
    detail = serializers.CharField(required=False)
