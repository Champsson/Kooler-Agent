import os
import boto3
from botocore.exceptions import NoCredentialsError
from app.config import Config
from app.utils import timer_decorator, logger

@timer_decorator
def upload_to_s3(local_file, s3_file_name=None):
    """Upload a file to S3 and return its public URL"""
    if s3_file_name is None:
        s3_file_name = os.path.basename(local_file)
    
    bucket_name = os.getenv('AWS_S3_BUCKET', 'kooler-agent-tts')
    
    s3 = boto3.client('s3', 
                     region_name=os.getenv('AWS_REGION', 'us-west-2'),
                     aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
                     aws_secret_access_key=os.getenv('AWS_SECRET_KEY'))
    try:
        s3.upload_file(local_file, bucket_name, s3_file_name)
        logger.info(f"File uploaded to S3: {s3_file_name}")
        return f"https://{bucket_name}.s3.amazonaws.com/{s3_file_name}"
    except NoCredentialsError:
        logger.error("AWS credentials not available") 
        return None
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        return None
