import pandas as pd

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView

from . import analysis
from .forms import ColumnMappingForm, DatasetUploadForm, RegisterForm
from .models import Dataset


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
            dataset = form.save(commit=False)
            dataset.owner = request.user
            dataset.save()
            return redirect('analyzer:map_columns', pk=dataset.pk)
    else:
        form = DatasetUploadForm()

    datasets = request.user.datasets.order_by('-uploaded_at')
    return render(request, 'analyzer/dataset_list.html', {'form': form, 'datasets': datasets})


@login_required
def map_columns(request, pk):
    dataset = get_object_or_404(Dataset, pk=pk, owner=request.user)
    try:
        preview_df = pd.read_csv(dataset.file.path, nrows=5)
    except Exception as exc:
        return render(request, 'analyzer/error.html', {'error': str(exc), 'dataset': dataset})

    columns = list(preview_df.columns)
    initial_mapping = dataset.column_mapping or analysis.detect_column_mapping(columns)

    if request.method == 'POST':
        form = ColumnMappingForm(request.POST, columns=columns, initial_mapping=initial_mapping)
        if form.is_valid():
            dataset.column_mapping = form.get_mapping()
            dataset.save()
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

    try:
        df = pd.read_csv(dataset.file.path)
    except Exception as exc:
        return render(request, 'analyzer/error.html', {'error': str(exc), 'dataset': dataset})

    normalized = analysis.normalize_dataframe(df, dataset.column_mapping)

    if normalized.empty:
        return render(request, 'analyzer/error.html', {
            'error': 'Eşlediğin tarih ve tutar sütunlarında geçerli veri bulunamadı. Lütfen sütun eşlemesini kontrol et.',
            'dataset': dataset,
        })

    metrics = analysis.compute_metrics(normalized)

    context = {
        'dataset': dataset,
        'metrics': metrics,
        'revenue_trend_chart': analysis.build_revenue_trend_chart(normalized),
        'top_products_chart': analysis.build_top_products_chart(normalized),
        'category_chart': analysis.build_category_chart(normalized),
        'status_chart': analysis.build_status_chart(normalized),
    }
    return render(request, 'analyzer/analyze.html', context)
