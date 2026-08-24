import flet as ft

def main(page: ft.Page):
    page.title = "空間カウント付き 3×5 グリッド"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    CELL_W = 100
    CELL_H = 80
    ROWS = 3
    COLS = 5
    LINE_THICK = 6  

    TOTAL_W = CELL_W * COLS
    TOTAL_H = CELL_H * ROWS

    current_mode = "COLOR" 
    selected_color = ft.Colors.BLUE_400
    PALETTE_COLORS = [ft.Colors.BLUE_400, ft.Colors.GREEN_400, ft.Colors.ORANGE_400, ft.Colors.RED_400]

    horiz_line_dict = {}
    vert_line_dict = {}

    # --- 完全に囲まれた空間だけを数えるアルゴリズム ---
    def count_enclosed_spaces():
        visited = [[False for _ in range(COLS)] for _ in range(ROWS)]
        
        # 1. まず「外周（盤面の外）」につながっている開いたグループを探索して除外する
        border_cells = []
        for r in range(ROWS):
            for c in range(COLS):
                if r == 0 or r == ROWS - 1 or c == 0 or c == COLS - 1:
                    border_cells.append((r, c))

        for r, c in border_cells:
            if not visited[r][c]:
                is_leaking = False
                
                if r == 0 and horiz_line_dict[(0, c)].bgcolor != ft.Colors.BLACK: is_leaking = True
                if r == ROWS - 1 and horiz_line_dict[(ROWS, c)].bgcolor != ft.Colors.BLACK: is_leaking = True
                if c == 0 and vert_line_dict[(0, r)].bgcolor != ft.Colors.BLACK: is_leaking = True
                if c == COLS - 1 and vert_line_dict[(COLS, r)].bgcolor != ft.Colors.BLACK: is_leaking = True

                if is_leaking:
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        curr_r, curr_c = queue.pop(0)
                        
                        if curr_r > 0 and not visited[curr_r - 1][curr_c]:
                            if horiz_line_dict[(curr_r, curr_c)].bgcolor != ft.Colors.BLACK:
                                visited[curr_r - 1][curr_c] = True
                                queue.append((curr_r - 1, curr_c))
                        if curr_r < ROWS - 1 and not visited[curr_r + 1][curr_c]:
                            if horiz_line_dict[(curr_r + 1, curr_c)].bgcolor != ft.Colors.BLACK:
                                visited[curr_r + 1][curr_c] = True
                                queue.append((curr_r + 1, curr_c))
                        if curr_c > 0 and not visited[curr_r][curr_c - 1]:
                            if vert_line_dict[(curr_c, curr_r)].bgcolor != ft.Colors.BLACK:
                                visited[curr_r][curr_c - 1] = True
                                queue.append((curr_r, curr_c - 1))
                        if curr_c < COLS - 1 and not visited[curr_r][curr_c + 1]:
                            if vert_line_dict[(curr_c + 1, curr_r)].bgcolor != ft.Colors.BLACK:
                                visited[curr_r][curr_c + 1] = True
                                queue.append((curr_r, curr_c + 1))

        # 2. 外に漏れていない、残りの「完全に閉じ込められた内側の空間」だけをカウントする
        enclosed_count = 0
        for r in range(ROWS):
            for c in range(COLS):
                if not visited[r][c]:
                    enclosed_count += 1
                    queue = [(r, c)]
                    visited[r][c] = True
                    while queue:
                        curr_r, curr_c = queue.pop(0)
                        if curr_r > 0 and not visited[curr_r - 1][curr_c]:
                            if horiz_line_dict[(curr_r, curr_c)].bgcolor != ft.Colors.BLACK:
                                visited[curr_r - 1][curr_c] = True
                                queue.append((curr_r - 1, curr_c))
                        if curr_r < ROWS - 1 and not visited[curr_r + 1][curr_c]:
                            if horiz_line_dict[(curr_r + 1, curr_c)].bgcolor != ft.Colors.BLACK:
                                visited[curr_r + 1][curr_c] = True
                                queue.append((curr_r + 1, curr_c))
                        if curr_c > 0 and not visited[curr_r][curr_c - 1]:
                            if vert_line_dict[(curr_c, curr_r)].bgcolor != ft.Colors.BLACK:
                                visited[curr_r][curr_c - 1] = True
                                queue.append((curr_r, curr_c - 1))
                        if curr_c < COLS - 1 and not visited[curr_r][curr_c + 1]:
                            if vert_line_dict[(curr_c + 1, curr_r)].bgcolor != ft.Colors.BLACK:
                                visited[curr_r][curr_c + 1] = True
                                queue.append((curr_r, curr_c + 1))
                                
        return enclosed_count

    def update_mode_ui():
        if current_mode == "COLOR":
            mode_text.value = "現在のモード: 🎨 色塗り中"
            mode_text.color = ft.Colors.BLUE_700
            line_mode_btn.style = ft.ButtonStyle(bgcolor=ft.Colors.GREY_300, color=ft.Colors.BLACK, shape=ft.RoundedRectangleBorder(radius=8))
        else:
            mode_text.value = "現在のモード: ✏️ 線を選択中"
            mode_text.color = ft.Colors.BLACK
            line_mode_btn.style = ft.ButtonStyle(bgcolor=ft.Colors.BLACK, color=ft.Colors.WHITE, shape=ft.RoundedRectangleBorder(radius=8))
            for c in palette_row.controls:
                c.border = None
        
        spaces = count_enclosed_spaces()
        space_count_text.value = f"📦 黒線で囲まれた空間の数: {spaces} つ"
        
        line_mode_btn.update()
        mode_text.update()
        palette_row.update()
        space_count_text.update()

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
            update_mode_ui()

    palette_options = [ft.Container(width=40, height=40, bgcolor=col, border_radius=20, data=col, on_click=on_palette_click) for col in PALETTE_COLORS]
    
    # 【インデックスを確実に設定】
    palette_options[0].border = ft.border.all(3, ft.Colors.BLACK) 
    
    palette_row = ft.Row(controls=palette_options, alignment=ft.MainAxisAlignment.CENTER)

    line_mode_btn = ft.ElevatedButton(
        text="✏️ 黒線を選択する",
        on_click=on_line_mode_click,
        style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_300, color=ft.Colors.BLACK, shape=ft.RoundedRectangleBorder(radius=8))
    )

    top_control_row = ft.Row(controls=[palette_row, ft.VerticalDivider(width=20), line_mode_btn], alignment=ft.MainAxisAlignment.CENTER)
    mode_text = ft.Text("現在のモード: 🎨 色塗り中", size=16, weight="bold", color=ft.Colors.BLUE_700)
    space_count_text = ft.Text("📦 黒線で囲まれた空間の数: 0 つ", size=18, weight="bold", color=ft.Colors.GREEN_700)

    stack_layout = ft.Stack(width=TOTAL_W, height=TOTAL_H)

    for r in range(ROWS):
        for c in range(COLS):
            cell = ft.Container(
                content=ft.Text(f"{r*COLS + c + 1}", color=ft.Colors.GREY_400, size=12),
                alignment=ft.alignment.center, bgcolor=ft.Colors.GREY_100,
                width=CELL_W, height=CELL_H, left=c * CELL_W, top=r * CELL_H,
                on_click=on_cell_click
            )
            stack_layout.controls.append(cell)

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
            horiz_line_dict[(r, c)] = horiz_line

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
            vert_line_dict[(c, r)] = vert_line

    page.add(
        ft.Column([
            top_control_row,
            mode_text,
            ft.Divider(),
            ft.Container(content=stack_layout, border=ft.border.all(1, ft.Colors.GREY_300)),
            ft.Divider(),
            space_count_text
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

ft.app(target=main, view=ft.AppView.WEB_BROWSER)
