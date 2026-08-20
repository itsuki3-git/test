import flet as ft
from datetime import datetime
import json


def main(page: ft.Page):
    page.title = "フルーツ得点計算 & パスワード管理"
    page.window_width = 450
    page.window_height = 700
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- フルーツの配点設定 ---
    FRUIT_POINTS = {
        "apple": 10,
        "orange": 5,
        "grape": 15
    }

    # --- 状態管理用データ（初期化） ---
    current_player = None  # 現在ログイン中のプレイヤー名
    counts = {"apple": 0, "orange": 0, "grape": 0}

    # 永続保存用のキー定義
    STORAGE_DB_KEY = "fruit_app_user_db"
    STORAGE_RECORDS_KEY = "fruit_app_saved_records"
    STORAGE_COUNTER_KEY = "fruit_app_record_id_counter"

    # ブラウザのストレージからデータを読み込む（データがない場合は空の初期値を設定）
    user_db = page.client_storage.get(STORAGE_DB_KEY) or {}
    saved_records = page.client_storage.get(STORAGE_RECORDS_KEY) or []
    record_id_counter = page.client_storage.get(STORAGE_COUNTER_KEY) or 0

    # --- UIコンポーネントの参照定義 ---
    login_name_input = ft.TextField(
        label="プレイヤー名",
        hint_text="例: たろう"
    )
    login_pass_input = ft.TextField(
        label="パスワード",
        hint_text="登録・ログイン共通",
        password=True,
        can_reveal_password=FALSE,
        on_submit=lambda e: handle_auth(None)
    )

    logged_in_user_text = ft.Text(value="", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800)
    score_display = ft.Text(value="0", size=48, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600)

    apple_count_text = ft.Text(value="0", size=20, weight=ft.FontWeight.BOLD, width=40, text_align=ft.TextAlign.CENTER)
    orange_count_text = ft.Text(value="0", size=20, weight=ft.FontWeight.BOLD, width=40, text_align=ft.TextAlign.CENTER)
    grape_count_text = ft.Text(value="0", size=20, weight=ft.FontWeight.BOLD, width=40, text_align=ft.TextAlign.CENTER)

    saved_records_list = ft.ListView(expand=True, spacing=10, padding=10)

    # --- エラー警告ダイアログの制御 ---
    def close_dialog(e):
        alert_dialog.open = False
        page.update()

    alert_dialog = ft.AlertDialog(
        title=ft.Text("認証エラー"),
        content=ft.Text(""),
        actions=[ft.TextButton("OK", on_click=close_dialog)]
    )

    def show_alert(message):
        alert_dialog.content.value = message
        if alert_dialog not in page.overlay:
            page.overlay.append(alert_dialog)
        alert_dialog.open = True
        page.update()

    # --- ログイン / 新規登録 処理 ---
    def handle_auth(e):
        nonlocal current_player
        input_name = login_name_input.value.strip()
        input_pass = login_pass_input.value.strip()

        if not input_pass:
            show_alert("パスワードを入力してください。")
            return

        # 1. 既存のパスワードかどうかチェック（ログイン）
        if input_pass in user_db:
            current_player = user_db[input_pass]
            message = f"👤 {current_player} さんとしてログインしました！"

        # 2. 新しいパスワードの場合（新規登録）
        else:
            if not input_name:
                show_alert("新しいパスワードです。プレイヤー名を入力して新規登録してください。")
                return

            # パスワード被りはNG、名前かぶりは枝番で回避
            final_name = input_name
            counter = 2
            existing_names = list(user_db.values())
            while final_name in existing_names:
                final_name = f"{input_name} ({counter})"
                counter += 1

            # データベースを更新し、ブラウザに永続保存
            user_db[input_pass] = final_name
            page.client_storage.set(STORAGE_DB_KEY, user_db)

            current_player = final_name
            message = f"🎉 {final_name} さんを新規登録＆ログインしました！"

        # ログイン成功時の画面遷移
        logged_in_user_text.value = f"👤 ログイン中: {current_player} さん"
        login_name_input.value = ""
        login_pass_input.value = ""

        login_view.visible = False
        main_tab_view.visible = True
        reset_current_game(None)

        page.overlay.append(ft.SnackBar(ft.Text(message), open=True))
        page.update()

    # --- ログアウト処理 ---
    def handle_logout(e):
        nonlocal current_player
        current_player = None
        login_view.visible = True
        main_tab_view.visible = False
        page.update()

    # --- 合計得点の計算・更新 ---
    def calculate_total_score():
        total = (
                counts["apple"] * FRUIT_POINTS["apple"] +
                counts["orange"] * FRUIT_POINTS["orange"] +
                counts["grape"] * FRUIT_POINTS["grape"]
        )
        score_display.value = str(total)
        page.update()
        return total

    # --- カウントボタンの操作ロジック ---
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
            calculate_total_score()

    # --- 過去の記録リストの描画更新 ---
    def update_saved_records_ui():
        saved_records_list.controls.clear()
        if not saved_records:
            saved_records_list.controls.append(
                ft.Text("保存された記録はありません", italic=True, color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER)
            )
        else:
            for record in reversed(saved_records):
                saved_records_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Column([
                                    ft.Text(f"プレイヤー: {record['player']}", size=16, weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.BLUE_GREY_800),
                                    ft.Text(f"合計得点: {record['final_score']} 点", size=18, weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.BLUE_700),
                                    ft.Text(f"内訳: 🍎{record['apple']} 🍊{record['orange']} 🍇{record['grape']}", size=13,
                                            color=ft.Colors.GREY_700),
                                    ft.Text(f"保存日時: {record['date']}", size=11, color=ft.Colors.GREY_500),
                                ], expand=True),
                                ft.IconButton(
                                    icon=ft.Icons.DELETE_FOREVER,
                                    icon_color=ft.Colors.RED_600,
                                    tooltip="記録を削除",
                                    on_click=lambda e, idx=record["id"]: delete_saved_record(idx)
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        padding=12,
                        border=ft.border.all(1, ft.Colors.BLUE_100),
                        border_radius=8,
                        bgcolor=ft.Colors.BLUE_50
                    )
                )
        page.update()

    # --- 現在のゲームをリセット ---
    def reset_current_game(e):
        for fruit in counts:
            counts[fruit] = 0
        apple_count_text.value = "0"
        orange_count_text.value = "0"
        grape_count_text.value = "0"
        calculate_total_score()

    # --- 現在のスコアを過去の記録へ保存（永続化対応） ---
    def save_current_game(e):
        nonlocal record_id_counter

        if not current_player:
            show_alert("ログインしていません。")
            return

        total_score = calculate_total_score()
        date_str = datetime.now().strftime("%Y/%m/%d %H:%M")

        saved_records.append({
            "id": record_id_counter,
            "player": current_player,
            "date": date_str,
            "final_score": total_score,
            "apple": counts["apple"],
            "orange": counts["orange"],
            "grape": counts["grape"]
        })
        record_id_counter += 1

        # ブラウザのストレージへ永続化保存
        page.client_storage.set(STORAGE_RECORDS_KEY, saved_records)
        page.client_storage.set(STORAGE_COUNTER_KEY, record_id_counter)

        reset_current_game(None)
        update_saved_records_ui()

        page.overlay.append(ft.SnackBar(ft.Text(f"{current_player} の記録を保存しました！"), open=True))
        page.update()

    # --- 過去の記録の削除（永続化対応） ---
    def delete_saved_record(target_id):
        target_idx = next((i for i, r in enumerate(saved_records) if r["id"] == target_id), None)
        if target_idx is not None:
            saved_records.pop(target_idx)
            # 削除された状態をブラウザのストレージへ上書き保存
            page.client_storage.set(STORAGE_RECORDS_KEY, saved_records)
            update_saved_records_ui()

    # --- フルーツごとの操作行を作成する共通関数 ---
    def create_fruit_selector(label, fruit_key, count_text_component, color):
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Text(f"{label} ({FRUIT_POINTS[fruit_key]}点)", size=16, weight=ft.FontWeight.W_500, expand=True),
                    ft.Row(
                        controls=[
                            ft.IconButton(
                                icon=ft.Icons.REMOVE_CIRCLE_OUTLINED,
                                icon_color=color,
                                on_click=lambda e: adjust_count(fruit_key, -1)
                            ),
                            count_text_component,
                            ft.IconButton(
                                icon=ft.Icons.ADD_CIRCLE,
                                icon_color=color,
                                on_click=lambda e: adjust_count(fruit_key, 1)
                            ),
                        ],
                        spacing=5
                    )
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            padding=10,
            border=ft.border.all(1, ft.Colors.GREY_300),
            border_radius=10,
            bgcolor=ft.Colors.WHITE
        )

    # --- ログイン画面のレイアウト ---
    login_view = ft.Container(
        content=ft.Column(
            controls=[
                ft.Icon(ft.Icons.LOCK_PERSON, size=80, color=ft.Colors.BLUE_600),
                ft.Text("プレイヤー認証", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("既存のパスワードでログイン、新しいパスワードで新規登録になります", size=12,
                        color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER),
                ft.Container(height=10),
                login_name_input,
                login_pass_input,
                ft.Container(height=10),
                ft.ElevatedButton(
                    "確定（ログイン / 新規登録）",
                    icon=ft.Icons.KEY,
                    on_click=handle_auth,
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    width=280,
                    height=45
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10
        ),
        padding=30,
        alignment=ft.alignment.center,
        expand=True,
        visible=True
    )

    # --- タブ1: 得点計算画面のレイアウト ---
    calc_tab_view = ft.Column(
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        logged_in_user_text,
                        ft.TextButton(
                            "ログアウト",
                            icon=ft.Icons.LOGOUT,
                            style=ft.ButtonStyle(
                                color=ft.Colors.RED_600,
                                icon_color=ft.Colors.RED_600
                            ),
                            on_click=handle_logout
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                padding=10,
                bgcolor=ft.Colors.GREY_100,
                border_radius=8
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("現在の合計得点", size=14, color=ft.Colors.GREY_600),
                    score_display,
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                alignment=ft.alignment.center,
                padding=10,
            ),
            ft.Container(
                content=ft.Column([
                    create_fruit_selector("🍎 りんご", "apple", apple_count_text, ft.Colors.RED_600),
                    create_fruit_selector("🍊 みかん", "orange", orange_count_text, ft.Colors.ORANGE_600),
                    create_fruit_selector("🍇 ブドウ", "grape", grape_count_text, ft.Colors.PURPLE_600),
                ], spacing=15),
                padding=10,
                expand=True
            ),
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            "リセット",
                            icon=ft.Icons.REFRESH,
                            on_click=reset_current_game,
                            style=ft.ButtonStyle(color=ft.Colors.RED_600, icon_color=ft.Colors.RED_600)
                        ),
                        ft.ElevatedButton(
                            "ゲーム記録を保存",
                            icon=ft.Icons.SAVE,
                            on_click=save_current_game,
                            bgcolor=ft.Colors.GREEN_700,
                            color=ft.Colors.WHITE
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                ),
                padding=15
            )
        ],
        expand=True
    )

    # --- タブ2: 過去の記録画面のレイアウト ---
    records_tab_view = ft.Column(
        controls=[
            ft.Container(
                content=ft.Text("保存されたゲーム結果一覧", size=16, weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE_GREY_700),
                padding=15
            ),
            ft.Container(content=saved_records_list, expand=True),
        ],
        expand=True
    )

    # --- メインタブ構造の配置 ---
    main_tab_view = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="得点計算", icon=ft.Icons.CALCULATE, content=calc_tab_view),
            ft.Tab(text="過去の記録", icon=ft.Icons.HISTORY, content=records_tab_view),
        ],
        expand=True,
        visible=False
    )

    # 初期描画のセットアップ（ストレージから読み込んだ過去データをUIに反映）
    calculate_total_score()
    update_saved_records_ui()

    page.add(login_view, main_tab_view)


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    ft.app(target=main, host="0.0.0.0", view=ft.AppView.WEB_BROWSER, port=port)
