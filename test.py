import hashlib, os, flet as ft
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

def main(page: ft.Page):
    page.title, page.window_width, page.window_height, page.theme_mode = "フルーツ管理", 450, 700, ft.ThemeMode.LIGHT
    FRUIT_POINTS = {"apple": 10, "orange": 5, "grape": 15}
    
    # =========================================================================
    # ⚠️ あなたのSupabaseの情報をここに貼り付けてください
    # =========================================================================
    SUPABASE_URL = "https://tqufugshygdknyfgrsxh.supabase.co"
    SUPABASE_KEY = "sb_publishable_fMuDE8giATkTj2UOjCyThg_wowMJz0s"
    # =========================================================================

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    current_player, my_group_list, active_ranking_group, counts = None, [], "1", {"apple": 0, "orange": 0, "grape": 0}
    STORAGE_REMEMBER_USER, STORAGE_REMEMBER_PASS = "fruit_user", "fruit_pass"

    login_name_input, login_pass_input = ft.TextField(label="名"), ft.TextField(label="パス", password=True, can_reveal_password=True)
    forgot_name_input, forgot_answer_input, forgot_new_pass_input = ft.TextField(label="名"), ft.TextField(label="答"), ft.TextField(label="新パス", password=True)
    forgot_question_text = ft.Text(value="プレイヤー名入力後に質問確認を押してください")
    logged_in_user_text, score_display = ft.Text(value="", size=16, weight=ft.FontWeight.BOLD), ft.Text(value="0", size=48, weight=ft.FontWeight.BOLD)
    apple_count_text, orange_count_text, grape_count_text = ft.Text("0", size=20, width=40, text_align=ft.TextAlign.CENTER), ft.Text("0", size=20, width=40, text_align=ft.TextAlign.CENTER), ft.Text("0", size=20, width=40, text_align=ft.TextAlign.CENTER)
    edit_name_input, ranking_switch = ft.TextField(label="名編集", expand=True), ft.Switch(label="ランキング公開", value=True)
    mypage_group_chips, my_records_list = ft.Row(wrap=True, spacing=5), ft.ListView(expand=True, spacing=10)
    ranking_tab_view, ranking_title_text = ft.ListView(expand=True, spacing=5), ft.Text(value="総合ランキング", size=16, weight=ft.FontWeight.BOLD)
    ranking_group_dropdown = ft.Dropdown(label="班切替", width=150, on_change=lambda e: handle_ranking_group_switch(e))
    mypage_old_pass, mypage_new_pass, mypage_question_input, mypage_answer_input = ft.TextField(label="現パス"), ft.TextField(label="新パス"), ft.TextField(label="質問"), ft.TextField(label="答")
    popup_group_input_field, popup_current_group_container = ft.TextField(label="班番号", keyboard_type=ft.KeyboardType.NUMBER, expand=True), ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
    admin_search_input = ft.TextField(label="検索", on_change=lambda e: update_admin_ui(), expand=True)
    admin_data_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("名")), ft.DataColumn(ft.Text("班")), ft.DataColumn(ft.Text("点"))], rows=[], expand=True)
    action_buttons_row = ft.ResponsiveRow()
    global_header_bar = ft.Container()

    def show_alert(m, t="エラー"):
        alert = ft.AlertDialog(title=ft.Text(t), content=ft.Text(m), actions=[ft.TextButton("OK", on_click=lambda e: (setattr(alert, "open", False), page.update()))])
        page.open(alert)
    def hash_password(p: str) -> str: return hashlib.sha256(p.encode('utf-8')).hexdigest()
    def get_jst_now_str() -> str: return datetime.now(timezone(timedelta(hours=9))).strftime("%Y/%m/%d %H:%M")
    def create_fruit_selector(l, k, c, col): return ft.Container(content=ft.Row([ft.Text(f"{l} ({FRUIT_POINTS[k]}点)", size=16, expand=True), ft.Row([ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINED, icon_color=col, on_click=lambda e: adjust_count(k, -1)), c, ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=col, on_click=lambda e: adjust_count(k, 1))], spacing=5)]), padding=10, border=ft.border.all(1, ft.Colors.GREY_300), border_radius=10)
    def calculate_total_score_ui_only():
        t = (counts["apple"] * FRUIT_POINTS["apple"] + counts["orange"] * FRUIT_POINTS["orange"] + counts["grape"] * FRUIT_POINTS["grape"])
        score_display.value = str(t); return t
    def adjust_count(f, d):
        n = counts[f] + d
        if n >= 0:
            counts[f] = n
            if f == "apple": apple_count_text.value = str(n)
            elif f == "orange": orange_count_text.value = str(n)
            elif f == "grape": grape_count_text.value = str(n)
            calculate_total_score_ui_only(); page.update()
    def reset_current_game(e):
        for f in counts: counts[f] = 0
        apple_count_text.value, orange_count_text.value, grape_count_text.value = "0", "0", "0"
        calculate_total_score_ui_only(); page.update()
    def update_all_uis():
        update_my_records_ui(); update_ranking_ui()
        if current_player == "admin": update_admin_ui()

    def update_my_records_ui():
        my_records_list.controls.clear(); mypage_group_chips.controls.clear()
        for g in sorted(my_group_list): mypage_group_chips.controls.append(ft.Chip(label=ft.Text(f"G{g}")))
        try:
            res = supabase.table("records").select("*").execute()
            flt = [r for r in (res.data or []) if r.get("player") == current_player and r.get("final_score", 0) > 0]
            for r in sorted(flt, key=lambda x: x["id"], reverse=True): my_records_list.controls.append(ft.Container(content=ft.Row([ft.Column([ft.Text(f"{r['final_score']}点"), ft.Text(f"🍎{r['apple']} 🍊{r['orange']} 🍇{r['grape']}")], expand=True), ft.IconButton(ft.Icons.DELETE, on_click=lambda e, idx=r["id"]: delete_saved_record(idx))]), padding=5, bgcolor=ft.Colors.BLUE_50))
        except Exception: pass
        page.update()
    def update_ranking_ui():
        ranking_tab_view.controls.clear()
        g_str = str(active_ranking_group).strip()
        ranking_title_text.value = f"ランキング (グループ {g_str})"
        ranking_tab_view.controls.append(ft.Container(content=ft.Row([ft.Container(content=ranking_title_text, expand=True), ranking_group_dropdown]), padding=10))
        try:
            p_res = supabase.table("privacy").select("*").execute()
            h_users = [p["username"] for p in (p_res.data or []) if p.get("is_visible") is False]
            g_users = [p["username"] for p in (p_res.data or []) if g_str in [t.strip() for t in str(p.get("group_number", "1")).replace("，", ",").split(",")]]
            r_res = supabase.table("records").select("*").execute()
            bests = {}
            for r in [r for r in (r_res.data or []) if r.get("final_score", 0) > 0 and r["player"] not in h_users and r["player"] in g_users]:
                p = r["player"]
                if p not in bests or r["final_score"] > bests[p]["final_score"]: bests[p] = r
            for idx, r in enumerate(sorted(list(bests.values()), key=lambda x: x["final_score"], reverse=True)):
                ranking_tab_view.controls.append(ft.Container(content=ft.Row([ft.Text(f"{idx+1}位"), ft.Text(r["player"], expand=True), ft.Text(f"{r['final_score']}点")]), padding=10, bgcolor=ft.Colors.WHITE))
        except Exception: pass
        page.update()

    def refresh_ranking_dropdown_options():
        ranking_group_dropdown.options.clear()
        if current_player == "admin":
            try:
                all_p = supabase.table("privacy").select("group_number").execute()
                gps = {0}
                for row in (all_p.data or []):
                    for tk in str(row.get("group_number", "1")).replace("，", ",").split(","):
                        if tk.strip().isdigit(): gps.add(int(tk.strip()))
                for g in sorted(list(gps)): ranking_group_dropdown.options.append(ft.dropdown.Option(str(g), f"グループ {g}"))
            except Exception: ranking_group_dropdown.options.append(ft.dropdown.Option("0", "グループ 0"))
        else:
            for g in my_group_list: ranking_group_dropdown.options.append(ft.dropdown.Option(str(g), f"グループ {g}"))
        ranking_group_dropdown.value = "0" if current_player == "admin" else (str(my_group_list) if my_group_list else "1")
        page.update()
    def handle_ranking_group_switch(e):
        nonlocal active_ranking_group
        active_ranking_group = e.control.value; update_ranking_ui()

    def handle_existing_login(e):
        nonlocal current_player, my_group_list, active_ranking_group
        n, p = login_name_input.value.strip(), login_pass_input.value.strip()
        if not n or not p: return
        try:
            res = supabase.table("users").select("username").eq("username", n).eq("password", hash_password(p)).execute()
            if not res.data: show_alert("認証失敗"); return
            page.client_storage.set(STORAGE_REMEMBER_USER, n); page.client_storage.set(STORAGE_REMEMBER_PASS, p)
            priv = supabase.table("privacy").select("is_visible", "group_number").eq("username", n).execute()
            my_group_list = []
            if priv.data:
                ranking_switch.value = priv.data.get("is_visible", True)
                raw_g = str(priv.data.get("group_number", "1"))
                if n.lower() == "admin":
                    raw_g = "0"; supabase.table("privacy").update({"group_number": "0"}).eq("username", "admin").execute()
                my_group_list = [int(x.strip()) for x in raw_g.replace("，", ",").split(",") if x.strip().isdigit()]
            if not my_group_list:
                my_group_list = [0] if n.lower() == "admin" else [1]
            active_ranking_group = "0" if n.lower() == "admin" else str(my_group_list[0])
            refresh_ranking_dropdown_options(); enter_game_session(n, "ログイン成功")
        except Exception as ex: show_alert(f"エラー: {ex}")

    def handle_new_register(e):
        nonlocal current_player, my_group_list, active_ranking_group
        n, p = login_name_input.value.strip(), login_pass_input.value.strip()
        if not n or not p: return
        if n.lower() == "admin": show_alert("adminは登録不可"); return
        try:
            res = supabase.table("users").select("username").eq("username", n).execute()
            if res.data: show_alert("重複名あり"); return
            supabase.table("users").insert({"username": n, "password": hash_password(p)}).execute()
            supabase.table("privacy").insert({"username": n, "is_visible": True, "group_number": "1"}).execute()
            page.client_storage.set(STORAGE_REMEMBER_USER, n); page.client_storage.set(STORAGE_REMEMBER_PASS, p)
            ranking_switch.value, my_group_list, active_ranking_group = True, [1], "1"
            refresh_ranking_dropdown_options(); enter_game_session(n, "登録成功")
        except Exception as ex: show_alert(f"登録エラー: {ex}")

    def enter_game_session(u, msg):
        nonlocal current_player; current_player = u
        logged_in_user_text.value = f"👤 {current_player}"
        edit_name_input.value = current_player
        login_view.visible, authenticated_view.visible = False, True
        if current_player == "admin" and len(main_tab_view.tabs) == 3: main_tab_view.tabs.append(ft.Tab(text="管理", content=admin_tab_view))
        elif current_player != "admin" and len(main_tab_view.tabs) == 4: main_tab_view.tabs.pop()
        reset_current_game(None); update_all_uis()
        page.overlay.append(ft.SnackBar(ft.Text(msg), open=True)); page.update()

    def check_auto_login():
        nonlocal my_group_list, active_ranking_group
        u, p = page.client_storage.get(STORAGE_REMEMBER_USER), page.client_storage.get(STORAGE_REMEMBER_PASS)
        if u and p:
            try:
                res = supabase.table("users").select("username").eq("username", u).eq("password", hash_password(p)).execute()
                if res.data:
                    priv = supabase.table("privacy").select("is_visible", "group_number").eq("username", u).execute()
                    my_group_list = []
                    if priv.data:
                        raw_g = str(priv.data.get("group_number", "1"))
                        if u.lower() == "admin": raw_g = "0"
                        my_group_list = [int(x.strip()) for x in raw_g.replace("，", ",").split(",") if x.strip().isdigit()]
                    if not my_group_list:
                        my_group_list = [0] if u.lower() == "admin" else [1]
                    active_ranking_group = "0" if u.lower() == "admin" else str(my_group_list[0])
                    refresh_ranking_dropdown_options(); enter_game_session(u, "自動ログイン")
            except Exception: pass

    def handle_logout(e):
        nonlocal current_player; current_player = None
        login_view.visible, authenticated_view.visible = True, False
        page.update()
    def handle_add_group_click(e):
        nonlocal my_group_list
        v = popup_group_input_field.value.strip()
        if not v or not v.isdigit(): return
        num = int(v)
        if current_player != "admin" and num == 0: return
        if num in my_group_list: return
        my_group_list.append(num); my_group_list.sort()
        popup_group_input_field.value = ""; save_group_list_to_database_and_refresh()

    def handle_remove_group_click(g_num):
        nonlocal my_group_list
        if current_player == "admin" and g_num == 0: return
        if g_num not in my_group_list: return
        my_group_list.remove(g_num); save_group_list_to_database_and_refresh()
    def save_group_list_to_database_and_refresh():
        try:
            c_str = ", ".join([str(n) for n in my_group_list])
            if not my_group_list: c_str, _ = ("0" if current_player == "admin" else "1"), my_group_list.append(0 if current_player == "admin" else 1)
            supabase.table("privacy").update({"group_number": c_str}).eq("username", current_player).execute()
            refresh_group_dialog_ui(); refresh_ranking_dropdown_options(); update_all_uis()
        except Exception: pass
    def refresh_group_dialog_ui():
        popup_current_group_container.controls.clear()
        for g in sorted(my_group_list):
            lock = (current_player == "admin" and g == 0)
            popup_current_group_container.controls.append(ft.Container(content=ft.Row([ft.Text(f"● グループ {g}"), ft.IconButton(ft.Icons.DELETE, disabled=lock, on_click=lambda e, n=g: handle_remove_group_click(n))]), padding=5))
        page.update()
    def handle_change_password(e):
        o, n = mypage_old_pass.value.strip(), mypage_new_pass.value.strip()
        if not o or not n: return
        try:
            res = supabase.table("users").select("username").eq("username", current_player).eq("password", hash_password(o)).execute()
            if res.data: supabase.table("users").update({"password": hash_password(n)}).eq("username", current_player).execute(); change_pass_dialog.open = False; show_alert("変更完了", "成功")
        except Exception: pass

    def handle_save_secret_question(e):
        q, a = mypage_question_input.value.strip(), mypage_answer_input.value.strip()
        if not q or not a: return
        try: supabase.table("users").update({"secret_question": q, "secret_answer": hash_password(a)}).eq("username", current_player).execute(); secret_question_dialog.open = False; show_alert("設定完了", "成功")
        except Exception: pass
    def handle_forgot_check_user(e):
        n = forgot_name_input.value.strip()
        if not n: return
        try:
            res = supabase.table("users").select("secret_question").eq("username", n).execute()
            forgot_question_text.value = f"❓ 質問: {res.data.get('secret_question') or '未設定'}" if res.data else "❌ 未登録"
        except Exception: pass
        page.update()
    def handle_forgot_reset_password(e):
        n, a, p = forgot_name_input.value.strip(), forgot_answer_input.value.strip(), forgot_new_pass_input.value.strip()
        if not n or not a or not p: return
        try:
            res = supabase.table("users").select("secret_answer").eq("username", n).execute()
            if res.data and res.data.get("secret_answer") == hash_password(a): supabase.table("users").update({"password": hash_password(p)}).eq("username", n).execute(); forgot_dialog.open = False; show_alert("再設定完了")
        except Exception: pass
    def handle_rename(e):
        nonlocal current_player; n = edit_name_input.value.strip()
        if not n or n == current_player: return
        try:
            res = supabase.table("users").select("username").eq("username", n).execute()
            if not res.data: supabase.table("users").update({"username": n}).eq("username", current_player).execute(); page.client_storage.set(STORAGE_REMEMBER_USER, n); current_player = n; logged_in_user_text.value = f"👤 {current_player}"; update_all_uis(); change_name_dialog.open = False
        except Exception: pass
    def handle_privacy_change(e):
        if current_player: supabase.table("privacy").update({"is_visible": e.control.value}).eq("username", current_player).execute(); update_ranking_ui()
    def execute_delete_account():
        if current_player: supabase.table("users").delete().eq("username", current_player).execute(); confirm_delete_dialog.open = False; handle_logout(None)
    def update_admin_ui():
        if current_player != "admin": return
        admin_data_table.rows.clear()
        try:
            u_res, p_res, r_res = supabase.table("users").select("username").execute(), supabase.table("privacy").select("username", "group_number").execute(), supabase.table("records").select("*").execute()
            g_map = {p["username"]: str(p.get("group_number", "1")) for p in (p_res.data or [])}
            for u in (u_res.data or []):
                name = u["username"]
                recs = [r for r in (r_res.data or []) if r["player"] == name]
                max_s = max([r["final_score"] for r in recs if r.get("final_score", 0) > 0]) if recs else 0
                admin_data_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(name)), ft.DataCell(ft.Text(g_map.get(name, "1"))), ft.DataCell(ft.Text(f"{max_s}点"))]))
        except Exception: pass
        page.update()
    def handle_tab_change(e):
        if main_tab_view.selected_index == 2: refresh_ranking_dropdown_options(); update_ranking_ui()

    change_group_dialog = ft.AlertDialog(title=ft.Text("班追加削除"), content=ft.Container(content=ft.Column([ft.Row([popup_group_input_field, ft.IconButton(ft.Icons.ADD, on_click=handle_add_group_click)]), ft.Divider(), ft.Container(content=popup_current_group_container, height=140)], tight=True), width=320, height=270))
    change_name_dialog = ft.AlertDialog(title=ft.Text("名変更"), content=ft.Container(content=edit_name_input, height=50), actions=[ft.ElevatedButton("変更", on_click=handle_rename)])
    change_pass_dialog = ft.AlertDialog(title=ft.Text("パス変更"), content=ft.Container(content=ft.Column([mypage_old_pass, mypage_new_pass]), height=120), actions=[ft.ElevatedButton("変更", on_click=handle_change_password)])
    secret_question_dialog = ft.AlertDialog(title=ft.Text("質問設定"), content=ft.Container(content=ft.Column([mypage_question_input, mypage_answer_input]), height=120), actions=[ft.ElevatedButton("保存", on_click=handle_save_secret_question)])
    privacy_setting_dialog = ft.AlertDialog(title=ft.Text("公開設定"), content=ft.Container(content=ranking_switch, height=50))
    confirm_delete_dialog = ft.AlertDialog(title=ft.Text("退会"), content=ft.Text("削除しますか？"), actions=[ft.ElevatedButton("削除", on_click=lambda e: execute_delete_account())])
    forgot_dialog = ft.AlertDialog(title=ft.Text("パス再設定"), content=ft.Container(content=ft.Column([forgot_name_input, ft.ElevatedButton("質問確認", on_click=handle_forgot_check_user), forgot_question_text, forgot_answer_input, forgot_new_pass_input]), height=300), actions=[ft.ElevatedButton("更新", on_click=handle_forgot_reset_password)])

    action_buttons_row.controls = [ft.Container(content=register_btn, padding=5), ft.Container(content=login_btn, padding=5)]
    global_header_bar.content = ft.Row([logged_in_user_text, ft.TextButton("ログアウト", on_click=handle_logout)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    admin_tab_view = ft.Column([ft.Container(content=ft.Text("🛠️ 管理者パネル"), padding=12), ft.Row([admin_search_input]), admin_data_table], expand=True)
    login_view = ft.Container(content=ft.Column([ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80), ft.Text("プレイヤー認証", size=24), login_name_input, login_pass_input, action_buttons_row, ft.TextButton("🔑 パスワードを忘れた場合", on_click=lambda e: page.open(forgot_dialog))], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), alignment=ft.alignment.center, expand=True)
    calc_tab_view = ft.Column([ft.Container(content=ft.Column([ft.Text("現在の合計得点"), score_display]), alignment=ft.alignment.center), create_fruit_selector("🍎 りんご", "apple", apple_count_text, ft.Colors.RED_600), create_fruit_selector("🍊 みかん", "orange", orange_count_text, ft.Colors.ORANGE_600), create_fruit_selector("🍇 ブドウ", "grape", grape_count_text, ft.Colors.PURPLE_600), ft.Row([ft.OutlinedButton("リセット", on_click=reset_current_game), ft.ElevatedButton("保存", on_click=save_current_game)], alignment=ft.MainAxisAlignment.SPACE_EVENLY)], expand=True)
    mypage_tab_view = ft.Column([ft.Container(content=ft.Text("あなたの所属グループ")), ft.Container(content=mypage_group_chips), ft.Divider(), my_records_list, ft.Container(content=ft.Row([ft.IconButton(ft.Icons.ACCOUNT_CIRCLE, on_click=lambda e: page.open(change_name_dialog)), ft.IconButton(ft.Icons.NUMBERS, on_click=lambda e: (refresh_group_dialog_ui(), page.open(change_group_dialog))), ft.IconButton(ft.Icons.LOCK, on_click=lambda e: page.open(change_pass_dialog)), ft.IconButton(ft.Icons.SHIELD, on_click=lambda e: page.open(secret_question_dialog)), ft.IconButton(ft.Icons.VISIBILITY, on_click=lambda e: page.open(privacy_setting_dialog)), ft.IconButton(ft.Icons.DELETE_FOREVER, on_click=lambda e: page.open(confirm_delete_dialog))], wrap=True), padding=10, bgcolor=ft.Colors.BLUE_GREY_600, border_radius=10)], expand=True, scroll=ft.ScrollMode.AUTO)
    main_tab_view = ft.Tabs(selected_index=0, tabs=[ft.Tab(text="得点計算", icon=ft.Icons.CALCULATE, content=calc_tab_view), ft.Tab(text="マイページ", icon=ft.Icons.PERSON, content=mypage_tab_view), ft.Tab(text="ランキング", icon=ft.Icons.EMOJI_EVENTS, content=ranking_tab_view)], expand=True, on_change=handle_tab_change)
    authenticated_view = ft.Column([global_header_bar, main_tab_view], expand=True, visible=False)

    def delete_saved_record(target_id):
        try: supabase.table("records").delete().eq("id", target_id).execute(); update_all_uis()
        except Exception: pass

    page.controls.clear(); page.add(login_view, authenticated_view); calculate_total_score_ui_only()
    login_name_input.value = page.client_storage.get(STORAGE_REMEMBER_USER) or ""
    login_pass_input.value = page.client_storage.get(STORAGE_REMEMBER_PASS) or ""
    check_auto_login(); page.update()

if __name__ == "__main__":
    ft.app(target=main, host="0.0.0.0", view=ft.AppView.WEB_BROWSER, port=int(os.getenv("PORT", 8000)))
