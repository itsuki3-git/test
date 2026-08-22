import hashlib
import os
from datetime import datetime
import flet as ft
from supabase import create_client, Client

def main(page: ft.Page):
    page.title = "フルーツ得点計算 & プレイヤー管理"
    page.window_width = 450
    page.window_height = 700
    page.theme_mode = ft.ThemeMode.LIGHT

    FRUIT_POINTS = {"apple": 10, "orange": 5, "grape": 15}

    # =========================================================================
    # ⚠️【超重要】あなたのSupabaseの情報をここに貼り付けてください
    # ==========================================
    SUPABASE_URL = "https://tqufugshygdknyfgrsxh.supabase.co"
    SUPABASE_KEY = "sb_publishable_fMuDE8giATkTj2UOjCyThg_wowMJz0s"
    # =========================================================================

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    current_player = None
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
    ranking_switch = ft.Switch(label="ランキングに名前と記録を表示する", value=True, on_change=lambda e: handle_privacy_change(e))

    my_records_list = ft.ListView(expand=True, spacing=10, padding=10)
    ranking_list = ft.ListView(expand=True, spacing=10, padding=10)

    mypage_old_pass = ft.TextField(label="現在のパスワード", password=True)
    mypage_new_pass = ft.TextField(label="新しいパスワード (4桁以上)", password=True)
    mypage_question_input = ft.TextField(label="新しく登録する「秘密の質問」", hint_text="例: 初めて飼ったペットの名前は？")
    mypage_answer_input = ft.TextField(label="質問の答え", hint_text="答えを入力してください")

    # --- ダイアログ表示共通関数 ---
    def show_alert(message, title="エラー"):
        alert_dialog = ft.AlertDialog(
            title=ft.Text(title), 
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda e: page.close(alert_dialog))]
        )
        page.open(alert_dialog)

    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    # --- 既存ユーザーのログイン（リスト型バグを完全排除） ---
    def handle_existing_login(e):
        nonlocal current_player
        input_name = login_name_input.value.strip()
        input_pass = login_pass_input.value.strip()
        if not input_name or not input_pass:
            show_alert("プレイヤー名とパスワードを入力してください。")
            return
        try:
            hashed_pass = hash_password(input_pass)
            res = supabase.table("users").select("username").eq("username", input_name).eq("password", hashed_pass).execute()

            # 💡【重要バグ修正】データが正しく取得できているかをリストの件数で厳密にチェック
            if not res.data or len(res.data) == 0:
                show_alert("名前またはパスワードが間違っています。")
                return

            page.client_storage.set(STORAGE_REMEMBER_USER, input_name)
            page.client_storage.set(STORAGE_REMEMBER_PASS, input_pass)

            # プライバシー設定の読み込みも安全に1件目から取得
            priv_res = supabase.table("privacy").select("is_visible").eq("username", input_name).execute()
            if priv_res.data and len(priv_res.data) > 0:
                ranking_switch.value = priv_res.data[0].get("is_visible", True)
            else:
                ranking_switch.value = True
        except Exception as ex:
            show_alert(f"ログインエラー: {ex}")
            return
        enter_game_session(input_name, f"👤 {input_name} さんとしてログインしました！")

    # --- 新規プレイヤーの登録 ---
    def handle_new_register(e):
        nonlocal current_player
        input_name = login_name_input.value.strip()
        input_pass = login_pass_input.value.strip()
        if not input_name or not input_pass:
            show_alert("プレイヤー名とパスワードを入力してください。")
            return
        
        if input_name.lower() == "admin":
            show_alert("「admin」という名前は管理者専用のため登録できません。")
            return
            
        if len(input_pass) < 4:
            show_alert("パスワードは4桁以上で入力してください。")
            return
        try:
            res = supabase.table("users").select("username").eq("username", input_name).execute()
            if res.data and len(res.data) > 0:
                show_alert("その名前はすでに使用されています。")
                return

            hashed_pass = hash_password(input_pass)
            supabase.table("users").insert({"username": input_name, "password": hashed_pass}).execute()
            supabase.table("privacy").insert({"username": input_name, "is_visible": True}).execute()

            page.client_storage.set(STORAGE_REMEMBER_USER, input_name)
            page.client_storage.set(STORAGE_REMEMBER_PASS, input_pass)
            ranking_switch.value = True
        except Exception as ex:
            show_alert(f"登録エラー: {ex}")
            return
        enter_game_session(input_name, f"🎉 新しいプレイヤー {input_name} さんを登録しました！")

    # --- セッション開始共通処理 ---
    def enter_game_session(username, success_message):
        nonlocal current_player
        current_player = username
        logged_in_user_text.value = f"👤 ログイン中: {current_player} さん"
        edit_name_input.value = current_player
        try:
            res = supabase.table("users").select("secret_question").eq("username", current_player).execute()
            if res.data and len(res.data) > 0:
                # 💡【重要バグ修正】リストの[0]番目から安全に辞書を取得
                mypage_question_input.value = res.data[0].get("secret_question") or ""
                mypage_answer_input.value = ""
        except Exception:
            pass
        login_view.visible = False
        main_tab_view.visible = True
        
        # 💡 管理者タブの表示切り替え
        if current_player == "admin" and len(main_tab_view.tabs) == 3:
            main_tab_view.tabs.append(ft.Tab(text="管理者", icon=ft.Icons.ADMIN_PANEL_SETTINGS, content=admin_tab_view))
        elif current_player != "admin" and len(main_tab_view.tabs) == 4:
            main_tab_view.tabs.pop()
            
        reset_current_game(None)
        update_all_uis()
        page.overlay.append(ft.SnackBar(ft.Text(success_message), open=True))
        page.update()

    # --- 自動ログイン処理 ---
    def check_auto_login():
        saved_user = page.client_storage.get(STORAGE_REMEMBER_USER)
        saved_pass = page.client_storage.get(STORAGE_REMEMBER_PASS)
        if saved_user and saved_pass:
            try:
                hashed_pass = hash_password(saved_pass)
                res = supabase.table("users").select("username").eq("username", saved_user).eq("password", hashed_pass).execute()
                if res.data and len(res.data) > 0:
                    priv_res = supabase.table("privacy").select("is_visible").eq("username", saved_user).execute()
                    if priv_res.data and len(priv_res.data) > 0:
                        ranking_switch.value = priv_res.data[0].get("is_visible", True)
                    else:
                        ranking_switch.value = True
                    enter_game_session(saved_user, f"🚀 おかえりなさい！ {saved_user} さん")
            except Exception:
                pass

    
    # --- マイページでのパスワード変更処理 ---
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
            res = supabase.table("users").select("username").eq("username", current_player).eq("password", hashed_old).execute()
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

    # --- マイページでの秘密の質問と答えの保存処理（修正版） ---
    def handle_save_secret_question(e):
        q = mypage_question_input.value.strip()
        a = mypage_answer_input.value.strip()
        if not q or not a:
            show_alert("質問と答えの両方を入力してください。")
            return
        try:
            # 💡【セキュリティ強化】秘密の質問の「答え」をハッシュ化して保存
            hashed_answer = hash_password(a)
            supabase.table("users").update({"secret_question": q, "secret_answer": hashed_answer}).eq("username", current_player).execute()
            mypage_answer_input.value = ""  # 入力欄をクリア
            page.close(secret_question_dialog)
            show_alert("秘密の質問と答えを保存しました！", title="成功")
        except Exception as ex:
            show_alert(f"保存失敗: {ex}")

    # --- パスワードを忘れた場合：ユーザー名から質問を引っ張る処理（修正版） ---
    def handle_forgot_check_user(e):
        name = forgot_name_input.value.strip()
        if not name:
            show_alert("プレイヤー名を入力してください。")
            return
        try:
            res = supabase.table("users").select("secret_question").eq("username", name).execute()
            
            # 💡【重要バグ修正】res.data が空（ユーザーがいない）か、リストになっているかを正しくチェック
            if not res.data:
                forgot_question_text.value = "❌ そのプレイヤー名は登録されていません。"
            else:
                # リストの先頭要素 [0] から安全にデータを取得
                user_data = res.data[0]
                if not user_data.get("secret_question"):
                    forgot_question_text.value = "⚠ 秘密の質問が設定されていません。"
                else:
                    forgot_question_text.value = f"❓ 質問: {user_data['secret_question']}"
        except Exception as ex:
            forgot_question_text.value = f"エラー: {ex}"
        page.update()


        # --- パスワードリセット実行（修正・バグ完全排除版） ---
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
            res = supabase.table("users").select("secret_answer").eq("username", name).execute()
            
            # 💡【重要バグ修正】res.data[0] から辞書を取り出して安全に回答を比較する
            if not res.data or res.data[0].get("secret_answer") != hash_password(ans):
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
            main_tab_view.visible = False

            update_all_uis()
            show_alert("パスワードを再設定しました！ログイン画面から新しいパスワードでログインしてください。", title="再設定完了")
        except Exception as ex:
            show_alert(f"リセット失敗: {ex}")


    # --- 名前の変更処理 ---
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

    # --- 非表示設定 ---
    def handle_privacy_change(e):
        if not current_player: return
        try:
            supabase.table("privacy").update({"is_visible": e.control.value}).eq("username", current_player).execute()
        except Exception:
            pass
        update_ranking_ui()

    # --- アカウント完全削除 ---
    def execute_delete_account():
        nonlocal current_player
        if not current_player: return
        try:
            supabase.table("users").delete().eq("username", current_player).execute()
        except Exception:
            return
        page.client_storage.remove(STORAGE_REMEMBER_USER)
        page.client_storage.remove(STORAGE_REMEMBER_PASS)
        login_name_input.value, login_pass_input.value = "", ""

        page.close(confirm_delete_dialog)
        login_view.visible, main_tab_view.visible = True, False
        update_all_uis()

    # --- ログアウト処理 ---
    def handle_logout(e):
        nonlocal current_player
        current_player = None
        login_name_input.value = page.client_storage.get(STORAGE_REMEMBER_USER) or ""
        login_pass_input.value = page.client_storage.get(STORAGE_REMEMBER_PASS) or ""
        login_view.visible, main_tab_view.visible = True, False
        page.update()

    # --- スコア計算（不要な画面更新を抑制） ---
    def calculate_total_score_ui_only():
        total = (counts["apple"] * FRUIT_POINTS["apple"] + counts["orange"] * FRUIT_POINTS["orange"] + counts["grape"] * FRUIT_POINTS["grape"])
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

    def update_all_uis():
        update_my_records_ui()
        update_ranking_ui()

    # --- マイページ（自分だけの記録）の描画更新 ---
    def update_my_records_ui():
        my_records_list.controls.clear()
        if not current_player: return
        try:
            res = supabase.table("records").select("*").eq("player", current_player).execute()
            my_filtered = res.data or []
        except Exception as ex:
            my_records_list.controls.append(ft.Text(f"データ取得エラー: {ex}", color=ft.Colors.RED))
            page.update()
            return
        if not my_filtered:
            my_records_list.controls.append(ft.Text("あなたの保存された記録はありません", italic=True, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER))
        else:
            for record in sorted(my_filtered, key=lambda x: x["id"], reverse=True):
                my_records_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Column([
                                    ft.Text(f"合計得点: {record['final_score']} 点", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                                    ft.Text(f"内訳: 🍎{record['apple']} 🍊{record['orange']} 🍇{record['grape']}", size=13, color=ft.Colors.GREY_700),
                                    ft.Text(f"保存日時: {record['date']}", size=11, color=ft.Colors.GREY_500)
                                ], expand=True),
                                ft.IconButton(icon=ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_600, tooltip="記録を削除", on_click=lambda e, idx=record["id"]: delete_saved_record(idx))
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ), padding=12, border=ft.border.all(1, ft.Colors.BLUE_100), border_radius=8, bgcolor=ft.Colors.BLUE_50
                    )
                )
        page.update()

    # --- 全体のランキング描画更新 ---
    def update_ranking_ui():
        ranking_list.controls.clear()
        try:
            privacy_res = supabase.table("privacy").select("username").eq("is_visible", False).execute()
            hidden_users = [p["username"] for p in privacy_res.data] if privacy_res.data else []
            records_res = supabase.table("records").select("*").execute()
            all_records = records_res.data or []
        except Exception as ex:
            ranking_list.controls.append(ft.Text(f"ランキング取得エラー: {ex}", color=ft.Colors.RED))
            page.update()
            return
        visible_records = [r for r in all_records if r["player"] not in hidden_users]
        if not visible_records:
            ranking_list.controls.append(ft.Text("公開されている記録はありません", italic=True, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER))
        else:
            sorted_records = sorted(visible_records, key=lambda x: x["final_score"], reverse=True)
            for index, record in enumerate(sorted_records):
                rank = index + 1
                if rank == 1: rank_color, rank_text = ft.Colors.AMBER_500, f"🥇 {rank}位"
                elif rank == 2: rank_color, rank_text = ft.Colors.BLUE_GREY_300, f"🥈 {rank}位"
                elif rank == 3: rank_color, rank_text = ft.Colors.BROWN_400, f"🥉 {rank}位"
                else: rank_color, rank_text = ft.Colors.BLUE_GREY_700, f"  {rank}位"
                ranking_list.controls.append(
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
        page.update()

    # --- スコア操作 ---
    def reset_current_game(e):
        for fruit in counts: counts[fruit] = 0
        apple_count_text.value, orange_count_text.value, grape_count_text.value = "0", "0", "0"
        calculate_total_score_ui_only()
        if e: page.update()

    def save_current_game(e):
        if not current_player: return
        total_score = (counts["apple"] * FRUIT_POINTS["apple"] + counts["orange"] * FRUIT_POINTS["orange"] + counts["grape"] * FRUIT_POINTS["grape"])
        date_str = datetime.now().strftime("%Y/%m/%d %H:%M")
        try:
            supabase.table("records").insert({
                "player": current_player, "final_score": total_score, "apple": counts["apple"],
                "orange": counts["orange"], "grape": counts["grape"], "date": date_str
            }).execute()
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
        except Exception:
            return
        update_all_uis()

    # 💡【管理者用機能】管理者タブの情報をリフレッシュする処理
    def update_admin_ui():
        if current_player != "admin": return
        admin_users_list.controls.clear()
        try:
            # 全ユーザーと全記録を取得
            users_res = supabase.table("users").select("username").execute()
            records_res = supabase.table("records").select("*").execute()
            
            all_users = users_res.data or []
            all_records = records_res.data or []
            
            # 1. 登録プレイヤー一覧の描画
            admin_users_list.controls.append(ft.Text(f"👥 登録プレイヤー数: {len(all_users)}人", weight=ft.FontWeight.BOLD, size=14))
            for u in all_users:
                # admin自身は削除できないようにガード
                is_admin_user = (u["username"].lower() == "admin")
                admin_users_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.PERSON if not is_admin_user else ft.Icons.SUPERVISED_USER_CIRCLE),
                        title=ft.Text(u["username"]),
                        trailing=None if is_admin_user else ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINED,
                            icon_color=ft.Colors.RED_600,
                            tooltip="プレイヤーを強制削除",
                            on_click=lambda e, name=u["username"]: delete_user_by_admin(name)
                        )
                    )
                )
            
            # 2. 全プレイヤーのゲーム結果ログの描画
            admin_records_list.controls.clear()
            admin_records_list.controls.append(ft.Text(f"📊 全ゲーム記録数: {len(all_records)}件", weight=ft.FontWeight.BOLD, size=14))
            for r in sorted(all_records, key=lambda x: x["id"], reverse=True):
                admin_records_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"プレイヤー: {r['player']}", size=14, weight=ft.FontWeight.W_500),
                                ft.Text(f"得点: {r['final_score']} 点 (🍎{r['apple']} 🍊{r['orange']} 🍇{r['grape']})", size=12, color=ft.Colors.GREY_700),
                                ft.Text(f"日時: {r['date']}", size=10, color=ft.Colors.GREY_500)
                            ], expand=True),
                            ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_400, on_click=lambda e, idx=r["id"]: delete_record_by_admin(idx))
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=8, border=ft.border.all(1, ft.Colors.GREY_300), border_radius=6, bgcolor=ft.Colors.GREY_50
                    )
                )
        except Exception as ex:
            admin_users_list.controls.append(ft.Text(f"データ取得エラー: {ex}", color=ft.Colors.RED))
        page.update()

    # 💡【管理者用機能】指定したユーザーを強制削除
    def delete_user_by_admin(username):
        try:
            supabase.table("users").delete().eq("username", username).execute()
            update_all_uis()
        except Exception:
            pass

    # 💡【管理者用機能】指定したゲーム記録を強制削除
    def delete_record_by_admin(target_id):
        try:
            supabase.table("records").delete().eq("id", target_id).execute()
            update_all_uis()
        except Exception:
            pass
    def create_fruit_selector(label, fruit_key, count_text_component, color):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(f"{label} ({FRUIT_POINTS[fruit_key]}点)", size=16, weight=ft.FontWeight.W_500, expand=True),
                    ft.Row(
                        controls=[
                            ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE_OUTLINED, icon_color=color, on_click=lambda e: adjust_count(fruit_key, -1)),
                            count_text_component,
                            ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color=color, on_click=lambda e: adjust_count(fruit_key, 1))
                        ], spacing=5
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ), padding=10, border=ft.border.all(1, ft.Colors.GREY_300), border_radius=10, bgcolor=ft.Colors.WHITE
        )

    # --- 各種ダイアログ設定 ---
    change_name_dialog = ft.AlertDialog(title=ft.Text("👤 プレイヤー名の変更"), content=ft.Container(content=ft.Column([edit_name_input], spacing=10, tight=True), width=320, height=70), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(change_name_dialog)), ft.ElevatedButton("名前を変更", on_click=handle_rename, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)
    change_pass_dialog = ft.AlertDialog(title=ft.Text("🔒 パスワードの変更"), content=ft.Container(content=ft.Column([mypage_old_pass, mypage_new_pass], spacing=10, tight=True), width=320, height=140), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(change_pass_dialog)), ft.ElevatedButton("変更を実行", on_click=handle_change_password, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)
    secret_question_dialog = ft.AlertDialog(title=ft.Text("🛡️ 秘密の質問の設定"), content=ft.Container(content=ft.Column([mypage_question_input, mypage_answer_input], spacing=10, tight=True), width=320, height=140), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(secret_question_dialog)), ft.ElevatedButton("設定を保存", on_click=handle_save_secret_question, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)
    privacy_setting_dialog = ft.AlertDialog(title=ft.Text("👁️ プライバシー設定"), content=ft.Container(content=ft.Column([ft.Text("スコアを全体のランキングに公開するかどうかを切り替えます。", size=14, color=ft.Colors.GREY_700), ft.Container(height=5), ranking_switch], spacing=10, tight=True), width=320, height=100), actions=[ft.ElevatedButton("閉じる", on_click=lambda e: page.close(privacy_setting_dialog), bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)
    confirm_delete_dialog = ft.AlertDialog(title=ft.Text("⚠️ 最終確認"), content=ft.Text("本当にアカウントを削除しますか？\n過去のゲーム記録もすべて消去され、元に戻すことはできません。"), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(confirm_delete_dialog)), ft.TextButton("削除する", style=ft.ButtonStyle(color=ft.Colors.RED_600), on_click=lambda e: execute_delete_account())], actions_alignment=ft.MainAxisAlignment.END)
    forgot_dialog = ft.AlertDialog(title=ft.Text("🔑 パスワードの再設定"), content=ft.Container(content=ft.Column([forgot_name_input, ft.ElevatedButton("1. 質問を確認する", on_click=handle_forgot_check_user, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE), ft.Divider(height=10), forgot_question_text, forgot_answer_input, forgot_new_pass_input], spacing=10, tight=True), width=320, height=325), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(forgot_dialog)), ft.ElevatedButton("2. パスワードを更新", on_click=handle_forgot_reset_password, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)

    action_buttons_row = ft.ResponsiveRow(controls=[ft.Container(content=register_btn, col={"xs": 12, "md": 6}, alignment=ft.alignment.center, padding=5), ft.Container(content=login_btn, col={"xs": 12, "md": 6}, alignment=ft.alignment.center, padding=5)], alignment=ft.MainAxisAlignment.CENTER)

    # 💡【管理者対応】管理者専用タブ内のリスト表示コンポーネント
    admin_users_list = ft.ListView(spacing=5, padding=5, height=200)
    admin_records_list = ft.ListView(spacing=10, padding=5, expand=True)

    # 💡【管理者対応】管理者タブのレイアウト構築
    admin_tab_view = ft.Column(
        controls=[
            ft.Container(content=ft.Text("🛠️ 管理者コントロールパネル", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800), padding=12),
            ft.Container(content=admin_users_list, border=ft.border.all(1, ft.Colors.GREY_300), border_radius=8, padding=5, bgcolor=ft.Colors.WHITE),
            ft.Divider(height=15),
            ft.Container(content=admin_records_list, expand=True)
        ], expand=True, scroll=ft.ScrollMode.AUTO
    )

    # --- 各種表示構築 ---
    login_view = ft.Container(content=ft.Column(controls=[ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80, color=ft.Colors.BLUE_600), ft.Text(value="プレイヤー認証", size=24, weight=ft.FontWeight.BOLD), ft.Container(height=15), ft.Container(content=login_name_input, width=300), ft.Container(content=login_pass_input, width=300), ft.Container(height=10), ft.Container(content=action_buttons_row, width=340), ft.Container(height=10), ft.TextButton("🔑 パスワードを忘れた場合はこちら", on_click=lambda e: (setattr(forgot_name_input, "value", ""), setattr(forgot_answer_input, "value", ""), setattr(forgot_new_pass_input, "value", ""), setattr(forgot_question_text, "value", "プレイヤー名を入力して「質問を確認」を押してください"), page.open(forgot_dialog)))], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10), padding=20, alignment=ft.alignment.center, expand=True, visible=True)
    calc_tab_view = ft.Column(controls=[ft.Container(content=ft.Row(controls=[logged_in_user_text, ft.TextButton("ログアウト", icon=ft.Icons.LOGOUT, style=ft.ButtonStyle(color=ft.Colors.RED_600, icon_color=ft.Colors.RED_600), on_click=handle_logout)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=10, bgcolor=ft.Colors.GREY_100, border_radius=8), ft.Container(content=ft.Column([ft.Text("現在の合計得点", size=14, color=ft.Colors.GREY_600), score_display], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), alignment=ft.alignment.center, padding=10), ft.Container(content=ft.Column([create_fruit_selector("🍎 りんご", "apple", apple_count_text, ft.Colors.RED_600), create_fruit_selector("🍊 みかん", "orange", orange_count_text, ft.Colors.ORANGE_600), create_fruit_selector("🍇 ブドウ", "grape", grape_count_text, ft.Colors.PURPLE_600)], spacing=15), padding=10, expand=True), ft.Container(content=ft.Row(controls=[ft.OutlinedButton("リセット", icon=ft.Icons.REFRESH, on_click=reset_current_game, style=ft.ButtonStyle(color=ft.Colors.RED_600, icon_color=ft.Colors.RED_600)), ft.ElevatedButton("ゲーム記録を保存", icon=ft.Icons.SAVE, on_click=save_current_game, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)], alignment=ft.MainAxisAlignment.SPACE_EVENLY), padding=15)], expand=True)
    mypage_tab_view = ft.Column(controls=[ft.Container(content=ft.Text("あなたの過去のゲーム結果一覧", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_700), padding=ft.padding.only(left=15, top=15, right=15)), ft.Container(content=my_records_list, expand=True), ft.Container(height=5), ft.Container(content=ft.Row([ft.Text("各種設定を開く:", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_500), ft.Row([ft.IconButton(ft.Icons.ACCOUNT_CIRCLE, tooltip="名前変更", on_click=lambda e: page.open(change_name_dialog), icon_color=ft.Colors.BLUE_600), ft.IconButton(ft.Icons.LOCK, tooltip="パスワード変更", on_click=lambda e: page.open(change_pass_dialog), icon_color=ft.Colors.BLUE_600), ft.IconButton(ft.Icons.SHIELD, tooltip="秘密の質問設定", on_click=lambda e: page.open(secret_question_dialog), icon_color=ft.Colors.BLUE_600), ft.IconButton(ft.Icons.VISIBILITY, tooltip="ランキング公開設定", on_click=lambda e: page.open(privacy_setting_dialog), icon_color=ft.Colors.BLUE_600), ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="アカウントの完全削除", on_click=lambda e: page.open(confirm_delete_dialog), icon_color=ft.Colors.RED_600)], spacing=1)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=8, bgcolor=ft.Colors.GREY_100, border_radius=10, border=ft.border.all(1, ft.Colors.GREY_300)),], expand=True, scroll=ft.ScrollMode.AUTO)
    ranking_tab_view = ft.Column(controls=[ft.Container(content=ft.Text("総合得点ハイスコアランキング", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_700), padding=15), ft.Container(content=ranking_list, expand=True)], expand=True, scroll=ft.ScrollMode.AUTO)

    main_tab_view = ft.Tabs(selected_index=0, animation_duration=300, tabs=[ft.Tab(text="得点計算", icon=ft.Icons.CALCULATE, content=calc_tab_view), ft.Tab(text="マイページ", icon=ft.Icons.PERSON, content=mypage_tab_view), ft.Tab(text="ランキング", icon=ft.Icons.EMOJI_EVENTS, content=ranking_tab_view)], expand=True, visible=False)

    # UIコンポーネントを画面に追加
    page.add(login_view, main_tab_view)

    calculate_total_score_ui_only()
    
    # 💡【管理者対応】UIリフレッシュに管理画面の更新を統合
    def update_all_uis_with_admin():
        update_my_records_ui()
        update_ranking_ui()
        if current_player == "admin":
            update_admin_ui()
    update_all_uis = update_all_uis_with_admin
    update_all_uis()

    login_name_input.value = page.client_storage.get(STORAGE_REMEMBER_USER) or ""
    login_pass_input.value = page.client_storage.get(STORAGE_REMEMBER_PASS) or ""

    check_auto_login()
    page.update()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    ft.app(target=main, host="0.0.0.0", view=ft.AppView.WEB_BROWSER, port=port)
