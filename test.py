# -*- coding: utf-8 -*-
import flet as ft

# ----------------------------------------------------
# 接続情報（必要に応じてご自身の環境のものに書き換えてください）
# ----------------------------------------------------
SUPABASE_URL = "https://tqufugshygdknyfgrsxh.supabase.co"
SUPABASE_KEY = "sb_publishable_fMuDE8giATkTj2UOjCyThg_wowMJz0s"

def main(page: ft.Page):
    page.title = "フルーツ得点計算＆プレイヤー管理"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20

    # ダミーの初期データ（ランキング・管理用DataTableテスト用）
    # 本来はSupabaseから取得する想定
    players_data = [
        {"name": "プレイヤーA", "score": 150, "group": "グループ1"},
        {"name": "プレイヤーB", "score": 230, "group": "グループ2"},
        {"name": "プレイヤーC", "score": 90, "group": "グループ1"},
        {"name": "プレイヤーD", "score": 310, "group": "グループ3"},
    ]
    
    # ソート状態保持用変数
    sort_ascending = {"name": True, "score": False}

    # 各種ダイアログ初期化
    change_name_dialog = ft.AlertDialog(
        title=ft.Text("名前変更"),
        content=ft.TextField(label="新しい名前を入力してください"),
        actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(change_name_dialog))]
    )
    
    change_password_dialog = ft.AlertDialog(
        title=ft.Text("パスワード変更"),
        content=ft.TextField(label="新しいパスワードを入力してください", password=True, can_reveal_password=True),
        actions=[ft.TextButton("キャンセル", on_click=lambda e: page.close(change_password_dialog))]
    )
    
    confirm_delete_dialog = ft.AlertDialog(
        title=ft.Text("⚠️ 最終確認"),
        content=ft.Text("本当にアカウントを削除しますか？"),
        actions=[
            ft.TextButton("はい", on_click=lambda e: page.close(confirm_delete_dialog)),
            ft.TextButton("いいえ", on_click=lambda e: page.close(confirm_delete_dialog))
        ]
    )

    # ----------------------------------------------------
    # ランキング・管理ページの修正関数（ソート機能の正常化）
    # ----------------------------------------------------
    def rebuild_table():
        # 選択されたグループで絞り込み
        selected_grp = group_filter.value
        filtered = [p for p in players_data if selected_grp == "すべて" or p["group"] == selected_grp]
        
        rows = []
        for p in filtered:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(p["name"])),
                        ft.DataCell(ft.Text(str(p["score"]))),
                        ft.DataCell(ft.Text(p["group"])),
                    ]
                )
            )
        data_table.rows = rows
        page.update()

    def on_sort(e):
        # e.column_index: 0=名前, 1=スコア
        col_key = "name" if e.column_index == 0 else "score"
        
        # トグル反転
        sort_ascending[col_key] = not sort_ascending[col_key]
        
        # データの並び替えを実行
        players_data.sort(key=lambda x: x[col_key], reverse=not sort_ascending[col_key])
        
        # DataTable側のソートインジケータ表示を切り替え
        if e.column_index == 0:
            data_table.columns[0].sort_ascending = sort_ascending["name"]
            data_table.sort_column_index = 0
        else:
            data_table.columns[1].sort_ascending = sort_ascending["score"]
            data_table.sort_column_index = 1
            
        rebuild_table()

    def on_filter_change(e):
        rebuild_table()

    # ランキング用 UIコンポーネント
    group_filter = ft.Dropdown(
        label="グループ絞り込み",
        value="すべて",
        options=[
            ft.dropdown.Option("すべて"),
            ft.dropdown.Option("グループ1"),
            ft.dropdown.Option("グループ2"),
            ft.dropdown.Option("グループ3"),
        ],
        on_change=on_filter_change,
        width=200
    )

    data_table = ft.DataTable(
        sort_column_index=1,
        sort_ascending=False,
        columns=[
            ft.DataColumn(ft.Text("プレイヤー名"), on_sort=on_sort),
            ft.DataColumn(ft.Text("スコア"), numeric=True, on_sort=on_sort),
            ft.DataColumn(ft.Text("グループ")),
        ],
        rows=[]
    )

    # ----------------------------------------------------
    # UIレイアウト構築
    # ----------------------------------------------------
    # 計算エリアのリセットボタン（「リセット」タイポ修正版）
    reset_button = ft.OutlinedButton(
        "リセット", 
        icon=ft.Icons.REFRESH, 
        on_click=lambda e: print("リセットされました")
    )

    # マイページの各種設定メニュー（レスポンシブ・クリック不具合修正版）
    settings_row = ft.Row(
        wrap=True,
        controls=[
            ft.IconButton(
                icon=ft.Icons.EDIT, 
                tooltip="名前変更", 
                on_click=lambda e: page.open(change_name_dialog)
            ),
            ft.IconButton(
                icon=ft.Icons.LOCK, 
                tooltip="パスワード変更", 
                on_click=lambda e: page.open(change_password_dialog)
            ),
            ft.IconButton(
                icon=ft.Icons.DELETE_FOREVER, 
                tooltip="アカウント削除", 
                on_click=lambda e: page.open(confirm_delete_dialog)
            ),
        ]
    )

    # 画面への配置
    page.add(
        ft.Text("📊 ランキング ＆ 管理ページ (Flet 0.28.3 適合版)", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
        group_filter,
        data_table,
        ft.Divider(),
        ft.Text("⚙️ マイページ / 各種設定", style=ft.TextThemeStyle.TITLE_MEDIUM),
        settings_row,
        ft.Divider(),
        ft.Text("🍎 得点計算エリア", style=ft.TextThemeStyle.TITLE_MEDIUM),
        reset_button
    )

    # 初期描画
    rebuild_table()

if __name__ == "__main__":
    ft.app(target=main)
