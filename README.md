6⃣️6⃣️6⃣️

```
pip3 install git+https://github.com/dlran/ffd.git
```

```
ffd -h
usage: ffd [options...] [args] url

hls segment downloader

positional arguments:
  url                   file/hls url

optional arguments:
  -h, --help            show this help message and exit
  -t THREADS, --threads THREADS
                        max workers threads
  -d DEST, --dest DEST  output destination
  -o OUTPUT, --output OUTPUT
                        output file name
  -v, --version         show program's version number and exit
  -f, --force           force override

```

```
ffd "https://devstreaming-cdn.apple.com/videos/wwdc/2019/502gzyuhh8p2r8g8/502/hls_vod_mvp.m3u8"
```
