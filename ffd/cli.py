import sys
import os
import argparse
from .__init__ import download, hls
from .__version__ import __version__

def main():
    parser = argparse.ArgumentParser(description = 'oo', usage=".py [options...] [args] url")
    parser.add_argument('url', type=str, help="file url")
    parser.add_argument('-t', '--threads', type=int, help='max workers threads')
    parser.add_argument('-d', '--dest', type=str, help='output cache destination')
    parser.add_argument('-o', '--output', type=str, help='output file name')
    parser.add_argument('-v', '--version', action='version', version=__version__)
    argv = sys.argv
    args = parser.parse_args()
    if len(argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if os.path.splitext(args.url)[-1] == '.m3u8':
        hls(url=args.url, dest=args.dest, threads=args.threads)
    else:
        download(url=args.url, threads=args.threads, output=args.output, dest=args.dest)

if __name__ == '__main__':
    main()
