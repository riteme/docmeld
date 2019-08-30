#!/usr/bin/env python3

DEBUG_MODE = True

import os
import sys
import json
import hmac
import shutil
import hashlib
import tempfile
import subprocess

from filelock import FileLock
from flask import Flask, request, abort

import logging as log
log.basicConfig(
    format='[%(asctime)s][%(filename)s:%(funcName)s@%(lineno)d][%(levelname)s] %(message)s',
    level=log.DEBUG if DEBUG_MODE else log.INFO
)

application = Flask(__name__)

ENCODING = 'utf-8'
DOCMELD_EXECUTABLE = './docmeld.py'
DATABASE_DIRECTORY = 'database'
WEBPAGE_DIRECTORY = '/var/www/html/docmeld'
WEBURL = 'https://riteme.site/docmeld/'
STATUS_FILE = 'status.txt'
INDEX_FILE = 'index.html'
OUTPUT_FILE = 'output.html'
GIT_URL_START = 'git+'
COMPILE_TIME_LIMIT = 300  # 5min

# HTTP error codes
BAD_REQUEST = 400
UNAUTHORIZED = 401
FORBIDDEN = 403
METHOD_NOT_ALLOWED = 405

def md5(x):
    return hashlib.md5(x.encode(ENCODING)).hexdigest()

def authenticate(secret, signature, data):
    method, digest = signature.split('=', 1)
    if method not in hashlib.algorithms_available:
        log.error('Unsupported hash method: "%s"', method)
        return False
    mac = hmac.new(secret, msg=data, digestmod=method)
    return hmac.compare_digest(mac.hexdigest(), digest)

@application.route('/docmeld-webhook/', methods=['GET', 'POST'])
def main():
    if request.method != 'POST':
        abort(METHOD_NOT_ALLOWED)

    try:
        payload = request.get_json()
        if payload is None:
            raise RuntimeError
    except:
        log.error('Failed to obtain payload data.')
        abort(BAD_REQUEST)

    repo = payload['repository']['full_name']
    clone_url = payload['repository']['clone_url']
    idx = md5(clone_url)
    record_file_path = '%s/%s.json' % (DATABASE_DIRECTORY, idx)
    if not os.path.isfile(record_file_path):
        log.error('DECLINED: repository "%s" has no record on the server. Please contact the administrator.', repo)
        abort(UNAUTHORIZED)

    with open(record_file_path, 'r') as fp:
        record = json.load(fp)
        log.info('Record file "%s" loaded.', record_file_path)

    if not DEBUG_MODE:
        secret = record['secret']
        signature = request.headers.get('X-Hub-Signature')
        if signature is None:
            log.error('DECLINED: no signature provided.')
            abort(BAD_REQUEST)
        if not authenticate(secret, signature, request.data):
            log.error('DECLINED: failed to pass authentication.')
            abort(UNAUTHORIZED)

    event = request.headers.get('X-GitHub-Event')
    if event is None:
        log.error('DECLINED: no event provided.')
        abort(BAD_REQUEST)

    # Ping event
    if event == 'ping':
        return json.dumps({'msg': 'pong'})

    if event not in ['push']:
        return json.dumps({
            'status': 'fail',
            'reason': 'not a push event'
        })

    branch = payload['ref'].rsplit('/', 1)[-1]
    head = payload['after']
    folder_name = '%s/%s' % (repo, branch)
    folder = os.path.join(WEBPAGE_DIRECTORY, folder_name)
    if not os.path.exists(folder):
        os.makedirs(folder)
    status = os.path.join(folder, STATUS_FILE)
    index = os.path.join(folder, INDEX_FILE)
    output = os.path.join(folder, OUTPUT_FILE)

    index_lock = index + '.lock'
    with FileLock(index_lock):
        tmpfd, tmppath = tempfile.mkstemp()
        log.debug('tmppath = %s', tmppath)
        with os.fdopen(tmpfd, 'w') as fp:
            json.dump(record['checksums'], fp)

        log.info('Launching docmeld...')
        with open(status, 'w') as fp:
            proc = subprocess.Popen(
                [DOCMELD_EXECUTABLE, GIT_URL_START + clone_url,
                 '-b', branch, '-s', head, '-c', tmppath, '-o', output],
                stdout=fp, stderr=subprocess.STDOUT)
            try:
                proc.wait(timeout=COMPILE_TIME_LIMIT)
            except:
                log.error('Time limit exceeded.')
                return json.dumps({
                    'status': 'fail',
                    'reason': 'time limit exceeded (%ss)' % COMPILE_TIME_LIMIT,
                    'detail': WEBURL + os.path.join(folder_name, STATUS_FILE)
                })

        if proc.returncode != 0:
            log.error('docmeld execution failed with status code %s', proc.returncode)
            return json.dumps({
                'status': 'fail',
                'reason': 'docmeld failed with status code %s' % proc.returncode,
                'detail': WEBURL + os.path.join(folder_name, STATUS_FILE)
            })

        log.info('Copying index.html to output.html...')
        shutil.copyfile(output, index)

    os.remove(tmppath)
    result = {
        'status': 'success',
        'returncode': proc.returncode,
        'output_url': WEBURL + os.path.join(folder_name, INDEX_FILE),
        'detail': WEBURL + os.path.join(folder_name, STATUS_FILE)
    }
    return json.dumps(result, sort_keys=True)

if __name__ == '__main__':
    application.run(host='0.0.0.0', debug=DEBUG_MODE)