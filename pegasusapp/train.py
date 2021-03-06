import typer
import boto3
from datetime import datetime
import os
import os.path as osp
import zipfile
from pathlib import Path
import shutil


def zipdir(path, ziph: zipfile.ZipFile):
    # ziph is zipfile handle

    from_path = str(Path(__file__).parents[1].absolute() / "pegasus_run.sh")
    ziph.write(from_path, arcname="./pegasus_run.sh")
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))


def upload_file(file_name: str, bucket: str, object_name: str = None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client("s3")
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except Exception as e:
        typer.echo(f"Could not upload to s3 {e}")
    return True


def run_train(path_to_zip: str):
    filepath = f"ml-training/{Path(__file__).stem}/{datetime.now().timestamp()}"
    s3_code_path = f"{filepath}/code.zip"
    typer.echo(f"Compressing {path_to_zip}")

    zipf = zipfile.ZipFile("/tmp/code.zip", "w", zipfile.ZIP_DEFLATED)
    zipdir(path_to_zip, zipf)
    zipf.close()

    typer.echo(f"Uploading to s3 on path {s3_code_path}")
    upload_file(f"/tmp/code.zip", "gene", s3_code_path)

    path_for_docker = f"s3://gene/{filepath}"
    typer.echo(f"Would now call docker container with env var {path_for_docker}")

    batch = boto3.client("batch")
    # command = "pip install pegasusapp && pegasus pull-code-and-unzip".split(" ")
    command = ["bash", "-c", f"pip install pegasusapp && pegasus pull-code-and-unzip {path_for_docker}"]
    batch.submit_job(
        jobName="test1",
        jobQueue="general-job-queue",
        jobDefinition="ml-training",
        containerOverrides=dict(command=command),
    )

