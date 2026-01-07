import flet as ft
import json
import os
import time

# --- НАСТРОЙКИ ПУТЕЙ ---
# Для Android важно использовать правильные пути
data_dir = os.getenv("FLET_APP_DATA_DIR", ".")
TRACKS_DB = os.path.join(data_dir, "muzlon_tracks.json")
USERS_DB = os.path.join(data_dir, "muzlon_users.json")
DEFAULT_IMG = "https://cdn-icons-png.flaticon.com/512/461/461238.png" # Заглушка

def main(page: ft.Page):
    # --- БАЗОВЫЕ НАСТРОЙКИ ---
    page.title = "Muzlon"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#050505"
    page.padding = 0
    # Убрали жесткие window_width/height, так как на Android это вызывает проблемы с отрисовкой

    state = {
        "tracks": [],
        "users": {},
        "current_user": None,
        "is_admin": False,
        "playing_track": None,
        "temp_mp3": None,
        "temp_cover": None,
        "duration": 0,
        "view_stack": [] # Для навигации "Назад" из чужого профиля
    }

    # --- РАБОТА С ДАННЫМИ ---
    def load_data():
        try:
            if os.path.exists(TRACKS_DB):
                with open(TRACKS_DB, "r", encoding="utf-8") as f:
                    state["tracks"] = json.load(f)
                    # Миграция: добавляем uploader, если нет
                    for t in state["tracks"]:
                        if "comments" not in t: t["comments"] = []
                        if "uploader" not in t: t["uploader"] = "admin" # Дефолтный автор для старых треков

            if os.path.exists(USERS_DB):
                with open(USERS_DB, "r", encoding="utf-8") as f:
                    state["users"] = json.load(f)
                    # Миграция: добавляем подписки
                    for u in state["users"].values():
                        if "subscriptions" not in u: u["subscriptions"] = []
            else:
                state["users"] = {}
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            # Если файл битый, сбрасываем, чтобы приложение запустилось на Android
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

    # --- АУДИО И ПЕРЕМОТКА ---
    def on_duration_changed(e):
        state["duration"] = e.data
        player_slider.max = float(e.data) if e.data else 100
        page.update()

    def on_position_changed(e):
        if not player_slider.disabled: 
            player_slider.value = float(e.data) if e.data else 0
            player_slider.update()

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
        time.sleep(0.1) 
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

    # Основной контейнер для смены экранов
    app_content = ft.Column(expand=True)

    # --- КОММЕНТАРИИ ---
    bs_comments = ft.Column(scroll="auto", expand=True)
    txt_comment = ft.TextField(hint_text="Напишите комментарий...", border_radius=20, expand=True)

    def show_comments_sheet(track):
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
        
        def send_comment(e):
            if txt_comment.value:
                new_com = {
                    "user": state["current_user"],
                    "text": txt_comment.value,
                    "date": time.strftime("%H:%M %d.%m")
                }
                if "comments" not in track: track["comments"] = []
                track["comments"].append(new_com)
                save_tracks()
                txt_comment.value = ""
                page.bottom_sheet.open = False
                page.update()
                show_comments_sheet(track)

        sheet_content = ft.Container(
            content=ft.Column([
                ft.Text(f"Комментарии: {track['title']}", weight="bold", size=18),
                ft.Divider(),
                ft.Container(bs_comments, expand=True, height=300),
                ft.Row([txt_comment, ft.IconButton(ft.icons.SEND, icon_color="cyan", on_click=send_comment)])
            ]),
            padding=20, bgcolor="#151515", border_radius=ft.border_radius.only(top_left=20, top_right=20)
        )
        
        page.bottom_sheet = ft.BottomSheet(sheet_content)
        page.bottom_sheet.open = True
        page.update()

    # --- ЛОГИКА АВТОРИЗАЦИИ (ИСПРАВЛЕНИЕ 1) ---
    def check_auto_login():
        # Проверяем сохраненную сессию
        last_user = page.client_storage.get("last_user")
        if last_user and last_user in state["users"]:
            state["current_user"] = last_user
            state["is_admin"] = (last_user.lower() == "admin")
            show_main_app()
        else:
            show_auth_screen()

    def show_auth_screen():
        app_content.controls.clear()
        player_bar.visible = False
        state["current_user"] = None
        # Очищаем сессию
        page.client_storage.remove("last_user")

        login_in = ft.TextField(label="Никнейм", border_color="cyan", border_radius=15, bgcolor="#111")
        pass_in = ft.TextField(label="Пароль", password=True, border_color="cyan", border_radius=15, bgcolor="#111")

        def login_logic(e):
            u, p = login_in.value.strip(), pass_in.value.strip()
            if u in state["users"] and state["users"][u]["pass"] == p:
                state["current_user"] = u
                state["is_admin"] = (u.lower() == "admin")
                # Сохраняем сессию
                page.client_storage.set("last_user", u)
                show_main_app()
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Ошибка: проверьте данные"))
                page.snack_bar.open = True
                page.update()

        def reg_logic(e):
            u, p = login_in.value.strip(), pass_in.value.strip()
            if u and p:
                if u in state["users"]:
                    page.snack_bar = ft.SnackBar(ft.Text("Логин занят!"))
                else:
                    state["users"][u] = {
                        "pass": p, "favs": [], "subscriptions": [], 
                        "reg_date": "07.01.2026", "avatar": None
                    }
                    save_users()
                    page.snack_bar = ft.SnackBar(ft.Text("Аккаунт создан! Войдите."))
                page.snack_bar.open = True
                page.update()

        app_content.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.icons.HEADPHONES_ROUNDED, size=60, color="cyan"),
                    ft.Text("MUZLON", size=40, weight="bold", color="cyan"),
                    ft.Divider(height=20, color="transparent"),
                    login_in, pass_in,
                    ft.ElevatedButton("ВОЙТИ", on_click=login_logic, bgcolor="cyan", color="black", width=250),
                    ft.TextButton("РЕГИСТРАЦИЯ", on_click=reg_logic) 
                ], horizontal_alignment="center", alignment="center"),
                expand=True, padding=40,
                gradient=ft.LinearGradient(["#050505", "#0a1a1a"])
            )
        )
        page.update()

    # --- ПРОСМОТР ЧУЖОГО ПРОФИЛЯ (ИСПРАВЛЕНИЕ 2) ---
    def show_user_profile(username):
        state["view_stack"].append("main") # Чтобы знать куда вернуться
        
        user_data = state["users"].get(username)
        if not user_data: return

        app_content.controls.clear()
        
        # Данные чужого профиля
        avatar_src = user_data.get("avatar") or DEFAULT_IMG
        user_tracks = [t for t in state["tracks"] if t.get("uploader") == username]
        
        curr = state["current_user"]
        is_subscribed = username in state["users"][curr]["subscriptions"]
        
        def subscribe_action(e):
            if username in state["users"][curr]["subscriptions"]:
                state["users"][curr]["subscriptions"].remove(username)
                btn_sub.text = "ПОДПИСАТЬСЯ"
                btn_sub.bgcolor = "cyan"
                btn_sub.color = "black"
                msg = f"Вы отписались от {username}"
            else:
                state["users"][curr]["subscriptions"].append(username)
                btn_sub.text = "ВЫ ПОДПИСАНЫ"
                btn_sub.bgcolor = "grey"
                btn_sub.color = "white"
                msg = f"Вы подписались на {username}"
            
            save_users()
            page.snack_bar = ft.SnackBar(ft.Text(msg))
            page.snack_bar.open = True
            page.update()

        btn_sub = ft.ElevatedButton(
            "ВЫ ПОДПИСАНЫ" if is_subscribed else "ПОДПИСАТЬСЯ",
            bgcolor="grey" if is_subscribed else "cyan",
            color="white" if is_subscribed else "black",
            on_click=subscribe_action,
            visible=(username != curr) # Нельзя подписаться на себя
        )

        tracks_col = ft.Column(spacing=10, scroll="auto", expand=True)
        for t in user_tracks:
            # Используем create_card из контекста (нужно будет сделать глобальной или дублировать логику)
            # Для простоты упрощенная карточка
            tracks_col.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.MUSIC_NOTE, color="cyan"),
                        ft.Column([
                            ft.Text(t["title"], weight="bold"),
                            ft.Text(t["artist"], size=12, color="grey")
                        ], expand=True),
                        ft.IconButton(ft.icons.PLAY_ARROW, on_click=lambda _, trk=t: start_track(trk))
                    ]),
                    bgcolor="#1a1a1a", padding=10, border_radius=10
                )
            )

        def go_back(_):
            state["view_stack"].clear()
            show_main_app()

        profile_content = ft.Column([
            ft.IconButton(ft.icons.ARROW_BACK, on_click=go_back),
            ft.Container(
                content=ft.Column([
                    ft.CircleAvatar(radius=50, foreground_image_src=avatar_src if user_data.get("avatar") else None, content=ft.Icon(ft.icons.PERSON) if not user_data.get("avatar") else None),
                    ft.Text(username, size=24, weight="bold"),
                    btn_sub,
                    ft.Divider(),
                    ft.Text("Треки пользователя:", color="grey"),
                ], horizontal_alignment="center"),
                alignment=ft.alignment.center
            ),
            tracks_col
        ], expand=True, padding=20)

        app_content.controls.append(profile_content)
        page.update()


    # --- ГЛАВНОЕ ПРИЛОЖЕНИЕ ---
    def show_main_app():
        app_content.controls.clear()
        
        home_list = ft.Column(scroll="auto", expand=True, spacing=10)
        fav_list = ft.Column(scroll="auto", expand=True, spacing=10)
        
        def toggle_like(e, track):
            u = state["current_user"]
            if track["path"] in state["users"][u]["favs"]:
                state["users"][u]["favs"].remove(track["path"])
                e.control.icon = ft.icons.FAVORITE_BORDER
                e.control.icon_color = "white24"
            else:
                state["users"][u]["favs"].append(track["path"])
                e.control.icon = ft.icons.FAVORITE
                e.control.icon_color = "red"
            save_users()
            refresh_ui()

        def delete_track(track):
            state["tracks"].remove(track)
            save_tracks()
            refresh_ui()

        def create_card(t, is_fav_view=False):
            u = state["current_user"]
            liked = t["path"] in state["users"][u]["favs"]
            
            # Аватар автора трека
            uploader = t.get("uploader", "admin")
            uploader_data = state["users"].get(uploader, {})
            uploader_avatar = uploader_data.get("avatar")
            
            # Кликабельная аватарка
            avatar_widget = ft.Container(
                content=ft.CircleAvatar(
                    radius=15, 
                    foreground_image_src=uploader_avatar if uploader_avatar else None,
                    content=ft.Icon(ft.icons.PERSON, size=15) if not uploader_avatar else None,
                    bgcolor="cyan"
                ),
                on_click=lambda _: show_user_profile(uploader),
                tooltip=f"Профиль: {uploader}"
            )

            card_content = ft.Row([
                ft.Image(src=t.get("cover") or DEFAULT_IMG, width=50, height=50, border_radius=8),
                ft.Column([
                    ft.Text(t["title"], weight="bold", size=15),
                    ft.Row([
                        avatar_widget, # Аватар автора рядом с именем артиста
                        ft.Text(t["artist"], size=12, color="white54")
                    ], spacing=5)
                ], expand=True),
                ft.Row([
                    ft.IconButton(ft.icons.CHAT_BUBBLE_OUTLINE, icon_color="cyan", icon_size=20, on_click=lambda e: show_comments_sheet(t)),
                    ft.IconButton(ft.icons.FAVORITE if liked else ft.icons.FAVORITE_BORDER, icon_color="red" if liked else "white24", on_click=lambda e: toggle_like(e, t)),
                    ft.IconButton(ft.icons.DELETE, icon_color="red300", on_click=lambda _, trk=t: delete_track(trk), visible=state["is_admin"])
                ], spacing=0)
            ])

            return ft.Container(
                content=card_content,
                bgcolor="#121212", padding=10, border_radius=12,
                on_click=lambda _, trk=t: start_track(trk)
            )

        def refresh_ui():
            home_list.controls.clear()
            fav_list.controls.clear()
            u_favs = state["users"][state["current_user"]]["favs"]
            
            for t in state["tracks"]:
                home_list.controls.append(create_card(t))
                if t["path"] in u_favs:
                    fav_list.controls.append(create_card(t, True))
            
            update_profile_stats()
            page.update()

        # ЭКРАН ПРОФИЛЯ (МОЙ)
        stat_likes = ft.Text("0", size=22, weight="bold", color="cyan")
        stat_reg = ft.Text("-", size=14, color="white54")
        user_avatar = ft.CircleAvatar(radius=50, bgcolor="cyan", content=ft.Icon(ft.icons.PERSON, size=50))
        
        def update_profile_stats():
            u = state["current_user"]
            u_data = state["users"][u]
            stat_likes.value = str(len(u_data["favs"]))
            stat_reg.value = f"В Muzlon с {u_data.get('reg_date', 'недавно')}"
            
            if u_data.get("avatar"):
                user_avatar.foreground_image_src = u_data["avatar"]
                user_avatar.content = None
            else:
                user_avatar.foreground_image_src = None
                user_avatar.content = ft.Icon(ft.icons.PERSON, size=50)

        def pick_avatar_click(_):
            fp_avatar.pick_files()

        profile_view = ft.Container(
            content=ft.Column([
                ft.Container(height=20),
                ft.Container(content=user_avatar, on_click=pick_avatar_click, tooltip="Нажми, чтобы сменить фото"),
                ft.Text(state["current_user"].upper() if state["current_user"] else "", size=28, weight="bold"),
                ft.Divider(height=40, color="white10"),
                ft.Row([
                    ft.Column([ft.Text("Любимых", color="white54"), stat_likes], horizontal_alignment="center"),
                    ft.Column([ft.Text("Всего треков", color="white54"), ft.Text(str(len(state["tracks"])), size=22, weight="bold")], horizontal_alignment="center"),
                ], alignment="spaceAround", width=350),
                ft.Divider(height=40, color="white10"),
                stat_reg,
                ft.ElevatedButton("ВЫЙТИ", icon=ft.icons.LOGOUT, on_click=lambda _: show_auth_screen(), color="red", bgcolor="#1a0000")
            ], horizontal_alignment="center"),
            padding=20
        )

        # АДМИН ПАНЕЛЬ
        in_title = ft.TextField(label="Название трека")
        in_artist = ft.TextField(label="Артист")
        lbl_file = ft.Text("Файл MP3 не выбран", color="red")
        lbl_cover = ft.Text("Обложка не выбрана", color="grey")

        admin_view = ft.Column([
            ft.Text("ЗАГРУЗКА ТРЕКА", size=20, weight="bold", color="cyan"),
            ft.Divider(),
            in_title, in_artist, 
            ft.Row([
                ft.ElevatedButton("ВЫБРАТЬ MP3", icon=ft.icons.AUDIO_FILE, on_click=lambda _: fp_mp3.pick_files()),
                lbl_file
            ]),
            ft.Row([
                ft.ElevatedButton("ВЫБРАТЬ ОБЛОЖКУ", icon=ft.icons.IMAGE, on_click=lambda _: fp_cover.pick_files()),
                lbl_cover
            ]),
            ft.Divider(),
            ft.ElevatedButton("ОПУБЛИКОВАТЬ", bgcolor="cyan", color="black", width=200, 
                              on_click=lambda _: publish_track(in_title.value, in_artist.value, lbl_file, lbl_cover))
        ], spacing=15) # Видно всем, кто хочет загрузить? Или только админу? Оставим админу как было, или сделаем доступным всем? 
        # В коде было visible=state["is_admin"]. Оставим так.

        def publish_track(title, artist, lbl_f, lbl_c):
            if title and state["temp_mp3"]:
                current_u = state["current_user"]
                state["tracks"].append({
                    "title": title,
                    "artist": artist or "Неизвестен",
                    "path": state["temp_mp3"],
                    "cover": state["temp_cover"],
                    "comments": [],
                    "uploader": current_u # Запоминаем кто залил
                })
                save_tracks()
                
                # --- ИСПРАВЛЕНИЕ 2: СМС/УВЕДОМЛЕНИЕ ---
                # Проходим по всем пользователям и ищем, кто подписан на current_u
                # Поскольку это локальное демо, мы просто показываем уведомление прямо сейчас
                # как будто оно пришло на "телефон".
                count_subs = 0
                for u_name, u_dat in state["users"].items():
                    if current_u in u_dat.get("subscriptions", []):
                        count_subs += 1
                
                # Имитация SMS (SnackBar сверху или диалог)
                if count_subs > 0:
                    page.snack_bar = ft.SnackBar(
                        ft.Row([
                            ft.Icon(ft.icons.SMS, color="white"),
                            ft.Text(f"SMS: У {current_u} вышел новый трек! (Подписчиков: {count_subs})")
                        ]),
                        bgcolor="green"
                    )
                    page.snack_bar.open = True
                
                state["temp_mp3"] = None
                state["temp_cover"] = None
                lbl_f.value = "Успешно добавлено!"
                lbl_f.color = "green"
                lbl_c.value = "Обложка сброшена"
                refresh_ui()
            else:
                lbl_f.value = "Ошибка: введите название и файл"
                page.update()

        tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Обзор", icon=ft.icons.EXPLORE_ROUNDED, content=ft.Container(home_list, padding=10)),
                ft.Tab(text="Лайки", icon=ft.icons.FAVORITE_ROUNDED, content=ft.Container(fav_list, padding=10)),
                ft.Tab(text="Профиль", icon=ft.icons.PERSON_ROUNDED, content=profile_view),
            ],
            expand=True
        )

        # Теперь вкладку "Загрузить" (бывший админ) видят все или только админ?
        # По логике "подписки на автора", загружать должны многие.
        # Но по твоему коду только админ. Оставлю проверку.
        if state["is_admin"]:
             tabs.tabs.append(ft.Tab(text="Загрузка", icon=ft.icons.CLOUD_UPLOAD, content=ft.Container(admin_view, padding=20)))

        app_content.controls.append(ft.Container(tabs, expand=True))
        refresh_ui()
        page.update()

    # --- FILE PICKERS ---
    def on_mp3_result(e: ft.FilePickerResultEvent):
        if e.files:
            state["temp_mp3"] = e.files[0].path
            page.snack_bar = ft.SnackBar(ft.Text(f"MP3 выбран: {e.files[0].name}"))
            page.snack_bar.open = True
            page.update()

    def on_cover_result(e: ft.FilePickerResultEvent):
        if e.files:
            state["temp_cover"] = e.files[0].path
            page.snack_bar = ft.SnackBar(ft.Text(f"Обложка выбрана: {e.files[0].name}"))
            page.snack_bar.open = True
            page.update()

    def on_avatar_result(e: ft.FilePickerResultEvent):
        if e.files and state["current_user"]:
            path = e.files[0].path
            state["users"][state["current_user"]]["avatar"] = path
            save_users()
            page.snack_bar = ft.SnackBar(ft.Text("Аватар обновлен!"))
            page.snack_bar.open = True
            # Обновляем UI
            show_main_app() 

    fp_mp3 = ft.FilePicker(on_result=on_mp3_result)
    fp_cover = ft.FilePicker(on_result=on_cover_result)
    fp_avatar = ft.FilePicker(on_result=on_avatar_result)
    
    page.overlay.extend([fp_mp3, fp_cover, fp_avatar])

    # --- ЗАПУСК ---
    page.add(
        ft.Column([
            app_content,
            player_bar
        ], expand=True, spacing=0)
    )
    
    # Запускаем проверку авто-входа вместо show_auth_screen()
    check_auto_login()

ft.app(target=main)
