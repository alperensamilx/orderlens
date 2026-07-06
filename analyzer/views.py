import io

import pandas as pd

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView

from . import analysis
from .forms import ColumnMappingForm, DatasetUploadForm, RegisterForm
from .models import AnalysisResult, Dataset
from .tasks import run_analysis


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'analyzer/register.html'
    success_url = reverse_lazy('analyzer:dataset_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class OrderLensLoginView(LoginView):
    template_name = 'analyzer/login.html'


@login_required
def dataset_list(request):
    if request.method == 'POST':
        form = DatasetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = form.cleaned_data['file']
            dataset = Dataset.objects.create(
                owner=request.user,
                name=uploaded.name,
                content=uploaded.read().decode('utf-8'),
            )
            return redirect('analyzer:map_columns', pk=dataset.pk)
    else:
        form = DatasetUploadForm()

    datasets = request.user.datasets.order_by('-uploaded_at')
    return render(request, 'analyzer/dataset_list.html', {'form': form, 'datasets': datasets})


@login_required
def map_columns(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk, owner=request.user)
    try:
        preview_df = pd.read_csv(io.StringIO(dataset.content), nrows=5)
    except Exception as exc:
        return render(request, 'analyzer/error.html', {'error': str(exc), 'dataset': dataset})

    columns = list(preview_df.columns)
    initial_mapping = dataset.column_mapping or analysis.detect_column_mapping(columns)

    if request.method == 'POST':
        form = ColumnMappingForm(request.POST, columns=columns, initial_mapping=initial_mapping)
        if form.is_valid():
            dataset.column_mapping = form.get_mapping()
            dataset.save()
            run_analysis.delay(dataset.pk)
            return redirect('analyzer:analyze', pk=dataset.pk)
    else:
        form = ColumnMappingForm(columns=columns, initial_mapping=initial_mapping)

    context = {
        'form': form,
        'dataset': dataset,
        'preview': preview_df.to_html(classes='table', index=False, na_rep='—'),
    }
    return render(request, 'analyzer/map_columns.html', context)


@login_required
def analyze_dataset(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk, owner=request.user)

    if not dataset.is_mapped:
        return redirect('analyzer:map_columns', pk=dataset.pk)

    result = AnalysisResult.objects.filter(dataset=dataset).first()

    if result is None or result.status in (AnalysisResult.PENDING, AnalysisResult.PROCESSING):
        return render(request, 'analyzer/processing.html', {'dataset': dataset})

    if result.status == AnalysisResult.FAILED:
        return render(request, 'analyzer/error.html', {'error': result.error_message, 'dataset': dataset})

    context = {
        'dataset': dataset,
        'metrics': result.metrics,
        'revenue_trend_chart': result.charts.get('revenue_trend'),
        'top_products_chart': result.charts.get('top_products'),
        'category_chart': result.charts.get('category'),
        'status_chart': result.charts.get('status'),
    }
    return render(request, 'analyzer/analyze.html', context)
