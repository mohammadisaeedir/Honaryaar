from django.db.models.signals import post_delete, post_save

from honaryaar.models import Opportunity, Profile, Project, ProjectContact


def _forget(**kwargs):
    from honaryaar.catalog import forget_stat_counters

    forget_stat_counters()


for model in (Profile, Project, Opportunity, ProjectContact):
    post_save.connect(_forget, sender=model, dispatch_uid=f"stat-save-{model._meta.label_lower}")
    post_delete.connect(_forget, sender=model, dispatch_uid=f"stat-delete-{model._meta.label_lower}")
