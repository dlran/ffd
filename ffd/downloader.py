import os
import sys
import argparse
from urllib import request
import ssl
import math
import time
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed


def humanSize(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

class Progressbar:
    def __init__(self, total):
        self.terminalWidth = os.get_terminal_size().columns
        self.spinner = "|/-\\";
        self.total = total
        self.width = self.terminalWidth - len(str(self.total)) - 25
        self.finish = 0

    def update(self, blocksize, spent_time):
        self.finish = min(self.finish + blocksize, self.total)
        percent = min(self.finish, self.total) / self.total
        finishWidth = math.ceil(percent * self.width)
        bar = ("=" * finishWidth) + (" " * (self.width - finishWidth))
        speed = blocksize / spent_time
        # self.spinner[finishWidth%4]
        print(' ' * self.terminalWidth, end='\r')
        print("[%.2f%%][%s] %s %s/s" % ((percent * 100), bar, self.finish, humanSize(speed)), end='\r')
        # sys.stdout.flush()


class Downloader:
    def __init__(self, url, threads=None, filename=None):
        self.g_spent_start = time.time()
        self.url = url
        self.blocksize = 524288
        self.filename = filename or os.path.basename(self.url)
        self.threads = threads or multiprocessing.cpu_count() * 5
        r = request.urlopen(self.request(method='HEAD'))
        self.total = int(r.getheader(name='Content-Length'))
        print('Length: %s (%s)' % (self.total, humanSize(self.total)))
        # self.tellSet = set()

    def request(self, method, header={}):
        return request.Request(
            url = self.url,
            headers = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36', **header},
            method = method)

    def getInterval(self):
        interval = []
        blockNum = math.ceil(self.total / self.blocksize)
        for i in range(blockNum):
            if i == blockNum - 1:
                interval.append((i * self.blocksize, ''))
            else:
                interval.append((i * self.blocksize, (i+1) * self.blocksize - 1))
        return interval

    def download(self, start, end):
        try:
            # [0-1023] = start 0 len 1024 bytes
            st = time.time()
            header = {'Range': 'Bytes=%s-%s' % (start, end), 'Accept-Encoding': '*'}
            with request.urlopen(self.request(method='GET', header=header), timeout=5) as res:
                # print("%s-%s download success" % (start,end))
                # print('%.2fKB/s' % (self.blocksize / 1024 / (time.time() - st)))
                spent_time = time.time() - st
                return start, res.read(), spent_time
        except Exception as e:
            print(' ' * os.get_terminal_size().columns, end='\r')
            if isinstance(e, ssl.SSLError):
                print('SSL Error', end=' ')
            elif isinstance(e, IOError):
                print('IO Error', end=' ')
            print(e)
            print('Retry block %s-%s' % (start, end))
            return self.download(start, end)

    def run(self):
        self.fs = open(self.filename, "wb")

        with ThreadPoolExecutor(self.threads) as executor:
            pb = Progressbar(total=self.total)
            # print('block len: %s' % len(self.getInterval()))
            tasks = [executor.submit(self.download, s, e) for s, e in self.getInterval()]
            for future in as_completed(tasks):
                try:
                    start, data, spent_time = future.result()

                    self.fs.seek(start)
                    self.fs.write(data)
                    # self.tellSet.add(self.fs.tell())

                    pb.update(blocksize=self.blocksize, spent_time=spent_time)
                except Exception as e:
                    print(e)
            m, s = divmod(int(time.time() - self.g_spent_start), 60)
            print()
            # print('get block %s' % len(self.tellSet))
            print('(%sm%ss) %s Saved' % (m, s, self.filename))

        self.fs.close()

def main():
    parser = argparse.ArgumentParser(description = 'oo', usage=".py [options...] [args] url")
    parser.add_argument('url', type=str, help="file url")
    parser.add_argument('-t', '--threads', type=int, help='max workers threads')
    parser.add_argument('-o', '--output', type=str, help='output file name')
    parser.add_argument('-v', '--version', action='version', version='0.0.1')
    argv = sys.argv
    args = parser.parse_args()
    if len(argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    Downloader(url=args.url, threads=args.threads, filename=args.output).run()

if __name__ == '__main__':
    main()

