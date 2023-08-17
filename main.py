import hashlib
import json
import os
import random
import subprocess
import webbrowser

import flet as ft
from appdata import AppDataPaths
from configobj import ConfigObj
from humanfriendly import format_timespan


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


class PlaylistItem(ft.UserControl):
    def __init__(self, page, refresh, playlist_file):
        super().__init__()
        self.page = page
        self.refresh = refresh
        self.playlist_file = playlist_file
        self.data = json.load(open(f"{app_paths.app_data_path}/{playlist_file}"))
        self.container = ft.Container(bgcolor=ft.colors.BLACK12, padding=10, margin=10)

        self.output = ft.ListView(expand=True, width=1000)
        self.dlg_output = ft.AlertDialog(
            modal=True,
            title=ft.Text("Progress"),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[self.output]), )

        if self.data:
            self.name = self.data[0]["list_name"]
            self.url = self.data[0]["list_url"]
            self.tracks = self.data[0]["list_length"]
            self.remove_btn = ft.IconButton(ft.icons.DELETE, on_click=self.remove, tooltip="Remove playlist")
            self.sync_btn = ft.IconButton(ft.icons.SYNC, on_click=self.sync_playlist, tooltip="Sync playlist")
            self.download_btn = ft.IconButton(ft.icons.DOWNLOAD, on_click=self.download, tooltip="Download playlist")
            self.duration = self.find_playlist_duration()
            self.cover = self.generate_cover()

    def close_output_dialog(self, e):
        self.dlg_output.open = False
        self.page.update()

    def append_output_to_list(self, output):
        self.output.controls.append(ft.Text(output, font_family="monospace"))
        self.output.scroll_to(offset=-1, duration=1000)
        self.page.update()

    def open_output_dialog(self, e):
        self.page.dialog = self.dlg_output
        self.dlg_output.open = True
        self.page.update()

    def sync_playlist(self, e):
        self.open_output_dialog(None)
        self.dlg_output.disabled = True
        self.page.update()

        download_playlists_meta([self.url], self.append_output_to_list)
        self.dlg_output.disabled = False
        self.page.update()
        self.close_output_dialog(None)
        self.refresh()

    def download(self, e):
        self.open_output_dialog(None)
        self.dlg_output.disabled = True
        download_playlists_songs([self.playlist_file], self.append_output_to_list)
        self.dlg_output.disabled = False
        self.page.update()
        self.close_output_dialog(None)

        self.refresh()

    def find_playlist_duration(self):
        duration = 0

        for track in self.data:
            duration += track["duration"]
        if "spotify" in self.url:
            return format_timespan(int(duration/1000))
        return format_timespan(duration)

    def generate_cover(self):
        covers = min(4, len(self.data))
        covers = random.sample(range(0, len(self.data)), covers)
        images_urls = list(map(lambda i: self.data[i]["cover_url"], covers))
        cover_size = 150
        cover = ft.GridView(
            expand=0,
            width=cover_size,
            height=cover_size,
            runs_count=2,
            max_extent=int(cover_size / 2),
            child_aspect_ratio=1.0,
            spacing=0,
            run_spacing=0,
            controls=list(
                map(lambda url: ft.Image(src=url, width=int(cover_size / 2), height=int(cover_size / 2)), images_urls))
        )
        return cover

    def remove(self, e):
        os.remove(f"{app_paths.app_data_path}/{self.playlist_file}")
        self.refresh()

    def build(self):
        self.container.content = ft.Row(
            controls=[
                ft.Column(
                    controls=[self.cover]
                ),
                ft.Column(
                    controls=[
                        ft.Text(self.name, size=20),
                        ft.Text(f"{self.tracks} tracks", font_family="monospace"),
                        ft.Text(self.duration, font_family="monospace"),
                        ft.Row(controls=[
                            self.remove_btn,
                            self.sync_btn,
                            self.download_btn,
                            ft.IconButton(ft.icons.OPEN_IN_NEW, tooltip="Open in browser",
                                          on_click=lambda e: webbrowser.open(self.url))], )
                    ]
                )
            ]
        )
        return self.container


def main(page: ft.Page):
    page.title = "Playlist Downloader"
    page.theme_mode = ft.ThemeMode.DARK
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    playlists = ft.ListView(expand=True)

    meta_downloader_output = ft.ListView(expand=True)

    def append_output_to_list(output):
        print("--->", output)

        meta_downloader_output.controls.append(ft.Text(output, font_family="monospace"))
        meta_downloader_output.scroll_to(offset=-1, duration=1000)

        page.update()

    def refresh_playlists():
        playlists.controls = []
        # get all files in data folder
        for file in os.listdir(app_paths.app_data_path):
            if file.endswith(".spotdl"):
                playlist_item = PlaylistItem(page, refresh_playlists, file)
                playlists.controls.append(playlist_item)
        playlists.update()

    def add_playlists(e):
        dlg_add_playlists.disabled = True
        page.update()
        new_urls = parse_urls(urls_input.value)
        urls_input.value = ""

        download_playlists_meta(new_urls, append_output_to_list)
        meta_downloader_output.controls = []
        refresh_playlists()
        dlg_add_playlists.disabled = False

        close_dlg(e)

    def close_dlg(e):
        dlg_add_playlists.open = False
        page.update()

    def open_dlg_modal(e):
        page.dialog = dlg_add_playlists
        dlg_add_playlists.open = True
        page.update()

    def on_select_library_result(e: ft.FilePickerResultEvent):
        config["library"] = e.path
        config.write()

    file_picker = ft.FilePicker(on_result=on_select_library_result)
    page.overlay.append(file_picker)

    urls_input = ft.TextField(multiline=True)
    dlg_add_playlists = ft.AlertDialog(
        modal=True,
        title=ft.Text("Paste your playlists here"),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("for multiple playlists, separate them with a comma or a new line"),
                urls_input,
                meta_downloader_output
            ], )
        ,
        actions=[
            ft.TextButton("Add", on_click=add_playlists),
            ft.TextButton("Cancel", on_click=close_dlg),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=lambda e: print("Modal dialog dismissed!"),
    )

    page.add(playlists)

    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.icons.MUSIC_NOTE),
        leading_width=40,
        title=ft.Text("Playlist Downloader"),
        center_title=False,
        bgcolor=ft.colors.SURFACE_VARIANT,
        actions=[
            ft.IconButton(ft.icons.ADD, on_click=open_dlg_modal, tooltip="Add playlists"),
            ft.IconButton(ft.icons.FOLDER, on_click=lambda e: file_picker.get_directory_path(),
                          tooltip="Select music library folder"),
        ],
    )
    refresh_playlists()
    page.update()


app_paths = AppDataPaths("playlist_downloader")
app_paths.setup()

config = ConfigObj(app_paths.config_path, )

# create dir if not exists
if not os.path.exists(f"{app_paths.app_data_path}/library"):
    os.makedirs(f"{app_paths.app_data_path}/library")

ft.app(target=main)
