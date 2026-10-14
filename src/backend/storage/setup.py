"""Configure upload CORS after provisioning private Garage buckets and key permissions."""

from backend.core.config import get_settings
from backend.storage.s3 import create_s3_client


def main() -> None:
    settings = get_settings()
    client = create_s3_client(settings)
    try:
        for bucket in (settings.avatar_bucket, settings.publication_bucket):
            client.head_bucket(Bucket=bucket)
            client.put_bucket_cors(Bucket=bucket, CORSConfiguration={"CORSRules": [{
                "AllowedOrigins": settings.storage_cors_origins,
                "AllowedMethods": ["PUT"],
                # Browser preflight uses lower-case names; Garage matches them literally.
                "AllowedHeaders": ["content-type"],
                "MaxAgeSeconds": 600,
            }]})
            print(f"Configured private image bucket: {bucket}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
