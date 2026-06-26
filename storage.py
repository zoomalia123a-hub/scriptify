import os
import io
import uuid
from datetime import datetime

S3_ENABLED = all(os.environ.get(k) for k in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_BUCKET'))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DIRS = {
    'photos': os.environ.get('PHOTOS_DIR', os.path.join(BASE_DIR, 'photos')),
    'examenes': os.environ.get('EXAMENES_DIR', os.path.join(BASE_DIR, 'examenes')),
    'documentos': os.environ.get('DOCS_DIR', os.path.join(BASE_DIR, 'documentos')),
}

_S3_CLIENT = None

def _get_s3():
    global _S3_CLIENT
    if _S3_CLIENT is None:
        import boto3
        _S3_CLIENT = boto3.client(
            's3',
            aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
            region_name=os.environ.get('AWS_REGION', 'us-east-1'),
            endpoint_url=os.environ.get('AWS_S3_ENDPOINT'),
        )
    return _S3_CLIENT

def _bucket():
    return os.environ['AWS_S3_BUCKET']

def save_file(file_obj, category='photos', filename=None):
    if not filename:
        ext = os.path.splitext(getattr(file_obj, 'filename', 'file.jpg'))[1] or '.jpg'
        filename = f"{uuid.uuid4().hex[:12]}{ext}"
    if S3_ENABLED:
        s3 = _get_s3()
        key = f"{category}/{filename}"
        s3.upload_fileobj(file_obj, _bucket(), key, ExtraArgs={'ACL': 'public-read'})
        url = f"https://{_bucket()}.s3.amazonaws.com/{key}"
        return filename, url
    else:
        os.makedirs(LOCAL_DIRS[category], exist_ok=True)
        path = os.path.join(LOCAL_DIRS[category], filename)
        file_obj.save(path)
        return filename, filename

def get_url(filename, category='photos'):
    if S3_ENABLED:
        return f"https://{_bucket()}.s3.amazonaws.com/{category}/{filename}"
    return f"/{category}/{filename}"

def delete_file(filename, category='photos'):
    if S3_ENABLED:
        s3 = _get_s3()
        s3.delete_object(Bucket=_bucket(), Key=f"{category}/{filename}")
    else:
        path = os.path.join(LOCAL_DIRS[category], filename)
        if os.path.exists(path):
            os.remove(path)

def get_local_path(filename, category='photos'):
    return os.path.join(LOCAL_DIRS[category], filename)
