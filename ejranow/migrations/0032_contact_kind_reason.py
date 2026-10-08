from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ejranow", "0031_support_ticket_gfk"),
    ]

    operations = [
        migrations.AlterField(
            model_name="supportticket",
            name="kind_reason",
            field=models.CharField(
                choices=[
                    ("general", "Public"),
                    ("collaboration", "Collaboration"),
                    ("complaint", "Criticism and complaint"),
                    ("account", "Account"),
                    ("profile", "Profile"),
                    ("project", "Project"),
                    ("opportunity", "Opportunity"),
                    ("technical", "Technical"),
                    ("wrong", "Wrong information"),
                    ("ownership", "Ownership mismatch"),
                    ("spam", "Spam"),
                    ("other", "Other"),
                ],
                max_length=20,
            ),
        ),
        migrations.RemoveConstraint(model_name="supportticket", name="support_ticket_kind_reason"),
        migrations.AddConstraint(
            model_name="supportticket",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("kind", "contact"),
                        ("kind_reason__in", ["general", "collaboration", "complaint", "other"]),
                    ),
                    models.Q(
                        ("kind", "ticket"),
                        ("kind_reason__in", ["account", "profile", "project", "opportunity", "technical", "other"]),
                    ),
                    models.Q(
                        ("kind", "report"),
                        ("kind_reason__in", ["wrong", "ownership", "spam", "other"]),
                    ),
                    _connector="OR",
                ),
                name="support_ticket_kind_reason",
            ),
        ),
    ]
