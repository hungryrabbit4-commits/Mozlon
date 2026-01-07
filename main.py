import flet as ft
import json
import os
import time

# --- КОНФИГУРАЦИЯ ФАЙЛОВ ---
TRACKS_DB = "muzlon_tracks.json"
USERS_DB = "muzlon_users.json"
ADMIN_PASS_CODE = "admin123321"
DEFAULT_IMG = "https://cdn-icons-png.flaticon.com/512/3844/3844724.png"

def main(page: ft.Page):
    # 1. Приложение просто называется Muzlon
    page.title = "Muzlon"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#050505"
    page.window_width = 420
    page.window_height = 850
    page.padding = 0

    state = {
        "tracks": [],
        "users": {},
        "current_user": None,
        "is_admin": False,
        "playing_track": None,
        "temp_mp3": None,
        "temp_cover": None,
        "duration": 0,  # Для перемотки
    }

    def load_data():
        if os.path.exists(TRACKS_DB):
            with open(TRACKS_DB, "r", encoding="utf-8") as f:
                state["tracks"] = json.load(f)
                # Миграция для старых данных (добавляем список комментов, если нет)
                for t in state["tracks"]:
                    if "comments" not in t:
                        t["comments"] = []
        if os.path.exists(USERS_DB):
            with open(USERS_DB, "r", encoding="utf-8") as f:
                state["users"] = json.load(f)
        else:
            state["users"] = {}

    def save_tracks():
        with open(TRACKS_DB, "w", encoding="utf-8") as f:
            json.dump(state["tracks"], f, ensure_ascii=False, indent=4)

    def save_users():
        with open(USERS_DB, "w", encoding="utf-8") as f:
            json.dump(state["users"], f, ensure_ascii=False, indent=4)

    load_data()

    # --- АУДИО И ПЕРЕМОТКА ---
    # 2. Возможность перемотки трека (логика)
    def on_duration_changed(e):
        state["duration"] = e.data
        player_slider.max = float(e.data)
        page.update()

    def on_position_changed(e):
        # Обновляем слайдер только если пользователь его не тащит прямо сейчас
        if not player_slider.disabled: 
            player_slider.value = float(e.data)
            player_slider.update()

    def on_seek(e):
        # Конвертируем значение слайдера в миллисекунды для seek
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
    
    # Слайдер для перемотки
    player_slider = ft.Slider(
        min=0, max=100, 
        height=20, 
        active_color="cyan", 
        thumb_color="white",
        on_change_end=on_seek # Перематываем когда отпустили ползунок
    )

    btn_play_pause = ft.IconButton(ft.icons.PLAY_ARROW_ROUNDED, icon_size=30, icon_color="cyan")

    # Основной контейнер плеера (немного увеличил высоту для слайдера)
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
            player_slider # Добавили слайдер вниз
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

    app_content = ft.Column(expand=True)

    # --- КОММЕНТАРИИ (НИЖНЯЯ ШТОРКА) ---
    # 3. Возможность оставить комментарий под треком
    bs_comments = ft.Column(scroll="auto", expand=True)
    txt_comment = ft.TextField(hint_text="Напишите комментарий...", border_radius=20, expand=True)

    def show_comments_sheet(track):
        bs_comments.controls.clear()
        
        # Загрузка существующих комментариев
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
                if "comments" not in track:
                    track["comments"] = []
                track["comments"].append(new_com)
                save_tracks()
                txt_comment.value = ""
                # Переоткрываем/обновляем список
                page.bottom_sheet.open = False
                page.update()
                show_comments_sheet(track) # Рекурсивно обновляем

        # Нижняя панель (BottomSheet)
        sheet_content = ft.Container(
            content=ft.Column([
                ft.Text(f"Комментарии: {track['title']}", weight="bold", size=18),
                ft.Divider(),
                ft.Container(bs_comments, expand=True, height=300), # Ограничим высоту
                ft.Row([txt_comment, ft.IconButton(ft.icons.SEND, icon_color="cyan", on_click=send_comment)])
            ]),
            padding=20,
            bgcolor="#151515",
            border_radius=ft.border_radius.only(top_left=20, top_right=20)
        )
        
        page.bottom_sheet = ft.BottomSheet(sheet_content)
        page.bottom_sheet.open = True
        page.update()

    # --- ЭКРАН АВТОРИЗАЦИИ ---
    def show_auth_screen():
        app_content.controls.clear()
        player_bar.visible = False

        login_in = ft.TextField(label="Никнейм", border_color="cyan", border_radius=15, bgcolor="#111")
        pass_in = ft.TextField(label="Пароль", password=True, border_color="cyan", border_radius=15, bgcolor="#111")

        def login_logic(e):
            u, p = login_in.value.strip(), pass_in.value.strip()
            if u in state["users"] and state["users"][u]["pass"] == p:
                state["current_user"] = u
                state["is_admin"] = (u.lower() == "admin")
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
                    state["users"][u] = {"pass": p, "favs": [], "reg_date": "07.01.2026", "avatar": None}
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
            
            # Контейнер кликабельный для воспроизведения
            card_content = ft.Row([
                ft.Image(src=t.get("cover") or DEFAULT_IMG, width=50, height=50, border_radius=8),
                ft.Column([
                    ft.Text(t["title"], weight="bold", size=15),
                    ft.Text(t["artist"], size=12, color="white54")
                ], expand=True),
                ft.Row([
                    # Кнопка комментариев
                    ft.IconButton(
                        ft.icons.CHAT_BUBBLE_OUTLINE,
                        icon_color="cyan",
                        icon_size=20,
                        on_click=lambda e: show_comments_sheet(t)
                    ),
                    ft.IconButton(
                        ft.icons.FAVORITE if liked else ft.icons.FAVORITE_BORDER,
                        icon_color="red" if liked else "white24",
                        on_click=lambda e: toggle_like(e, t)
                    ),
                    ft.IconButton(ft.icons.DELETE, icon_color="red300", 
                                  on_click=lambda _, trk=t: delete_track(trk),
                                  visible=state["is_admin"])
                ], spacing=0)
            ])

            return ft.Container(
                content=card_content,
                bgcolor="#121212", padding=10, border_radius=12,
                # Воспроизводим только если нажали не на кнопки, а на саму карточку
                # (В Flet нажатие на дочернюю кнопку перехватывает событие, так что здесь ок)
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

        # ЭКРАН ПРОФИЛЯ
        stat_likes = ft.Text("0", size=22, weight="bold", color="cyan")
        stat_reg = ft.Text("-", size=14, color="white54")
        
        # 4. Возможность поставить аватарку себе на профиль
        user_avatar = ft.CircleAvatar(radius=50, bgcolor="cyan", content=ft.Icon(ft.icons.PERSON, size=50))
        
        def update_profile_stats():
            u = state["current_user"]
            u_data = state["users"][u]
            stat_likes.value = str(len(u_data["favs"]))
            stat_reg.value = f"В Muzlon с {u_data.get('reg_date', 'недавно')}"
            
            # Обновляем аватар
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
                # Кликабельный контейнер для аватара
                ft.Container(content=user_avatar, on_click=pick_avatar_click, tooltip="Нажми, чтобы сменить фото"),
                ft.Text(state["current_user"].upper() if state["current_user"] else "", size=28, weight="bold"),
                ft.Divider(height=40, color="white10"),
                ft.Row([
                    ft.Column([ft.Text("Любимых", color="white54"), stat_likes], horizontal_alignment="center"),
                    ft.Column([ft.Text("Библиотека", color="white54"), ft.Text(str(len(state["tracks"])), size=22, weight="bold")], horizontal_alignment="center"),
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
        lbl_cover = ft.Text("Обложка не выбрана", color="grey") # 5. Индикатор обложки

        # 5. Возможность поставить аватарку на профиль трека (только для админов)
        admin_view = ft.Column([
            ft.Text("ПАНЕЛЬ АДМИНИСТРАТОРА", size=20, weight="bold", color="cyan"),
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
        ], spacing=15, visible=state["is_admin"])

        def publish_track(title, artist, lbl_f, lbl_c):
            if title and state["temp_mp3"]:
                state["tracks"].append({
                    "title": title,
                    "artist": artist or "Неизвестен",
                    "path": state["temp_mp3"],
                    "cover": state["temp_cover"], # Может быть None
                    "comments": []
                })
                save_tracks()
                # Сброс
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

        if state["is_admin"]:
            tabs.tabs.append(ft.Tab(text="Админ", icon=ft.icons.SETTINGS_ROUNDED, content=ft.Container(admin_view, padding=20)))

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

    # 5. Пикер для обложки трека
    def on_cover_result(e: ft.FilePickerResultEvent):
        if e.files:
            state["temp_cover"] = e.files[0].path
            page.snack_bar = ft.SnackBar(ft.Text(f"Обложка выбрана: {e.files[0].name}"))
            page.snack_bar.open = True
            page.update()

    # 4. Пикер для аватарки пользователя
    def on_avatar_result(e: ft.FilePickerResultEvent):
        if e.files and state["current_user"]:
            path = e.files[0].path
            state["users"][state["current_user"]]["avatar"] = path
            save_users()
            page.snack_bar = ft.SnackBar(ft.Text("Аватар обновлен!"))
            page.snack_bar.open = True
            # Если мы на экране профиля, надо обновить UI
            show_main_app() 

    fp_mp3 = ft.FilePicker(on_result=on_mp3_result)
    fp_cover = ft.FilePicker(on_result=on_cover_result)
    fp_avatar = ft.FilePicker(on_result=on_avatar_result)
    
    page.overlay.extend([fp_mp3, fp_cover, fp_avatar])

    # --- ГЛАВНАЯ СТРУКТУРА ---
    page.add(
        ft.Column([
            app_content,
            player_bar
        ], expand=True, spacing=0)
    )
    
    show_auth_screen()

ft.app(target=main)