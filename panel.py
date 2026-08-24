import flet as ft


def main(page: ft.Page):
    page.title = "モード切り替え付き 3×5 グリッドアプリ"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # --- 1マスのサイズと全体の定義 ---
    CELL_W = 100
    CELL_H = 80
    ROWS = 3
    COLS = 5
    LINE_THICK = 6

    TOTAL_W = CELL_W * COLS
    TOTAL_H = CELL_H * ROWS

    # --- アプリの状態管理 ---
    current_mode = "COLOR"
    selected_color = ft.Colors.BLUE_400
    PALETTE_COLORS = [ft.Colors.BLUE_400, ft.Colors.GREEN_400, ft.Colors.ORANGE_400, ft.Colors.RED_400]

    # --- モード表示の更新関数 ---
    def update_mode_ui():
        if current_mode == "COLOR":
            mode_text.value = "現在のモード: 🎨 色塗り中"
            mode_text.color = ft.Colors.BLUE_700
            line_mode_btn.style = ft.ButtonStyle(
                bgcolor=ft.Colors.GREY_300,
                color=ft.Colors.BLACK,
                shape=ft.RoundedRectangleBorder(radius=8)
            )
        else:
            mode_text.value = "現在のモード: ✏️ 線を選択中"
            mode_text.color = ft.Colors.BLACK
            line_mode_btn.style = ft.ButtonStyle(
                bgcolor=ft.Colors.BLACK,
                color=ft.Colors.WHITE,
                shape=ft.RoundedRectangleBorder(radius=8)
            )
            # パレットの枠線をすべて消す
            for c in palette_row.controls:
                c.border = None

        line_mode_btn.update()
        mode_text.update()
        palette_row.update()

    # --- イベント処理 ---
    def on_palette_click(e):
        nonlocal selected_color, current_mode
        current_mode = "COLOR"
        selected_color = e.control.data
        for c in palette_row.controls:
            c.border = None
        e.control.border = ft.border.all(3, ft.Colors.BLACK)
        update_mode_ui()

    def on_line_mode_click(e):
        nonlocal current_mode
        current_mode = "LINE"
        update_mode_ui()

    def on_cell_click(e):
        if current_mode == "COLOR":
            e.control.bgcolor = selected_color
            e.control.update()

    def toggle_line(e):
        if current_mode == "LINE":
            if e.control.bgcolor == ft.Colors.BLACK:
                e.control.bgcolor = ft.Colors.GREY_300
            else:
                e.control.bgcolor = ft.Colors.BLACK
            e.control.update()

    # --- UIパーツ作成 ---
    palette_options = [
        ft.Container(width=40, height=40, bgcolor=col, border_radius=20, data=col, on_click=on_palette_click) for col in
        PALETTE_COLORS]

    # 【ここを完全に修正】リストの0番目のContainerに対して枠線を正しく設定
    palette_options[0].border = ft.border.all(3, ft.Colors.BLACK)

    palette_row = ft.Row(controls=palette_options, alignment=ft.MainAxisAlignment.CENTER)

    # 「線選択」ボタン
    line_mode_btn = ft.ElevatedButton(
        text="✏️ 黒線を選択する",
        on_click=on_line_mode_click,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.GREY_300,
            color=ft.Colors.BLACK,
            shape=ft.RoundedRectangleBorder(radius=8)
        )
    )

    top_control_row = ft.Row(
        controls=[
            palette_row,
            ft.VerticalDivider(width=20),
            line_mode_btn
        ],
        alignment=ft.MainAxisAlignment.CENTER
    )

    mode_text = ft.Text("現在のモード: 🎨 色塗り中", size=16, weight="bold", color=ft.Colors.BLUE_700)
    stack_layout = ft.Stack(width=TOTAL_W, height=TOTAL_H)

    # マスの配置
    for r in range(ROWS):
        for c in range(COLS):
            cell = ft.Container(
                content=ft.Text(f"{r * COLS + c + 1}", color=ft.Colors.GREY_400, size=12),
                alignment=ft.alignment.center,
                bgcolor=ft.Colors.GREY_100,
                width=CELL_W, height=CELL_H,
                left=c * CELL_W, top=r * CELL_H,
                on_click=on_cell_click
            )
            stack_layout.controls.append(cell)

    # 横の短い境界線の配置
    for r in range(ROWS + 1):
        for c in range(COLS):
            left_pos = c * CELL_W
            top_pos = r * CELL_H - (LINE_THICK / 2)
            if r == 0: top_pos = 0
            if r == ROWS: top_pos = TOTAL_H - LINE_THICK

            horiz_line = ft.Container(
                width=CELL_W, height=LINE_THICK, bgcolor=ft.Colors.GREY_300,
                left=left_pos, top=top_pos, on_click=toggle_line,
                animate=ft.Animation(100, curve="easeOut")
            )
            stack_layout.controls.append(horiz_line)

    # 縦の短い境界線の配置
    for c in range(COLS + 1):
        for r in range(ROWS):
            left_pos = c * CELL_W - (LINE_THICK / 2)
            top_pos = r * CELL_H
            if c == 0: left_pos = 0
            if c == COLS: left_pos = TOTAL_W - LINE_THICK

            vert_line = ft.Container(
                width=LINE_THICK, height=CELL_H, bgcolor=ft.Colors.GREY_300,
                left=left_pos, top=top_pos, on_click=toggle_line,
                animate=ft.Animation(100, curve="easeOut")
            )
            stack_layout.controls.append(vert_line)

    page.add(
        ft.Column([
            top_control_row,
            mode_text,
            ft.Divider(),
            ft.Container(content=stack_layout, border=ft.border.all(1, ft.Colors.GREY_300))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )


ft.app(target=main, view=ft.AppView.WEB_BROWSER)
