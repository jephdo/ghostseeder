# Ghostseeder

This Python script spoofs seeding of torrent files to private trackers
by sending fake announces. 

Private trackers usually reward bonus points for seeding a lot of torrents. But 
at the same time, trackers don't have an explicit way to verify you actually have the files

## Requirements

Tested with Python v3.8+
* [aiohttp](https://github.com/aio-libs/aiohttp) - A library for sending http requests
* [pyben](https://github.com/alexpdev/pyben) -  Bencoding library for reading torrent files
  
Script will announce itself as a qBittorrent client

## Example Usage
Add torrents to a folder:
```
$ tree torrents/
torrents/
├── Top.Gun.Maverick.2022.1080p.WEB-DL.H264.AAC-EVO.torrent
├── lord-of-the-rings
│      ├── The.Lord.of.the.Rings.The.Rings.of.Power.S01E06.Udun.1080p.AMZN.WEBRip.DDP5.1.x264-NTb.torrent
│      ├── The.Lord.of.the.Rings.The.Rings.of.Power.S01E07.The.Eye.1080p.AMZN.WEBRip.DDP5.1.x264-NTb.torrent
│      └── The.Lord.of.the.Rings.The.Rings.of.Power.S01E08.Alloyed.1080p.AMZN.WEBRip.DDP5.1.x264-NTb.torrent
└── ubuntu-22.10-desktop-amd64.iso.torrent

1 directory, 5 files
```

The script will search for all `.torrent` files in the folder passed to it. Run this on your server/seedbox:

```
$ nohup python ghostseeder/ghostseeder.py -f torrents/ &>> output.log &
```

This will keep the script running in the background and store logs in `output.log`

* `-f`, `--folder` your directory containing `.torrent` files
* `-p`, `--port` the port number announced to the tracker to receive incoming connections. Used if you want to change the port number announced to the tracker. Optional, defaults to `6881`
* `-v`, `--version` the version of qBittorrent that you want to announce to the tracker. This info is used to generate the peer id and user agent string. Setting `-v '4.3.9'` will use qBittorrent v4.3.9. Optional, defaults to  `'4.4.5'`


**Example output**
```
$ python ghostseeder.py -f torrents/ -p 59097
2022-10-27 12:34:23 INFO     Generating torrent client peer id: -qB4450-NgMhgWdDpKul
2022-10-27 12:34:23 INFO     Searching for torrent files located under 'torrents/'
2022-10-27 12:34:23 INFO     Found torrents/ubuntu-22.10-desktop-amd64.iso.torrent
2022-10-27 12:34:23 INFO     Found torrents/Top.Gun.Maverick.2022.1080p.WEB-DL.H264.AAC-EVO.torrent
2022-10-27 12:34:23 INFO     Found torrents/lord-of-the-rings/The.Lord.of.the.Rings.The.Rings.of.Power.S01E08.Alloyed.1080p.AMZN.WEBRip.DDP5.1.x264-NTb.torrent
2022-10-27 12:34:23 INFO     Found torrents/lord-of-the-rings/The.Lord.of.the.Rings.The.Rings.of.Power.S01E07.The.Eye.1080p.AMZN.WEBRip.DDP5.1.x264-NTb.torrent
2022-10-27 12:34:23 INFO     Found torrents/lord-of-the-rings/The.Lord.of.the.Rings.The.Rings.of.Power.S01E06.Udun.1080p.AMZN.WEBRip.DDP5.1.x264-NTb.torrent
2022-10-27 12:34:23 INFO     Found 5 torrent files
2022-10-27 12:34:23 INFO     Loading torrent files into memory
2022-10-27 12:34:23 INFO     Tracker announces will use the following settings: (port=59097, peer_id='-qB4450-NgMhgWdDpKul')
2022-10-27 12:34:26 INFO     Announcing ubuntu-22.10-desktop-amd64.iso to https://torrent.ubuntu.com/announce?info_hash=%99%C8%2B%B75%05%A3%C0%B4S%F9%FA%0E%88%1DnZ2%A0%C1&peer_id=-qB4450-NgMhgWdDpKul&uploaded=0&downloaded=0&left=0&compact=1&port=6881
2022-10-27 12:34:26 INFO     Re-announcing ubuntu-22.10-desktop-amd64.iso in 1800 seconds...
...
```

## Details of this script

Every private torrent has an announce url to the tracker containing a unique passkey (e.g. `https://flacsfor.me/123456789abcdefg37ss9t0awe3dlyqs/announce`). When a torrent client begins seeding a torrent, it uses this url to send parameters describing the current state of the torrent (including how much has been downloaded and uploaded). All information about the torrent is self-reported by the client.

Key request parameters to modify are `info_hash` and `left`. `info_hash` identifies the specific torrent and `left` states how many bytes needed to finish downloading the torrent. This script repeatedly sends HTTP requests to the tracker, setting `left=0`, declaring to the tracker that you are actively seeding the torrent:
```
GET https://flacsfor.me/123456789abcdefg37ss9t0awe3dlyqs/announce?info_hash=%D5E%DB%06v%15D%8CLx%21%3B%C5v%1DNf%8E%1B4&peer_id=-qB4450-IdEkAzfIlnfw&uploaded=0&downloaded=0&left=0&compact=1&port=6881
```

More details on the HTTP protocol between trackers and peers[here](https://wiki.theory.org/BitTorrentSpecification#Tracker_HTTP.2FHTTPS_Protocol) 
