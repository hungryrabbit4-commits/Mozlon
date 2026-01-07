import flet as ft
import json
import os
import time

# --- НАСТРОЙКИ ПУТЕЙ ---
data_dir = os.getenv("FLET_APP_DATA_DIR", ".")
TRACKS_DB = os.path.join(data_dir, "muzlon_tracks.json")
USERS_DB = os.path.join(data_dir, "muzlon_users.json")
DEFAULT_IMG = "https://cdn-icons-png.flaticon.com/512/461/461238.png"

def main(page: ft.Page):
    # --- БАЗОВЫЕ НАСТРОЙКИ ДЛЯ ANDROID ---
    page.title = "Muzlon"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#050505"
    page.padding = 0
    # Настройка адаптивности
    page.spacing = 0
    
    state = {
        "tracks": [],
        "users": {},
        "current_user": None,
        "is_admin": False,
        "playing_track": None,
        "temp_mp3": None,
        "temp_cover": None,
        "duration": 0,
        "view_stack": []
    }

    # --- РАБОТА С ДАННЫМИ ---
    def load_data():
        try:
            if os.path.exists(TRACKS_DB):
                with open(TRACKS_DB, "r", encoding="utf-8") as f:
                    state["tracks"] = json.load(f)
                    for t in state["tracks"]:
                        if "comments" not in t: t["comments"] = []
                        if "uploader" not in t: t["uploader"] = "admin"

            if os.path.exists(USERS_DB):
                with open(USERS_DB, "r", encoding="utf-8") as f:
                    state["users"] = json.load(f)
                    for u in state["users"].values():
                        if "subscriptions" not in u: u["subscriptions"] = []
            else:
                state["users"] = {}
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            state["tracks"] = []
            state["users"] = {}

    def save_tracks():
        try:
            with open(TRACKS_DB, "w", encoding="utf-8") as f:
                json.dump(state["tracks"], f, ensure_ascii=False, indent=4)
        except: pass

    def save_users():
        try:
            with open(USERS_DB, "w", encoding="utf-8") as f:
                json.dump(state["users"], f, ensure_ascii=False, indent=4)
        except: pass

    load_data()

    # --- АУДИО ---
    def on_duration_changed(e):
        state["duration"] = e.data
        player_slider.max = float(e.data) if e.data else 100
        page.update()

    def on_position_changed(e):
        if not player_slider.disabled: 
            player_slider.value = float(e.data) if e.data else 0
            page.update()

    def on_seek(e):
        audio_player.seek(int(e.control.value))

    audio_player = ft.Audio(
        src="https://luan.xyz/files/audio/ambient_c_motion.mp3", 
        autoplay=False,
        volume=1.0,
        on_duration_changed=on_duration_changed,
        on_position_changed=on_position_changed
    )
    page.overlay.append(audio_player)

    # --- ПАНЕЛЬ ПЛЕЕРА ---
    p_title = ft.Text("Не выбрано", size=14, weight="bold", no_wrap=True)
    p_artist = ft.Text("-", size=12, color="white54")
    p_img = ft.Image(src=DEFAULT_IMG, width=45, height=45, border_radius=8)
    
    player_slider = ft.Slider(
        min=0, max=100, height=20, active_color="cyan", thumb_color="white",
        on_change_end=on_seek
    )

    btn_play_pause = ft.IconButton(ft.icons.PLAY_ARROW_ROUNDED, icon_size=30, icon_color="cyan")

    player_bar = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Row([p_img, ft.Column([p_title, p_artist], spacing=0, width=150)], spacing=10),
                ft.Row([
                    btn_play_pause,
                    ft.IconButton(ft.icons.CLOSE_ROUNDED, icon_size=20, icon_color="white24", 
                                  on_click=lambda _: hide_player())
                ])
            ], alignment="spaceBetween"),
            player_slider
        ], spacing=0),
        bgcolor="#111111",
        padding=10,
        border_radius=ft.border_radius.only(top_left=20, top_right=20),
        visible=False,
    )

    def hide_player():
        audio_player.pause()
        player_bar.visible = False
        page.update()

    def start_track(track):
        state["playing_track"] = track
        audio_player.src = track["path"]
        audio_player.update()
        p_title.value = track["title"]
        p_artist.value = track["artist"]
        p_img.src = track.get("cover") or DEFAULT_IMG
        btn_play_pause.icon = ft.icons.PAUSE_ROUNDED
        player_bar.visible = True
        page.update()
        time.sleep(0.2) # Чуть больше задержка для Android
        audio_player.play()

    def toggle_play_pause(e):
        if btn_play_pause.icon == ft.icons.PAUSE_ROUNDED:
            audio_player.pause()
            btn_play_pause.icon = ft.icons.PLAY_ARROW_ROUNDED
        else:
            audio_player.resume()
            btn_play_pause.icon = ft.icons.PAUSE_ROUNDED
        page.update()

    btn_play_pause.on_click = toggle_play_pause

    # Основной контейнер (Важно для Android!)
    app_content = ft.Column(expand=True, spacing=0)

    # --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ UI ---
    def show_comments_sheet(track):
        bs_comments = ft.Column(scroll="auto", expand=True)
        txt_comment = ft.TextField(hint_text="Текст...", border_radius=20, expand=True)
        
        def refresh_comments():
            bs_comments.controls.clear()
            if "comments" in track:
                for com in track["comments"]:
                    bs_comments.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"{com['user']} ({com['date']})", size=10, color="cyan"),
                                ft.Text(com['text'], size=14)
                            ]),
                            bgcolor="#222", padding=10, border_radius=10, margin=ft.margin.only(bottom=5)
                        )
                    )
            page.update()

        def send_comment(e):
            if txt_comment.value:
                new_com = {"user": state["current_user"], "text": txt_comment.value, "date": time.strftime("%H:%M %d.%m")}
                if "comments" not in track: track["comments"] = []
                track["comments"].append(new_com)
                save_tracks()
                txt_comment.value = ""
                refresh_comments()

        refresh_comments()
        sheet_content = ft.Container(
            content=ft.Column([
                ft.Text(f"Комментарии", weight="bold", size=18),
                ft.Container(bs_comments, expand=True),
                ft.Row([txt_comment, ft.IconButton(ft.icons.SEND, icon_color="cyan", on_click=send_comment)])
            ]),
            padding=20, bgcolor="#151515", height=400
        )
        page.bottom_sheet = ft.BottomSheet(sheet_content)
        page.bottom_sheet.open = True
        page.update()

    # --- ЭКРАНЫ ---
    def show_auth_screen():
        app_content.controls.clear()
        player_bar.visible = False
        page.client_storage.remove("last_user")

        login_in = ft.TextField(label="Никнейм", border_color="cyan", border_radius=15)
        pass_in = ft.TextField(label="Пароль", password=True, border_color="cyan", border_radius=15)

        def login_logic(e):
            u, p = login_in.value.strip(), pass_in.value.strip()
            if u in state["users"] and state["users"][u]["pass"] == p:
                state["current_user"] = u
                state["is_admin"] = (u.lower() == "admin")
                page.client_storage.set("last_user", u)
                show_main_app()
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Ошибка данных"))
                page.snack_bar.open = True
                page.update()

        def reg_logic(e):
            u, p = login_in.value.strip(), pass_in.value.strip()
            if u and p:
                if u in state["users"]:
                    page.snack_bar = ft.SnackBar(ft.Text("Занято"))
                else:
                    state["users"][u] = {"pass": p, "favs": [], "subscriptions": [], "reg_date": "07.01.2026", "avatar": None}
                    save_users()
                    page.snack_bar = ft.SnackBar(ft.Text("Создано! Войдите."))
                page.snack_bar.open = True
                page.update()

        app_content.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.HEADPHONES_ROUNDED, size=60, color="cyan"),
                    ft.Text("MUZLON", size=40, weight="bold", color="cyan"),
                    login_in, pass_in,
                    ft.ElevatedButton("ВОЙТИ", on_click=login_logic, bgcolor="cyan", color="black", width=250),
                    ft.TextButton("РЕГИСТРАЦИЯ", on_click=reg_logic)
                ], horizontal_alignment="center", alignment="center"),
                expand=True, padding=40
            )
        )
        page.update()

    def show_user_profile(username):
        user_data = state["users"].get(username)
        if not user_data: return
        app_content.controls.clear()
        
        curr = state["current_user"]
        is_subscribed = username in state["users"][curr]["subscriptions"]
        
        def subscribe_action(e):
            if username in state["users"][curr]["subscriptions"]:
                state["users"][curr]["subscriptions"].remove(username)
                e.control.text = "ПОДПИСАТЬСЯ"
                e.control.bgcolor = "cyan"
            else:
                state["users"][curr]["subscriptions"].append(username)
                e.control.text = "ВЫ ПОДПИСАНЫ"
                e.control.bgcolor = "grey"
            save_users()
            page.update()

        tracks_col = ft.Column(spacing=10, scroll="auto", expand=True)
        user_tracks = [t for t in state["tracks"] if t.get("uploader") == username]
        for t in user_tracks:
            tracks_col.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.MUSIC_NOTE, color="cyan"),
                        ft.Column([ft.Text(t["title"], weight="bold"), ft.Text(t["artist"], size=12, color="grey")], expand=True),
                        ft.IconButton(ft.icons.PLAY_ARROW, on_click=lambda _, trk=t: start_track(trk))
                    ]),
                    bgcolor="#1a1a1a", padding=10, border_radius=10
                )
            )

        app_content.controls.append(
            ft.Column([
                ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: show_main_app()),
                ft.Container(
                    content=ft.Column([
                        ft.CircleAvatar(radius=40, foreground_image_src=user_data.get("avatar")),
                        ft.Text(username, size=24, weight="bold"),
                        ft.ElevatedButton("ПОДПИСАТЬСЯ" if not is_subscribed else "ВЫ ПОДПИСАНЫ", 
                                         on_click=subscribe_action, visible=(username != curr))
                    ], horizontal_alignment="center"), alignment=ft.alignment.center
                ),
                ft.Text("Треки пользователя:", color="grey", size=12),
                tracks_col
            ], expand=True, padding=10)
        )
        page.update()

    def show_main_app():
        app_content.controls.clear()
        
        home_list = ft.Column(scroll="auto", expand=True, spacing=10)
        fav_list = ft.Column(scroll="auto", expand=True, spacing=10)
        
        def create_card(t):
            u = state["current_user"]
            liked = t["path"] in state["users"][u]["favs"]
            uploader = t.get("uploader", "admin")
            uploader_avatar = state["users"].get(uploader, {}).get("avatar")
            
            return ft.Container(
                content=ft.Row([
                    ft.Image(src=t.get("cover") or DEFAULT_IMG, width=50, height=50, border_radius=8),
                    ft.Column([
                        ft.Text(t["title"], weight="bold", size=14, no_wrap=True),
                        ft.Row([
                            ft.Container(ft.CircleAvatar(radius=10, foreground_image_src=uploader_avatar), 
                                         on_click=lambda _: show_user_profile(uploader)),
                            ft.Text(t["artist"], size=11, color="white54")
                        ], spacing=5)
                    ], expand=True),
                    ft.IconButton(ft.icons.CHAT_BUBBLE_OUTLINE, icon_size=18, on_click=lambda _: show_comments_sheet(t)),
                    ft.IconButton(ft.icons.FAVORITE if liked else ft.icons.FAVORITE_BORDER, 
                                  icon_color="red" if liked else "white24", 
                                  on_click=lambda e: toggle_like(e, t))
                ]),
                bgcolor="#121212", padding=8, border_radius=12, on_click=lambda _, trk=t: start_track(trk)
            )

        def toggle_like(e, track):
            u = state["current_user"]
            if track["path"] in state["users"][u]["favs"]:
                state["users"][u]["favs"].remove(track["path"])
            else:
                state["users"][u]["favs"].append(track["path"])
            save_users()
            refresh_ui()

        def refresh_ui():
            home_list.controls.clear()
            fav_list.controls.clear()
            for t in state["tracks"]:
                home_list.controls.append(create_card(t))
                if t["path"] in state["users"][state["current_user"]]["favs"]:
                    fav_list.controls.append(create_card(t))
            page.update()

        # Вид профиля
        my_avatar = ft.CircleAvatar(radius=50, bgcolor="cyan")
        def pick_avatar(_): fp_avatar.pick_files()
        
        u_data = state["users"][state["current_user"]]
        my_avatar.foreground_image_src = u_data.get("avatar")

        profile_view = ft.Column([
            ft.Container(my_avatar, on_click=pick_avatar, alignment=ft.alignment.center, padding=20),
            ft.Text(state["current_user"], size=24, weight="bold", text_align="center", width=400),
            ft.Row([
                ft.Column([ft.Text("Лайков"), ft.Text(str(len(u_data['favs'])), weight="bold")], horizontal_alignment="center"),
                ft.Column([ft.Text("Треков"), ft.Text(str(len(state['tracks'])), weight="bold")], horizontal_alignment="center"),
            ], alignment="spaceAround"),
            ft.Container(ft.ElevatedButton("ВЫЙТИ", on_click=lambda _: show_auth_screen(), color="red"), alignment=ft.alignment.center, padding=20)
        ], scroll="auto")

        # Админка
        in_title = ft.TextField(label="Название")
        in_artist = ft.TextField(label="Артист")
        def publish(_):
            if in_title.value and state["temp_mp3"]:
                state["tracks"].append({
                    "title": in_title.value, "artist": in_artist.value,
                    "path": state["temp_mp3"], "cover": state["temp_cover"],
                    "comments": [], "uploader": state["current_user"]
                })
                save_tracks()
                show_main_app()

        admin_view = ft.Column([
            in_title, in_artist,
            ft.ElevatedButton("Файл MP3", on_click=lambda _: fp_mp3.pick_files()),
            ft.ElevatedButton("Обложка", on_click=lambda _: fp_cover.pick_files()),
            ft.ElevatedButton("ОПУБЛИКОВАТЬ", on_click=publish, bgcolor="cyan", color="black")
        ], padding=20, scroll="auto")

        tabs = ft.Tabs(
            selected_index=0, expand=True,
            tabs=[
                ft.Tab(text="Обзор", content=home_list),
                ft.Tab(text="Лайки", content=fav_list),
                ft.Tab(text="Профиль", content=profile_view),
            ]
        )
        if state["is_admin"]:
            tabs.tabs.append(ft.Tab(text="Загрузка", content=admin_view))

        app_content.controls.append(tabs)
        refresh_ui()

    # --- PICKERS ---
    def on_mp3_result(e: ft.FilePickerResultEvent):
        if e.files: state["temp_mp3"] = e.files[0].path
    def on_cover_result(e: ft.FilePickerResultEvent):
        if e.files: state["temp_cover"] = e.files[0].path
    def on_avatar_result(e: ft.FilePickerResultEvent):
        if e.files:
            state["users"][state["current_user"]]["avatar"] = e.files[0].path
            save_users()
            show_main_app()

    fp_mp3 = ft.FilePicker(on_result=on_mp3_result)
    fp_cover = ft.FilePicker(on_result=on_cover_result)
    fp_avatar = ft.FilePicker(on_result=on_avatar_result)
    page.overlay.extend([fp_mp3, fp_cover, fp_avatar])

    # --- СТАРТ ПРИЛОЖЕНИЯ ---
    # Оборачиваем всё в контейнер с фиксированной высотой (через expand)
    main_container = ft.Column([
        ft.Container(app_content, expand=True),
        player_bar
    ], expand=True, spacing=0)

    page.add(main_container)
    
    # Авто-вход
    last_user = page.client_storage.get("last_user")
    if last_user and last_user in state["users"]:
        state["current_user"] = last_user
        state["is_admin"] = (last_user.lower() == "admin")
        show_main_app()
    else:
        show_auth_screen()
    
    page.update()

ft.app(target=main)
