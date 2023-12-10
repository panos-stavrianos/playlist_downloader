import hashlib
import json
import os

import subprocess

from appdata import AppDataPaths
from configobj import ConfigObj

app_paths = AppDataPaths("playlist_downloader")
app_paths.setup()

config = ConfigObj(app_paths.config_path, )

# create dir if not exists
if not os.path.exists(f"{app_paths.app_data_path}/library"):
    os.makedirs(f"{app_paths.app_data_path}/library")


def parse_urls(text):
    text = text.replace("\n", ",")
    text = text.replace(" ", "")
    urls = text.split(",")
    urls = list(filter(None, urls))
    for i, url in enumerate(urls):
        if "www.youtube.com" in url:
            urls[i] = url.replace("www.youtube.com", "music.youtube.com")
    return urls


def get_library_path():
    return config.get("library", f"{app_paths.app_data_path}/library")


def download_playlists_meta(urls, append_output):
    for url in urls:
        hash_url = hashlib.md5(url.encode()).hexdigest()
        process = subprocess.Popen(
            ['spotdl', 'save', url, '--save-file', f"{app_paths.app_data_path}/{hash_url}.spotdl"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                append_output(output.strip().decode("utf-8"))


def download_playlists_songs(playlist_files, append_output):
    for playlist_file in playlist_files:
        data = json.load(open(f"{app_paths.app_data_path}/{playlist_file}"))
        print(data)
        if not data:
            continue

        url = data[0]["list_url"]
        output_pattern = get_library_path() + "/{list-name}/{artist} - {title}.{output-ext}"
        print(output_pattern)
        print(" ".join(['spotdl', '"' + url + '"', '--output', '"' + output_pattern + '"']))
        process = subprocess.Popen(
            ['spotdl', url, '--output', output_pattern],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                append_output(output.strip().decode("utf-8"))
