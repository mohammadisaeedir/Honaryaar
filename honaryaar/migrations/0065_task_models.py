import django.db.models.deletion
from django.db import migrations, models

import honaryaar.storage


class Migration(migrations.Migration):

    dependencies = [
        ("honaryaar", "0064_backfill_project_members"),
    ]

    operations = [
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, verbose_name="عنوان")),
                ("description", models.TextField(blank=True, verbose_name="توضیحات")),
                (
                    "phase",
                    models.CharField(
                        choices=[
                            ("create", "خلق"),
                            ("develop", "توسعه"),
                            ("produce", "تولید"),
                            ("perform", "اجرا"),
                            ("after", "پس‌اجرا"),
                        ],
                        max_length=10,
                        verbose_name="فاز",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("todo", "انجام‌نشده"), ("done", "انجام‌شده")],
                        default="todo",
                        max_length=10,
                    ),
                ),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("due_date", models.DateField(blank=True, null=True, verbose_name="ددلاین")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_tasks",
                        to="honaryaar.profile",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to="honaryaar.project",
                    ),
                ),
            ],
            options={
                "verbose_name": "تسک",
                "verbose_name_plural": "تسک‌ها",
                "ordering": ["sort_order", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TaskAssignee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_assignments",
                        to="honaryaar.profile",
                    ),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignees",
                        to="honaryaar.task",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TaskComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(verbose_name="متن")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "author",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="honaryaar.profile"),
                ),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="honaryaar.task",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="TaskAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "file",
                    models.FileField(
                        max_length=300,
                        storage=honaryaar.storage.MediaStorage(),
                        upload_to="task-attachments/",
                    ),
                ),
                ("label", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="honaryaar.task",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="honaryaar.profile",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="taskassignee",
            constraint=models.UniqueConstraint(fields=("task", "profile"), name="unique_task_assignee"),
        ),
    ]
