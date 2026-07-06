from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from analyzer import analysis
from analyzer.models import AnalysisResult, Dataset
from analyzer.tasks import run_analysis

DEMO_USERNAME = 'demo'
DEMO_PASSWORD = 'demo1234'


class Command(BaseCommand):
    help = (
        'Creates (or reuses) a demo user with a pre-mapped sample dataset, '
        'so a freshly deployed instance (ephemeral disk) still has something to show. '
        'Safe to run on every deploy.'
    )

    def handle(self, *args, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(username=DEMO_USERNAME)
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created demo user "{DEMO_USERNAME}"'))
        else:
            self.stdout.write(f'Demo user "{DEMO_USERNAME}" already exists')

        dataset = Dataset.objects.filter(owner=user).first()

        if dataset is None:
            csv_path = settings.BASE_DIR / 'sample_data' / 'orders.csv'
            content = csv_path.read_bytes()
            columns = content.decode('utf-8').splitlines()[0].split(',')
            mapping = analysis.detect_column_mapping(columns)

            dataset = Dataset(owner=user, name='orders.csv', column_mapping=mapping)
            dataset.file.save('orders.csv', ContentFile(content), save=True)
            self.stdout.write(self.style.SUCCESS('Created demo dataset with column mapping'))
        else:
            self.stdout.write('Demo dataset already exists')

        result = AnalysisResult.objects.filter(dataset=dataset).first()
        if result is None or result.status != AnalysisResult.DONE:
            # Run inline (not .delay()) since this runs during the build step, before
            # any worker process is up — we want the demo ready the moment the app starts.
            run_analysis(dataset.pk)
            self.stdout.write(self.style.SUCCESS('Computed demo analysis result'))
        else:
            self.stdout.write('Demo analysis already computed, skipping')
