import flet as ft

def request_history_view(page: ft.Page):
    return ft.View(
        "/history",
        controls=[
            ft.AppBar(title=ft.Text("Request History | درخواستوں کی تاریخ")),
            ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("Patient | مریض")),
                    ft.DataColumn(ft.Text("Group | گروپ")),
                    ft.DataColumn(ft.Text("Status | حال")),
                ],
                rows=[
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Zubair Ahmed")),
                        ft.DataCell(ft.Text("A+")),
                        ft.DataCell(ft.Text("Completed | مکمل", color="green")),
                    ]),
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Sara Khan")),
                        ft.DataCell(ft.Text("O-")),
                        ft.DataCell(ft.Text("Pending | زیر التواء", color="orange")),
                    ]),
                ]
            )
        ]
    )