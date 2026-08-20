import flet as ft
from datetime import datetime


def main(page: ft.Page):
    page.title = "フルーツ得点計算 & プレイヤー管理"
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
    STORAGE_USERS_KEY = "fruit_app_registered_users"
    STORAGE_RECORDS_KEY = "fruit_app_saved_records"
    STORAGE_COUNTER_KEY = "fruit_app_record_id_counter"
    STORAGE_PRIVACY_KEY = "fruit_app_privacy_settings"  # 非表示設定用のキー

    # ブラウザのストレージからデータをロード
    registered_users = page.client_storage.get(STORAGE_USERS_KEY) or []
    saved_records = page.client_storage.get(STORAGE_RECORDS_KEY) or []
    record_id_counter = page.client_storage.get(STORAGE_COUNTER_KEY) or 0
    privacy_settings = page.client_storage.get(STORAGE_PRIVACY_KEY) or {}  # {"ユーザー名": bool(表示するか)}

    # --- UIコンポーネントの参照定義 ---
    login_name_input = ft.TextField(
        label="プレイヤー名を入力してください",
        hint_text="例: たろう",
        on_submit=lambda e: handle_login(None)
    )

    logged_in_user_text = ft.Text(value="", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_800)
    score_display = ft.Text(value="0", size=48, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600)

    apple_count_text = ft.Text(value="0", size=20, weight=ft.FontWeight.BOLD, width=40, text_align=ft.TextAlign.CENTER)
    orange_count_text = ft.Text(value="0", size=20, weight=ft.FontWeight.BOLD, width=40, text_align=ft.TextAlign.CENTER)
    grape_count_text = ft.Text(value="0", size=20, weight=ft.FontWeight.BOLD, width=40, text_align=ft.TextAlign.CENTER)

    # 各種リスト用・設定用コンポーネント
    edit_name_input = ft.TextField(label="名前を編集", hint_text="新しい名前を入力", expand=True)
    ranking_switch = ft.Switch(label="ランキングに名前と記録を表示する", value=True,
                               on_change=lambda e: handle_privacy_change(e))
    my_records_list = ft.ListView(expand=True, spacing=10, padding=10)
    ranking_list = ft.ListView(expand=True, spacing=10, padding=10)

    # --- 確認・エラーダイアログの制御 ---
    def close_dialog(e):
        alert_dialog.open = False
        page.update()

    alert_dialog = ft.AlertDialog(
        title=ft.Text("メッセージ"),
        content=ft.Text(""),
        actions=[ft.TextButton("OK", on_click=close_dialog)]
    )

    def show_alert(message, title="エラー"):
        alert_dialog.title.value = title
        alert_dialog.content.value = message
        if alert_dialog not in page.overlay:
            page.overlay.append(alert_dialog)
        alert_dialog.open = True
        page.update()

    # --- ログイン / 新規登録 処理 ---
    def handle_login(e):
        nonlocal current_player
        input_name = login_name_input.value.strip()

        if not input_name:
            show_alert("プレイヤー名を入力してください。")
            return

        if input_name in registered_users:
            show_alert("その名前はすでに使用されています。")
            return

        registered_users.append(input_name)
        page.client_storage.set(STORAGE_USERS_KEY, registered_users)

        current_player = input_name
        logged_in_user_text.value = f"👤 ログイン中: {current_player} さん"
        edit_name_input.value = current_player

        # プライバシー設定の初期化（デフォルトは表示ON）
        if current_player not in privacy_settings:
            privacy_settings[current_player] = True
        ranking_switch.value = privacy_settings[current_player]

        login_name_input.value = ""
        login_view.visible = False
        main_tab_view.visible = True
        reset_current_game(None)
        update_all_uis()

        page.overlay.append(ft.SnackBar(ft.Text(f"🎉 {current_player} さんを登録しました！"), open=True))
        page.update()

    # --- 名前の変更（編集）処理 ---
    def handle_rename(e):
        nonlocal current_player
        new_name = edit_name_input.value.strip()

        if not new_name:
            show_alert("名前を空にすることはできません。")
            return

        if new_name == current_player:
            return

        if new_name in registered_users:
            show_alert("その名前はすでに使用されています。")
            return

        # ユーザー名簿の更新
        if current_player in registered_users:
            registered_users.remove(current_player)
        registered_users.append(new_name)
        page.client_storage.set(STORAGE_USERS_KEY, registered_users)

        # プライバシー設定（非表示スイッチの設定）の引き継ぎ
        old_privacy = privacy_settings.pop(current_player, True)
        privacy_settings[new_name] = old_privacy
        page.client_storage.set(STORAGE_PRIVACY_KEY, privacy_settings)

        # 過去のゲーム記録の名前を一括書き換え
        for record in saved_records:
            if record["player"] == current_player:
                record["player"] = new_name
        page.client_storage.set(STORAGE_RECORDS_KEY, saved_records)

        current_player = new_name
        logged_in_user_text.value = f"👤 ログイン中: {current_player} さん"

        update_all_uis()
        page.overlay.append(ft.SnackBar(ft.Text("プレイヤー名を変更しました！"), open=True))
        page.update()

    # --- 非表示設定（トグルの切り替え）処理 ---
    def handle_privacy_change(e):
        if not current_player:
            return
        privacy_settings[current_player] = ranking_switch.value
        page.client_storage.set(STORAGE_PRIVACY_KEY, privacy_settings)
        update_ranking_ui()  # ランキング画面を即座に再計算して更新

    # --- アカウント完全削除処理 ---
    def handle_delete_account(e):
        nonlocal current_player, saved_records
        if not current_player:
            return

        # 1. 名簿とプライバシー設定から削除
        if current_player in registered_users:
            registered_users.remove(current_player)
        page.client_storage.set(STORAGE_USERS_KEY, registered_users)

        privacy_settings.pop(current_player, None)
        page.client_storage.set(STORAGE_PRIVACY_KEY, privacy_settings)

        # 2. ゲーム記録を完全削除
        saved_records = [r for r in saved_records if r["player"] != current_player]
        page.client_storage.set(STORAGE_RECORDS_KEY, saved_records)

        deleted_name = current_player
        current_player = None

        login_view.visible = True
        main_tab_view.visible = False
        update_all_uis()

        show_alert(f"{deleted_name} さんのアカウントとすべての記録を完全に削除しました。", title="アカウント削除完了")

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

    # --- UI全体の一括描画更新 ---
    def update_all_uis():
        update_my_records_ui()
        update_ranking_ui()

    # --- マイページ（自分だけの記録）の描画更新 ---
    def update_my_records_ui():
        my_records_list.controls.clear()
        my_filtered = [r for r in saved_records if r["player"] == current_player]

        if not my_filtered:
            my_records_list.controls.append(
                ft.Text("あなたの保存された記録はありません", italic=True, color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER)
            )
        else:
            for record in reversed(my_filtered):
                my_records_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Column([
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

    # --- ランキング（非表示設定のユーザーを除外してハイスコア順に表示）の描画更新 ---
    def update_ranking_ui():
        ranking_list.controls.clear()

        # ★ここがポイント：プライバシー設定がON（True）のプレイヤーの記録だけを抽出★
        # 設定データがないプレイヤーはデフォルトで表示（True）とみなします
        visible_records = [r for r in saved_records if privacy_settings.get(r["player"], True) == True]

        if not visible_records:
            ranking_list.controls.append(
                ft.Text("公開されている記録はありません", italic=True, color=ft.Colors.GREY_500,
                        text_align=ft.TextAlign.CENTER)
            )
        else:
            sorted_records = sorted(visible_records, key=lambda x: x["final_score"], reverse=True)

            for index, record in enumerate(sorted_records):
                rank = index + 1
                if rank == 1:
                    rank_color = ft.Colors.AMBER_500
                    rank_text = f"🥇 {rank}位"
                elif rank == 2:
                    rank_color = ft.Colors.BLUE_GREY_300
                    rank_text = f"🥈 {rank}位"
                elif rank == 3:
                    rank_color = ft.Colors.BROWN_400
                    rank_text = f"🥉 {rank}位"
                else:
                    rank_color = ft.Colors.BLUE_GREY_700
                    rank_text = f"  {rank}位"

                ranking_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Text(rank_text, size=18, weight=ft.FontWeight.BOLD, color=rank_color, width=60),
                                ft.Column([
                                    ft.Text(f"{record['player']}", size=15, weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.BLUE_GREY_800),
                                    ft.Text(f"内訳: 🍎{record['apple']} 🍊{record['orange']} 🍇{record['grape']}", size=12,
                                            color=ft.Colors.GREY_600),
                                ], expand=True),
                                ft.Text(f"{record['final_score']} 点", size=18, weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE_700)
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        padding=12,
                        border=ft.border.all(1, ft.Colors.GREY_200),
                        border_radius=8,
                        bgcolor=ft.Colors.WHITE
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

    # --- 現在のスコアを過去の記録へ保存 ---
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

        page.client_storage.set(STORAGE_RECORDS_KEY, saved_records)
        page.client_storage.set(STORAGE_COUNTER_KEY, record_id_counter)

        reset_current_game(None)
        update_all_uis()

        page.overlay.append(ft.SnackBar(ft.Text(f"{current_player} の記録を保存しました！"), open=True))
        page.update()

    # --- 過去の記録の削除 ---
    def delete_saved_record(target_id):
        target_idx = next((i for i, r in enumerate(saved_records) if r["id"] == target_id), None)
        if target_idx is not None:
            deleted_player = saved_records[target_idx]["player"]
            saved_records.pop(target_idx)

            still_has_records = any(r["player"] == deleted_player for r in saved_records)
            if not still_has_records and deleted_player in registered_users:
                registered_users.remove(deleted_player)
                page.client_storage.set(STORAGE_USERS_KEY, registered_users)
                privacy_settings.pop(deleted_player, None)
                page.client_storage.set(STORAGE_PRIVACY_KEY, privacy_settings)

            page.client_storage.set(STORAGE_RECORDS_KEY, saved_records)
            update_all_uis()

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
                ft.Icon(ft.Icons.ACCOUNT_CIRCLE, size=80, color=ft.Colors.BLUE_600),
                ft.Text("プレイヤー登録", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("ゲームを始める前に名前を登録してください", size=14, color=ft.Colors.GREY_600),
                ft.Container(height=10),
                login_name_input,
                ft.Container(height=10),
                ft.ElevatedButton(
                    "登録してゲーム開始", 
                    icon=ft.Icons.PLAY_ARROW,
                    on_click=handle_login,
                    bgcolor=ft.Colors.BLUE,
                    color=ft.Colors.WHITE,
                    width=250,
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

    # --- タブ2: マイページ（名前編集 ＆ 自分の過去の記録 ＆ 各種設定）のレイアウト ---
    mypage_tab_view = ft.Column(
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Text("プロフィール設定", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_400),
                    ft.Row(
                        controls=[
                            edit_name_input,
                            ft.ElevatedButton(
                                "名前を変更", 
                                icon=ft.Icons.EDIT,
                                on_click=handle_rename,
                                bgcolor=ft.Colors.BLUE_600,
                                color=ft.Colors.WHITE
                            )
                        ],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    ft.Divider(height=10, thickness=1),
                    # プライバシー設定（ランキング表示ON/OFFスイッチ）
                    ranking_switch,
                    ft.Divider(height=10, thickness=1),
                    # アカウント削除エリア
                    ft.Row(
                        controls=[
                            ft.Text("アカウントの完全削除:", size=13, color=ft.Colors.RED_400),
                            ft.ElevatedButton(
                                "アカウントを削除する",
                                icon=ft.Icons.DANGEROUS,
                                on_click=handle_delete_account,
                                bgcolor=ft.Colors.RED_600,
                                color=ft.Colors.WHITE,
                                style=ft.ButtonStyle(padding=8)
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    )
                ]),
                padding=15,
                bgcolor=ft.Colors.GREY_50,
                border=ft.border.all(1, ft.Colors.GREY_200),
                border_radius=10
            ),
            ft.Container(
                content=ft.Text("あなたの過去のゲーム結果一覧", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_700),
                padding=ft.padding.only(left=15, top=15, right=15)
            ),
            ft.Container(content=my_records_list, expand=True),
        ],
        expand=True
    )

    # --- タブ3: ランキング（全員の記録を高い順に表示）のレイアウト ---
    ranking_tab_view = ft.Column(
        controls=[
            ft.Container(
                content=ft.Text("総合得点ハイスコアランキング", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_GREY_700),
                padding=15
            ),
            ft.Container(content=ranking_list, expand=True),
        ],
        expand=True
    )

    # --- メインタブ構造の配置 ---
    main_tab_view = ft.Tabs(
        selected_index=0,
        animation_duration=300,
        tabs=[
            ft.Tab(text="得点計算", icon=ft.Icons.CALCULATE, content=calc_tab_view),
            ft.Tab(text="マイページ", icon=ft.Icons.PERSON, content=mypage_tab_view),
            ft.Tab(text="ランキング", icon=ft.Icons.EMOJI_EVENTS, content=ranking_tab_view),
        ],
        expand=True,
        visible=False
    )

    # 初期描画のセットアップ
    calculate_total_score()
    update_all_uis()

    page.add(login_view, main_tab_view)

if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    ft.app(target=main, host="0.0.0.0", view=ft.AppView.WEB_BROWSER, port=port)
