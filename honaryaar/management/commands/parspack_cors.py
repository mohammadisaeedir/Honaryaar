import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from honaryaar.storage import (
    UPLOAD_CONTENT_TYPE,
    cors_configuration,
    merge_cors,
    parspack_configured,
    reset_backend,
    storage_prefix,
    upload_origins,
)


class Command(BaseCommand):
    help = "Show the CORS rule for direct uploads. --apply merges it and keeps unrelated rules."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        if not parspack_configured():
            raise CommandError("ParsPack settings are incomplete.")
        origins = upload_origins()
        desired = cors_configuration()
        self.stdout.write(f"prefix={storage_prefix()} origins={', '.join(origins) or '(none)'}")
        self.stdout.write(json.dumps(desired, ensure_ascii=False, indent=2))
        from botocore.exceptions import ClientError

        reset_backend()
        from honaryaar.storage import get_backend

        client = get_backend().client()
        bucket = settings.PARSPACK_BUCKET_NAME
        current = {"CORSRules": []}
        try:
            current = client.get_bucket_cors(Bucket=bucket)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            self.stdout.write(f"current cors: {code or 'unavailable'}")
        else:
            self.stdout.write("current cors rules=" + str(len(current.get("CORSRules") or [])))
        merged = merge_cors(current, desired)
        self.stdout.write("merged:")
        self.stdout.write(json.dumps({"CORSRules": merged["CORSRules"]}, ensure_ascii=False, indent=2))
        if not options["apply"]:
            self.stdout.write("not applied")
            return
        if not origins:
            raise CommandError("Set MEDIA_UPLOAD_ORIGINS before applying preview CORS.")
        client.put_bucket_cors(Bucket=bucket, CORSConfiguration={"CORSRules": merged["CORSRules"]})
        self.stdout.write("applied")
