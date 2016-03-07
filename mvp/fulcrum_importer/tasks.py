from __future__ import absolute_import

from celery import shared_task, task
from S3.Exceptions import *
from S3.S3 import S3
from S3.Config import Config
from S3.S3Uri import S3Uri
import json
import os
from .models import S3Sync
from .fulcrum_importer import FulcrumImporter, process_fulcrum_data
from django.conf import settings
from django.core.cache import cache
import requests
from hashlib import md5

LOCK_EXPIRE = 60 * 60 # LOCK_EXPIRE SHOULD IS IN SECONDS

@shared_task(name="fulcrum_importer.tasks.task_update_layers")
def task_update_layers():
    name = "fulcrum_importer.tasks.task_update_layers"
    #http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#ensuring-a-task-is-only-executed-one-at-a-time
    file_name_hexdigest = md5(name).hexdigest()
    lock_id = '{0}-lock-{1}'.format(name, file_name_hexdigest)
    acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
    release_lock = lambda: cache.delete(lock_id)
    if acquire_lock():
        try:
            fulcrum_importer = FulcrumImporter()
            fulcrum_importer.update_all_layers()
        finally:
            release_lock()


@shared_task(name="fulcrum_importer.tasks.pull_s3_data")
def pull_s3_data():
    #http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#ensuring-a-task-is-only-executed-one-at-a-time
    #https://www.mail-archive.com/s3tools-general@lists.sourceforge.net/msg00174.html

    name = "fulcrum_importer.tasks.pull_s3_data"
    try:
        S3_KEY = settings.S3_KEY
        S3_SECRET = settings.S3_SECRET
    except AttributeError:
        S3_KEY = None
        S3_SECRET = None

    try:
        S3_GPG = settings.S3_GPG
    except AttributeError:
        S3_GPG = None

    cfg = Config(configfile=settings.S3_CFG, access_key=S3_KEY, secret_key=S3_SECRET)
    if S3_GPG:
        cfg.gpg_passphrase = S3_GPG
    s3 = S3(cfg)
    file_name_hexdigest = md5(name).hexdigest()
    lock_id = '{0}-lock-{1}'.format(name, file_name_hexdigest)
    acquire_lock = lambda: cache.add(lock_id, "true", LOCK_EXPIRE)
    release_lock = lambda: cache.delete(lock_id)
    if acquire_lock():
        try:
            for file_name, file_size in list_bucket_files(s3, settings.S3_BUCKET):
                handle_file(s3, file_name, file_size)
        finally:
            release_lock()


def list_bucket_files(s3, bucket):
    response = s3.bucket_list(bucket)
    for key in response["list"]:
        yield key["Key"], key["Size"]


def is_loaded(file_name):
    s3_file = S3Sync.objects.filter(s3_filename=file_name)
    if s3_file:
        return True
    return False


def s3_download(s3, uri, file_name, file_size):
    start_pos = 0
    print "File Size Reported: {}".format(int(file_size))
    if os.path.exists(os.path.join(settings.FULCRUM_UPLOAD, file_name)):
        start_pos = int(os.path.getsize(os.path.join(settings.FULCRUM_UPLOAD, file_name)))
        print("Starting Position Reported for {}: {}".format(os.path.join(settings.FULCRUM_UPLOAD, file_name), start_pos))
        if start_pos == int(file_size):
            return
    print("Downloading from S3: {}".format(file_name))
    with open(os.path.join(settings.FULCRUM_UPLOAD, file_name), 'wb') as download:
        response = s3.object_get(uri, download, file_name, start_position = start_pos-8)
    print("Download returned with filesize: {}".format(int(os.path.getsize(os.path.join(settings.FULCRUM_UPLOAD, file_name)))))
    return response


def handle_file(s3, file_name, file_size):
    # if 'N-Z' not in file_name:
    #     return
    if is_loaded(file_name):
        return
    print(str(s3_download(s3, S3Uri("s3://{}/{}".format(settings.S3_BUCKET,file_name)), file_name, file_size)))
    print("Processing: {}".format(file_name))
    process_fulcrum_data(file_name)
    S3Sync.objects.create(s3_filename=file_name)


@shared_task(name="fulcrum_importer.tasks.task_update_tiles")
def update_tiles(filtered_features, layer_name):
    truncate_tiles(layer_name=layer_name.lower(), srs=4326)
    truncate_tiles(layer_name=layer_name.lower(), srs=900913)


def truncate_tiles(layer_name=None, srs=None, geoserver_base_url=None, **kwargs):
    #See http://docs.geoserver.org/stable/en/user/geowebcache/rest/seed.html for more parameters.
    #See also https://github.com/GeoNode/geonode/issues/1656
    params = kwargs
    params.setdefault("name", "geonode:{0}".format(layer_name))
    params.setdefault("srs", {"number": srs})
    params.setdefault("zoomStart", 0)
    if srs == 4326:
        params.setdefault("zoomStop", 21)
    else:
        params.setdefault("zoomStop", 31)
    params.setdefault("format", "image/png")
    params.setdefault("type", "truncate")
    params.setdefault("threadCount", 4)

    payload = json.dumps({"seedRequest": params})

    if not geoserver_base_url:
        geoserver_base_url = settings.GEOSERVER_URL.rstrip('/')

    url = "{0}/gwc/rest/seed/geonode:{1}.json".format(geoserver_base_url, layer_name)

    requests.post(url,
                  auth=(settings.OGC_SERVER['default']['USER'],
                        settings.OGC_SERVER['default']['PASSWORD'],
                        ),
                  headers={"content-type": "application/json"},
                  data=payload,
                  verify=False)
