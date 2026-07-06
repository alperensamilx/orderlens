from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .analysis import CANONICAL_FIELDS, FIELD_LABELS, REQUIRED_FIELDS
from .models import Dataset


class DatasetUploadForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['file']

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.lower().endswith('.csv'):
            raise forms.ValidationError('Lütfen sadece .csv dosyası yükleyin.')
        return file


class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username']


class ColumnMappingForm(forms.Form):
    def __init__(self, *args, columns, initial_mapping=None, **kwargs):
        super().__init__(*args, **kwargs)
        initial_mapping = initial_mapping or {}
        choices = [('', '— Kullanma —')] + [(col, col) for col in columns]
        for field in CANONICAL_FIELDS:
            self.fields[field] = forms.ChoiceField(
                label=FIELD_LABELS[field],
                choices=choices,
                required=field in REQUIRED_FIELDS,
                initial=initial_mapping.get(field, ''),
            )

    def get_mapping(self):
        return {field: value for field, value in self.cleaned_data.items() if value}
