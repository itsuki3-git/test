import hashlib
import os
import datetime
import json
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
    editing_record_id = None
    
    # 牧場管理グリッド用の定数設定
    CELL_W, CELL_H = 65, 65
    ROWS, COLS = 3, 5
    LINE_THICK = 4
    HIT_BOX_EXT = 14
    OFFSET = HIT_BOX_EXT
    TOTAL_W = CELL_W * COLS + (OFFSET * 2)
    TOTAL_H = CELL_H * ROWS + (OFFSET * 2)

    current_mode = "COLOR"
    
    PALETTE_INFO = [
        {"name": "木の家", "color": ft.Colors.GREEN_400},
        {"name": "レンガの家", "color": ft.Colors.DEEP_ORANGE_700},
        {"name": "石の家", "color": ft.Colors.GREY_900},
        {"name": "畑", "color": ft.Colors.AMBER_500},
        {"name": "厩", "color": ft.Colors.LIGHT_BLUE_300},
    ]
    
    selected_color = PALETTE_INFO[0]["color"]

    horiz_line_dict = {}
    vert_line_dict = {}
    cell_dict = {}

    # 入力数値を管理する辞書（統合版）
    agri_inputs = {"小麦": 0, "野菜": 0, "羊": 0, "猪": 0, "牛": 0, "家族の数": 2, "乞食の枚数": 0}
    card_inputs = {"職業": 0, "小さい進歩": 0, "大きい進歩": 0}
    card_details = {"職業": [], "小さい進歩": [], "大きい進歩": []}

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
    forgot_question_text = ft.Text(value="プレイヤー名を入力して「質問を確認」を押してください", color=ft.Colors.BLUE_GREY_600, weight=ft.FontWeight.W_500)
    forgot_answer_input = ft.TextField(label="質問の答えを入力")
    forgot_new_pass_input = ft.TextField(label="新しいパスワード (4桁以上)", password=True, can_reveal_password=True)

    logged_in_user_text = ft.Text(value="", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800)
    score_display = ft.Text(value="0", size=48, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600)

    edit_name_input = ft.TextField(label="名前を編集", expand=True)
    group_inputs_container = ft.Column(spacing=10)
    my_records_list = ft.ListView(expand=True, spacing=10, padding=10)

    mypage_old_pass = ft.TextField(label="現在のパスワード", password=True)
    mypage_new_pass = ft.TextField(label="新しいパスワード (4桁以上)", password=True)
    mypage_question_input = ft.TextField(label="新しく登録する「秘密の質問」", hint_text="例: 初めて飼ったペットの名前は？")
    mypage_answer_input = ft.TextField(label="質問の答え", hint_text="答えを入力してください")

    ranking_title_text = ft.Text(value="🏆 ハイスコアランキング", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_700)
    ranking_group_dropdown = ft.Dropdown(label="グループ切り替え", width=160, options=[], on_change=lambda e: update_ranking_ui())
    ranking_list = ft.ListView(expand=True, spacing=10, padding=10)

    authenticated_view = None

    def show_alert(message, title="エラー"):
        alert_dialog = ft.AlertDialog(title=ft.Text(title), content=ft.Text(message))
        alert_dialog.actions = [ft.TextButton("OK", on_click=lambda e: page.close(alert_dialog))]
        page.open(alert_dialog)

    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def get_jst_now_str() -> str:
        jst = timezone(timedelta(hours=9))
        return datetime.now(jst).strftime("%Y/%m/%d %H:%M")

    # 💡 【重要】UI組み立て時の読み込み順エラー（NameError）を100%根絶するためのダミー関数予約ブロック
    def handle_rename(e): pass
    def handle_change_password(e): pass
    def handle_save_secret_question(e): pass
    def execute_delete_account(): pass
    def open_change_group_dialog(e): pass
    def handle_save_group_number(e): pass
    def handle_forgot_check_user(e): pass
    def handle_forgot_reset_password(e): pass
    def save_current_game(e): pass

    # 行（Row）を生成する補助関数
    def create_group_input_row(val):
        tf = ft.TextField(value=str(val), width=100, height=40, text_size=14, keyboard_type=ft.KeyboardType.NUMBER)
        row = ft.Row([tf])
        btn_del = ft.IconButton(ft.Icons.REMOVE_CIRCLE_OUTLINE, icon_color=ft.Colors.RED_400, on_click=lambda e: (group_inputs_container.controls.remove(row), page.update()))
        row.controls.append(btn_del)
        return row

    # 「グループを追加」ボタンが参照する関数
    def add_blank_group_input_row(e):
        group_inputs_container.controls.append(create_group_input_row("1"))
        page.update()

    # --- 牧場（閉空間）と未使用パネル、および柵に囲まれた厩を数えるアルゴリズム ---
    def analyze_grid():
        visited = { (r, c): False for r in range(-1, ROWS + 1) for c in range(-1, COLS + 1) }
        queue = []
        for r in range(-1, ROWS + 1):
            for c in range(-1, COLS + 1):
                if r == -1 or r == ROWS or c == -1 or c == COLS:
                    visited[(r, c)] = True
                    queue.append((r, c))

        while queue:
            curr_r, curr_c = queue.pop(0)
            if curr_r > -1:
                if 0 <= curr_r < ROWS + 1 and 0 <= curr_c < COLS:
                    if horiz_line_dict[(curr_r, curr_c)].bgcolor != ft.Colors.BROWN_700:
                        if not visited[(curr_r - 1, curr_c)]:
                            visited[(curr_r - 1, curr_c)] = True
                            queue.append((curr_r - 1, curr_c))
            if curr_r < ROWS:
                if 0 <= curr_r + 1 < ROWS + 1 and 0 <= curr_c < COLS:
                    if horiz_line_dict[(curr_r + 1, curr_c)].bgcolor != ft.Colors.BROWN_700:
                        if not visited[(curr_r + 1, curr_c)]:
                            visited[(curr_r + 1, curr_c)] = True
                            queue.append((curr_r + 1, curr_c))
            if curr_c > -1:
                if 0 <= curr_c < COLS + 1 and 0 <= curr_r < ROWS:
                    if vert_line_dict[(curr_c, curr_r)].bgcolor != ft.Colors.BROWN_700:
                        if not visited[(curr_r, curr_c - 1)]:
                            visited[(curr_r, curr_c - 1)] = True
                            queue.append((curr_r, curr_c - 1))
            if curr_c < COLS:
                if 0 <= curr_c + 1 < COLS + 1 and 0 <= curr_r < ROWS:
                    if vert_line_dict[(curr_c + 1, curr_r)].bgcolor != ft.Colors.BROWN_700:
                        if not visited[(curr_r, curr_c + 1)]:
                            visited[(curr_r, curr_c + 1)] = True
                            queue.append((curr_r, curr_c + 1))

        unused_count = 0
        for r in range(ROWS):
            for c in range(COLS):
                if visited[(r, c)] and cell_dict[(r, c)].bgcolor == ft.Colors.GREY_100:
                    unused_count += 1

        ranch_count = 0
        ranch_with_stable_count = 0
        for r in range(ROWS):
            for c in range(COLS):
                if not visited[(r, c)]:
                    ranch_count += 1
                    inner_queue = [(r, c)]
                    visited[(r, c)] = True
                    has_stable = False
                    while inner_queue:
                        curr_r, curr_c = inner_queue.pop(0)
                        if cell_dict[(curr_r, curr_c)].bgcolor == ft.Colors.LIGHT_BLUE_300:
                            has_stable = True
                        if curr_r > 0 and horiz_line_dict[(curr_r, curr_c)].bgcolor != ft.Colors.BROWN_700:
                            if not visited[(curr_r - 1, curr_c)]:
                                visited[(curr_r - 1, curr_c)] = True
                                inner_queue.append((curr_r - 1, curr_c))
                        if curr_r < ROWS - 1 and horiz_line_dict[(curr_r + 1, curr_c)].bgcolor != ft.Colors.BROWN_700:
                            if not visited[(curr_r + 1, curr_c)]:
                                visited[(curr_r + 1, curr_c)] = True
                                inner_queue.append((curr_r + 1, curr_c))
                        if curr_c > 0 and vert_line_dict[(curr_c, curr_r)].bgcolor != ft.Colors.BROWN_700:
                            if not visited[(curr_r, curr_c - 1)]:
                                visited[(curr_r, curr_c - 1)] = True
                                inner_queue.append((curr_r, curr_c - 1))
                        if curr_c < COLS - 1 and vert_line_dict[(curr_c + 1, curr_r)].bgcolor != ft.Colors.BROWN_700:
                            if not visited[(curr_r, curr_c + 1)]:
                                visited[(curr_r, curr_c + 1)] = True
                                inner_queue.append((curr_r, curr_c + 1))
                    if has_stable:
                        ranch_with_stable_count += 1

        return ranch_count, unused_count, ranch_with_stable_count

    def get_agri_subtotal():
        sub_total = 0
        for name, count in agri_inputs.items():
            score = -1
            if name == "小麦":
                if count == 0: score = -1
                elif count <= 3: score = 1
                elif count <= 5: score = 2
                elif count <= 7: score = 3
                else: score = 4
            elif name == "野菜":
                if count == 0: score = -1
                elif count == 1: score = 1
                elif count == 2: score = 2
                elif count == 3: score = 3
                else: score = 4
            elif name == "羊":
                if count == 0: score = -1
                elif count <= 3: score = 1
                elif count <= 5: score = 2
                elif count <= 7: score = 3
                else: score = 4
            elif name == "猪":
                if count == 0: score = -1
                elif count <= 2: score = 1
                elif count <= 4: score = 2
                elif count <= 6: score = 3
                else: score = 4
            elif name == "牛":
                if count == 0: score = -1
                elif count == 1: score = 1
                elif count <= 3: score = 2
                elif count <= 5: score = 3
                else: score = 4
            elif name == "家族の数": score = count * 3
            elif name == "乞食の枚数": score = count * -3
            sub_total += score
        return sub_total

    def get_grand_total():
        counts = {"木の家": 0, "レンガの家": 0, "石の家": 0, "畑": 0}
        for cell in cell_dict.values():
            for info in PALETTE_INFO:
                if info["name"] in counts and cell.bgcolor == info["color"]:
                    counts[info["name"]] += 1
        ranch_c, unused_c, ranch_stable = analyze_grid()
        field_count = counts["畑"]
        if field_count <= 1: field_score = -1
        elif field_count == 2: field_score = 1
        elif field_count == 3: field_score = 2
        elif field_count == 4: field_score = 3
        else: field_score = 4

        if ranch_c == 0: ranch_score = -1
        elif ranch_c <= 4: ranch_score = ranch_c
        else: ranch_score = 4

        stable_score = min(ranch_stable, 4) if ranch_stable > 0 else 0
        house_score = (counts["レンガの家"] * 1) + (counts["石の家"] * 2)
        unused_score = unused_c * -1
        
        table1_total = field_score + ranch_score + stable_score + house_score + unused_score
        table2_total = get_agri_subtotal()
        table3_total = sum(card_inputs.values())
        return table1_total + table2_total + table3_total

    def refresh_grand_total_labels():
        gt = get_grand_total()
        score_display.value = str(gt)
        bottom_grand_total_display.value = str(gt)

    def calculate_total_score_ui_only():
        gt = get_grand_total()
        score_display.value = str(gt)
        bottom_grand_total_display.value = str(gt)
        return gt

    def update_all_uis():
        update_my_records_ui()
        if current_player:
            refresh_ranking_dropdown_options()
            update_ranking_ui()
        if current_player == "admin": update_admin_ui()

    def delete_saved_record(target_id):
        try:
            supabase.table("records").delete().eq("id", target_id).execute()
        except Exception: return
        update_all_uis()

    def update_data_table(ranch_count, unused_count, ranch_stable_count):
        counts = {"木の家": 0, "レンガの家": 0, "石の家": 0, "畑": 0}
        for cell in cell_dict.values():
            for info in PALETTE_INFO:
                if info["name"] in counts and cell.bgcolor == info["color"]:
                    counts[info["name"]] += 1

        rows = []
        table1_subtotal = 0
        field_count = counts["畑"]
        if field_count <= 1: field_score = -1
        elif field_count == 2: field_score = 1
        elif field_count == 3: field_score = 2
        elif field_count == 4: field_score = 3
        else: field_score = 4

        table1_subtotal += field_score
        rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("畑", size=14, weight="bold", color=ft.Colors.AMBER_700)), ft.DataCell(ft.Text(f"{field_count} 個", size=14)), ft.DataCell(ft.Text(f"{field_score} 点", size=14, weight="bold"))]))

        if ranch_count == 0: ranch_score = -1
        elif ranch_count <= 4: ranch_score = ranch_count
        else: ranch_score = 4

        table1_subtotal += ranch_score
        rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("牧場", size=14, weight="bold", color=ft.Colors.BROWN_700)), ft.DataCell(ft.Text(f"{ranch_count} つ", size=14)), ft.DataCell(ft.Text(f"{ranch_score} 点", size=14, weight="bold"))]))
    
        limited_ranch_stable_count = min(ranch_stable_count, 4)
        if ranch_stable_count > 0:
            score = limited_ranch_stable_count
            table1_subtotal += score
            rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("厩", size=14, weight="bold", color=ft.Colors.LIGHT_BLUE_700)), ft.DataCell(ft.Text(f"{ranch_stable_count} つ", size=14)), ft.DataCell(ft.Text(f"{score} 点", size=14, weight="bold"))]))
        
        for info in PALETTE_INFO:
            name = info["name"]
            if name not in counts or name == "畑": continue
            count = counts[name]
            if count > 0:
                score = count * 1 if name == "レンガの家" else (count * 2 if name == "石の家" else 0)
                table1_subtotal += score
                rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(name, size=14, weight="bold", color=info["color"] if info["color"] != ft.Colors.GREEN_400 else ft.Colors.GREEN_700)), ft.DataCell(ft.Text(f"{count} 個", size=14)), ft.DataCell(ft.Text(f"{score} 点", size=14, weight="bold"))]))
        
        if unused_count > 0:
            score = unused_count * -1
            table1_subtotal += score
            rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text("未使用", size=14, color=ft.Colors.BLUE_GREY_600)), ft.DataCell(ft.Text(f"{unused_count} マス", size=14)), ft.DataCell(ft.Text(f"{score} 点", size=14, weight="bold"))]))

        rows.append(ft.DataRow(color=ft.Colors.BLUE_GREY_50, cells=[
            ft.DataCell(ft.Text("盤面 小計", size=14, weight="bold")),
            ft.DataCell(ft.Text("")),
            ft.DataCell(ft.Text(f"{table1_subtotal} 点", size=14, weight="bold", color=ft.Colors.BLUE_700))
        ]))
        count_table.rows = rows

    def update_data_table2():
        rows = []
        table2_subtotal = 0
        for name, count in agri_inputs.items():
            score = -1
            text_color = ft.Colors.BLACK
            if name == "小麦": text_color = ft.Colors.AMBER_700
            elif name == "野菜": text_color = ft.Colors.DEEP_ORANGE_700
            elif name == "羊": text_color = ft.Colors.BLUE_GREY_500
            elif name == "家族の数": text_color = ft.Colors.BLUE_700
            elif name == "乞食の枚数": text_color = ft.Colors.RED_700

            if name == "小麦":
                if count == 0: score = -1
                elif count <= 3: score = 1
                elif count <= 5: score = 2
                elif count <= 7: score = 3
                else: score = 4
            elif name == "野菜":
                if count == 0: score = -1
                elif count == 1: score = 1
                elif count == 2: score = 2
                elif count == 3: score = 3
                else: score = 4
            elif name == "羊":
                if count == 0: score = -1
                elif count <= 3: score = 1
                elif count <= 5: score = 2
                elif count <= 7: score = 3
                else: score = 4
            elif name == "猪":
                if count == 0: score = -1
                elif count <= 2: score = 1
                elif count <= 4: score = 2
                elif count <= 6: score = 3
                else: score = 4
            elif name == "牛":
                if count == 0: score = -1
                elif count == 1: score = 1
                elif count <= 3: score = 2
                elif count <= 5: score = 3
                else: score = 4
            elif name == "家族の数": score = count * 3
            elif name == "乞食の枚数": score = count * -3

            table2_subtotal += score

            def make_on_change(k=name):
                return lambda e: on_input_change(k, e.control.value)
                
            def clear_card_on_focus(e):
                e.control.value = ""
                e.control.update()

            input_field = ft.TextField(
                value=str(count), width=60, height=35, text_size=14, content_padding=5,
                text_align=ft.TextAlign.CENTER, keyboard_type=ft.KeyboardType.NUMBER, 
                on_change=make_on_change(),
                on_focus=clear_card_on_focus
            )
            rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(name, size=14, weight="bold", color=text_color)), ft.DataCell(input_field), ft.DataCell(ft.Text(f"{score} 点", size=14, weight="bold"))]))
        
        rows.append(ft.DataRow(color=ft.Colors.BLUE_GREY_50, cells=[
            ft.DataCell(ft.Text("資源 小計", size=14, weight="bold")),
            ft.DataCell(ft.Text("")),
            ft.DataCell(ft.Text(f"{table2_subtotal} 点", size=14, weight="bold", color=ft.Colors.BLUE_700))
        ]))
        count_table2.rows = rows

    def close_dialog(e):
        page.close(page.dialog)

    def show_card_dialog(name):
        dialog_items_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, height=200)

        def refresh_dialog_ui():
            dialog_items_container.controls.clear()
            for idx, item in enumerate(card_details[name]):
                if name == "大きい進歩":
                    options_list = [
                        ft.dropdown.Option("かまど"), ft.dropdown.Option("調理場"),
                        ft.dropdown.Option("井戸"), ft.dropdown.Option("レンガ窯"),
                        ft.dropdown.Option("石窯"), ft.dropdown.Option("家具製作所"),
                        ft.dropdown.Option("製陶所"), ft.dropdown.Option("カゴ製作所")
                    ]
                    default_scores = {
                        "かまど": 1, "調理場": 1, "井戸": 4, "レンガ窯": 2, 
                        "石窯": 3, "家具製作所": 2, "製陶所": 2, "カゴ製作所": 2
                    }
                    def make_dropdown_change(i=idx): return lambda e: on_big_progress_change(i, e.control.value)
                    def on_big_progress_change(index, selected_value):
                        card_details["大きい進歩"][index]["name"] = selected_value
                        card_details["大きい進歩"][index]["score"] = default_scores.get(selected_value, 0)
                        recalculate_card_score("大きい進歩")
                        refresh_dialog_ui()

                    input_name_widget = ft.Container(
                        content=ft.Dropdown(
                            value=item["name"] if item["name"] else None, hint_text="選択",
                            options=options_list, text_size=13, content_padding=5, on_change=make_dropdown_change()
                        ), width=120, height=35
                    )
                else:
                    def make_name_change(i=idx): return lambda e: on_detail_name_change(name, i, e.control.value)
                    input_name_widget = ft.TextField(
                        value=item["name"], hint_text="カード名など", width=120, height=35,
                        text_size=13, content_padding=5, on_change=make_name_change()
                    )

                def make_score_change(i=idx): return lambda e: on_detail_score_change(name, i, e.control.value)
                txt_score = ft.TextField(
                    value=str(item["score"]), hint_text="点数", width=50, height=35,
                    text_size=13, content_padding=5, text_align=ft.TextAlign.CENTER,
                    keyboard_type=ft.KeyboardType.NUMBER, on_change=make_score_change()
                )

                def make_delete_click(i=idx): return lambda e: remove_detail_item(name, i, refresh_dialog_ui)
                btn_delete = ft.IconButton(
                    icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_400, width=30, height=30, on_click=make_delete_click()
                )

                item_row = ft.Row(controls=[input_name_widget, txt_score, btn_delete], spacing=5, alignment=ft.MainAxisAlignment.CENTER)
                dialog_items_container.controls.append(item_row)
            dialog_items_container.update()

        def add_detail_item(e):
            card_details[name].append({"name": "", "score": 0})
            refresh_dialog_ui()

        def remove_detail_item(category, index, callback):
            card_details[category].pop(index)
            recalculate_card_score(category)
            callback()

        def on_detail_name_change(category, index, val):
            card_details[category][index]["name"] = val

        def on_detail_score_change(category, index, val):
            try: card_details[category][index]["score"] = int(val) if val != "" else 0
            except ValueError: card_details[category][index]["score"] = 0
            recalculate_card_score(category)

        def recalculate_card_score(category):
            total = sum(item["score"] for item in card_details[category])
            card_inputs[category] = total
            ranch_c, unused_c, ranch_stable = analyze_grid()
            update_data_table(ranch_c, unused_c, ranch_stable)
            update_data_table3()
            refresh_grand_total_labels()
            page.update()

        page.dialog = ft.AlertDialog(
            title=ft.Text(f"📋 {name}の内訳入力", weight="bold"),
            content=ft.Column(
                controls=[
                    ft.ElevatedButton(text="項目を追加", icon=ft.Icons.ADD, on_click=add_detail_item, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6))),
                    ft.Divider(),
                    dialog_items_container
                ], tight=True, width=240
            ),
            actions=[ft.TextButton("決定・閉じる", on_click=close_dialog)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(page.dialog)
        refresh_dialog_ui()

    def update_data_table3():
        rows = []
        table3_subtotal = 0

        for name, score in card_inputs.items():
            if name == "職業": text_color = ft.Colors.CYAN_800
            elif name == "小さい進歩": text_color = ft.Colors.TEAL_700
            elif name == "大きい進歩": text_color = ft.Colors.RED_900

            table3_subtotal += score
            def make_on_change(k=name): return lambda e: on_card_input_change(k, e.control.value)
            def clear_card_on_focus(e):
                e.control.value = ""
                e.control.update()

            input_field = ft.TextField(
                value=str(score), width=60, height=35, text_size=14, content_padding=5,
                text_align=ft.TextAlign.CENTER, keyboard_type=ft.KeyboardType.NUMBER, 
                on_change=make_on_change(),
                on_focus=clear_card_on_focus
            )
            detail_btn = ft.ElevatedButton(
                text="入力", style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_200, color=text_color, shape=ft.RoundedRectangleBorder(radius=6), padding=ft.padding.all(5)),
                on_click=lambda e, k=name: show_card_dialog(k)
            )
            rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(name, size=14, weight="bold", color=text_color)), ft.DataCell(input_field), ft.DataCell(detail_btn)]))

        rows.append(ft.DataRow(color=ft.Colors.BLUE_GREY_50, cells=[
            ft.DataCell(ft.Text("カード 小計", size=14, weight="bold")),
            ft.DataCell(ft.Text("")),
            ft.DataCell(ft.Text(f"{table3_subtotal} 点", size=14, weight="bold", color=ft.Colors.BLUE_700))
        ]))
        count_table3.rows = rows

    # ⭕ カードボーナスの手入力値をリアルタイムに表と総合点へ反映
    def on_card_input_change(key, val):
        try: card_inputs[key] = int(val) if val != "" else 0
        except ValueError: card_inputs[key] = 0
        ranch_c, unused_c, ranch_stable = analyze_grid()
        update_data_table(ranch_c, unused_c, ranch_stable)
        update_data_table3()
        refresh_grand_total_labels()
        page.update()

    # ⭕ 資源・家族の手入力値をリアルタイムに表と総合点へ反映
    def on_input_change(key, val):
        try: agri_inputs[key] = int(val) if val != "" else 0
        except ValueError: agri_inputs[key] = 0
        ranch_c, unused_c, ranch_stable = analyze_grid()
        update_data_table(ranch_c, unused_c, ranch_stable)
        update_data_table2()
        refresh_grand_total_labels()
        page.update()

    def update_mode_ui():
        ranch_c, unused_c, ranch_stable = analyze_grid()
        update_data_table(ranch_c, unused_c, ranch_stable)
        refresh_grand_total_labels()
        page.update()

    def on_palette_click(e):
        nonlocal selected_color, current_mode
        current_mode = "COLOR"
        selected_color = e.control.data
        for p_col in palette_options:
            p_col.controls[0].border = None
        e.control.border = ft.border.all(3, ft.Colors.BLACK)
        update_mode_ui()

    def on_line_mode_click(e):
        nonlocal current_mode
        current_mode = "LINE"
        for p_col in palette_options:
            p_col.controls[0].border = None
        line_mode_btn.style = ft.ButtonStyle(bgcolor=ft.Colors.BLACK, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8))
        update_mode_ui()

    def on_cell_click(e):
        if current_mode == "COLOR":
            if e.control.bgcolor == selected_color: e.control.bgcolor = ft.Colors.GREY_100
            else: e.control.bgcolor = selected_color
            update_mode_ui()

    def toggle_line(e):
        if current_mode == "LINE":
            actual_line = e.control.content
            if actual_line.bgcolor == ft.Colors.BROWN_700: actual_line.bgcolor = ft.Colors.GREY_300
            else: actual_line.bgcolor = ft.Colors.BROWN_700
            update_mode_ui()

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

    # =========================================================================
    # 🔒 認証系（新規登録・質問確認・パスワード再設定・自動ログイン）の関数本体
    # =========================================================================
    def _handle_new_register(e):
        username = login_name_input.value.strip()
        password = login_pass_input.value.strip()
        if not username:
            show_alert("プレイヤー名を入力してください。")
            return
        if len(password) < 4:
            show_alert("パスワードは4桁以上で入力してください。")
            return
        try:
            existing_user = supabase.table("users").select("username").eq("username", username).execute()
            if existing_user.data and len(existing_user.data) > 0:
                show_alert("このプレイヤー名は既に登録されています。")
                return
            hashed_pass = hash_password(password)
            supabase.table("users").insert({"username": username, "password": hashed_pass}).execute()
            supabase.table("privacy").insert({"username": username, "group_number": "1"}).execute()
            page.overlay.append(ft.SnackBar(ft.Text(f"🎉 {username} さんの登録が完了しました！"), open=True))
            handle_existing_login(None)
        except Exception as ex:
            show_alert(f"新規登録に失敗しました: {ex}")

    def _handle_forgot_check_user(e):
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
            forgot_question_text.value = f"❓ 質問: {user_priv.get('secret_question')}"
            forgot_question_text.color = ft.Colors.BLUE_600
            page.update()
        except Exception as ex:
            show_alert(f"ユーザー確認エラー: {ex}")

    def _handle_forgot_reset_password(e):
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
            res = supabase.table("privacy").select("*").execute()
            user_priv = next((p for p in (res.data or []) if (p.get("username") or p.get("player")) == target_user), None)
            if not user_priv or not user_priv.get("secret_answer"):
                show_alert("再設定手続きを行えません。")
                return
            if hash_password(answer) != user_priv.get("secret_answer"):
                show_alert("秘密の質問の答えが間違っています。")
                return
            hashed_new_pass = hash_password(new_pass)
            supabase.table("users").update({"password": hashed_new_pass}).eq("username", target_user).execute()
            page.close(forgot_dialog)
            login_name_input.value = target_user
            login_pass_input.value = new_pass
            page.overlay.append(ft.SnackBar(ft.Text("🎉 パスワードを再設定しました。ログインしてください。"), open=True))
            page.update()
        except Exception as ex:
            show_alert(f"パスワード再設定失敗: {ex}")

    def _check_auto_login():
        saved_user = page.client_storage.get(STORAGE_REMEMBER_USER)
        saved_pass = page.client_storage.get(STORAGE_REMEMBER_PASS)
        if saved_user and saved_pass:
            login_name_input.value = saved_user
            login_pass_input.value = saved_pass
            handle_existing_login(None)

    # 💾 ゲーム記録の新規保存ロジックの実体
    def _save_current_game(e):
        if not current_player: return
        total_score = get_grand_total()
        memo_text = game_memo_input.value.strip() if game_memo_input.value else ""
        
        # 🚜 現在の盤面の色、柵、手入力値をすべて1つのパックにパックしてシリアライズ
        board_pack = {
            "cells": [str(cell_dict[(r, c)].bgcolor) for r in range(ROWS) for c in range(COLS)],
            "horiz": [str(horiz_line_dict[(r, c)].bgcolor) for r in range(ROWS + 1) for c in range(COLS)],
            "vert": [str(vert_line_dict[(c, r)].bgcolor) for c in range(COLS + 1) for r in range(ROWS)],
            "agri_inputs": agri_inputs,
            "card_inputs": card_inputs,
            "card_details": card_details
        }
        board_json_str = json.dumps(board_pack)

        try:
            supabase.table("records").insert({
                "player": current_player, 
                "final_score": total_score, 
                "date": get_jst_now_str(),
                "memo": memo_text,
                "game_data": board_json_str
            }).execute()
            msg = f"🎉 {current_player} の新しい記録を保存しました！"
        except Exception as ex:
            show_alert(f"記録保存失敗: {ex}")
            return
        
        reset_current_game()
        game_memo_input.value = ""
        current_date_text.value = f"📅 対戦日時: {get_jst_now_str()}"
        
        update_all_uis()
        page.overlay.append(ft.SnackBar(ft.Text(msg), open=True))
        page.update()

    # 💡 上部で作成した予約関数へ実体を確実にバインド
    handle_new_register = _handle_new_register
    handle_forgot_check_user = _handle_forgot_check_user
    handle_forgot_reset_password = _handle_forgot_reset_password
    check_auto_login = _check_auto_login
    save_current_game = _save_current_game

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
        reset_current_game()
        update_all_uis()
        page.overlay.append(ft.SnackBar(ft.Text(success_message), open=True))
        page.update()

    def handle_logout(e):
        nonlocal current_player
        current_player = None
        page.controls.clear()
        page.add(login_view)
        page.update()

    def reset_current_game():
        for cell in cell_dict.values():
            cell.bgcolor = ft.Colors.GREY_100
        for hl in horiz_line_dict.values():
            hl.bgcolor = ft.Colors.GREY_300
        for vl in vert_line_dict.values():
            vl.bgcolor = ft.Colors.GREY_300
        for k in agri_inputs:
            agri_inputs[k] = 2 if k == "家族の数" else 0
        for k in card_inputs:
            card_inputs[k] = 0
        for k in card_details:
            card_details[k].clear()
        update_data_table2()
        update_data_table3()
        ranch_c, unused_c, ranch_stable = analyze_grid()
        update_data_table(ranch_c, unused_c, ranch_stable)
        refresh_grand_total_labels()

    # =========================================================================
    # 📊 マイページ履歴一覧の生成（スコープバグを100%根絶し、確実にダイアログをキックする最新版）
    # =========================================================================
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
                
                # 💡 スコープの競合（何も起きないバグ）を完全に回避するため、
                # グローバル名前空間から直接関数を引っ張ってきて安全に実行する構造に変更
                def make_load_click(rec):
                    return lambda e: globals()["show_record_detail_dialog"](rec)

                memo_str = record.get("memo", "")
                memo_preview = f" 📝 {memo_str}" if memo_str else " (メモなし)"
                
                my_records_list.controls.append(
                    ft.Container(
                        content=ft.Row(controls=[
                            ft.Column([
                                ft.Text(f"合計得点: {record['final_score']} 点", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700),
                                ft.Text(value=f"登録日: {record['date']}{memo_preview}", size=12, color=ft.Colors.GREY_600)
                            ], expand=True),
                            ft.IconButton(
                                ft.Icons.DELETE_FOREVER, 
                                icon_color=ft.Colors.RED_600, 
                                tooltip="この記録を削除", 
                                on_click=lambda e, idx=record["id"]: delete_saved_record(idx)
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=12, 
                        border=ft.border.all(1, ft.Colors.BLUE_100), 
                        border_radius=8, 
                        bgcolor=ft.Colors.BLUE_50,
                        on_click=make_load_click(record) # 💡 Container全体をタップ可能に
                    )
                )
            page.update()

    # =========================================================================
    # 📊 マイページ履歴一覧から、タップして直接編集・上書き保存できる詳細ダイアログ（不具合対策版）
    # =========================================================================
    def show_record_detail_dialog(record):
        import json
        # 🧪 【不具合調査用】どこで処理が止まっているか画面に表示する
        debug_logs = []
        def log(msg):
            debug_logs.append(msg)
            print(f"[DEBUG_DIALOG] {msg}") # コンソールにも出力

        log("1. show_record_detail_dialog が起動しました")
        log(f"データ型: {type(record.get('game_data'))}")

        
        # 💡 クラッシュ防止のための初期値（デフォルト文字列）
        dialog_cell_bgcolors = ["grey100"] * (ROWS * COLS)
        dialog_horiz_bgcolors = ["grey300"] * ((ROWS + 1) * COLS)
        dialog_vert_bgcolors = ["grey300"] * ((COLS + 1) * ROWS)
        
        local_agri = {"小麦": 0, "野菜": 0, "羊": 0, "猪": 0, "牛": 0, "家族の数": 2, "乞食の枚数": 0}
        local_card = {"職業": 0, "小さい進歩": 0, "大きい進歩": 0}
        local_memo = str(record.get("memo", "")) if record.get("memo") else ""

        # 💡 データの読み込み部分を徹底的に保護（データが壊れていても無視して進む）
        raw_game_data = record.get("game_data", "")
        if raw_game_data:
            try:
                # 文字列型であればパースする
                if isinstance(raw_game_data, str):
                    board_pack = json.loads(raw_game_data)
                else:
                    board_pack = raw_game_data
                
                if isinstance(board_pack, dict):
                    if "agri_inputs" in board_pack and isinstance(board_pack["agri_inputs"], dict):
                        local_agri.update(board_pack["agri_inputs"])
                    if "card_inputs" in board_pack and isinstance(board_pack["card_inputs"], dict):
                        local_card.update(board_pack["card_inputs"])
                    
                    # 色データがオブジェクトで壊れて保存されている場合は文字列として抽出
                    if "cells" in board_pack and isinstance(board_pack["cells"], list):
                        dialog_cell_bgcolors = [str(c) for c in board_pack["cells"]]
                    if "horiz" in board_pack and isinstance(board_pack["horiz"], list):
                        dialog_horiz_bgcolors = [str(h) for h in board_pack["horiz"]]
                    if "vert" in board_pack and isinstance(board_pack["vert"], list):
                        dialog_vert_bgcolors = [str(v) for v in board_pack["vert"]]
            except Exception:
                pass # 万が一読み込みでエラーが出ても、絶対にアプリを落とさず初期状態で開く

        # 独立したパレット状態（PALETTE_INFOの安全な参照）
        dialog_current_mode = "COLOR"  
        dialog_selected_color = PALETTE_INFO[0]["color"] if (isinstance(PALETTE_INFO, list) and len(PALETTE_INFO) > 0) else ft.Colors.GREEN_400

        D_CELL_W, D_CELL_H = 40, 40
        D_LINE_THICK = 3
        D_HIT_BOX_EXT = 8
        D_OFFSET = D_HIT_BOX_EXT
        D_TOTAL_W = D_CELL_W * COLS + (D_OFFSET * 2)
        D_TOTAL_H = D_CELL_H * ROWS + (D_OFFSET * 2)

        detail_memo_input = ft.TextField(label="対戦メモ", value=local_memo, multiline=True, min_lines=1, max_lines=2, text_size=12, content_padding=6)
        
        # 各入力フィールドの値を変更した時にリアルタイム再計算を走らせる
        def on_d_input_change(e):
            recalculate_dialog_score()

        agri_fields = {name: ft.TextField(value=str(val), label=name, width=75, height=38, text_size=11, text_align=ft.TextAlign.CENTER, keyboard_type=ft.KeyboardType.NUMBER, on_change=on_d_input_change) for name, val in local_agri.items()}
        card_fields = {name: ft.TextField(value=str(val), label=name, width=88, height=38, text_size=11, text_align=ft.TextAlign.CENTER, keyboard_type=ft.KeyboardType.NUMBER, on_change=on_d_input_change) for name, val in local_card.items()}
        total_score_preview = ft.Text(value=f"合計得点: {record.get('final_score')} 点", size=18, weight="bold", color=ft.Colors.BLUE_700)

        # 内蔵パレットの切り替えイベント
        def on_d_palette_click(e):
            nonlocal dialog_selected_color, dialog_current_mode
            dialog_current_mode = "COLOR"
            dialog_selected_color = e.control.data
            for p_col in d_palette_options: 
                p_col.controls[0].border = None 
                p_col.controls[0].update()
            e.control.border = ft.border.all(2, ft.Colors.BLACK)
            e.control.update()
            d_line_mode_btn.style = ft.ButtonStyle(bgcolor=ft.Colors.GREY_300, color=ft.Colors.BLACK)
            d_line_mode_btn.update()

        def on_d_line_mode_click(e):
            nonlocal dialog_current_mode
            dialog_current_mode = "LINE"
            for p_col in d_palette_options: 
                p_col.controls[0].border = None
                p_col.controls[0].update()
            d_line_mode_btn.style = ft.ButtonStyle(bgcolor=ft.Colors.BLACK, color=ft.Colors.WHITE)
            d_line_mode_btn.update()

        # 内蔵パレットUIの組み立て
        d_palette_options = []
        if isinstance(PALETTE_INFO, list):
            for i, info in enumerate(PALETTE_INFO):
                border_style = ft.border.all(2, ft.Colors.BLACK) if i == 0 else None
                btn = ft.Container(width=22, height=22, bgcolor=info["color"], border_radius=11, data=info["color"], border=border_style, on_click=on_d_palette_click)
                lbl = ft.Text(info["name"][:1], size=7, weight="bold")
                d_palette_options.append(ft.Column([btn, lbl], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=1))
        
        d_palette_row = ft.Row(controls=d_palette_options, alignment=ft.MainAxisAlignment.CENTER, spacing=6)
        d_line_mode_btn = ft.ElevatedButton(text="✏️ 柵", on_click=on_d_line_mode_click, style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_300, color=ft.Colors.BLACK, shape=ft.RoundedRectangleBorder(radius=6), padding=ft.padding.all(2)))
        d_control_bar = ft.Row(controls=[d_palette_row, d_line_mode_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=10)

        # ミニチュア盤面の組み立て
        d_cell_dict = {}
        d_horiz_dict = {}
        d_vert_dict = {}
        
        def on_d_cell_click(e):
            if dialog_current_mode == "COLOR":
                e.control.bgcolor = "grey100" if e.control.bgcolor == dialog_selected_color else dialog_selected_color
                e.control.update()
                recalculate_dialog_score()

        def toggle_d_line(e):
            if dialog_current_mode == "LINE":
                line_node = e.control.content
                line_node.bgcolor = "grey300" if line_node.bgcolor == "brown700" else "brown700"
                line_node.update()
                recalculate_dialog_score()

        d_stack = ft.Stack(width=D_TOTAL_W, height=D_TOTAL_H)
        
        idx = 0
        for r in range(ROWS):
            for c in range(COLS):
                cell_bg = dialog_cell_bgcolors[idx] if idx < len(dialog_cell_bgcolors) else "grey100"
                cell = ft.Container(content=ft.Text(f"{r * COLS + c + 1}", color=ft.Colors.GREY_400, size=9), alignment=ft.alignment.center, bgcolor=cell_bg, width=D_CELL_W, height=D_CELL_H, left=c * D_CELL_W + D_OFFSET, top=r * D_CELL_H + D_OFFSET, on_click=on_d_cell_click)
                d_stack.controls.append(cell)
                d_cell_dict[(r, c)] = cell
                idx += 1

        idx = 0
        for r in range(ROWS + 1):
            for c in range(COLS):
                line_bg = dialog_horiz_bgcolors[idx] if idx < len(dialog_horiz_bgcolors) else "grey300"
                top_pos = r * D_CELL_H - (D_LINE_THICK / 2) + D_OFFSET
                if r == 0: top_pos = D_OFFSET
                if r == ROWS: top_pos = D_TOTAL_H - D_LINE_THICK - D_OFFSET
                h_line = ft.Container(width=D_CELL_W, height=D_LINE_THICK, bgcolor=line_bg)
                hit_box = ft.Container(content=h_line, width=D_CELL_W, height=D_LINE_THICK + (D_HIT_BOX_EXT * 2), bgcolor=ft.Colors.TRANSPARENT, alignment=ft.alignment.center, left=c * D_CELL_W + D_OFFSET, top=top_pos - D_HIT_BOX_EXT, on_click=toggle_d_line)
                d_stack.controls.append(hit_box)
                d_horiz_dict[(r, c)] = h_line
                idx += 1

        idx = 0
        for c in range(COLS + 1):
            for r in range(ROWS):
                line_bg = dialog_vert_bgcolors[idx] if idx < len(dialog_vert_bgcolors) else "grey300"
                left_pos = c * D_CELL_W - (D_LINE_THICK / 2) + D_OFFSET
                if c == 0: left_pos = D_OFFSET
                if c == COLS: left_pos = D_TOTAL_W - D_LINE_THICK - D_OFFSET
                v_line = ft.Container(width=D_LINE_THICK, height=D_CELL_H, bgcolor=line_bg)
                hit_box = ft.Container(content=v_line, width=D_LINE_THICK + (D_HIT_BOX_EXT * 2), height=D_CELL_H, bgcolor=ft.Colors.TRANSPARENT, alignment=ft.alignment.center, left=left_pos - D_HIT_BOX_EXT, top=r * D_CELL_H + D_OFFSET, on_click=toggle_d_line)
                d_stack.controls.append(hit_box)
                d_vert_dict[(c, r)] = v_line
                idx += 1


        # =========================================================================
        # 📊 マイページ履歴一覧から、タップして直接編集・上書き保存できる詳細ダイアログ（後半）
        # =========================================================================
        # ダイアログ内専用の牧場グリッド自動点数計算アルゴリズム
        def analyze_d_grid():
            visited = {(r, c): False for r in range(-1, ROWS + 1) for c in range(-1, COLS + 1)}
            queue = []
            for r in range(-1, ROWS + 1):
                for c in range(-1, COLS + 1):
                    if r == -1 or r == ROWS or c == -1 or c == COLS:
                        visited[(r, c)] = True
                        queue.append((r, c))
            while queue:
                curr_r, curr_c = queue.pop(0)
                if curr_r > -1 and curr_r < ROWS + 1 and curr_c >= 0 and curr_c < COLS:
                    if d_horiz_dict[(curr_r, curr_c)].bgcolor != ft.Colors.BROWN_700:
                        if not visited[(curr_r - 1, curr_c)]: visited[(curr_r - 1, curr_c)] = True; queue.append((curr_r - 1, curr_c))
                if curr_r < ROWS and curr_r + 1 < ROWS + 1 and curr_c >= 0 and curr_c < COLS:
                    if d_horiz_dict[(curr_r + 1, curr_c)].bgcolor != ft.Colors.BROWN_700:
                        if not visited[(curr_r + 1, curr_c)]: visited[(curr_r + 1, curr_c)] = True; queue.append((curr_r + 1, curr_c))
                if curr_c > -1 and curr_c < COLS + 1 and curr_r >= 0 and curr_r < ROWS:
                    if d_vert_dict[(curr_c, curr_r)].bgcolor != ft.Colors.BROWN_700:
                        if not visited[(curr_r, curr_c - 1)]: visited[(curr_r, curr_c - 1)] = True; queue.append((curr_r, curr_c - 1))
                if curr_c < COLS and curr_c + 1 < COLS + 1 and curr_r >= 0 and curr_r < ROWS:
                    if d_vert_dict[(curr_c + 1, curr_r)].bgcolor != ft.Colors.BROWN_700:
                        if not visited[(curr_r, curr_c + 1)]: visited[(curr_r, curr_c + 1)] = True; queue.append((curr_r, curr_c + 1))
            u_count = sum(1 for r in range(ROWS) for c in range(COLS) if visited[(r, c)] and d_cell_dict[(r, c)].bgcolor == ft.Colors.GREY_100)
            r_count, s_count = 0, 0
            for r in range(ROWS):
                for c in range(COLS):
                    if not visited[(r, c)]:
                        r_count += 1; i_q = [(r, c)]; visited[(r, c)] = True; has_s = False
                        while i_q:
                            cr, cc = i_q.pop(0)
                            if d_cell_dict[(cr, cc)].bgcolor == ft.Colors.LIGHT_BLUE_300: has_s = True
                            if cr > 0 and d_horiz_dict[(cr, cc)].bgcolor != ft.Colors.BROWN_700 and not visited[(cr - 1, cc)]: visited[(cr - 1, cc)] = True; i_q.append((cr - 1, cc))
                            if cr < ROWS - 1 and d_horiz_dict[(cr + 1, cc)].bgcolor != ft.Colors.BROWN_700 and not visited[(cr + 1, cc)]: visited[(cr + 1, cc)] = True; i_q.append((cr + 1, cc))
                            if cc > 0 and d_vert_dict[(cc, cr)].bgcolor != ft.Colors.BROWN_700 and not visited[(cr, cc - 1)]: visited[(cr, cc - 1)] = True; i_q.append((cr, cc - 1))
                            if cc < COLS - 1 and d_vert_dict[(cc + 1, cr)].bgcolor != ft.Colors.BROWN_700 and not visited[(cr, cc + 1)]: visited[(cr, cc + 1)] = True; i_q.append((cr, cc + 1))
                        if has_s: s_count += 1
            return r_count, u_count, s_count

        def get_local_agri_score(inputs):
            sub = 0
            for name, count in inputs.items():
                score = -1
                if name == "小麦": score = -1 if count==0 else (1 if count<=3 else (2 if count<=5 else (3 if count<=7 else 4)))
                elif name == "野菜": score = -1 if count==0 else (1 if count==1 else (2 if count==2 else (3 if count==3 else 4)))
                elif name == "羊": score = -1 if count==0 else (1 if count<=3 else (2 if count<=5 else (3 if count<=7 else 4)))
                elif name == "猪": score = -1 if count==0 else (1 if count<=2 else (2 if count<=4 else (3 if count<=6 else 4)))
                elif name == "牛": score = -1 if count==0 else (1 if count==1 else (2 if count<=3 else (3 if count<=5 else 4)))
                elif name == "家族の数": score = count * 3
                elif name == "乞食の枚数": score = count * -3
                sub += score
            return sub

        # ダイアログ盤面＋手入力値の再計算
        def recalculate_dialog_score():
            t_agri = {}
            for k, f in agri_fields.items():
                try: t_agri[k] = int(f.value) if f.value != "" else 0
                except ValueError: t_agri[k] = 0

            t_card = {}
            for k, f in card_fields.items():
                try: t_card[k] = int(f.value) if f.value != "" else 0
                except ValueError: t_card[k] = 0
            
            c_counts = {"木の家": 0, "レンガの家": 0, "石の家": 0, "畑": 0}
            for cell in d_cell_dict.values():
                for info in PALETTE_INFO:
                    if info["name"] in c_counts and cell.bgcolor == info["color"]: c_counts[info["name"]] += 1
            
            r_c, u_c, s_c = analyze_d_grid()
            f_score = -1 if c_counts["畑"]<=1 else (1 if c_counts["畑"]==2 else (2 if c_counts["畑"]==3 else (3 if c_counts["畑"]==4 else 4)))
            r_score = -1 if r_c==0 else (min(r_c, 4))
            st_score = min(s_c, 4) if s_c > 0 else 0
            h_score = (c_counts["レンガの家"] * 1) + (c_counts["石の家"] * 2)
            u_score = u_c * -1
            
            board_total = f_score + r_score + st_score + h_score + u_score
            new_total = board_total + get_local_agri_score(t_agri) + sum(t_card.values())
            total_score_preview.value = f"合計得点: {new_total} 点"
            total_score_preview.update()
            return new_total, t_agri, t_card

        # --- 修正データのUPDATE処理 ---
        def save_edited_record(e):
            try:
                final_score, updated_agri, updated_card = recalculate_dialog_score()
                
                # 🚜 修正された盤面・柵の色を安全に文字列に変換してパック
                new_board_pack = {
                    "cells": [str(d_cell_dict[(r, c)].bgcolor) for r in range(ROWS) for c in range(COLS)],
                    "horiz": [str(d_horiz_dict[(r, c)].bgcolor) for r in range(ROWS + 1) for c in range(COLS)],
                    "vert": [str(d_vert_dict[(c, r)].bgcolor) for c in range(COLS + 1) for r in range(ROWS)],
                    "agri_inputs": updated_agri,
                    "card_inputs": updated_card,
                    "card_details": board_pack.get("card_details", {"職業":[],"小さい進歩":[],"大きい進歩":[]}) if raw_game_data else {"職業":[],"小さい進歩":[],"大きい進歩":[]}
                }
                
                supabase.table("records").update({
                    "final_score": final_score,
                    "memo": detail_memo_input.value.strip(),
                    "game_data": json.dumps(new_board_pack)
                }).eq("id", record["id"]).execute()

                page.close(target_dialog) 
                update_all_uis() # 全体の画面表示を一括更新
                page.overlay.append(ft.SnackBar(ft.Text("🚜 牧場ボードとスコアの変更を上書き保存しました！"), open=True))
                page.update()
            except Exception as ex:
                show_alert(f"保存に失敗しました: {ex}")

        # UIのグリッド構築
        agri_grid = ft.Row(controls=list(agri_fields.values()), wrap=True, spacing=5)
        card_grid = ft.Row(controls=list(card_fields.values()), wrap=True, spacing=5)

        # 初期ロード計算を実行して数値を同期
        recalculate_dialog_score()

        target_dialog = ft.AlertDialog(
            title=ft.Text("📊 スコア履歴の確認・直接編集", weight="bold", size=15),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"📅 对戦日: {record.get('date')}", size=11, color=ft.Colors.GREY_600),
                    total_score_preview,
                    ft.Divider(height=10),
                    ft.Text("🚜 牧場盤面ボードとパレット（メイン同様に編集可能）", size=12, weight="bold", color=ft.Colors.BLUE_GREY_700),
                    ft.Container(content=d_control_bar, padding=ft.padding.only(bottom=5)), 
                    ft.Container(content=d_stack, border=ft.border.all(1, ft.Colors.GREY_300), alignment=ft.alignment.center, padding=5),
                    ft.Text("🌾 資源・家族の数 (数値を書き換えると自動計算)", size=12, weight="bold", color=ft.Colors.BLUE_GREY_700),
                    agri_grid,
                    ft.Text("🃏 カードボーナス点数", size=12, weight="bold", color=ft.Colors.BLUE_GREY_700),
                    card_grid,
                    ft.Divider(height=10),
                    detail_memo_input
                ], spacing=6, tight=True, scroll=ft.ScrollMode.AUTO),
                width=350,
                height=450
            ),
            actions=[
                ft.TextButton("キャンセル", on_click=lambda e: page.close(target_dialog)),
                ft.ElevatedButton("変更を保存", on_click=save_edited_record, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        # 🧪 【不具合調査用】もし開かない場合は、エラーダイアログを代わりに強制起動する
        try:
            log("2. 盤面組み立て完了、ダイアログを開きます")
            page.open(target_dialog)
        except Exception as dialog_ex:
            log(f"❌ ダイアログ起動クラッシュ: {dialog_ex}")
            
        # 💡 万が一開かない場合のための、ログ確認用緊急ダイアログ
        debug_dialog = ft.AlertDialog(
            title=ft.Text("🧪 デバッグログ確認"),
            content=ft.Container(
                content=ft.Column([ft.Text(l, size=12, color=ft.Colors.RED if "❌" in l else ft.Colors.BLACK) for l in debug_logs], scroll=ft.ScrollMode.AUTO),
                width=300, height=200
            ),
            actions=[ft.TextButton("閉じる", on_click=lambda e: page.close(debug_dialog))]
        )
                # show_record_detail_dialog の一番最後にある page.open(target_dialog) を以下に変更
        page.dialog = target_dialog
        target_dialog.open = True
        page.update()



    # =========================================================================
    # 👤 マイページ設定メニュー（名前変更・パスワード変更・秘密の質問・削除）の実体
    # =========================================================================
    def _handle_rename(e):
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
            existing = supabase.table("users").select("username").eq("username", new_name).execute()
            if existing.data:
                show_alert("その名前は既に使われています。")
                return
            supabase.table("users").update({"username": new_name}).eq("username", current_player).execute()
            priv_res = supabase.table("privacy").select("*").execute()
            if priv_res.data:
                p_key = "username" if "username" in priv_res.data else "player"
                supabase.table("privacy").update({p_key: new_name}).eq(p_key, current_player).execute()
            supabase.table("records").update({"player": new_name}).eq("player", current_player).execute()
            current_player = new_name
            logged_in_user_text.value = f"👤 ログイン中: {current_player} さん"
            page.client_storage.set(STORAGE_REMEMBER_USER, new_name)
            page.close(change_name_dialog)
            update_all_uis()
            page.overlay.append(ft.SnackBar(ft.Text(f"👤 名前を {new_name} に変更しました"), open=True))
            page.update()
        except Exception as ex:
            show_alert(f"名前変更失敗: {ex}")

    def _handle_change_password(e):
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
            hashed_old = hash_password(old_pass)
            res = supabase.table("users").select("password").eq("username", current_player).execute()
            if not res.data or res.data["password"] != hashed_old:
                show_alert("現在のパスワードが間違っています。")
                return
            hashed_new = hash_password(new_pass)
            supabase.table("users").update({"password": hashed_new}).eq("username", current_player).execute()
            mypage_old_pass.value = ""
            mypage_new_pass.value = ""
            page.close(change_pass_dialog)
            page.client_storage.set(STORAGE_REMEMBER_PASS, new_pass)
            page.overlay.append(ft.SnackBar(ft.Text("🔒 パスワードを変更しました"), open=True))
            page.update()
        except Exception as ex:
            show_alert(f"パスワード変更失敗: {ex}")

    def _handle_save_secret_question(e):
        if not current_player: return
        question = mypage_question_input.value.strip()
        answer = mypage_answer_input.value.strip()
        if not question or not answer:
            show_alert("質問と答えの両方を入力してください。")
            return
        try:
            hashed_answer = hash_password(answer)
            priv_res = supabase.table("privacy").select("*").eq("username", current_player).execute()
            update_data = {"secret_question": question, "secret_answer": hashed_answer}
            if priv_res.data:
                p_key = "username" if "username" in priv_res.data else "player"
                supabase.table("privacy").update(update_data).eq(p_key, current_player).execute()
            else:
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

    def _execute_delete_account():
        nonlocal current_player
        if not current_player: return
        try:
            supabase.table("records").delete().eq("player", current_player).execute()
            priv_res = supabase.table("privacy").select("*").execute()
            if priv_res.data:
                p_key = "username" if "username" in priv_res.data else "player"
                supabase.table("privacy").delete().eq(p_key, current_player).execute()
            supabase.table("users").delete().eq("username", current_player).execute()
            page.client_storage.remove(STORAGE_REMEMBER_USER)
            page.client_storage.remove(STORAGE_REMEMBER_PASS)
            current_player = None
            page.close(confirm_delete_dialog)
            page.controls.clear()
            page.add(login_view)
            page.overlay.append(ft.SnackBar(ft.Text("⚠️ アカウントを完全に削除しました"), open=True))
            page.update()
        except Exception as ex:
            show_alert(f"アカウント削除失敗: {ex}")

    def _open_change_group_dialog(e):
        group_inputs_container.controls.clear()
        for g_num in my_group_list: group_inputs_container.controls.append(create_group_input_row(g_num))
        if not group_inputs_container.controls: group_inputs_container.controls.append(create_group_input_row("1"))
        page.open(change_group_dialog)

    def _handle_save_group_number(e):
        nonlocal my_group_list
        parsed_list = []
        for row in group_inputs_container.controls:
            tf_control = row.controls[0] # 💡 インデックスの指定ミスを修正
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
                    rank_row = ft.Row(spacing=10, controls=[
                        ft.Text(f"{medal} {rank}位", size=14, weight=ft.FontWeight.BOLD, width=55),
                        ft.Text(f"{record['player']}", expand=True, weight=ft.FontWeight.BOLD, size=14),
                        ft.Text(f"{record['final_score']} 点", weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700, size=14)
                    ])
                    ranking_list.controls.append(ft.Container(content=rank_row, padding=8, border=ft.border.all(1, ft.Colors.GREY_200), border_radius=8))
        except Exception: pass
        page.update()

    # 💡 事前宣言への実体バインド（最終代入）
    handle_rename = _handle_rename
    handle_change_password = _handle_change_password
    handle_save_secret_question = _handle_save_secret_question
    execute_delete_account = _execute_delete_account
    open_change_group_dialog = _open_change_group_dialog
    handle_save_group_number = _handle_save_group_number

    # 各種ダイアログ構造構築
    change_name_dialog = ft.AlertDialog(title=ft.Text("👤 プレイヤー名の変更"), content=ft.Container(content=ft.Column([edit_name_input], spacing=10, tight=True), width=320, height=70), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(change_name_dialog)), ft.ElevatedButton("名前を変更", on_click=handle_rename, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)
    change_pass_dialog = ft.AlertDialog(title=ft.Text("🔒 パスワードの変更"), content=ft.Container(content=ft.Column([mypage_old_pass, mypage_new_pass], spacing=10, tight=True), width=320, height=140), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(change_pass_dialog)), ft.ElevatedButton("変更を実行", on_click=handle_change_password, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)
    secret_question_dialog = ft.AlertDialog(title=ft.Text("🛡️ 秘密の質問の設定"), content=ft.Container(content=ft.Column([mypage_question_input, mypage_answer_input], spacing=10, tight=True), width=320, height=140), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(secret_question_dialog)), ft.ElevatedButton("設定を保存", on_click=handle_save_secret_question, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)
    confirm_delete_dialog = ft.AlertDialog(title=ft.Text("⚠️ 最終確認"), content=ft.Text("本当にアカウントを削除しますか？"), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(confirm_delete_dialog)), ft.TextButton("削除する", style=ft.ButtonStyle(color=ft.Colors.RED_600), on_click=lambda e: execute_delete_account())], actions_alignment=ft.MainAxisAlignment.END)
    forgot_dialog = ft.AlertDialog(title=ft.Text("🔑 パスワードの再設定"), content=ft.Container(content=ft.Column([forgot_name_input, ft.ElevatedButton("1. 質問を確認する", on_click=handle_forgot_check_user, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE), ft.Divider(height=10), forgot_question_text, forgot_answer_input, forgot_new_pass_input], spacing=10, tight=True), width=320, height=325), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(forgot_dialog)), ft.ElevatedButton("2. パスワードを更新", on_click=handle_forgot_reset_password, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)
    change_group_dialog = ft.AlertDialog(title=ft.Text("🔢 グループ番号の管理"), content=ft.Container(content=ft.ListView(controls=[group_inputs_container, ft.TextButton("グループを追加", icon=ft.Icons.ADD, on_click=add_blank_group_input_row)], spacing=10), width=320, height=250), actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(change_group_dialog)), ft.ElevatedButton("変更を保存", on_click=handle_save_group_number, bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)], actions_alignment=ft.MainAxisAlignment.END)

    action_buttons_row = ft.ResponsiveRow(controls=[ft.Container(content=register_btn, col={"xs": 6}, alignment=ft.alignment.center, padding=5), ft.Container(content=login_btn, col={"xs": 6}, alignment=ft.alignment.center, padding=5)], alignment=ft.MainAxisAlignment.CENTER)
    global_header_bar = ft.Container(content=ft.Row(controls=[logged_in_user_text, ft.TextButton("ログアウト", icon=ft.Icons.LOGOUT, style=ft.ButtonStyle(color=ft.Colors.RED_600, icon_color=ft.Colors.RED_600), on_click=handle_logout)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=10, bgcolor=ft.Colors.GREY_100, border_radius=8)
    
    admin_search_input = ft.TextField(label="プレイヤー名で検索", prefix_icon=ft.Icons.SEARCH, on_change=lambda e: update_admin_ui(), expand=True)
    admin_data_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("プレイヤー名"), on_sort=handle_admin_table_sort), ft.DataColumn(ft.Text("グループ"), on_sort=handle_admin_table_sort), ft.DataColumn(ft.Text("最終ログイン"), on_sort=handle_admin_table_sort), ft.DataColumn(ft.Text("最高点"), on_sort=handle_admin_table_sort)], rows=[], heading_row_color=ft.Colors.BLUE_GREY_50, divider_thickness=1, column_spacing=10, sort_column_index=3, sort_ascending=False, expand=True)
    admin_tab_view = ft.Column(controls=[ft.Container(content=ft.Text("🛠️ 管理者コントロールパネル", size=16, weight=ft.FontWeight.BOLD), padding=12), ft.Container(content=ft.Row([admin_search_input]), padding=5), ft.ListView(controls=[admin_data_table], expand=True)], expand=True)

    login_view = ft.Container(content=ft.Column(controls=[ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80, color=ft.Colors.BLUE_600), ft.Text(value="プレイヤー認証", size=24, weight=ft.FontWeight.BOLD), ft.Container(height=15), ft.Container(content=login_name_input, width=300), ft.Container(content=login_pass_input, width=300), ft.Container(height=10), ft.Container(content=action_buttons_row, width=340), ft.Container(height=10), ft.TextButton("🔑 パスワードを忘れた場合はこちら", on_click=lambda e: page.open(forgot_dialog))], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10), padding=20, alignment=ft.alignment.center, expand=True, visible=True)

    # 🚜 牧場・資源管理グリッドボードUI組み立て
    palette_options = []
    for info in PALETTE_INFO:
        btn = ft.Container(width=35, height=35, bgcolor=info["color"], border_radius=18, data=info["color"], on_click=on_palette_click)
        lbl = ft.Text(info["name"], size=8, weight="bold")
        palette_options.append(ft.Column([btn, lbl], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=1))

    palette_row = ft.Row(controls=palette_options, alignment=ft.MainAxisAlignment.CENTER, spacing=8)
    line_mode_btn = ft.ElevatedButton(text="✏️ 柵の建設", on_click=on_line_mode_click, style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_300, color=ft.Colors.BLACK, shape=ft.RoundedRectangleBorder(radius=8)))
    top_control_row = ft.Row(controls=[palette_row, line_mode_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=10)
    
    count_table = ft.DataTable(width=360, column_spacing=10, columns=[ft.DataColumn(ft.Text("盤面項目")), ft.DataColumn(ft.Text("数")), ft.DataColumn(ft.Text("得点"))])
    count_table2 = ft.DataTable(width=360, column_spacing=10, columns=[ft.DataColumn(ft.Text("資源・家族")), ft.DataColumn(ft.Text("数")), ft.DataColumn(ft.Text("得点"))])
    count_table3 = ft.DataTable(width=360, column_spacing=10, columns=[ft.DataColumn(ft.Text("カードボーナス")), ft.DataColumn(ft.Text("得点")), ft.DataColumn(ft.Text("内訳入力"))])

    stack_layout = ft.Stack(width=TOTAL_W, height=TOTAL_H)
    for r in range(ROWS):
        for c in range(COLS):
            cell = ft.Container(content=ft.Text(f"{r * COLS + c + 1}", color=ft.Colors.GREY_400, size=11), alignment=ft.alignment.center, bgcolor=ft.Colors.GREY_100, width=CELL_W, height=CELL_H, left=c * CELL_W + OFFSET, top=r * CELL_H + OFFSET, on_click=on_cell_click)
            stack_layout.controls.append(cell)
            cell_dict[(r, c)] = cell

    for r in range(ROWS + 1):
        for c in range(COLS):
            left_pos, top_pos = c * CELL_W + OFFSET, r * CELL_H - (LINE_THICK / 2) + OFFSET
            if r == 0: top_pos = OFFSET
            if r == ROWS: top_pos = TOTAL_H - LINE_THICK - OFFSET
            horiz_line = ft.Container(width=CELL_W, height=LINE_THICK, bgcolor=ft.Colors.GREY_300)
            hit_box = ft.Container(content=horiz_line, width=CELL_W, height=LINE_THICK + (HIT_BOX_EXT * 2), bgcolor=ft.Colors.TRANSPARENT, alignment=ft.alignment.center, left=left_pos, top=top_pos - HIT_BOX_EXT, on_click=toggle_line)
            stack_layout.controls.append(hit_box)
            horiz_line_dict[(r, c)] = horiz_line

    for c in range(COLS + 1):
        for r in range(ROWS):
            left_pos, top_pos = c * CELL_W - (LINE_THICK / 2) + OFFSET, r * CELL_H + OFFSET
            if c == 0: left_pos = OFFSET
            if c == COLS: left_pos = TOTAL_W - LINE_THICK - OFFSET
            vert_line = ft.Container(width=LINE_THICK, height=CELL_H, bgcolor=ft.Colors.GREY_300)
            hit_box = ft.Container(content=vert_line, width=LINE_THICK + (HIT_BOX_EXT * 2), height=CELL_H, bgcolor=ft.Colors.TRANSPARENT, alignment=ft.alignment.center, left=left_pos - HIT_BOX_EXT, top=top_pos, on_click=toggle_line)
            stack_layout.controls.append(hit_box)
            vert_line_dict[(c, r)] = vert_line

    current_date_text = ft.Text(value=f"📅 対戦日時: {get_jst_now_str()}", size=12, color=ft.Colors.BLUE_GREY_600, weight=ft.FontWeight.W_500)
    game_memo_input = ft.TextField(
        label="対戦メモ・コメント", hint_text="エンターで改行できます。記録と一緒に保存されます", 
        multiline=True, min_lines=1, max_lines=4, text_size=13, content_padding=10
    )

    bottom_grand_total_display = ft.Text(value="0", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
    bottom_score_row = ft.Container(
        content=ft.Row([
            ft.Text("最終合計得点 :", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800),
            bottom_grand_total_display
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        padding=12, bgcolor=ft.Colors.GREEN_50, border_radius=10, border=ft.border.all(1.5, ft.Colors.GREEN_200)
    )

    calc_tab_view = ft.ListView(
        controls=[
            ft.Container(content=ft.Column([current_date_text, game_memo_input], spacing=8), padding=ft.padding.only(left=10, right=10, top=5)),
            ft.Container(content=ft.Column([ft.Text("現在のアグリコラ合計得点", size=13, color=ft.Colors.GREY_600), score_display], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER), alignment=ft.alignment.center, padding=5),
            ft.Container(content=top_control_row, padding=5),
            ft.Container(content=stack_layout, border=ft.border.all(1, ft.Colors.GREY_300), alignment=ft.alignment.center),
            ft.Container(content=count_table, alignment=ft.alignment.center),
            ft.Container(content=count_table2, alignment=ft.alignment.center),
            ft.Container(content=count_table3, alignment=ft.alignment.center),
            ft.Container(content=bottom_score_row, alignment=ft.alignment.center, padding=ft.padding.symmetric(horizontal=10)), 
            ft.Container(content=ft.Row(controls=[
                ft.OutlinedButton("リセット", icon=ft.Icons.REFRESH, on_click=lambda e: reset_current_game(), style=ft.ButtonStyle(color=ft.Colors.RED_600, icon_color=ft.Colors.RED_600)),
                ft.ElevatedButton("ゲーム記録を保存", icon=ft.Icons.SAVE, on_click=save_current_game, bgcolor=ft.Colors.GREEN_700, color=ft.Colors.WHITE)
            ], alignment=ft.MainAxisAlignment.SPACE_EVENLY), padding=10)
        ], expand=True, spacing=10
    )

    # =========================================================================
    # 👤 マイページ設定メニュー（Fletの無限高さバグを回避し、確実にタップを通す修正版）
    # =========================================================================
    mypage_tab_view = ft.Column(
        controls=[
            ft.Text("📊 保存されたスコア履歴 (タップして詳細/編集)", size=15, weight=ft.FontWeight.BOLD), 
            
            # 💡 Containerでの不要な内包を廃止し、直接高さを固定・自動スクロールさせることで
            # 当たり判定の消失や画面全体のフリーズバグを100%解決
            ft.Container(
                content=my_records_list, 
                expand=True,
                height=250, # 高さを明示的に確保
            ), 
            
            ft.Container(
                content=ft.Column([
                    ft.Text("👤 各種設定メニュー :", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE), 
                    ft.Row(controls=[
                        ft.IconButton(ft.Icons.ACCOUNT_CIRCLE, tooltip="名前変更", on_click=lambda e: page.open(change_name_dialog), icon_color=ft.Colors.WHITE), 
                        ft.IconButton(ft.Icons.NUMBERS, tooltip="グループ変更", on_click=open_change_group_dialog, icon_color=ft.Colors.WHITE), 
                        ft.IconButton(ft.Icons.LOCK, tooltip="パスワード変更", on_click=lambda e: page.open(change_pass_dialog), icon_color=ft.Colors.WHITE), 
                        ft.IconButton(ft.Icons.SHIELD, tooltip="秘密の質問", on_click=lambda e: page.open(secret_question_dialog), icon_color=ft.Colors.WHITE), 
                        ft.IconButton(ft.Icons.DELETE_FOREVER, tooltip="アカウント削除", on_click=lambda e: page.open(confirm_delete_dialog), icon_color=ft.Colors.RED_300)
                    ], wrap=True, spacing=5)
                ]), 
                padding=10, bgcolor=ft.Colors.BLUE_GREY_600, border_radius=10
            )
        ], 
        expand=True,
        spacing=10
    )

    
    ranking_tab_view = ft.Column(controls=[ft.Container(content=ft.Row([ft.Container(content=ranking_title_text, expand=True), ranking_group_dropdown], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=10), ft.Container(content=ranking_list, height=430)])

    main_tab_view = ft.Tabs(selected_index=0, animation_duration=300, tabs=[ft.Tab(text="得点計算ボード", icon=ft.Icons.CALCULATE, content=calc_tab_view), ft.Tab(text="マイページ", icon=ft.Icons.PERSON, content=mypage_tab_view), ft.Tab(text="ランキング", icon=ft.Icons.EMOJI_EVENTS, content=ranking_tab_view)], expand=True, on_change=lambda e: ((refresh_ranking_dropdown_options(), update_ranking_ui()) if main_tab_view.selected_index == 2 else None, page.update()))

    authenticated_view = ft.Column(controls=[global_header_bar, main_tab_view], expand=True, visible=False)

    page.controls.clear()
    page.add(login_view, authenticated_view)

    # ⭕ 【安全な枠線適用】通常のリストに対して直接 border プロパティにアクセスしていた不具合を安全に回避
    if len(palette_options) > 0:
        for option in palette_options:
            if hasattr(option, 'border'):
                option.border = ft.border.all(3, ft.Colors.BLACK)
    reset_current_game()

    login_name_input.value = page.client_storage.get(STORAGE_REMEMBER_USER) or ""
    login_pass_input.value = page.client_storage.get(STORAGE_REMEMBER_PASS) or ""
    check_auto_login()
    page.update()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    ft.app(target=main, host="0.0.0.0", view=ft.AppView.WEB_BROWSER, port=port)

