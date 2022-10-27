# Ghostseeder

This Python script spoofs seeding of torrent files to private trackers
by sending fake announces. 

Private trackers often reward bonus points for seeding large torrents 
with few seeders. But trackers don't have a direct way to verify you 
actually have the files except for possibly indirectly measuring
self-reported upload/download rates from other peers on the same torrent.

But if you seed torrents that are unlikely to ever be snatched (e.g. those very 
same large torrents with few seeders!), there would be little 
evidence that you are spoofing

## Requirements

Tested with Python v3.8+
* [aiohttp](https://github.com/aio-libs/aiohttp) - A library for sending http requests
* [pyben](https://github.com/alexpdev/pyben) -  Bencoding library for reading torrent files

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

Run this on your server/seedbox/long-running pc:

```
$ nohup python ghostseeder.py -f torrents/ &>> output.log &
```

This will keep the script running in the background and stores logs in `output.log`

* `-f`, `--folder` your directory containing `.torrent` files
* `-p`, `--port` the port number announced to the tracker to receive incoming connections. Used if you want to change the port number announced to the tracker. Optional, defaults to `6881`
* `-s`, `--sleepextra` Added time to wait (seconds) in between announces if you want to send less frequent announces. Optional, defaults to `0`


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
2022-10-27 12:34:23 INFO     Tracker announces will use the following settings: (port=59097, peer_id='-qB4450-NgMhgWdDpKul', sleep_extra=0s)
2022-10-27 12:34:26 INFO     Announcing ubuntu-22.10-desktop-amd64.iso to https://torrent.ubuntu.com/announce?info_hash=%99%C8%2B%B75%05%A3%C0%B4S%F9%FA%0E%88%1DnZ2%A0%C1&peer_id=-qB4450-NgMhgWdDpKul&uploaded=0&downloaded=0&left=0&compact=1&port=6881
2022-10-27 12:34:26 INFO     Re-announcing ubuntu-22.10-desktop-amd64.iso in 1800 seconds...
...
```

## Explanation of Bittorrent Protocol

The HTTP protocol between trackers and peers is explained [here](https://wiki.theory.org/BitTorrentSpecification#Tracker_HTTP.2FHTTPS_Protocol) 

Every private torrent has an announce url to the tracker containing your unique passkey (e.g. `https://flacsfor.me/hu23mb2ik2vmetji37ss9t0awe3dlyqs/announce`). When your torrent client begins seeding a torrent, it uses this url to send parameters describing the current state of the torrent (including how much you've downloaded and uploaded). **All information about the torrent is self-reported by the client and the tracker does not have an explicit way to verify that information.**

The key request parameters are `info_hash` and `left`. `info_hash` identifies the specific torrent and `left` states how many bytes needed to finish downloading the torrent. **Setting `left=0` announces to the tracker that you are actively seeding the torrent**:
```
GET https://flacsfor.me/hu23mb2ik2vmetji37ss9t0awe3dlyqs/announce?info_hash=%D5E%DB%06v%15D%8CLx%21%3B%C5v%1DNf%8E%1B4&peer_id=-qB4450-IdEkAzfIlnfw&uploaded=0&downloaded=0&left=0&compact=1&port=6881
```

The server will respond with statistics about the torrent:

```
{
   "complete":24,
   "downloaded":103,
   "incomplete":1,
   "interval":1824,
   "min interval":1800,
   "peers":[
      "46.232.211.245:52482",
      "70.179.102.222:65479",
      "23.93.184.25:8001",
      ...
   ]
}
```
And `interval` is the time in seconds the client should wait to re-announce again to keep seeding
