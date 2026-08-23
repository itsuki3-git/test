import hashlib
import os
from datetime import datetime, timezone, timedelta
import flet as ft
from supabase import create_client, Client


def main(page: ft.Page):
    page.title = "フルーツ得点計算 & プレイヤー管理"
    page.window_width = 450
    page.window_height = 700
    page.theme_mode = ft.ThemeMode.LIGHT

    FRUIT_POINTS = {"apple": 10, "orange": 5, "grape": 15}

    # =========================================================================
    # ⚠️ あなたのSupabaseの情報をここに貼り付けてください
    # =========================================================================
    SUPABASE_URL = "https://tqufugshygdknyfgrsxh.supabase.co"
    SUPABASE_KEY = "sb_publishable_fMuDE8giATkTj2UOjCyThg_wowMJz0s"
    # =========================================================================

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    current_player = None
    my_group_list = [1]
    active_ranking_group = 1
    counts = {"apple": 0, "orange": 0, "grape": 0}
    STORAGE_REMEMBER_USER = "fruit_app_remembered_user"
    STORAGE_REMEMBER_PASS = "fruit_app_remembered_pass"

    # --- UIコンポーネント定義 ---
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
    apple_count_text = ft.Text(value="0", size=20, weight=ft.FontWeight.BOLD, width=40, text_align=ft.TextAlign.CENTER)
    orange_count_text = ft.Text(value="0", size=20, weight=ft.FontWeight.BOLD, width=40, text_align=ft.TextAlign.CENTER)
    grape_count_text = ft.Text(value="0", size=20, weight=ft.FontWeight.BOLD, width=40, text_align=ft.TextAlign.CENTER)

    edit_name_input = ft.TextField(label="名前を編集", expand=True)
    ranking_switch = ft.Switch(label="ランキングに名前と記録を表示する", value=True,
                               on_change=lambda e: handle_privacy_change(e))
    mypage_group_input = ft.TextField(label="所属グループ番号 (複数時はカンマ区切り)", hint_text="例: 1, 3, 5",
                                      expand=True)

    my_records_list = ft.ListView(expand=True, spacing=10, padding=10)
    ranking_list = ft.ListView(expand=True, spacing=10, padding=10)

    ranking_title_text = ft.Text(value="総合ハイスコアランキング (グループ1)", size=16, weight=ft.FontWeight.BOLD,
                                 color=ft.Colors.BLUE_GREY_700)
    ranking_group_dropdown = ft.Dropdown(
        label="表示グループ切り替え",
        width=180,
        options=[ft.dropdown.Option("1", "グループ 1")],
        value="1",
        on_change=lambda e: handle_ranking_group_switch(e)
    )

    mypage_old_pass = ft.TextField(label="現在のパスワード", password=True)
    mypage_new_pass = ft.TextField(label="新しいパスワード (4桁以上)", password=True)
    mypage_question_input = ft.TextField(label="新しく登録する「秘密の質問」",
                                         hint_text="例: 初めて飼ったペットの名前は？")
    mypage_answer_input = ft.TextField(label="質問の答え", hint_text="答えを入力してください")

    def show_alert(message, title="エラー"):
        alert_dialog = ft.AlertDialog(title=ft.Text(title), content=ft.Text(message))
        alert_dialog.actions = [
            ft.TextButton("OK", on_click=lambda e: (setattr(alert_dialog, "open", False), page.update()))]
        page.open(alert_dialog)

    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def get_jst_now_str() -> str:
        jst = timezone(timedelta(hours=9))
        return datetime.now(jst).strftime("%Y/%m/%d %H:%M")

    def create_fruit_selector(label, fruit_key, count_text_component, color):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(f"{label} ({FRUIT_POINTS[fruit_key]}点)", size=16, weight=ft.FontWeight.W_500, expand=True),
                    ft.Row(
                        controls=[
                            ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE_OUTLINED, icon_color=color,
                                          on_click=lambda e: adjust_count(fruit_key, -1)),
                            count_text_component,
                            ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=color,
                                          on_click=lambda e: adjust_count(fruit_key, 1))
                        ], spacing=5
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ), padding=10, border=ft.border.all(1, ft.Colors.GREY_300), border_radius=10, bgcolor=ft.Colors.WHITE
        )

    def calculate_total_score_ui_only():
        total = (counts["apple"] * FRUIT_POINTS["apple"] + counts["orange"] * FRUIT_POINTS["orange"] + counts["grape"] *
                 FRUIT_POINTS["grape"])
        score_display.value = str(total)
        return total

    def adjust_count(fruit, delta):
        new_count = counts[fruit] + delta
        if new_count >= 0:
            counts[fruit] = new_count
            if fruit == "apple":
                apple_count_text.value = str(new_count)
            elif fruit == "orange":
                orange_count_text.value = str(new_count)
            elif fruit == "grape":
                grape_count_text.value = str(new_count)
            calculate_total_score_ui_only()
            page.update()

    def reset_current_game(e):
        for fruit in counts: counts[fruit] = 0
        apple_count_text.value, orange_count_text.value, grape_count_text.value = "0", "0", "0"
        calculate_total_score_ui_only()
        if e: page.update()

    def update_all_uis():
        update_my_records_ui()
        update_ranking_ui()
        if current_player == "admin": update_admin_ui()

    def update_my_records_ui():
        my_records_list.controls.clear()
        if not current_player: return
        try:
            res = supabase.table("records").select("*").execute()
            my_filtered = [r for r in (res.data or []) if
                           r.get("player") == current_player and r.get("final_score", 0) > 0]
        except Exception as ex:
            my_records_list.controls.append(ft.Text(f"データ取得エラー: {ex}", color=ft.Colors.RED))
            page.update()
            return
        if not my_filtered:
            my_records_list.controls.append(
                ft.Text("あなたの保存された記録はありません", italic=True, color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER))
        else:
            for record in sorted(my_filtered, key=lambda x: x["id"], reverse=True):
                my_records_list.controls.append(ft.Container(content=ft.Row(controls=[ft.Column(
                    [ft.Text(f"合計得点: {record['final_score']} 点", size=18, weight=ft.FontWeight.BOLD,
                             color=ft.Colors.BLUE_700),
                     ft.Text(value=f"内訳: 🍎{record['apple']} 🍊{record['orange']} 🍇{record['grape']}", size=13,
                             color=ft.Colors.GREY_700),
                     ft.Text(value=f"保存日時: {record['date']}", size=11, color=ft.Colors.GREY_500)], expand=True),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_FOREVER,
                        icon_color=ft.Colors.RED_600,
                        on_click=lambda e, idx=record[
                            "id"]: delete_saved_record(
                            idx))],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=12, border=ft.border.all(1, ft.Colors.BLUE_100),
                    border_radius=8, bgcolor=ft.Colors.BLUE_50))
        page.update()

    def update_ranking_ui():
        """どんな型エラーやデータ破損が起きても絶対にクラッシュしない超安全版"""
        ranking_list.controls.clear()

        if str(active_ranking_group) == "0":
            ranking_title_text.value = "総合ハイスコアランキング (グループ 0: 管理者専用)"
        else:
            ranking_title_text.value = f"総合ハイスコアランキング (グループ {active_ranking_group})"

        try:
            # 1. privacy テーブルから全ユーザー情報を安全に取得
            privacy_res = supabase.table("privacy").select("*").execute()
            privacy_list = privacy_res.data or []

            try:
                target_g = int(active_ranking_group)
            except Exception:
                target_g = 1

            same_group_users = []
            for p in privacy_list:
                if not isinstance(p, dict):
                    continue
                
                # カラム名が 'username' と 'player' のどちらでも動くように安全に名前を取得
                p_name = p.get("username") or p.get("player")
                if not p_name:
                    continue
                
                # 💡 型エラー防御：データが数値(int)でも文字列(str)でも安全にリスト化する
                raw_g_val = p.get("group_number", 1)
                user_g_list = []
                
                if isinstance(raw_g_val, int):
                    user_g_list.append(raw_g_val)
                elif raw_g_val is not None:
                    # 文字列としてカンマ分割を試みる（全角・半角対応）
                    for token in str(raw_g_val).replace("，", ",").split(","):
                        clean_token = token.strip()
                        if clean_token.isdigit():
                            user_g_list.append(int(clean_token))

                if target_g in user_g_list:
                    same_group_users.append(p_name)

            # 2. records テーブルからスコアデータを安全に取得
            records_res = supabase.table("records").select("*").execute()
            records_raw = records_res.data or []
            
            # スコアが存在し、かつplayer名がしっかりと入っているレコードのみを厳選
            all_records = []
            for r in records_raw:
                if isinstance(r, dict) and r.get("player") and r.get("final_score", 0) > 0:
                    all_records.append(r)

            # 3. 該当グループのレコードに絞り込み
            visible_records = [r for r in all_records if r["player"] in same_group_users]

            # 💡 表示できるスコアデータが1件もない場合のメッセージ対応
            if not visible_records:
                ranking_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Icon(ft.Icons.LEADERBOARD_OUTLINED, size=40, color=ft.Colors.GREY_400),
                            ft.Text("このグループに保存されている記録はありません", color=ft.Colors.GREY_500, size=14),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=30
                    )
                )
            else:
                # プレイヤーごとの自己ベスト（最高スコア）を算出
                user_best_records = {}
                for r in visible_records:
                    p_name = r["player"]
                    if p_name not in user_best_records or r["final_score"] > user_best_records[p_name]["final_score"]:
                        user_best_records[p_name] = r

                sorted_records = sorted(list(user_best_records.values()), key=lambda x: x["final_score"], reverse=True)

                # ランキングUIカードの生成
                for index, record in enumerate(sorted_records):
                    rank = index + 1
                    rank_color = ft.Colors.AMBER_500 if rank == 1 else (ft.Colors.BLUE_GREY_300 if rank == 2 else (
                        ft.Colors.BROWN_400 if rank == 3 else ft.Colors.BLUE_GREY_700))
                    rank_text = f"🥇 {rank}位" if rank == 1 else (
                        f"🥈 {rank}位" if rank == 2 else (f"🥉 {rank}位" if rank == 3 else f"  {rank}位"))
                    
                    ranking_list.controls.controls.append(
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Text(rank_text, size=18, weight=ft.FontWeight.BOLD, color=rank_color, width=60),
                                    ft.Column([
                                        ft.Text(f"{record['player']}", size=15, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
                                        ft.Text(f"内訳: 🍎{record['apple']} 🍊{record['orange']} 🍇{record['grape']}", size=12, color=ft.Colors.GREY_600)
                                    ], expand=True),
                                    ft.Text(f"{record['final_score']} 点", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                            ), padding=12, border=ft.border.all(1, ft.Colors.GREY_200), border_radius=8, bgcolor=ft.Colors.WHITE
                        )
                    )
        except Exception as ex:
            # 💡 もしこれでもエラーが起きた場合は、画面上に直接エラー文を吐き出す
            ranking_list.controls.append(
                ft.Container(
                    content=ft.Text(f"⚠️ ランキング処理内でクラッシュが発生しました:\n{str(ex)}", color=ft.Colors.RED_600, weight=ft.FontWeight.BOLD),
                    padding=20,
                    bgcolor=ft.Colors.RED_50,
                    border_radius=8
                )
            )
        
        # 何が起きても必ず最後に画面を更新する
        page.update()

    def save_current_game(e):
        if not current_player: return
        total_score = calculate_total_score_ui_only()
        if total_score == 0: show_alert("0点の記録は保存できません。"); return
        try:
            supabase.table("records").insert(
                {"player": current_player, "final_score": total_score, "apple": counts["apple"],
                 "orange": counts["orange"], "grape": counts["grape"], "date": get_jst_now_str()}).execute()
        except Exception as ex:
            show_alert(f"記録保存失敗: {ex}");
            return
        reset_current_game(None)
        update_all_uis()
        page.overlay.append(ft.SnackBar(ft.Text(f"{current_player} の記録を保存しました！"), open=True))
        page.update()

    def delete_saved_record(target_id):
        try:
            supabase.table("records").delete().eq("id", target_id).execute()
        except Exception:
            return
        update_all_uis()

    def refresh_ranking_dropdown_options():
        current_value = ranking_group_dropdown.value
        ranking_group_dropdown.options.clear()

        if current_player == "admin":
            try:
                all_priv = supabase.table("privacy").select("group_number").execute()
                detected_groups = {0}

                if all_priv.data:
                    for row in all_priv.data:
                        raw_val = row.get("group_number")
                        if raw_val:
                            for token in str(raw_val).replace("，", ",").split(","):
                                if (t := token.strip()).isdigit():
                                    detected_groups.add(int(t))

                for g in sorted(list(detected_groups)):
                    label_text = "グループ 0 (管理者専用)" if g == 0 else f"グループ {g}"
                    ranking_group_dropdown.options.append(ft.dropdown.Option(str(g), label_text))
            except Exception:
                ranking_group_dropdown.options.append(ft.dropdown.Option("0", "グループ 0 (管理者専用)"))
        else:
            for g in my_group_list:
                ranking_group_dropdown.options.append(ft.dropdown.Option(str(g), f"グループ {g}"))

        # ⭕ 修正後: 存在しない文字列がDropdownの初期値に代入されるのを絶対に防ぐガード
        if current_player == "admin":
            ranking_group_dropdown.value = "0"
        else:
            # my_group_listの最初の1つの要素を文字列にして安全に代入する
            ranking_group_dropdown.value = str(my_group_list[0]) if (my_group_list and len(my_group_list) > 0) else "1"
            
        page.update()

    def handle_ranking_group_switch(e):
        nonlocal active_ranking_group
        active_ranking_group = e.control.value
        update_ranking_ui()

    def handle_existing_login(e):
        nonlocal current_player, my_group_list, active_ranking_group
        input_name = login_name_input.value.strip()
        input_pass = login_pass_input.value.strip()
        if not input_name or not input_pass:
            show_alert("プレイヤー名とパスワードを入力してください。")
            return
        try:
            hashed_pass = hash_password(input_pass)
            res = supabase.table("users").select("username").eq("username", input_name).eq("password",
                                                                                           hashed_pass).execute()
            if not res.data or len(res.data) == 0:
                show_alert("名前またはパスワードが間違っています。")
                return

            page.client_storage.set(STORAGE_REMEMBER_USER, input_name)
            page.client_storage.set(STORAGE_REMEMBER_PASS, input_pass)

            priv_res = supabase.table("privacy").select("*").execute()
            user_privacy_data = None
            if priv_res.data:
                for p in priv_res.data:
                    p_name = p.get("username") or p.get("player")
                    if p_name == input_name:
                        user_privacy_data = p
                        break

            if user_privacy_data:
                ranking_switch.value = user_privacy_data.get("is_visible", True)
                raw_group_str = str(user_privacy_data.get("group_number", "1"))

                if input_name.lower() == "admin":
                    raw_group_str = "0"
                    p_key = "username" if "username" in user_privacy_data else "player"
                    supabase.table("privacy").update({"group_number": "0"}).eq(p_key, "admin").execute()

                mypage_group_input.value = raw_group_str

                my_group_list = []
                for x in raw_group_str.replace("，", ",").split(","):
                    if (x_strip := x.strip()).isdigit():
                        my_group_list.append(int(x_strip))
                if not my_group_list:
                    my_group_list = [0] if input_name.lower() == "admin" else [1]
            else:
                ranking_switch.value = True
                if input_name.lower() == "admin":
                    my_group_list = [0]
                    mypage_group_input.value = "0"
                    supabase.table("privacy").insert(
                        {"username": "admin", "is_visible": True, "group_number": "0"}).execute()
                else:
                    my_group_list = [1]
                    mypage_group_input.value = "1"

            if input_name.lower() == "admin":
                active_ranking_group = 0
            else:
                active_ranking_group = my_group_list[0] if my_group_list else 1

            refresh_ranking_dropdown_options()
        except Exception as ex:
            show_alert(f"ログインエラー: {ex}")
            return
        enter_game_session(input_name, f"👤 {input_name} さんとしてログインしました！")

    def enter_game_session(username, success_message):
        nonlocal current_player
        current_player = username
        logged_in_user_text.value = f"👤 ログイン中: {current_player} さん"
        edit_name_input.value = current_player
        try:
            res = supabase.table("users").select("secret_question").eq("username", current_player).execute()
            if res.data and len(res.data) > 0:
                mypage_question_input.value = res.data.get("secret_question") or ""
                mypage_answer_input.value = ""
        except Exception:
            pass

        # 💡 修正のコア：グレーの箱を残さないよう、ページから login_view を完全に消去して authenticated_view だけを再配置する！
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


    def check_auto_login():
        nonlocal my_group_list, active_ranking_group
        saved_user = page.client_storage.get(STORAGE_REMEMBER_USER)
        saved_pass = page.client_storage.get(STORAGE_REMEMBER_PASS)
        if saved_user and saved_pass:
            try:
                hashed_pass = hash_password(saved_pass)
                res = supabase.table("users").select("username").eq("username", saved_user).eq("password",
                                                                                               hashed_pass).execute()
                if res.data and len(res.data) > 0:
                    priv_res = supabase.table("privacy").select("*").execute()
                    user_privacy_data = None
                    if priv_res.data:
                        for p in priv_res.data:
                            p_name = p.get("username") or p.get("player")
                            if p_name == saved_user:
                                user_privacy_data = p
                                break

                    if user_privacy_data:
                        ranking_switch.value = user_privacy_data.get("is_visible", True)
                        raw_group_str = str(user_privacy_data.get("group_number", "1"))

                        if saved_user.lower() == "admin":
                            raw_group_str = "0"
                            p_key = "username" if "username" in user_privacy_data else "player"
                            supabase.table("privacy").update({"group_number": "0"}).eq(p_key, "admin").execute()

                        mypage_group_input.value = raw_group_str

                        my_group_list = []
                        for x in raw_group_str.replace("，", ",").split(","):
                            if (x_strip := x.strip()).isdigit():
                                my_group_list.append(int(x_strip))
                        if not my_group_list:
                            my_group_list = [0] if saved_user.lower() == "admin" else [1]
                    else:
                        ranking_switch.value = True
                        if saved_user.lower() == "admin":
                            my_group_list = [0]
                            mypage_group_input.value = "0"
                        else:
                            my_group_list = [1]
                            mypage_group_input.value = "1"

                    if saved_user.lower() == "admin":
                        active_ranking_group = 0
                    else:
                        active_ranking_group = my_group_list[0] if my_group_list else 1

                    refresh_ranking_dropdown_options()
                    enter_game_session(saved_user, f"🚀 おかえりなさい！ {saved_user} さん")
            except Exception:
                pass

    def handle_logout(e):
        nonlocal current_player
        current_player = None
        login_name_input.value = page.client_storage.get(STORAGE_REMEMBER_USER) or ""
        login_pass_input.value = page.client_storage.get(STORAGE_REMEMBER_PASS) or ""
        
        # 💡 ログアウト時はログイン画面だけを配置し直す
        page.controls.clear()
        page.add(login_view)
        login_view.visible = True
        page.update()


    def handle_change_password(e):
        old_pass = mypage_old_pass.value.strip()
        new_pass = mypage_new_pass.value.strip()
        if not old_pass or not new_pass:
            show_alert("現在のパスワードと新しいパスワードを入力してください。")
            return
        if len(new_pass) < 4:
            show_alert("新しいパスワードは4桁以上で入力してください。")
            return
        try:
            hashed_old = hash_password(old_pass)
            res = supabase.table("users").select("username").eq("username", current_player).eq("password",
                                                                                               hashed_old).execute()
            if not res.data:
                show_alert("現在のパスワードが間違っています。")
                return

            hashed_new = hash_password(new_pass)
            supabase.table("users").update({"password": hashed_new}).eq("username", current_player).execute()
            page.client_storage.set(STORAGE_REMEMBER_PASS, new_pass)
            mypage_old_pass.value = ""
            mypage_new_pass.value = ""
            page.close(change_pass_dialog)
            show_alert("パスワードを変更しました！", title="成功")
        except Exception as ex:
            show_alert(f"パスワード変更失敗: {ex}")

    def handle_save_secret_question(e):
        q = mypage_question_input.value.strip()
        a = mypage_answer_input.value.strip()
        if not q or not a:
            show_alert("質問と答えの両方を入力してください。")
            return
        try:
            hashed_answer = hash_password(a)
            supabase.table("users").update({"secret_question": q, "secret_answer": hashed_answer}).eq("username",
                                                                                                      current_player).execute()
            mypage_answer_input.value = ""
            page.close(secret_question_dialog)
            show_alert("秘密の質問と答えを保存しました！", title="成功")
        except Exception as ex:
            show_alert(f"保存失敗: {ex}")

    def handle_save_group_number(e):
        nonlocal my_group_list
        grp_str = mypage_group_input.value.strip()
        if not grp_str:
            show_alert("グループ番号を入力してください。")
            return

        parsed_list = []
        for x in grp_str.replace("，", ",").split(","):
            x_strip = x.strip()
            if x_strip:
                if not x_strip.isdigit():
                    show_alert("グループ番号には半角数字とカンマのみを入力してください。")
                    return

                group_num = int(x_strip)
                if current_player != "admin" and group_num == 0:
                    show_alert("「グループ0」は管理者専用の所属枠です。他のグループ番号を設定してください。")
                    return

                parsed_list.append(group_num)

        if not parsed_list:
            show_alert("有効なグループ番号が見つかりませんでした。")
            return

        try:
            clean_str = ", ".join([str(n) for n in parsed_list])
            
            priv_res = supabase.table("privacy").select("*").eq("username", current_player).execute()
            p_key = "username" if priv_res.data else "player"
            
            supabase.table("privacy").update({"group_number": clean_str}).eq(p_key, current_player).execute()
            my_group_list = parsed_list
            mypage_group_input.value = clean_str
            refresh_ranking_dropdown_options()
            page.close(change_group_dialog)
            update_all_uis()
            show_alert(f"所属グループを「{clean_str}」に変更しました！", title="成功")
        except Exception as ex:
            show_alert(f"グループ変更失敗: {ex}")

    def handle_forgot_check_user(e):
        name = forgot_name_input.value.strip()
        if not name:
            show_alert("プレイヤー名を入力してください。")
            return
        try:
            res = supabase.table("users").select("username", "secret_question").execute()
            user_found = None
            for u in (res.data or []):
                if u.get("username") == name:
                    user_found = u
                    break
            if not user_found:
                forgot_question_text.value = "❌ そのプレイヤー名は登録されていません。"
            else:
                if not user_found.get("secret_question"):
                    forgot_question_text.value = "⚠ 秘密の質問が設定されていません。"
                else:
                    forgot_question_text.value = f"❓ 質問: {user_found['secret_question']}"
        except Exception as ex:
            forgot_question_text.value = f"エラー: {ex}"
        page.update()

    def handle_forgot_reset_password(e):
        name = forgot_name_input.value.strip()
        ans = forgot_answer_input.value.strip()
        new_p = forgot_new_pass_input.value.strip()
        if not name or not ans or not new_p:
            show_alert("すべての項目を入力してください。")
            return
        if len(new_p) < 4:
            show_alert("新しいパスワードは4桁以上で入力してください。")
            return
        try:
            res = supabase.table("users").select("username", "secret_answer").execute()
            user_found = None
            for u in (res.data or []):
                if u.get("username") == name:
                    user_found = u
                    break
            if not user_found or user_found.get("secret_answer") != hash_password(ans):
                show_alert("質問の答えが間違っています。")
                return

            hashed_new = hash_password(new_p)
            supabase.table("users").update({"password": hashed_new}).eq("username", name).execute()
            page.client_storage.remove(STORAGE_REMEMBER_USER)
            page.client_storage.remove(STORAGE_REMEMBER_PASS)
            login_name_input.value = ""
            login_pass_input.value = ""
            page.close(forgot_dialog)
            login_view.visible = True
            authenticated_view.visible = False
            update_all_uis()
            show_alert("パスワードを再設定しました！ログイン画面から新しいパスワードでログインしてください。",
                       title="再設定完了")
        except Exception as ex:
            show_alert(f"リセット失敗: {ex}")

    def handle_rename(e):
        nonlocal current_player
        new_name = edit_name_input.value.strip()
        if not new_name or new_name == current_player: return
        try:
            res = supabase.table("users").select("username").eq("username", new_name).execute()
            if res.data:
                show_alert("その名前はすでに使用されています。")
                return
            supabase.table("users").update({"username": new_name}).eq("username", current_player).execute()
            page.client_storage.set(STORAGE_REMEMBER_USER, new_name)
        except Exception as ex:
            show_alert(f"名前変更失敗: {ex}")
            return
        current_player = new_name
        logged_in_user_text.value = f"👤 ログイン中: {current_player} さん"
        update_all_uis()
        page.close(change_name_dialog)
        page.overlay.append(ft.SnackBar(ft.Text("プレイヤー名を変更しました！"), open=True))
        page.update()

    def handle_privacy_change(e):
        if not current_player: return
        try:
            priv_res = supabase.table("privacy").select("*").eq("username", current_player).execute()
            p_key = "username" if priv_res.data else "player"
            supabase.table("privacy").update({"is_visible": e.control.value}).eq(p_key, current_player).execute()
        except Exception:
            pass
        update_ranking_ui()

    def handle_new_register(e):
        input_name = login_name_input.value.strip()
        input_pass = login_pass_input.value.strip()
        if not input_name or not input_pass:
            show_alert("名前とパスワードを入力してください。")
            return
        if len(input_pass) < 4:
            show_alert("パスワードは4桁以上で設定してください。")
            return
        try:
            res = supabase.table("users").select("username").eq("username", input_name).execute()
            if res.data:
                show_alert("そのプレイヤー名は既に使われています。")
                return
            hashed_pass = hash_password(input_pass)
            supabase.table("users").insert({"username": input_name, "password": hashed_pass}).execute()
            supabase.table("privacy").insert({"username": input_name, "is_visible": True, "group_number": "1"}).execute()
            show_alert(f"プレイヤー「{input_name}」を登録しました！ログインボタンを押して進んでください。", title="登録成功")
        except Exception as ex:
            show_alert(f"登録失敗: {ex}")

    def execute_delete_account():
        nonlocal current_player
        if not current_player: return
        try:
            supabase.table("users").delete().eq("username", current_player).execute()
            priv_res = supabase.table("privacy").select("*").eq("username", current_player).execute()
            p_key = "username" if priv_res.data else "player"
            supabase.table("privacy").delete().eq(p_key, current_player).execute()
        except Exception:
            return
        page.client_storage.remove(STORAGE_REMEMBER_USER)
        page.client_storage.remove(STORAGE_REMEMBER_PASS)
        login_name_input.value, login_pass_input.value = "", ""
        page.close(confirm_delete_dialog)
        login_view.visible = True
        authenticated_view.visible = False
        update_all_uis()

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
                if p_name:
                    group_map[p_name] = str(p.get("group_number", "1"))

            summary_data = []

            try:
                search_keyword = admin_search_input.value.strip().lower()
            except Exception:
                search_keyword = ""

            for u in all_users:
                username = u["username"]
                if search_keyword and search_keyword not in username.lower():
                    continue

                user_records = [r for r in all_records if r["player"] == username]
                valid_scores = [r["final_score"] for r in user_records if r.get("final_score", 0) > 0]
                max_score = max(valid_scores) if valid_scores else 0
                latest_date = max([r["date"] for r in user_records]) if user_records else "記録なし"
                user_group_str = group_map.get(username, "1")

                summary_data.append({"username": username, "group_str": user_group_str, "max_score": max_score,
                                     "latest_date": latest_date})

            if current_sort_column == 0:
                summary_data.sort(key=lambda x: x["username"], reverse=not current_sort_ascending)
            elif current_sort_column == 1:
                summary_data.sort(key=lambda x: x["group_str"], reverse=not current_sort_ascending)
            elif current_sort_column == 2:
                summary_data.sort(key=lambda x: x["latest_date"], reverse=not current_sort_ascending)
            elif current_sort_column == 3:
                summary_data.sort(key=lambda x: x["max_score"], reverse=not current_sort_ascending)

            for data in summary_data:
                is_admin = (data["username"].lower() == "admin")
                name_display = f"👑 {data['username']}" if is_admin else data["username"]
                admin_data_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(name_display, width=100,
                                            weight=ft.FontWeight.BOLD if is_admin else ft.FontWeight.NORMAL,
                                            color=ft.Colors.BLUE_600 if is_admin else ft.Colors.BLACK)),
                        ft.DataCell(ft.Text(data["group_str"], width=80)),
                        ft.DataCell(ft.Text(data["latest_date"], width=150, size=12)),
                        ft.DataCell(ft.Text(f"{data['max_score']}点", width=80, weight=ft.FontWeight.W_500,
                                            color=ft.Colors.BLUE_700)),
                    ])
                )
        except Exception as ex:
            admin_data_table.rows.append(ft.DataRow(
                cells=[ft.DataCell(ft.Text(f"エラー: {ex}", color=ft.Colors.RED)), ft.DataCell(ft.Text("")),
                       ft.DataCell(ft.Text("")), ft.DataCell(ft.Text(""))]))
        page.update()

    # ─── 各種ダイアログの定義（最新仕様 page.open に完全適合） ───
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
    privacy_setting_dialog = ft.AlertDialog(title=ft.Text("👁️ プライバシー設定"), content=ft.Container(
        content=ft.Column(
            [ft.Text("スコアを全体のランキングに公開するかどうかを切り替えます。", size=14, color=ft.Colors.GREY_700),
             ft.Container(height=5), ranking_switch], spacing=10, tight=True), width=320, height=100), actions=[
        ft.ElevatedButton("閉じる", on_click=lambda e: page.close(privacy_setting_dialog),
                          bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)],
                                            actions_alignment=ft.MainAxisAlignment.END)

    # ─── 修正：アカウント削除確認を1行化 ───
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
    change_group_dialog = ft.AlertDialog(title=ft.Text("🔢 グループ番号の変更"), content=ft.Container(
        content=ft.Column([mypage_group_input], spacing=10, tight=True), width=320, height=70), actions=[
        ft.TextButton("キャンセル", on_click=lambda e: page.close(change_group_dialog)),
        ft.ElevatedButton("変更を保存", on_click=handle_save_group_number, bgcolor=ft.Colors.BLUE_600,
                          color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)

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

    calc_tab_view = ft.Column(
    controls=[
        ft.Container(content=ft.Column([ft.Text("現在の合計得点", size=14, color=ft.Colors.GREY_600), score_display],
                                       alignment=ft.MainAxisAlignment.CENTER,
                                       horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                     alignment=ft.alignment.center, padding=10),
        ft.Container(content=ft.Column([create_fruit_selector("🍎 りんご", "apple", apple_count_text, ft.Colors.RED_600),
                                        create_fruit_selector("🍊 みかん", "orange", orange_count_text,
                                                              ft.Colors.ORANGE_600),
                                        create_fruit_selector("🍇 ブドウ", "grape", grape_count_text,
                                                              ft.Colors.PURPLE_600)], spacing=15), padding=10),
        ft.Container(content=ft.Row(controls=[
            ft.OutlinedButton("リセット", icon=ft.Icons.REFRESH, on_click=reset_current_game,
                              style=ft.ButtonStyle(color=ft.Colors.RED_600, icon_color=ft.Colors.RED_600)),
            ft.ElevatedButton("ゲーム記録を保存", icon=ft.Icons.SAVE, on_click=save_current_game,
                              bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)],
            alignment=ft.MainAxisAlignment.SPACE_EVENLY), padding=15)
    ]
)

    mypage_tab_view = ft.Column(
        controls=[
            ft.Container(content=ft.Text("あなたの過去 of ゲーム結果一覧", size=16, weight=ft.FontWeight.BOLD,
                                         color=ft.Colors.BLUE_GREY_700),
                         padding=ft.padding.only(left=15, top=15, right=15)),
            ft.Container(content=my_records_list, height=250), # 💡 ListViewの高さを250pxに固定して潰れを防止！
            ft.Container(height=5),
            ft.Container(
                content=ft.Column([
                    ft.Text("👤 各種設定メニュー :", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Container(height=3),
                    ft.Row(
                        controls=[
                            ft.IconButton(ft.Icons.ACCOUNT_CIRCLE, tooltip="名前変更", on_click=lambda e: page.open(change_name_dialog), icon_color=ft.Colors.WHITE, icon_size=26),
                            ft.IconButton(ft.Icons.NUMBERS, tooltip="グループ変更", on_click=lambda e: page.open(change_group_dialog), icon_color=ft.Colors.WHITE, icon_size=26),
                            ft.IconButton(ft.Icons.LOCK, tooltip="パスワード変更", on_click=lambda e: page.open(change_pass_dialog), icon_color=ft.Colors.WHITE, icon_size=26),
                            ft.IconButton(ft.Icons.SHIELD, tooltip="秘密の質問設定", on_click=lambda e: page.open(secret_question_dialog), icon_color=ft.Colors.WHITE, icon_size=26),
                            ft.IconButton(ft.Icons.VISIBILITY, tooltip="ランキング公開設定", on_click=lambda e: page.open(privacy_setting_dialog), icon_color=ft.Colors.WHITE, icon_size=26),
                            ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="アカウントの完全削除", on_click=lambda e: page.open(confirm_delete_dialog), icon_color=ft.Colors.RED_300, icon_size=26)
                        ],
                        wrap=True, spacing=8, run_spacing=5, alignment=ft.MainAxisAlignment.START
                    )
                ]),
                padding=12, bgcolor=ft.Colors.BLUE_GREY_600, border_radius=10, border=ft.border.all(1, ft.Colors.BLUE_GREY_700)
            ),
        ], 
        scroll=ft.ScrollMode.AUTO
    )

    ranking_tab_view = ft.Column(
        controls=[
            ft.Container(
                content=ft.Row([
                    ft.Container(content=ranking_title_text, padding=ft.padding.only(bottom=5), expand=True),
                    ranking_group_dropdown
                ],
                    wrap=True, spacing=10, run_spacing=10, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=15
            ),
            ft.Container(content=ranking_list, height=450) # 💡 ListViewを格納するContainerに明確な高さ(450)を指定！
        ]
    )

    main_tab_view = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="得点計算", icon=ft.Icons.CALCULATE, content=calc_tab_view),
            ft.Tab(text="マイページ", icon=ft.Icons.PERSON, content=mypage_tab_view),
            ft.Tab(text="ランキング", icon=ft.Icons.EMOJI_EVENTS, content=ranking_tab_view)
        ],
        expand=True, # 💡 一番外側のTabsだけがexpand=Trueを持つのがFletの正しい構造です！
        on_change=lambda e: (
            refresh_ranking_dropdown_options(),
            update_ranking_ui() if main_tab_view.selected_index == 2 else None,
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
