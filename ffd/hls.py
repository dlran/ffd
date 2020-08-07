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


def downTs(url, outDir):
    filePth = os.path.join(outDir, os.path.basename(urlparse(url).path))

    if os.path.exists(filePth) and os.path.getsize(filePth) > 0:
        print('already exists %s' % os.path.basename(url))
    else:
        ssl._create_default_https_context = ssl._create_unverified_context
        try:
            tsBinary = request.urlopen(__request(url), timeout=5)
            with open(filePth, 'wb') as f:
                f.write(tsBinary.read())
                print('downloaded %s' % url)
        except Exception as e:
            print('retry ' + url)
            if isinstance(e, socket.timeout):
                print('scoket timeout', end=' ')
            elif isinstance(e, IOError):
                print('IO Error', end=' ')
            print(e)
            return downTs(url, outDir)

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

def m3u8open(url, cachePth):

    def loadM3U8(url):
        print('loading ' + url)
        r = request.urlopen(__request(url))
        content = r.read().decode("UTF-8")
        streaminf = re.findall(r'#EXT-X-STREAM-INF:.+\n(.+?m3u8)', content)
        if streaminf:
            # Take the last one 
            inf_url = request.urljoin(url, streaminf[-1])
            return loadM3U8(inf_url)
        else:
            if not os.path.exists(cachePth):
                os.mkdir(cachePth)
            with open(os.path.join(cachePth, 'index.m3u8'), 'w') as f:
                f.write(content)

            # Download key
            key = re.findall(r'#EXT-X-KEY.*URI="(.+?\.key)"', content)
            if key:
                keyUrl = request.urljoin(url, key[0])
                print('downloading ' + keyUrl)
                keyres = request.urlopen(__request(keyUrl))
                with open(os.path.join(cachePth, key[0]), 'w') as f:
                    f.write(keyres.read().decode("UTF-8"))

            tsls = re.findall(r'.+\.ts.*', content)
            if not tsls:
                print('ts not found')
                sys.exit(1)
                return []
            else:
                return [request.urljoin(url, t) for t in tsls]

    return loadM3U8(url)

def hlscache(url, dest=None, threads=None, pack=False):
    g_spent_start = time.time()
    status = 1
    threads = threads or multiprocessing.cpu_count() * 5
    cachePth = (dest and os.path.abspath(dest)) or os.path.join(os.getcwd(), 'cache')
    segmentList = m3u8open(url, cachePth)
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

