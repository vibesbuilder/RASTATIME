# RASTATIME 2026-05-12 — add ``length`` field for Media-Library integration.
#
# When a line-in is dragged into a show's content list, this is the
# default slot length we reserve for it (same role as
# ``cc_webstream.length``).  NULL means "fall back to 30 minutes" so
# existing rows don't need a backfill.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('linein', '0002_alter_linein_priority'),
    ]

    operations = [
        migrations.AddField(
            model_name='linein',
            name='length',
            field=models.DurationField(
                blank=True,
                null=True,
                default=None,
                help_text=(
                    "Default duration when this line-in is added to a show. "
                    "NULL falls back to 30 minutes."
                ),
            ),
        ),
    ]
