# -*- coding: UTF-8 -*-
import subprocess
import re
import sys
import random
import socket
import struct
import time
import os
from urllib.parse import urlparse
from urllib import request
import ssl
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
import string


def getTsBsn(url):
    '''
    If ts basename length == 1 and all are the same, splice the previous dir
    '''
    urlbs = os.path.basename(urlparse(url).path)
    if len(urlbs) == 1:
        _p = urlparse(url).path.rsplit('/', 2)
        return _p[-2] + '_' + _p[-1]
    elif len(urlbs) > 100:
        return os.path.basename(urlparse(url).path)[-8:]
    else:
        return urlbs

def downTs(segment, outDir):
    filePth = os.path.join(outDir, segment['bsn'])

    if os.path.exists(filePth) and os.path.getsize(filePth) > 0:
        print('already exists %s' % segment['bsn'])
    else:
        try:
            tsBinary = request.urlopen(__request(segment['url']), timeout=5)
            with open(filePth, 'wb') as f:
                f.write(tsBinary.read())
                print('downloaded %s' % segment['url'])
        except Exception as e:
            print('retry ' + segment['url'])
            if isinstance(e, socket.timeout):
                print('scoket timeout', end=' ')
            elif isinstance(e, IOError):
                print('IO Error', end=' ')
            print(e)
            return downTs(segment, outDir)

    return True


def __request(url, method='GET', header={}):
    randIp = socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))
    return request.Request(
        url = url,
        headers = {
            'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
            'X-Forwarded-For': randIp,
            **header},
        method = method)

def m3u8open(url, cachePth, force):
    def loadM3U8(url, force=False, isStmInf=True):
        print('opening ' + url)
        stmInfPath = os.path.join(cachePth, 'index.stream.m3u8')
        orgInfPath = os.path.join(cachePth, 'index.original.m3u8')
        if not force and isStmInf and os.path.exists(stmInfPath) and os.path.getsize(stmInfPath) > 0:
            infIsExists = True
            with open(stmInfPath, 'r') as f:
                content = f.read()
            print('already exists index.stream.m3u8')
        elif not force and os.path.exists(orgInfPath) and os.path.getsize(orgInfPath) > 0:
            infIsExists = True
            if isStmInf:
                # if doesn't stream file but exists original.m3u8
                print('not exists index.stream.m3u8')
            isStmInf = False
            with open(orgInfPath, 'r') as f:
                content = f.read()
            print('already exists index.original.m3u8')
        else:
            infIsExists = False
            r = request.urlopen(__request(url), timeout=5)
            content = r.read().decode('UTF-8')
            print('downloaded ' + url)
        streaminf = re.findall(r'#EXT-X-STREAM-INF:.+\n(.+?)\n?$', content)
        # Correct status if not stream inf
        isStmInf = bool(streaminf)

        if not os.path.exists(cachePth):
            os.mkdir(cachePth)
        if not infIsExists:
            with open(stmInfPath if isStmInf else orgInfPath, 'w') as f:
                f.write(content)

        if streaminf:
            # Take the last one 
            # replace backslash in path
            stream_path = streaminf[-1].replace('\\', '/')
            inf_url = request.urljoin(url, stream_path)
            return loadM3U8(inf_url, force, False)
        else:
            # Find and replace key
            def keyMap(match):
                keyPath = os.path.join(cachePth, 'key.key')
                keyUrl = request.urljoin(url, match.group(2))
                if not os.path.exists(keyPath) or os.path.getsize(keyPath) == 0:
                    keyres = request.urlopen(__request(keyUrl), timeout=5)
                    with open(keyPath, 'wb') as f:
                        f.write(keyres.read())
                    print('downloaded ' + keyUrl)
                else:
                    print('already exists key.key')
                return match.group(1) + 'key.key"'

            content = re.sub(r'(#EXT-X-KEY.*URI=")(.+?)"', keyMap, content)

            # Find and replace ts
            chkTslsBsn = []
            tsls = []
            def tsMap(match):
                _path = match.group(3)
                _bsname = getTsBsn(_path)
                # Already exists same basename
                if _bsname in chkTslsBsn:
                    _bsname = str(len(chkTslsBsn)) + '.ts'
                chkTslsBsn.append(_bsname)
                tsls.append({'url': request.urljoin(url, _path), 'bsn': _bsname})
                return match.group(1) + _bsname + '\n'
            content = re.sub(r'(#EXTINF:.+?\n)(#EXT-X-PRIVINF:.+\n)?(.+)\n', tsMap, content)
            with open(os.path.join(cachePth, 'index.m3u8'), 'w') as f:
                f.write(content)
            if not tsls:
                print('ts not found')
                sys.exit(1)
                return []
            else:
                return tsls

    return loadM3U8(url, force)

def hlscache(url, dest=None, threads=None, force=False, inf_only=False, pack=False):
    g_spent_start = time.time()
    status = 1
    threads = threads or multiprocessing.cpu_count() * 5
    cachePth = (dest and os.path.abspath(dest)) or os.path.join(os.getcwd(), 'cache')
    ssl._create_default_https_context = ssl._create_unverified_context
    segmentList = m3u8open(url, cachePth, force)
    if inf_only:
        print('%s Index file saved' % cachePth)
        return
    with ThreadPoolExecutor(threads) as executor:
        tasks = [executor.submit(downTs, p, cachePth) for p in segmentList]
        for future in as_completed(tasks):
            try:
                future.result()
            except Exception as e:
                status = 2

    m, s = divmod(int(time.time() - g_spent_start), 60)
    print('(%sm%ss) %s Saved' % (m, s, cachePth))

    if pack and status == 1:
        print('packing')
        if isinstance(pack, str) and os.path.splitext(pack)[-1] == '.mp4':
            packup(cachePth, output=pack)
        packup(cachePth)


def packup(cachePth, output='index.mp4'):
    p = subprocess.Popen(\
        u'ffmpeg -allowed_extensions ALL -i "{segmentPth}" -c copy -y "{outPth}"'\
        .format(segmentPth=os.path.join(cachePth, 'index.m3u8'),
            outPth=os.path.join(cachePth, output)),
            shell=True)
    p.wait()

