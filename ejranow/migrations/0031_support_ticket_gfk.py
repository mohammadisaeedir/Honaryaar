import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_targets(apps, schema_editor):
    SupportTicket = apps.get_model("ejranow", "SupportTicket")
    ContentType = apps.get_model("contenttypes", "ContentType")
    type_ids = {
        "profile": ContentType.objects.get(app_label="ejranow", model="profile").pk,
        "project": ContentType.objects.get(app_label="ejranow", model="project").pk,
        "opportunity": ContentType.objects.get(app_label="ejranow", model="opportunity").pk,
    }
    for row in SupportTicket.objects.all():
        body = row.body or ""
        content_type_id = None
        object_id = None
        if row.kind == "contact":
            kind_reason = "general"
            prefix = [part for part in (row.name, row.phone, row.subject) if part]
        elif row.kind == "ticket":
            kind_reason = "other"
            prefix = [row.subject] if row.subject else []
        else:
            kind_reason = "ownership" if row.reason == "abuse" else (row.reason or "other")
            prefix = [part for part in (row.name, row.subject) if part]
            if row.profile_id:
                content_type_id = type_ids["profile"]
                object_id = row.profile_id
            elif row.project_id:
                content_type_id = type_ids["project"]
                object_id = row.project_id
            elif row.opportunity_id:
                content_type_id = type_ids["opportunity"]
                object_id = row.opportunity_id
        if prefix:
            body = "\n".join(prefix + [body])
        SupportTicket.objects.filter(pk=row.pk).update(
            kind_reason=kind_reason,
            body=body,
            content_type_id=content_type_id,
            object_id=object_id,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("ejranow", "0030_support_ticket"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="supportticket",
            name="kind_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("general", "General"),
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
        migrations.AddField(
            model_name="supportticket",
            name="content_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="contenttypes.contenttype",
            ),
        ),
        migrations.AddField(
            model_name="supportticket",
            name="object_id",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="supportticket",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RunPython(copy_targets, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="supportticket",
            name="kind_reason",
            field=models.CharField(
                choices=[
                    ("general", "General"),
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
        migrations.RemoveConstraint(model_name="supportticket", name="support_ticket_one_target"),
        migrations.RemoveConstraint(model_name="supportticket", name="support_ticket_requires_user"),
        migrations.RemoveConstraint(model_name="supportticket", name="support_ticket_reason"),
        migrations.RemoveField(model_name="supportticket", name="name"),
        migrations.RemoveField(model_name="supportticket", name="phone"),
        migrations.RemoveField(model_name="supportticket", name="subject"),
        migrations.RemoveField(model_name="supportticket", name="reason"),
        migrations.RemoveField(model_name="supportticket", name="reply"),
        migrations.RemoveField(model_name="supportticket", name="profile"),
        migrations.RemoveField(model_name="supportticket", name="project"),
        migrations.RemoveField(model_name="supportticket", name="opportunity"),
        migrations.AddConstraint(
            model_name="supportticket",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("kind", "ticket"), ("user__isnull", False)),
                    models.Q(("kind", "ticket"), _negated=True),
                    _connector="OR",
                ),
                name="support_ticket_requires_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="supportticket",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("kind", "contact"), ("kind_reason", "general")),
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
        migrations.AddConstraint(
            model_name="supportticket",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("content_type__isnull", False), ("kind", "report"), ("object_id__isnull", False)),
                    models.Q(
                        ("content_type__isnull", True),
                        ("kind__in", ["contact", "ticket"]),
                        ("object_id__isnull", True),
                    ),
                    _connector="OR",
                ),
                name="support_ticket_target",
            ),
        ),
    ]
