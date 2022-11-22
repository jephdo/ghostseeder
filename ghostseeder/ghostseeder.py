"""This Python script spoofs seeding of torrent files to private trackers
by sending fake announces. 

Trackers often reward bonus points for seeding large torrents 
with few seeders. But trackers don't have a direct way to verify you 
actually have the files except for possibly indirectly measuring
self-reported upload/download rates from other peers on the same torrent.

But if you seed torrents that are unlikely to ever be snatched (e.g. those very 
same large torrents with few seeders!), there would be little indirect 
evidence that you are spoofing
"""
import hashlib
import os
import logging
import time
import random
import argparse
import string

from urllib.parse import urlencode

import asyncio
import aiohttp
import yarl
import pyben

DEBUG = False
DEFAULT_SLEEP_INTERVAL = 3600  # 3600 seconds = 1 hour

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.DEBUG if DEBUG else logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def load_torrents(path: str) -> ["Torrent"]:
    """Recursively find and parse through all torrent files in a directory

    path: folder containing torrent files
    """
    logging.info(f"Searching for torrent files located under '{path}'")

    torrents = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".torrent"):
                filepath = os.path.join(root, file)

                logging.info(f"Found {filepath}")
                torrents.append(filepath)

    logging.info(f"Found {len(torrents)} torrent files")
    logging.info("Reading and parsing torrent files...")

    return [Torrent(file) for file in torrents]


def generate_peer_id(
    client: str = "qB", major: int = 4, minor: int = 4, patch: int = 5
) -> str:
    """Generates a unique string that identifies your torrent client to the
    tracker. Uses the "Azureus-style" convention. For more information
    see https://wiki.theory.org/BitTorrentSpecification#peer_id
    """

    assert len(client) == 2 and major < 16 and minor < 16 and patch < 16

    # The patch number is represented as hexadecimal and can go up to version x.y.15
    # See: https://github.com/qbittorrent/qBittorrent/wiki/Frequently-Asked-Questions#What_is_qBittorrent_Peer_ID
    hexmap = {10: "A", 11: "B", 12: "C", 13: "D", 14: "E", 15: "F"}
    patch = str(hexmap.get(patch, patch))

    client_version = f"-{client}{major}{minor}{patch}0-"
    random_hash = "".join(
        random.choices(string.ascii_uppercase + string.ascii_lowercase, k=12)
    )

    peer_id = client_version + random_hash
    assert len(peer_id) == 20

    logging.info(f"Generating torrent client peer id: {peer_id}")
    return peer_id


def generate_useragent(peer_id: str) -> str:
    # https://wiki.theory.org/BitTorrentSpecification#peer_id
    client_map = {
        "qB": "qBittorrent",
        "DE": "Deluge",
    }
    str_ = peer_id.split("-")[1]
    client_id = str_[:2]
    major = int(str_[2])
    minor = int(str_[3])
    patch = int(str_[4])
    client = client_map[client_id]

    return f"{client}/{major}.{minor}.{patch}"


class Torrent:
    def __init__(self, filepath: str):
        self.filepath = filepath
        torrent = pyben.load(filepath)
        info = torrent["info"]
        self.tracker_url = torrent["announce"]
        self.infohash = hashlib.sha1(pyben.benencode(info)).hexdigest()
        self.name = info["name"]

    @property
    def magnet_link(self):
        return f"magnet:?xt=urn:btih:{self.infohash}"

    async def announce(
        self,
        session: aiohttp.ClientSession,
        peer_id: str,
        port: int,
        uploaded: int = 0,
        downloaded: int = 0,
        left: int = 0,
        compact: int = 1,
        event: str = None,
    ) -> bytes:

        headers = {"User-Agent": generate_useragent(peer_id)}

        params = {
            "info_hash": bytes.fromhex(self.infohash),
            "peer_id": peer_id,
            "uploaded": uploaded,
            "downloaded": downloaded,
            "left": left,
            "compact": compact,
            "port": port,
        }

        if event is not None:
            assert event in ("started", "stopped", "completed")
            params["event"] = event

        url = yarl.URL(self.tracker_url + "?" + urlencode(params), encoded=True)

        logging.info(f"Announcing {self.name} to {url}")

        async with session.get(url, headers=headers) as response:
            response_bytes = await response.read()

            logging.debug(
                f"For {self.name} announcement, server returned response:\n\n {response_bytes}"
            )

        return response_bytes


def parse_interval(response_bytes: bytes, torrent: Torrent) -> int:
    try:
        data, _ = pyben.bendecode(response_bytes)
    except pyben.DecodeError:
        logging.warning(
            f"Unable to parse server response for {torrent.name}:\n\n{response_bytes}"
        )
        sleep = DEFAULT_SLEEP_INTERVAL
    else:
        sleep = data["interval"]

    return sleep


async def announce_forever(
    session: aiohttp.ClientSession,
    torrent: Torrent,
    peer_id: int,
    port: int,
    initial_wait: int = None,
) -> None:
    # Don't want to send out a ton of requests simultaneously at first start up
    # Add a random amount of sleep time on the first announce to space out torrents
    if initial_wait is not None:
        assert initial_wait > 0
        await asyncio.sleep(random.randint(1, 5 * (initial_wait + 1)))

    count = 1
    while True:
        event = "started" if count == 1 else None
        try:
            response_bytes = await torrent.announce(session, peer_id, port, event=event)
        except aiohttp.ClientError as exc:
            logging.warning(
                f"Unable to complete request for {torrent.name} exception occurred: {exc}"
            )
            response_bytes = None
            sleep = DEFAULT_SLEEP_INTERVAL
        else:
            # Re-announce again at the given time provided by tracker
            sleep = parse_interval(response_bytes, torrent)
        count += 1

        logging.info(f"Re-announcing (#{count}) {torrent.name} in {sleep} seconds...")

        await asyncio.sleep(sleep)


async def ghostseed(filepath: str, port: int) -> None:
    peer_id = generate_peer_id()
    useragent = generate_useragent(peer_id)

    torrents = load_torrents(filepath)
    logging.info("Finished reading in torrent files")
    n = len(torrents)

    logging.info(
        f"Tracker announces will use the following settings: (port={port}, peer_id='{peer_id}', user-agent='{useragent}')"
    )

    async with aiohttp.ClientSession() as session:
        announces = []
        for torrent in torrents:
            announces.append(
                announce_forever(
                    session,
                    torrent,
                    peer_id,
                    port,
                    initial_wait=n,
                )
            )

        await asyncio.gather(*announces)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enter path to directory of torrent files"
    )
    parser.add_argument("-f", "--folder", type=str, required=True)
    parser.add_argument("-p", "--port", nargs="?", type=int, const=1, default=6881)
    args = parser.parse_args()

    asyncio.run(ghostseed(args.folder, args.port))
