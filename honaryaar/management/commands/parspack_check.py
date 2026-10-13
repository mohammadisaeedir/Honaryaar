import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from honaryaar.storage import UPLOAD_CONTENT_TYPE, parspack_configured, reset_backend, storage_prefix


class Command(BaseCommand):
    help = "Check ParsPack without printing secrets. Writes and deletes one object under this prefix."

    def handle(self, *args, **options):
        if not parspack_configured():
            raise CommandError("ParsPack settings are incomplete. Endpoint, region, bucket, and keys are required.")
        endpoint = settings.PARSPACK_ENDPOINT_URL
        if not endpoint.startswith("https://"):
            raise CommandError("PARSPACK_ENDPOINT_URL must be an https URL from the ParsPack panel.")
        reset_backend()
        from honaryaar.storage import get_backend

        backend = get_backend()
        client = backend.client()
        bucket = settings.PARSPACK_BUCKET_NAME
        prefix = storage_prefix()
        self.stdout.write(
            " ".join(
                [
                    f"bucket={bucket}",
                    f"region={settings.PARSPACK_REGION_NAME}",
                    f"endpoint={endpoint}",
                    f"prefix={prefix}",
                    "signature=s3v4",
                    "addressing=path",
                    f"public_base={'set' if settings.PARSPACK_PUBLIC_MEDIA_BASE_URL else 'unset'}",
                ]
            )
        )
        client.head_bucket(Bucket=bucket)
        self.stdout.write("head_bucket=ok")
        key = f"{prefix}/_health/{uuid.uuid4()}.txt"
        body = b"honaryaar-parspack-check"
        client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="text/plain")
        found = client.head_object(Bucket=bucket, Key=key)
        if int(found["ContentLength"]) != len(body):
            raise CommandError("head size did not match the uploaded object")
        ranged = client.get_object(Bucket=bucket, Key=key, Range="bytes=0-3")
        if ranged["Body"].read() != body[:4]:
            raise CommandError("range request did not return the expected bytes")
        self.stdout.write("range=ok")
        signed = client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": key, "ContentType": UPLOAD_CONTENT_TYPE},
            ExpiresIn=60,
            HttpMethod="PUT",
        )
        if "X-Amz-Algorithm=AWS4-HMAC-SHA256" not in signed or not signed.startswith("https://"):
            raise CommandError("presigned PUT was not an https SigV4 URL")
        self.stdout.write("presign=ok")
        acl = "unsupported"
        from botocore.exceptions import ClientError

        try:
            client.put_object_acl(Bucket=bucket, Key=key, ACL="public-read")
            acl = "public-read"
            client.put_object_acl(Bucket=bucket, Key=key, ACL="private")
            acl = "private-after-public-read"
        except ClientError as exc:
            acl = exc.response.get("Error", {}).get("Code", "denied")
        self.stdout.write(f"object_acl={acl}")
        anonymous = "not-checked"
        try:
            import urllib.request

            public = f"{endpoint}/{bucket}/{key}"
            with urllib.request.urlopen(public, timeout=10) as response:
                anonymous = f"readable:{response.status}"
        except Exception as exc:
            anonymous = exc.__class__.__name__
        self.stdout.write(f"anonymous_get={anonymous}")
        if anonymous.startswith("readable"):
            self.stdout.write("warning: a private object was anonymously readable. Keep the bucket private.")
        client.delete_object(Bucket=bucket, Key=key)
        self.stdout.write("delete=ok")
        try:
            policy = client.get_bucket_policy(Bucket=bucket)
            text = policy.get("Policy") or ""
            public_write = '"s3:PutObject"' in text and '"Principal":"*"' in text.replace(" ", "")
            self.stdout.write(f"bucket_policy=present public_write={str(public_write).lower()}")
            if public_write:
                self.stdout.write("warning: bucket policy allows public writes. Remove that statement.")
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "unavailable")
            self.stdout.write(f"bucket_policy={code}")
        self.stdout.write("ok")
