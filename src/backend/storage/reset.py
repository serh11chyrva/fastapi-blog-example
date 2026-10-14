"""Explicitly reset the configured application database and its two image buckets."""

import argparse

from pymongo import MongoClient

from backend.core.config import get_settings
from backend.storage.s3 import create_s3_client


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-database", required=True, help="Exact MONGODB_DATABASE name to erase.")
    args = parser.parse_args()
    if args.confirm_database != settings.mongodb_database:
        parser.error("Confirmation must match MONGODB_DATABASE")
    client = create_s3_client(settings)
    try:
        for bucket in (settings.avatar_bucket, settings.publication_bucket):
            for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
                for item in page.get("Contents", []):
                    client.delete_object(Bucket=bucket, Key=item["Key"])
            print(f"Cleared image bucket: {bucket}")
        with MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=8_000) as mongo:
            mongo.drop_database(settings.mongodb_database)
        print(f"Cleared application database: {settings.mongodb_database}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
