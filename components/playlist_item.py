import json
import os
import random
import webbrowser
import flet as ft
from flet_timer.flet_timer import Timer
from humanfriendly import format_timespan
from rich import print  # noqa
from common import app_paths, download_playlists_meta, download_playlists_songs, get_library_path
from tinytag import TinyTag


class PlaylistItem(ft.UserControl):
    def __init__(self, page, refresh, playlist_file):
        super().__init__()
        self.page = page
        self.refresh = refresh
        self.timer = Timer(name="timer", interval_s=5, callback=self.tick)
        self.playlist_file = playlist_file
        self.data = json.load(open(f"{app_paths.app_data_path}/{playlist_file}"))
        self.container = ft.Container(bgcolor=ft.colors.BLACK12, padding=10, margin=10)

        self.missing_tracks = []
        self.missing_header = ft.Text("Missing tracks", size=20)
        self.missing_tracks_list_view = ft.ListView(expand=False, height=120)

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
            return format_timespan(int(duration / 1000))
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

    def tick(self):
        print("refreshing", self.playlist_file)
        with open(f"{app_paths.app_data_path}/{self.playlist_file}") as f:
            spotdl = json.load(f)
        spotdl = [f"{track['artist']} - {track['name']}.mp3" for track in spotdl]
        # read all tracks in the folder
        files = os.listdir(f"{get_library_path()}/{self.name}")
        # remove all tracks that are already downloaded
        files = list(set(spotdl) - set(files))
        self.missing_tracks = files
        self.update_missing_tracks()
        self.update()

    def update_missing_tracks(self):

        if len(self.missing_tracks) == 0:
            print("all tracks downloaded")
            self.missing_header.value = "All tracks downloaded"
            self.missing_header.color = ft.colors.GREEN
            return
        if len(self.missing_tracks) == 1:
            self.missing_header.value = f"{len(self.missing_tracks)} missing track"
        else:
            self.missing_header.value = f"{len(self.missing_tracks)} missing tracks"
        self.missing_header.color = ft.colors.RED
        self.missing_tracks_list_view.controls = []
        for track in self.missing_tracks:
            self.missing_tracks_list_view.controls.append(ft.Text(track, font_family="monospace"))
        self.missing_tracks_list_view.update()

    def remove(self, e):
        os.remove(f"{app_paths.app_data_path}/{self.playlist_file}")
        self.refresh()

    def build(self):

        self.container.content = ft.Row(
            controls=[
                self.timer,

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
                                          on_click=lambda e: webbrowser.open(self.url))], ),
                    ]
                ),
                ft.Container(
                    content=ft.Column(

                        controls=[self.missing_header, self.missing_tracks_list_view],
                    ),
                    padding=10,
                )
            ]
        )
        return self.container
