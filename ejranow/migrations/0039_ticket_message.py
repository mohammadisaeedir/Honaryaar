from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_opening_messages(apps, schema_editor):
    SupportTicket = apps.get_model("ejranow", "SupportTicket")
    TicketMessage = apps.get_model("ejranow", "TicketMessage")
    for ticket in SupportTicket.objects.all():
        message = TicketMessage.objects.create(
            ticket_id=ticket.pk,
            author_id=ticket.user_id,
            from_staff=False,
            body=ticket.body,
        )
        TicketMessage.objects.filter(pk=message.pk).update(created_at=ticket.created_at)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ejranow", "0038_opportunity_terms"),
    ]

    operations = [
        migrations.CreateModel(
            name="TicketMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("from_staff", models.BooleanField(default=False)),
                ("body", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ticket_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "ticket",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="ejranow.supportticket",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "pk"],
            },
        ),
        migrations.RunPython(seed_opening_messages, migrations.RunPython.noop),
    ]
