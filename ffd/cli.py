import sys
import os
from urllib.parse import urlparse
import argparse
from .__init__ import download, hls
from .__version__ import __version__

def main():
    parser = argparse.ArgumentParser(description = 'hls segment downloader', usage="ffd [options...] [args] url")
    parser.add_argument('url', type=str, help="file/hls url")
    parser.add_argument('-t', '--threads', type=int, help='max workers threads')
    parser.add_argument('-d', '--dest', type=str, help='output destination')
    parser.add_argument('-o', '--output', type=str, help='output file name')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    parser.add_argument('-f', '--force', action='store_true', help="force override")
    argv = sys.argv
    args = parser.parse_args()
    if len(argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if os.path.splitext(urlparse(args.url).path)[-1] == '.m3u8':
        hls(options=args.url, dest=args.dest, threads=args.threads, force=args.force)
    else:
        download(url=args.url, threads=args.threads, output=args.output, dest=args.dest, force=args.force)

if __name__ == '__main__':
    main()
