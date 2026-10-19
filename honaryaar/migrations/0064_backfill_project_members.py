from django.db import migrations


class Migration(migrations.Migration):
    """Intentionally a no-op.

    Production must not get ProjectMember rows for legacy projects.
    Board-created projects insert their own owner membership in the view.
    """

    dependencies = [
        ("honaryaar", "0063_project_member"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
