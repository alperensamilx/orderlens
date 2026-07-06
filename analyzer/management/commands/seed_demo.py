from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from analyzer import analysis
from analyzer.models import Dataset
from analyzer.tasks import run_analysis

DEMO_USERNAME = 'demo'
DEMO_PASSWORD = 'demo1234'


class Command(BaseCommand):
    help = (
        'Creates (or resets) a demo user with a pre-mapped sample dataset, '
        'so a freshly deployed instance still has something to show. '
        'Safe to run on every deploy — recreates the demo dataset each time '
        'so it can never get stuck in a stale/broken state.'
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

        # Recreate from scratch every run (cheap, and guarantees the demo
        # account is never left pointing at a half-finished/broken analysis).
        Dataset.objects.filter(owner=user).delete()

        csv_path = settings.BASE_DIR / 'sample_data' / 'orders.csv'
        content = csv_path.read_text()
        mapping = analysis.detect_column_mapping(content.splitlines()[0].split(','))

        dataset = Dataset.objects.create(
            owner=user, name='orders.csv', content=content, column_mapping=mapping,
        )
        self.stdout.write(self.style.SUCCESS('Created demo dataset with column mapping'))

        # Run inline (not .delay()) since this runs during the build step, before
        # any worker process is up — we want the demo ready the moment the app starts.
        run_analysis(dataset.pk)
        self.stdout.write(self.style.SUCCESS('Computed demo analysis result'))
