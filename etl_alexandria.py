# --- Imports and Basic Setup ---
from datetime import datetime
import os
import sys
import json
import argparse
import logging
from email.message import EmailMessage
import boto3
from botocore.exceptions import ClientError

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="Upload matching CSV files to S3.")
parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable debug logging"
)
args = parser.parse_args()

# --- Directory Setup ---
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

logs_dir = os.path.join(base_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)

# --- Logging Configuration ---
log_level = logging.DEBUG if args.debug else logging.INFO
timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
log_file_path = os.path.join(logs_dir, f"{timestamp}_UploadRun.log")
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Secrets Loader ---
def get_secret(secret_name, region):
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except ClientError as e:
        logging.error(f"Failed to retrieve secret '{secret_name}': {e.response['Error']['Message']}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error retrieving secret '{secret_name}': {e}")
        raise

# --- File Parsing and Upload Utilities ---
def build_s3_key_from_filename(filename: str):
    try:
        base = os.path.basename(filename)
        name_part, _ = os.path.splitext(base)
        parts = name_part.split("_")
        if len(parts) != 2:
            logging.warning(f"Skipping file with unexpected name: {filename}")
            return None
        end_date = datetime.strptime(parts[1], "%Y%m%d")
        return f"alexandria/{end_date:%Y/%m/%d}/{base}"
    except Exception as e:
        logging.error(f"Failed to parse S3 key from filename '{filename}': {e}")
        return None

def upload_matching_files_to_s3(local_dir: str, bucket_name: str):
    s3 = boto3.client("s3")
    for root, _, files in os.walk(local_dir):
        for file in files:
            if not file.endswith(".csv"):
                continue
            full_path = os.path.join(root, file)
            s3_key = build_s3_key_from_filename(file)
            if s3_key is None:
                continue
            try:
                logging.info(f"Uploading {full_path} to s3://{bucket_name}/{s3_key}")
                s3.upload_file(full_path, bucket_name, s3_key)
                logging.info("Upload successful.")
            except Exception as e:
                logging.error(f"Failed to upload {file} to S3: {e}")

# --- Main ---
def main():
    logging.info("--- Starting File Upload to S3 ---")
    try:
        config_path = os.path.join(base_dir, "config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        secret = get_secret(config["aws_secret_name"], config["aws_region"])
        bucket_name = secret["S3_BUCKET_NAME"]
        upload_dir = config.get("local_upload_dir", os.path.join(base_dir, "upload_files"))
        upload_matching_files_to_s3(upload_dir, bucket_name)
        logging.info("--- Upload complete ---")
    except Exception as e:
        logging.critical(f"Upload process failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
