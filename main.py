import os
import flet as ft
from common import download_playlists_meta, parse_urls, config, get_library_path, app_paths
from components.playlist_item import PlaylistItem


def main(page: ft.Page):
    page.title = "Playlist Downloader"
    page.theme_mode = ft.ThemeMode.DARK
    page.horizontal_alignment = ft.CrossAxisAlignment.START

    playlists = ft.ListView(expand=True)

    meta_downloader_output = ft.ListView(expand=True)

    def append_output_to_list(output):
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
                          tooltip="Select music library folder\n Current: " + get_library_path()),
        ],
    )
    refresh_playlists()
    page.update()


ft.app(target=main)
