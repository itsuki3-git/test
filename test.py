import hashlib
import os
from datetime import datetime, timezone, timedelta
import flet as ft
from supabase import create_client, Client


def main(page: ft.Page):
    page.title = "アグリコラ得点計算 & プレイヤー管理"
    page.window_width = 450
    page.window_height = 700
    page.theme_mode = ft.ThemeMode.LIGHT

    # =========================================================================
    # ⚠️ あなたのSupabaseの情報をここに貼り付けてください
    # =========================================================================
    SUPABASE_URL = "https://tqufugshygdknyfgrsxh.supabase.co"
    SUPABASE_KEY = "sb_publishable_fMuDE8giATkTj2UOjCyThg_wowMJz0s"
    # =========================================================================

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    current_player = None
    my_group_list = []
    
    # 🌾 アグリコラ専用データ構造（部屋はタイプと個数に統合）
    counts = {
        "field": 0, "pasture": 0, "grain": 0, "vegetable": 0,
        "sheep": 0, "wild_boar": 0, "cattle": 0, "empty_space": 0,
        "stable": 0, "room_type": "clay", "room_count": 0,
        "family": 2, "card_points": 0, "bonus_points": 0, "begging_card": 0
    }
    
    STORAGE_REMEMBER_USER = "fruit_app_remembered_user"
    STORAGE_REMEMBER_PASS = "fruit_app_remembered_pass"

    # --- UIコンポーネント基本定義 ---
    login_name_input = ft.TextField(label="プレイヤー名", hint_text="例: たろう")
    login_pass_input = ft.TextField(label="パスワード", password=True, can_reveal_password=True)

    register_btn = ft.ElevatedButton("新規登録", icon=ft.Icons.PERSON_ADD, on_click=lambda e: handle_new_register(e),
                                     bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE, width=140, height=45)
    login_btn = ft.ElevatedButton("ログイン", icon=ft.Icons.LOGIN, on_click=lambda e: handle_existing_login(e),
                                  bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE, width=140, height=45)

    forgot_name_input = ft.TextField(label="プレイヤー名を入力")
    forgot_question_text = ft.Text(value="プレイヤー名を入力して「質問を確認」を押してください",
                                   color=ft.Colors.BLUE_GREY_600, weight=ft.FontWeight.W_500)
    forgot_answer_input = ft.TextField(label="質問の答えを入力")
    forgot_new_pass_input = ft.TextField(label="新しいパスワード (4桁以上)", password=True, can_reveal_password=True)

    logged_in_user_text = ft.Text(value="", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800)
    score_display = ft.Text(value="0", size=48, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600)

    # 各要素の入力数値を画面中央にリアルタイム同期するTextマップ
    ui_text_map = {k: ft.Text(value="2" if k == "family" else "0", size=16, weight=ft.FontWeight.BOLD, width=30, text_align=ft.TextAlign.CENTER) for k in counts}

    # 🌾 修正: show_selected_icon=False を追加してチェックマークを非表示にしました
    room_type_switch = ft.SegmentedButton(
        selected={"clay"},
        show_selected_icon=False, # 💡 ここを追加してチェック（✓）を消しました
        segments=[
            ft.Segment(value="clay", label=ft.Text("レンガ", size=12)),
            ft.Segment(value="stone", label=ft.Text("石", size=12)),
        ],
        on_change=lambda e: handle_room_type_change(e)
    )


    edit_name_input = ft.TextField(label="名前を編集", expand=True)
    group_inputs_container = ft.Column(spacing=10)
    my_records_list = ft.ListView(expand=True, spacing=10, padding=10)

    mypage_old_pass = ft.TextField(label="現在のパスワード", password=True)
    mypage_new_pass = ft.TextField(label="新しいパスワード (4桁以上)", password=True)
    mypage_question_input = ft.TextField(label="新しく登録する「秘密の質問」", hint_text="例: 初めて飼ったペットの名前は？")
    mypage_answer_input = ft.TextField(label="質問の答え", hint_text="答えを入力してください")

    # 🏆 ランキング用コンポーネント
    ranking_title_text = ft.Text(value="🏆 ハイスコアランキング", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_700)
    ranking_group_dropdown = ft.Dropdown(label="グループ切り替え", width=160, options=[], on_change=lambda e: update_ranking_ui())
    ranking_list = ft.ListView(expand=True, spacing=10, padding=10)

    # 定義順エラー回避用の空定義
    authenticated_view = None

    def show_alert(message, title="エラー"):
        alert_dialog = ft.AlertDialog(title=ft.Text(title), content=ft.Text(message))
        alert_dialog.actions = [ft.TextButton("OK", on_click=lambda e: (setattr(alert_dialog, "open", False), page.update()))]
        page.open(alert_dialog)

    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def get_jst_now_str() -> str:
        jst = timezone(timedelta(hours=9))
        return datetime.now(jst).strftime("%Y/%m/%d %H:%M")

    # 🌾 1. アグリコラ各項目のUI生成関数（スマホ最適化版）
    def create_agricola_selector(label, key, color):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=ft.Text(label, size=13, weight=ft.FontWeight.BOLD, no_wrap=True), width=110, alignment=ft.alignment.center_left),
                    ft.Row(
                        controls=[
                            ft.Container(content=ft.TextButton("-3", style=ft.ButtonStyle(color=color, padding=0), on_click=lambda e: adjust_count(key, -3)), width=38, alignment=ft.alignment.center),
                            ft.Container(content=ft.TextButton("-1", style=ft.ButtonStyle(color=color, padding=0), on_click=lambda e: adjust_count(key, -1)), width=38, alignment=ft.alignment.center),
                            ft.Container(content=ui_text_map[key], width=30, alignment=ft.alignment.center),
                            ft.Container(content=ft.TextButton("+1", style=ft.ButtonStyle(color=color, padding=0), on_click=lambda e: adjust_count(key, 1)), width=38, alignment=ft.alignment.center),
                            ft.Container(content=ft.TextButton("+3", style=ft.ButtonStyle(color=color, padding=0), on_click=lambda e: adjust_count(key, 3)), width=38, alignment=ft.alignment.center)
                        ], spacing=0, alignment=ft.MainAxisAlignment.END
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER
            ), padding=4, border=ft.border.all(1, ft.Colors.GREY_300), border_radius=10, bgcolor=ft.Colors.WHITE
        )

    # 🌾 2. アグリコラ公式段階的得点テーブル
    def get_agricola_score(key, value):
        if key == "field":
            if value <= 1: return -1
            elif value == 2: return 1
            elif value == 3: return 2
            elif value == 4: return 3
            else: return 4
        elif key == "pasture":
            if value == 0: return -1
            elif value == 1: return 1
            elif value == 2: return 2
            elif value == 3: return 3
            else: return 4
        elif key == "grain":
            if value == 0: return -1
            elif value <= 3: return 1
            elif value <= 5: return 2
            elif value <= 7: return 3
            else: return 4
        elif key == "vegetable":
            if value == 0: return -1
            elif value == 1: return 1
            elif value == 2: return 2
            elif value == 3: return 3
            else: return 4
        elif key == "sheep":
            if value == 0: return -1
            elif value <= 3: return 1
            elif value <= 5: return 2
            elif value <= 7: return 3
            else: return 4
        elif key == "wild_boar":
            if value == 0: return -1
            elif value <= 2: return 1
            elif value <= 4: return 2
            elif value <= 6: return 3
            else: return 4
        elif key == "cattle":
            if value == 0: return -1
            elif value == 1: return 1
            elif value <= 3: return 2
            elif value <= 5: return 3
            else: return 4
        elif key == "empty_space": return value * -1
        elif key == "stable": return value * 1
        elif key == "room_count":
            multiplier = 2 if counts["room_type"] == "stone" else 1
            return value * multiplier
        elif key == "family": return value * 3
        elif key == "card_points": return value
        elif key == "bonus_points": return value
        elif key == "begging_card": return value * -3
        return 0

    def calculate_total_score_ui_only():
        total = sum(get_agricola_score(k, v) for k, v in counts.items())
        score_display.value = str(total)
        return total

    def handle_room_type_change(e):
        counts["room_type"] = list(e.selection)[0] if e.selection else "clay"
        calculate_total_score_ui_only()
        page.update()

    def adjust_count(key, delta):
        new_count = counts[key] + delta
        if key in ["card_points", "bonus_points"] or new_count >= 0:
            counts[key] = new_count
            ui_text_map[key].value = str(new_count)
            calculate_total_score_ui_only()
            page.update()

    def reset_current_game(e):
        for k in counts:
            if k == "family":
                counts[k] = 2
                ui_text_map[k].value = "2"
            elif k == "room_type":
                counts[k] = "clay"
                room_type_switch.selected = {"clay"}
            else:
                counts[k] = 0
                if k in ui_text_map:
                    ui_text_map[k].value = "0"
        calculate_total_score_ui_only()
        if e: page.update()

    def update_all_uis():
        update_my_records_ui()
        if current_player:
            refresh_ranking_dropdown_options()
            update_ranking_ui()
        if current_player == "admin": update_admin_ui()

    def update_my_records_ui():
        my_records_list.controls.clear()
        if not current_player: return
        try:
            res = supabase.table("records").select("*").execute()
            my_filtered = [r for r in (res.data or []) if r.get("player") == current_player]
        except Exception as ex:
            my_records_list.controls.append(ft.Text(f"データ取得エラー: {ex}", color=ft.Colors.RED))
            page.update()
            return
        if not my_filtered:
            my_records_list.controls.append(ft.Text("保存された記録はありません", italic=True, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER))
        else:
            for record in sorted(my_filtered, key=lambda x: x["id"], reverse=True):
                my_records_list.controls.append(ft.Container(content=ft.Row(controls=[ft.Column(
                    [ft.Text(f"合計得点: {record['final_score']} 点", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                     ft.Text(value=f"保存日時: {record['date']}", size=11, color=ft.Colors.GREY_500)], expand=True),
                    ft.IconButton(ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_600, on_click=lambda e, idx=record["id"]: delete_saved_record(idx))],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=12, border=ft.border.all(1, ft.Colors.BLUE_100), border_radius=8, bgcolor=ft.Colors.BLUE_50))
            page.update()

    def save_current_game(e):
        if not current_player: return
        total_score = calculate_total_score_ui_only()
        try:
            supabase.table("records").insert({"player": current_player, "final_score": total_score, "date": get_jst_now_str()}).execute()
        except Exception as ex:
            show_alert(f"記録保存失敗: {ex}")
            return
        reset_current_game(None)
        update_all_uis()
        page.overlay.append(ft.SnackBar(ft.Text(f"{current_player} の記録を保存しました！"), open=True))
        page.update()

    def delete_saved_record(target_id):
        try:
            supabase.table("records").delete().eq("id", target_id).execute()
        except Exception: return
        update_all_uis()

    def refresh_ranking_dropdown_options():
        ranking_group_dropdown.options.clear()
        try:
            if current_player == "admin":
                privacy_res = supabase.table("privacy").select("group_number").execute()
                detected_groups = {0}
                if privacy_res.data:
                    for row in privacy_res.data:
                        g_str = str(row.get("group_number", "1"))
                        for token in g_str.replace("，", ",").split(","):
                            if (t := token.strip()).isdigit(): detected_groups.add(int(t))
                for g in sorted(list(detected_groups)):
                    label_text = "グループ 0 (管理者)" if g == 0 else f"グループ {g}"
                    ranking_group_dropdown.options.append(ft.dropdown.Option(str(g), label_text))
                ranking_group_dropdown.value = "0"
            else:
                for g in sorted(my_group_list):
                    ranking_group_dropdown.options.append(ft.dropdown.Option(str(g), f"グループ {g}"))
                ranking_group_dropdown.value = str(my_group_list[0]) if my_group_list else None
        except Exception:
            ranking_group_dropdown.options.append(ft.dropdown.Option("1", "グループ 1"))
            ranking_group_dropdown.value = "1"
        page.update()

    def update_ranking_ui():
        ranking_list.controls.clear()
        selected_g = ranking_group_dropdown.value
        if not selected_g: return
        ranking_title_text.value = f"🏆 グループ {selected_g} ランキング"
        try:
            records_res = supabase.table("records").select("*").execute()
            privacy_res = supabase.table("privacy").select("*").execute()
            records_raw = records_res.data or []
            privacy_raw = privacy_res.data or []
            allowed_players = set()
            for p in privacy_raw:
                p_name = p.get("username") or p.get("player")
                p_groups = [x.strip() for x in str(p.get("group_number", "1")).replace("，", ",").split(",") if x.strip()]
                if selected_g in p_groups and p_name: allowed_players.add(p_name)
            if selected_g == "0" or current_player == "admin": allowed_players.add("admin")
            filtered = [r for r in records_raw if r.get("player") in allowed_players]
            
            if not filtered:
                ranking_list.controls.append(ft.Container(content=ft.Text("記録がまだありません", color=ft.Colors.GREY_500), alignment=ft.alignment.center))
            else:
                user_best = {}
                for r in filtered:
                    p = r["player"]
                    if p not in user_best or r["final_score"] > user_best[p]["final_score"]: user_best[p] = r
                
                for index, record in enumerate(sorted(list(user_best.values()), key=lambda x: x["final_score"], reverse=True)):
                    rank = index + 1
                    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "  ")
                    rank_row = ft.Row(spacing=10)
                    rank_row.controls = [
                        ft.Text(f"{medal} {rank}位", size=16, weight=ft.FontWeight.BOLD, width=60),
                        ft.Text(f"{record['player']}", expand=True, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{record['final_score']} 点", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
                    ]
                    ranking_list.controls.append(
                        ft.Container(content=rank_row, padding=10, border=ft.border.all(1, ft.Colors.GREY_200), border_radius=8)
                    )
        except Exception: pass
        page.update()

    def handle_existing_login(e):
        nonlocal current_player, my_group_list
        input_name = login_name_input.value.strip()
        input_pass = login_pass_input.value.strip()
        if not input_name or not input_pass: return
        try:
            hashed_pass = hash_password(input_pass)
            res = supabase.table("users").select("username").eq("username", input_name).eq("password", hashed_pass).execute()
            if not res.data or len(res.data) == 0: 
                show_alert("名前またはパスワードが間違っています。")
                return
                
            page.client_storage.set(STORAGE_REMEMBER_USER, input_name)
            page.client_storage.set(STORAGE_REMEMBER_PASS, input_pass)
            
            priv_res = supabase.table("privacy").select("*").execute()
            user_privacy_data = next((p for p in (priv_res.data or []) if (p.get("username") or p.get("player")) == input_name), None)
            
            # 💡 修正完了: 文法の不備を完全にクリーンアップしました
            if user_privacy_data:
                raw_group_str = str(user_privacy_data.get("group_number", "1"))
                if input_name.lower() == "admin": raw_group_str = "0"
                my_group_list = [int(x.strip()) for x in raw_group_str.replace("，", ",").split(",") if x.strip().isdigit()]
            else:
                my_group_list = [0] if input_name.lower() == "admin" else [1]
        except Exception as ex: 
            show_alert(f"ログイン処理エラー: {ex}")
            return
        enter_game_session(input_name, f"👤 {input_name} さんとしてログインしました！")

    def enter_game_session(username, success_message):
        nonlocal current_player
        current_player = username
        logged_in_user_text.value = f"👤 ログイン中: {current_player} さん"
        edit_name_input.value = current_player
        page.controls.clear()
        page.add(authenticated_view)
        authenticated_view.visible = True
        if current_player == "admin" and len(main_tab_view.tabs) == 3:
            main_tab_view.tabs.append(ft.Tab(text="管理者", icon=ft.Icons.ADMIN_PANEL_SETTINGS, content=admin_tab_view))
        elif current_player != "admin" and len(main_tab_view.tabs) == 4:
            main_tab_view.tabs.pop()
        reset_current_game(None)
        update_all_uis()
        page.overlay.append(ft.SnackBar(ft.Text(success_message), open=True))
        page.update()

    def handle_logout(e):
        nonlocal current_player
        current_player = None
        page.controls.clear()
        page.add(login_view)
        page.update()

    def create_group_input_row(initial_value=""):
        tf = ft.TextField(value=str(initial_value), label="グループ番号", keyboard_type=ft.KeyboardType.NUMBER, expand=True)
        row = ft.Row(spacing=5)
        row.controls = [tf, ft.IconButton(icon=ft.Icons.DELETE_OUTLINED, icon_color=ft.Colors.RED_400, on_click=lambda e: remove_group_input_row(row))]
        return row

    def remove_group_input_row(row_control):
        if len(group_inputs_container.controls) <= 1: return
        group_inputs_container.controls.remove(row_control)
        page.update()

    def add_blank_group_input_row(e):
        group_inputs_container.controls.append(create_group_input_row(""))
        page.update()

    def open_change_group_dialog(e):
        group_inputs_container.controls.clear()
        for g_num in my_group_list: group_inputs_container.controls.append(create_group_input_row(g_num))
        if not group_inputs_container.controls: group_inputs_container.controls.append(create_group_input_row("1"))
        page.open(change_group_dialog)

    def handle_save_group_number(e):
        nonlocal my_group_list
        parsed_list = []
        for row in group_inputs_container.controls:
            tf_control = row.controls[0]
            val_str = tf_control.value.strip() if tf_control.value else ""
            if val_str.isdigit():
                g_num = int(val_str)
                if current_player != "admin" and g_num == 0: continue
                if g_num not in parsed_list: parsed_list.append(g_num)
        if not parsed_list: return
        try:
            parsed_list.sort()
            clean_str = ", ".join([str(n) for n in parsed_list])
            priv_res = supabase.table("privacy").select("*").eq("username", current_player).execute()
            p_key = "username" if priv_res.data else "player"
            supabase.table("privacy").update({"group_number": clean_str}).eq(p_key, current_player).execute()
            my_group_list = parsed_list
            page.close(change_group_dialog)
            update_all_uis()
        except Exception: pass

    # 🛠️ 管理者データグリッドのソート状態管理
    current_sort_column = 3
    current_sort_ascending = False

    def handle_admin_table_sort(e):
        nonlocal current_sort_column, current_sort_ascending
        if current_sort_column == e.column_index:
            current_sort_ascending = not current_sort_ascending
        else:
            current_sort_column = e.column_index
            current_sort_ascending = True
        admin_data_table.sort_column_index = current_sort_column
        admin_data_table.sort_ascending = current_sort_ascending
        update_admin_ui()

    def update_admin_ui():
        if current_player != "admin": return
        admin_data_table.rows.clear()
        try:
            users_res = supabase.table("users").select("username").execute()
            privacy_res = supabase.table("privacy").select("*").execute()
            records_res = supabase.table("records").select("*").execute()
            all_users = users_res.data or []
            all_privacy = privacy_res.data or []
            all_records = records_res.data or []

            group_map = {}
            for p in all_privacy:
                p_name = p.get("username") or p.get("player")
                if p_name: group_map[p_name] = str(p.get("group_number", "1"))

            summary_data = []
            try: search_keyword = admin_search_input.value.strip().lower()
            except Exception: search_keyword = ""

            for u in all_users:
                username = u["username"]
                if search_keyword and search_keyword not in username.lower(): continue

                user_records = [r for r in all_records if r["player"] == username]
                valid_scores = [r["final_score"] for r in user_records if r.get("final_score") is not None]
                max_score = max(valid_scores) if valid_scores else 0
                latest_date = max([r["date"] for r in user_records]) if user_records else "記録なし"
                user_group_str = group_map.get(username, "1")

                summary_data.append({"username": username, "group_str": user_group_str, "max_score": max_score, "latest_date": latest_date})

            if current_sort_column == 0: summary_data.sort(key=lambda x: x["username"], reverse=not current_sort_ascending)
            elif current_sort_column == 1: summary_data.sort(key=lambda x: x["group_str"], reverse=not current_sort_ascending)
            elif current_sort_column == 2: summary_data.sort(key=lambda x: x["latest_date"], reverse=not current_sort_ascending)
            elif current_sort_column == 3: summary_data.sort(key=lambda x: x["max_score"], reverse=not current_sort_ascending)

            for data in summary_data:
                is_admin = (data["username"].lower() == "admin")
                name_display = f"👑 {data['username']}" if is_admin else data["username"]
                admin_data_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(name_display, width=100, weight=ft.FontWeight.BOLD if is_admin else ft.FontWeight.NORMAL, color=ft.Colors.BLUE_600 if is_admin else ft.Colors.BLACK)),
                        ft.DataCell(ft.Text(data["group_str"], width=80)),
                        ft.DataCell(ft.Text(data["latest_date"], width=150, size=12)),
                        ft.DataCell(ft.Text(f"{data['max_score']}点", width=80, weight=ft.FontWeight.W_500, color=ft.Colors.BLUE_700)),
                    ])
                )
        except Exception as ex:
            admin_data_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(f"エラー: {ex}", color=ft.Colors.RED)), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text(""))]))
        page.update()

    def handle_new_register(e):
        # 1. 入力値の取得とバリデーション
        username = login_name_input.value.strip()
        password = login_pass_input.value.strip()

        if not username:
            show_alert("プレイヤー名を入力してください。")
            return
        if len(password) < 4:
            show_alert("パスワードは4桁以上で入力してください。")
            return

        try:
            # 2. ユーザーの重複チェック
            existing_user = supabase.table("users").select("username").eq("username", username).execute()
            if existing_user.data and len(existing_user.data) > 0:
                show_alert("このプレイヤー名は既に登録されています。")
                return

            # 3. パスワードのハッシュ化とデータ挿入
            hashed_pass = hash_password(password)
            
            # users テーブルへの追加
            supabase.table("users").insert({
                "username": username,
                "password": hashed_pass
            }).execute()

            # privacy（グループ管理等）テーブルへの追加（初期グループは 1）
            supabase.table("privacy").insert({
                "username": username,
                "group_number": "1"
            }).execute()

            # 4. 登録成功後の自動ログイン処理
            page.overlay.append(ft.SnackBar(ft.Text(f"🎉 {username} さんの登録が完了しました！"), open=True))
            handle_existing_login(None) # そのままログインさせる

        except Exception as ex:
            show_alert(f"新規登録に失敗しました: {ex}")

    def handle_change_password(e):
        if not current_player: return
        old_pass = mypage_old_pass.value.strip()
        new_pass = mypage_new_pass.value.strip()

        if not old_pass or not new_pass:
            show_alert("両方のパスワードを入力してください。")
            return
        if len(new_pass) < 4:
            show_alert("新しいパスワードは4桁以上で入力してください。")
            return

        try:
            # 現在のパスワードが合っているかDBを確認
            hashed_old = hash_password(old_pass)
            res = supabase.table("users").select("password").eq("username", current_player).execute()
            
            if not res.data or res.data[0]["password"] != hashed_old:
                show_alert("現在のパスワードが間違っています。")
                return

            # 新しいパスワードをハッシュ化して更新
            hashed_new = hash_password(new_pass)
            supabase.table("users").update({"password": hashed_new}).eq("username", current_player).execute()

            # 入力欄のクリアとダイアログを閉じる
            mypage_old_pass.value = ""
            mypage_new_pass.value = ""
            page.close(change_pass_dialog)
            
            # クライアントストレージの記憶も更新
            page.client_storage.set(STORAGE_REMEMBER_PASS, new_pass)
            
            page.overlay.append(ft.SnackBar(ft.Text("🔒 パスワードを変更しました"), open=True))
            page.update()
        except Exception as ex:
            show_alert(f"パスワード変更失敗: {ex}")

    def handle_save_secret_question(e):
        if not current_player: return
        question = mypage_question_input.value.strip()
        answer = mypage_answer_input.value.strip()

        if not question or not answer:
            show_alert("質問と答えの両方を入力してください。")
            return

        try:
            # 答えをハッシュ化して安全に保存
            hashed_answer = hash_password(answer)
            
            # 既存のprivacyデータがあるか確認
            priv_res = supabase.table("privacy").select("*").eq("username", current_player).execute()
            
            # カラム名が 'secret_question' と 'secret_answer' だと想定
            update_data = {
                "secret_question": question,
                "secret_answer": hashed_answer
            }
            
            if priv_res.data:
                # 既存レコードの更新
                p_key = "username" if "username" in priv_res.data[0] else "player"
                supabase.table("privacy").update(update_data).eq(p_key, current_player).execute()
            else:
                # なければ新規挿入
                update_data["username"] = current_player
                update_data["group_number"] = "1"
                supabase.table("privacy").insert(update_data).execute()

            mypage_question_input.value = ""
            mypage_answer_input.value = ""
            page.close(secret_question_dialog)
            
            page.overlay.append(ft.SnackBar(ft.Text("🛡️ 秘密の質問を設定しました"), open=True))
            page.update()
        except Exception as ex:
            show_alert(f"秘密の質問設定失敗: {ex}")
                
    def handle_rename(e):
        nonlocal current_player
        if not current_player: return
        new_name = edit_name_input.value.strip()

        if not new_name:
            show_alert("新しい名前を入力してください。")
            return
        if new_name == current_player:
            page.close(change_name_dialog)
            return

        try:
            # 重複チェック
            existing = supabase.table("users").select("username").eq("username", new_name).execute()
            if existing.data:
                show_alert("その名前は既に使われています。")
                return

            # 各テーブルの名前を一括更新 (※外部キー制約のON UPDATE CASCADEがない場合、手動更新が必要)
            supabase.table("users").update({"username": new_name}).eq("username", current_player).execute()
            
            # privacyテーブルの更新 (カラム名がusernameかplayerかで対応)
            priv_res = supabase.table("privacy").select("*").execute()
            if priv_res.data:
                p_key = "username" if "username" in priv_res.data[0] else "player"
                supabase.table("privacy").update({p_key: new_name}).eq(p_key, current_player).execute()
                
            # 過去の対戦記録(records)のプレイヤー名も更新
            supabase.table("records").update({"player": new_name}).eq("player", current_player).execute()

            # ローカルの管理状態を更新
            old_name = current_player
            current_player = new_name
            logged_in_user_text.value = f"👤 ログイン中: {current_player} さん"
            
            page.client_storage.set(STORAGE_REMEMBER_USER, new_name)
            page.close(change_name_dialog)
            
            update_all_uis()
            page.overlay.append(ft.SnackBar(ft.Text(f"👤 名前を {new_name} に変更しました"), open=True))
            page.update()
        except Exception as ex:
            show_alert(f"名前変更失敗: {ex}")

    def execute_delete_account():
        nonlocal current_player
        if not current_player: return

        try:
            # 関連データの削除
            supabase.table("records").delete().eq("player", current_player).execute()
            
            priv_res = supabase.table("privacy").select("*").execute()
            if priv_res.data:
                p_key = "username" if "username" in priv_res.data[0] else "player"
                supabase.table("privacy").delete().eq(p_key, current_player).execute()

            supabase.table("users").delete().eq("username", current_player).execute()

            # ストレージとセッションのクリア
            page.client_storage.remove(STORAGE_REMEMBER_USER)
            page.client_storage.remove(STORAGE_REMEMBER_PASS)
            current_player = None
            
            page.close(confirm_delete_dialog)
            
            # ログイン画面へ戻す
            page.controls.clear()
            page.add(login_view)
            page.overlay.append(ft.SnackBar(ft.Text("⚠️ アカウントを完全に削除しました"), open=True))
            page.update()
        except Exception as ex:
            show_alert(f"アカウント削除失敗: {ex}")

    def handle_forgot_check_user(e):
        target_user = forgot_name_input.value.strip()
        if not target_user:
            show_alert("プレイヤー名を入力してください。")
            return

        try:
            res = supabase.table("privacy").select("*").execute()
            user_priv = next((p for p in (res.data or []) if (p.get("username") or p.get("player")) == target_user), None)
            
            if not user_priv or not user_priv.get("secret_question"):
                forgot_question_text.value = "❌ 秘密の質問が登録されていないか、ユーザーが見つかりません"
                forgot_question_text.color = ft.Colors.RED
                page.update()
                return

            # 質問文を画面にセットして有効化
            forgot_question_text.value = f"❓ 質問: {user_priv.get('secret_question')}"
            forgot_question_text.color = ft.Colors.BLUE_600
            page.update()
        except Exception as ex:
            show_alert(f"ユーザー確認エラー: {ex}")

    def handle_forgot_reset_password(e):
        target_user = forgot_name_input.value.strip()
        answer = forgot_answer_input.value.strip()
        new_pass = forgot_new_pass_input.value.strip()

        if not target_user or not answer or not new_pass:
            show_alert("すべての項目を入力してください。")
            return
        if len(new_pass) < 4:
            show_alert("新しいパスワードは4桁以上必要です。")
            return

        try:
            # 登録されている答えのハッシュを取得
            res = supabase.table("privacy").select("*").execute()
            user_priv = next((p for p in (res.data or []) if (p.get("username") or p.get("player")) == target_user), None)
            
            if not user_priv or not user_priv.get("secret_answer"):
                show_alert("再設定手続きを行えません。")
                return

            # 回答の照合
            if hash_password(answer) != user_priv.get("secret_answer"):
                show_alert("秘密の質問の答えが間違っています。")
                return

            # パスワードを更新
            hashed_new_pass = hash_password(new_pass)
            supabase.table("users").update({"password": hashed_new_pass}).eq("username", target_user).execute()

            # ダイアログを閉じてフォームリセット
            page.close(forgot_dialog)
            login_name_input.value = target_user
            login_pass_input.value = new_pass
            
            page.overlay.append(ft.SnackBar(ft.Text("🎉 パスワードを再設定しました。ログインしてください。"), open=True))
            page.update()
        except Exception as ex:
            show_alert(f"パスワード再設定失敗: {ex}")

    def check_auto_login():
        saved_user = page.client_storage.get(STORAGE_REMEMBER_USER)
        saved_pass = page.client_storage.get(STORAGE_REMEMBER_PASS)
        
        # 記憶されたデータがあれば自動でログイン処理を走らせる
        if saved_user and saved_pass:
            login_name_input.value = saved_user
            login_pass_input.value = saved_pass
            # すでに定義済みのログイン処理に偽のイベント(None)を渡して実行
            handle_existing_login(None)


    # ─── 各種ダイアログの定義 ───
    change_name_dialog = ft.AlertDialog(title=ft.Text("👤 プレイヤー名の変更"), content=ft.Container(
        content=ft.Column([edit_name_input], spacing=10, tight=True), width=320, height=70), actions=[
        ft.TextButton("キャンセル", on_click=lambda e: page.close(change_name_dialog)),
        ft.ElevatedButton("名前を変更", on_click=handle_rename, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)],
                                        actions_alignment=ft.MainAxisAlignment.END)
    change_pass_dialog = ft.AlertDialog(title=ft.Text("🔒 パスワードの変更"), content=ft.Container(
        content=ft.Column([mypage_old_pass, mypage_new_pass], spacing=10, tight=True), width=320, height=140), actions=[
        ft.TextButton("キャンセル", on_click=lambda e: page.close(change_pass_dialog)),
        ft.ElevatedButton("変更を実行", on_click=handle_change_password, bgcolor=ft.Colors.BLUE_600,
                          color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)
    secret_question_dialog = ft.AlertDialog(title=ft.Text("🛡️ 秘密の質問の設定"), content=ft.Container(
        content=ft.Column([mypage_question_input, mypage_answer_input], spacing=10, tight=True), width=320, height=140),
                                            actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(
                                                secret_question_dialog)),
                                                     ft.ElevatedButton("設定を保存",
                                                                       on_click=handle_save_secret_question,
                                                                       bgcolor=ft.Colors.BLUE_600,
                                                                       color=ft.Colors.WHITE)],
                                            actions_alignment=ft.MainAxisAlignment.END)

    confirm_delete_dialog = ft.AlertDialog(title=ft.Text("⚠️ 最終確認"), content=ft.Text(
        "本当にアカウントを削除しますか？"), actions=[
        ft.TextButton("キャンセル", on_click=lambda e: page.close(confirm_delete_dialog)),
        ft.TextButton("削除する", style=ft.ButtonStyle(color=ft.Colors.RED_600),
                      on_click=lambda e: execute_delete_account())], actions_alignment=ft.MainAxisAlignment.END)

    forgot_dialog = ft.AlertDialog(title=ft.Text("🔑 パスワードの再設定"), content=ft.Container(content=ft.Column(
        [forgot_name_input,
         ft.ElevatedButton("1. 質問を確認する", on_click=handle_forgot_check_user, bgcolor=ft.Colors.BLUE_600,
                           color=ft.Colors.WHITE), ft.Divider(height=10), forgot_question_text, forgot_answer_input,
         forgot_new_pass_input], spacing=10, tight=True), width=320, height=325), actions=[
        ft.TextButton("キャンセル", on_click=lambda e: page.close(forgot_dialog)),
        ft.ElevatedButton("2. パスワードを更新", on_click=handle_forgot_reset_password, bgcolor=ft.Colors.GREEN_700,
                          color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)

    change_group_dialog = ft.AlertDialog(
        title=ft.Text("🔢 グループ番号の管理"),
        content=ft.Container(
            content=ft.ListView(
                controls=[
                    group_inputs_container,
                    ft.TextButton(
                        "グループを追加",
                        icon=ft.Icons.ADD,
                        on_click=add_blank_group_input_row
                    )
                ],
                spacing=10,
            ),
            width=320,
            height=250
        ),
        actions=[
            ft.TextButton("キャンセル", on_click=lambda e: page.close(change_group_dialog)),
            ft.ElevatedButton("変更を保存", on_click=handle_save_group_number, bgcolor=ft.Colors.BLUE_600,
                              color=ft.Colors.WHITE)
        ],
        actions_alignment=ft.MainAxisAlignment.END
    )

    action_buttons_row = ft.ResponsiveRow(
        controls=[ft.Container(content=register_btn, col={"xs": 12, "md": 6}, alignment=ft.alignment.center, padding=5),
                  ft.Container(content=login_btn, col={"xs": 12, "md": 6}, alignment=ft.alignment.center, padding=5)],
        alignment=ft.MainAxisAlignment.CENTER)

    global_header_bar = ft.Container(content=ft.Row(controls=[logged_in_user_text,
                                                              ft.TextButton("ログアウト", icon=ft.Icons.LOGOUT,
                                                                            style=ft.ButtonStyle(
                                                                                color=ft.Colors.RED_600,
                                                                                icon_color=ft.Colors.RED_600),
                                                                            on_click=handle_logout)],
                                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=10,
                                     bgcolor=ft.Colors.GREY_100, border_radius=8)
    admin_search_input = ft.TextField(label="プレイヤー名で検索", prefix_icon=ft.Icons.SEARCH,
                                      on_change=lambda e: update_admin_ui(), expand=True)

    admin_data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("プレイヤー名", weight=ft.FontWeight.BOLD), on_sort=handle_admin_table_sort),
            ft.DataColumn(ft.Text("グループ", weight=ft.FontWeight.BOLD), on_sort=handle_admin_table_sort),
            ft.DataColumn(ft.Text("最終ログイン日時", weight=ft.FontWeight.BOLD), on_sort=handle_admin_table_sort),
            ft.DataColumn(ft.Text("最高得点", weight=ft.FontWeight.BOLD), on_sort=handle_admin_table_sort),
        ],
        rows=[], heading_row_color=ft.Colors.BLUE_GREY_50, divider_thickness=1, horizontal_margin=10, column_spacing=10,
        sort_column_index=3, sort_ascending=False, expand=True
    )

    admin_tab_view = ft.Column(
        controls=[
            ft.Container(content=ft.Text("🛠️ 管理者コントロールパネル", size=16, weight=ft.FontWeight.BOLD,
                                         color=ft.Colors.BLUE_GREY_800), padding=12),
            ft.Container(content=ft.Row([admin_search_input]), padding=ft.padding.only(left=10, right=10, bottom=5)),
            ft.Container(height=5),
            ft.ListView(controls=[admin_data_table], expand=True)
        ], expand=True
    )

    login_view = ft.Container(content=ft.Column(
        controls=[ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80, color=ft.Colors.BLUE_600),
                  ft.Text(value="プレイヤー認証", size=24, weight=ft.FontWeight.BOLD), ft.Container(height=15),
                  ft.Container(content=login_name_input, width=300), ft.Container(content=login_pass_input, width=300),
                  ft.Container(height=10), ft.Container(content=action_buttons_row, width=340), ft.Container(height=10),
                  ft.TextButton("🔑 パスワードを忘れた場合はこちら",
                                on_click=lambda e: (setattr(forgot_name_input, "value", ""),
                                                    setattr(forgot_answer_input, "value", ""),
                                                    setattr(forgot_new_pass_input, "value", ""),
                                                    setattr(forgot_question_text, "value",
                                                            "プレイヤー名を入力して「質問を確認」を押してください"),
                                                    page.open(forgot_dialog)))],
        alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        padding=20, alignment=ft.alignment.center, expand=True, visible=True)

    # 🌾 部屋数専用の選択＆カウンターUI定義（未定義順エラー対策でここに配置）
    def create_room_selector(color):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(content=room_type_switch, width=110, alignment=ft.alignment.center_left),
                    ft.Row(
                        controls=[
                            ft.Container(content=ft.TextButton("-3", style=ft.ButtonStyle(color=color, padding=0), on_click=lambda e: adjust_count("room_count", -3)), width=38, alignment=ft.alignment.center),
                            ft.Container(content=ft.TextButton("-1", style=ft.ButtonStyle(color=color, padding=0), on_click=lambda e: adjust_count("room_count", -1)), width=38, alignment=ft.alignment.center),
                            ft.Container(content=ui_text_map["room_count"], width=30, alignment=ft.alignment.center),
                            ft.Container(content=ft.TextButton("+1", style=ft.ButtonStyle(color=color, padding=0), on_click=lambda e: adjust_count("room_count", 1)), width=38, alignment=ft.alignment.center),
                            ft.Container(content=ft.TextButton("+3", style=ft.ButtonStyle(color=color, padding=0), on_click=lambda e: adjust_count("room_count", 3)), width=38, alignment=ft.alignment.center)
                        ], spacing=0, alignment=ft.MainAxisAlignment.END
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER
            ), padding=4, border=ft.border.all(1, ft.Colors.GREY_300), border_radius=10, bgcolor=ft.Colors.WHITE
        )

    # 🌾 アグリコラ全15大項目のUI入力フォーム配置
    calc_tab_view = ft.ListView(
        controls=[
            ft.Container(
                content=ft.Column([ft.Text("現在のアグリコラ合計得点", size=14, color=ft.Colors.GREY_600), score_display],
                                  alignment=ft.MainAxisAlignment.CENTER,
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center, padding=10),
            ft.Container(
                content=ft.Column([
                    create_agricola_selector("🟫 畑の枚数", "field", ft.Colors.BROWN_600),
                    create_agricola_selector("🟩 牧場の数", "pasture", ft.Colors.GREEN_600),
                    create_agricola_selector("🌾 小麦の数", "grain", ft.Colors.AMBER_600),
                    create_agricola_selector("🥕 野菜の数", "vegetable", ft.Colors.ORANGE_600),
                    create_agricola_selector("🐑 羊の頭数", "sheep", ft.Colors.BLUE_GREY_400),
                    create_agricola_selector("🐗 猪の頭数", "wild_boar", ft.Colors.BROWN_400),
                    create_agricola_selector("🐂 牛の頭数", "cattle", ft.Colors.BLUE_GREY_700),
                    
                    ft.Divider(height=20, thickness=1, color=ft.Colors.GREY_400),
                    
                    create_agricola_selector("❌ 未使用スペース (マイナス用)", "empty_space", ft.Colors.RED_400),
                    create_agricola_selector("🏠 柵の中の厩", "stable", ft.Colors.AMBER_800),
                    
                    create_room_selector(ft.Colors.DEEP_ORANGE_600),
                    
                    create_agricola_selector("👨‍👩‍👧 家族の人数", "family", ft.Colors.BLUE_400),
                    create_agricola_selector("🃏 カードの得点 (進歩/職業)", "card_points", ft.Colors.PURPLE_400),
                    create_agricola_selector("🎁 各種ボーナス点", "bonus_points", ft.Colors.PINK_400),
                    create_agricola_selector("🥺 乞食カードの枚数", "begging_card", ft.Colors.RED_700),
                ], spacing=12), padding=10),
            ft.Container(content=ft.Row(controls=[
                ft.OutlinedButton("リセット", icon=ft.Icons.REFRESH, on_click=reset_current_game,
                                  style=ft.ButtonStyle(color=ft.Colors.RED_600, icon_color=ft.Colors.RED_600)),
                ft.ElevatedButton("ゲーム記録を保存", icon=ft.Icons.SAVE, on_click=save_current_game,
                                  bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)],
                alignment=ft.MainAxisAlignment.SPACE_EVENLY), padding=15)
        ],
        expand=True,
        spacing=10
    )

    mypage_tab_view = ft.Column(
        controls=[
            ft.Container(content=ft.Text("スコア一覧", size=16, weight=ft.FontWeight.BOLD,
                                         color=ft.Colors.BLUE_GREY_700),
                         padding=ft.padding.only(left=15, top=15, right=15)),
            ft.Container(content=my_records_list, height=220),
            ft.Container(height=5),
            ft.Container(
                content=ft.Column([
                    ft.Text("👤 各種設定メニュー :", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Container(height=3),
                    ft.Row(
                        controls=[
                            ft.IconButton(ft.Icons.ACCOUNT_CIRCLE, tooltip="名前変更",
                                          on_click=lambda e: page.open(change_name_dialog), icon_color=ft.Colors.WHITE,
                                          icon_size=26),
                            ft.IconButton(ft.Icons.NUMBERS, tooltip="グループ変更",
                                          on_click=open_change_group_dialog, icon_color=ft.Colors.WHITE,
                                          icon_size=26),
                            ft.IconButton(ft.Icons.LOCK, tooltip="パスワード変更",
                                          on_click=lambda e: page.open(change_pass_dialog), icon_color=ft.Colors.WHITE,
                                          icon_size=26),
                            ft.IconButton(ft.Icons.SHIELD, tooltip="秘密の質問設定",
                                          on_click=lambda e: page.open(secret_question_dialog),
                                          icon_color=ft.Colors.WHITE, icon_size=26),
                            ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="アカウントの完全削除",
                                          on_click=lambda e: page.open(confirm_delete_dialog),
                                          icon_color=ft.Colors.RED_300, icon_size=26)
                        ],
                        wrap=True, spacing=8, run_spacing=5, alignment=ft.MainAxisAlignment.START
                    )
                ]),
                padding=12, bgcolor=ft.Colors.BLUE_GREY_600, border_radius=10,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_700)
            ),
        ],
        scroll=ft.ScrollMode.AUTO
    )

    ranking_tab_view = ft.Column(
        controls=[
            ft.Container(
                content=ft.Row([
                    ft.Container(content=ranking_title_text, expand=True),
                    ranking_group_dropdown
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15
            ),
            ft.Container(content=ranking_list, height=430)
        ]
    )

    main_tab_view = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="得点計算", icon=ft.Icons.CALCULATE, content=calc_tab_view),
            ft.Tab(text="マイページ", icon=ft.Icons.PERSON, content=mypage_tab_view),
            ft.Tab(text="ランキング", icon=ft.Icons.EMOJI_EVENTS, content=ranking_tab_view),
        ],
        expand=True,
        on_change=lambda e: (
            (refresh_ranking_dropdown_options(), update_ranking_ui()) if main_tab_view.selected_index == 2 else None,
            page.update()
        )
    )

    authenticated_view = ft.Column(
        controls=[
            global_header_bar,
            main_tab_view
        ],
        expand=True,
        visible=False
    )

    page.controls.clear()
    page.add(login_view, authenticated_view)

    calculate_total_score_ui_only()
    update_all_uis()

    login_name_input.value = page.client_storage.get(STORAGE_REMEMBER_USER) or ""
    login_pass_input.value = page.client_storage.get(STORAGE_REMEMBER_PASS) or ""

    check_auto_login()
    page.update()


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    ft.app(target=main, host="0.0.0.0", view=ft.AppView.WEB_BROWSER, port=port)
