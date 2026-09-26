import reflex as rx

from app.components.library import sidebar, select_control
from app.components.document import BUTTON, CONTROL
from app.states.git import GitState as G


def diff_line(line: str) -> rx.Component:
    return rx.el.div(
        line,
        class_name=rx.cond(
            line.startswith("+"),
            "min-w-full w-max border-l-2 border-green-600 bg-green-50 px-5 text-green-800",
            rx.cond(
                line.startswith("-"),
                "min-w-full w-max border-l-2 border-red-500 bg-red-50 px-5 text-red-800",
                rx.cond(
                    line.startswith("@@"),
                    "min-w-full w-max border-l-2 border-amber-500 bg-[#f6edda] px-5 py-2 text-amber-900",
                    "min-w-full w-max border-l-2 border-transparent px-5 text-[#626a61]",
                ),
            ),
        ),
    )


def change_row(change: dict[str, str]) -> rx.Component:
    return rx.el.button(
        rx.el.span(
            change["kind"],
            class_name="font-mono text-[10px] uppercase text-amber-800",
        ),
        rx.el.span(change["path"], class_name="block mt-2 break-all text-xs"),
        rx.cond(
            change["kind"] == "renamed",
            rx.el.span(
                f"← {change['old_path']}",
                class_name="block mt-2 break-all font-mono text-[10px]",
            ),
        ),
        on_click=G.select_document(change["path"]),
        disabled=G.busy | G.pending,
        aria_pressed=G.selected == change["path"],
        class_name=rx.cond(
            G.selected == change["path"],
            "w-full border-b border-l-2 border-[#dcd8ce] border-l-amber-600 bg-[#f6edda] p-4 text-left text-[#35413c] disabled:opacity-60",
            "w-full border-b border-l-2 border-[#dcd8ce] border-l-transparent bg-[#fffdf8] p-4 text-left text-[#737671] hover:bg-[#f1eee6] disabled:opacity-60",
        ),
    )


def history_row(item: dict[str, str]) -> rx.Component:
    return rx.el.article(
        rx.el.div(
            rx.icon(
                "git-commit-horizontal",
                class_name="h-4 w-4 text-amber-700 shrink-0",
            ),
            rx.el.a(
                item["sha"],
                href=item["url"],
                target="_blank",
                rel="noopener noreferrer",
                class_name="break-all font-mono text-[10px] text-amber-800 underline",
            ),
            rx.el.button(
                "Ver / preparar versión",
                on_click=G.prepare(item["sha"]),
                disabled=G.busy | G.pending | G.conflict,
                class_name=BUTTON,
            ),
            class_name="flex flex-wrap items-center gap-3",
        ),
        rx.el.p(
            item["message"],
            class_name="mt-3 whitespace-pre-wrap text-sm text-[#424942]",
        ),
        rx.el.p(
            f"{item['author']} · @{item['github']} · {item['date']}",
            class_name="mt-2 text-[11px] text-[#85867e]",
        ),
        rx.el.p(
            item["path"],
            class_name="mt-1 break-all font-mono text-[10px] text-[#85867e]",
        ),
        class_name="border-b border-l border-[#dcd8ce] p-5 bg-[#fffdf8]",
    )


def restoration_form() -> rx.Component:
    return rx.el.section(
        rx.el.h2(
            "Commit / restauración controlada",
            class_name="text-sm font-semibold text-[#35413c]",
        ),
        rx.el.p(
            "Cada escritura crea un commit real con Git Data API y actualiza la referencia remota: commit + push. Pull solo refresca desde GitHub. No hay staging local, merges ni push simulado.",
            class_name="mt-3 text-xs leading-6 text-[#737671]",
        ),
        rx.cond(
            G.pending,
            rx.el.div(
                rx.el.p(
                    f"PENDIENTE · {G.selected} ← {G.version}",
                    class_name="my-4 break-all font-mono text-[10px] text-amber-800",
                ),
                rx.el.p(
                    "Se restaura el archivo completo, incluidos metadatos y estado editorial, sin modificar otros archivos. Una versión sin archivo prepara su eliminación. No implica despliegue; vuelve a validar después.",
                    class_name="mb-4 text-xs leading-5 text-[#737671]",
                ),
                rx.el.form(
                    rx.el.fieldset(
                        rx.el.div(
                            rx.el.label(
                                "Mensaje de commit",
                                rx.el.input(
                                    name="message",
                                    required=True,
                                    placeholder="Motivo de la restauración",
                                    class_name=CONTROL,
                                ),
                                class_name="flex flex-col gap-2 text-xs text-[#626a61] md:col-span-2",
                            ),
                            rx.el.label(
                                "Nombre del actor operativo",
                                rx.el.input(
                                    name="name",
                                    required=True,
                                    placeholder="Tu nombre",
                                    class_name=CONTROL,
                                ),
                                class_name="flex flex-col gap-2 text-xs text-[#626a61]",
                            ),
                            rx.el.label(
                                "Email del actor operativo",
                                rx.el.input(
                                    name="email",
                                    type="email",
                                    required=True,
                                    placeholder="nombre@organizacion.com",
                                    class_name=CONTROL,
                                ),
                                class_name="flex flex-col gap-2 text-xs text-[#626a61]",
                            ),
                            class_name="grid grid-cols-1 md:grid-cols-2 gap-4",
                        ),
                        rx.el.label(
                            rx.el.input(
                                type="checkbox",
                                name="confirm",
                                required=True,
                                class_name="accent-amber-700",
                            ),
                            "Confirmo el diff y autorizo crear el commit y actualizar esta rama remota.",
                            class_name="my-5 flex items-start gap-3 text-xs leading-5 text-[#626a61]",
                        ),
                        rx.el.button(
                            rx.icon(
                                "git-commit-horizontal", class_name="h-4 w-4"
                            ),
                            "Crear commit + actualizar remoto",
                            type="submit",
                            class_name="flex items-center gap-2 bg-[#35413c] px-5 py-3 text-xs text-white hover:bg-[#4b5950] disabled:opacity-50",
                        ),
                        disabled=G.busy | G.conflict | (G.error != ""),
                    ),
                    on_submit=G.commit_restore,
                ),
                rx.el.button(
                    "Cancelar restauración (sin escribir)",
                    on_click=G.cancel,
                    disabled=G.busy,
                    class_name="mt-4 text-xs text-amber-800 underline disabled:opacity-50",
                ),
            ),
            rx.el.p(
                "Selecciona una versión del historial para preparar el diff contra HEAD. Nada se escribe hasta confirmar.",
                class_name="mt-4 text-xs text-[#85867e]",
            ),
        ),
        class_name="border border-[#dcd8ce] bg-[#f1eee6] p-5 mt-5",
    )


def git_page() -> rx.Component:
    return rx.el.div(
        sidebar(),
        rx.el.main(
            rx.el.header(
                rx.el.a(
                    "Biblioteca / Operaciones Git",
                    href="/",
                    class_name="text-xs text-[#636e56] hover:underline",
                ),
                rx.el.span(
                    "GITHUB · FUENTE CANÓNICA",
                    class_name="font-mono text-[10px] text-[#858e73]",
                ),
                class_name="flex flex-wrap justify-between gap-3 border-b border-[#dcd8ce] px-5 md:px-9 py-5",
            ),
            rx.el.div(
                rx.el.p(
                    "04 / CONTROL DE VERSIONES",
                    class_name="font-mono text-[10px] tracking-widest text-[#9a7a3d]",
                ),
                rx.el.h1(
                    "Operaciones Git",
                    class_name="mt-3 text-3xl md:text-4xl font-medium tracking-tight text-[#354132]",
                ),
                rx.el.p(
                    "Una historia trazable. Ninguna sobrescritura silenciosa.",
                    class_name="mt-3 mb-7 text-sm text-[#838b74]",
                ),
                rx.el.section(
                    rx.el.div(
                        rx.el.p(
                            f"{G.repository} · {G.branch}",
                            class_name="break-all font-mono text-xs text-[#35413c]",
                        ),
                        rx.el.p(
                            f"Base / default: {G.base} · ahead {G.ahead} / behind {G.behind}",
                            class_name="mt-2 font-mono text-xs text-[#737671]",
                        ),
                        rx.el.a(
                            f"HEAD cargado · {G.head}",
                            href=G.commit_url,
                            target="_blank",
                            rel="noopener noreferrer",
                            class_name="block mt-3 break-all font-mono text-[10px] text-amber-800 underline",
                        ),
                        rx.el.p(
                            f"Remoto observado · {G.remote_head}",
                            class_name="mt-2 break-all font-mono text-[10px] text-[#737671]",
                        ),
                        rx.el.p(
                            f"Base SHA · {G.base_head} · Lectura {G.checked}",
                            class_name="mt-2 break-all font-mono text-[10px] text-[#85867e]",
                        ),
                        class_name="flex-1 min-w-0",
                    ),
                    rx.el.button(
                        rx.icon("radar", class_name="h-4 w-4"),
                        "Comprobar remoto",
                        on_click=G.check_remote,
                        disabled=G.busy | ~G.ready,
                        class_name=BUTTON,
                    ),
                    rx.el.button(
                        rx.icon("refresh-cw", class_name="h-4 w-4"),
                        "Pull / recargar",
                        on_click=G.load,
                        disabled=G.busy | G.pending,
                        class_name=BUTTON,
                    ),
                    class_name="flex flex-wrap items-center gap-4 border-y border-[#dcd8ce] py-5",
                ),
                rx.cond(
                    G.conflict,
                    rx.el.div(
                        rx.icon(
                            "triangle-alert", class_name="h-5 w-5 shrink-0"
                        ),
                        rx.el.div(
                            rx.el.h2(
                                "Conflicto / operación bloqueada",
                                class_name="font-semibold",
                            ),
                            rx.el.p(
                                "No se fuerza la referencia ni se mezclan versiones. Cancela la restauración y haz Pull para revisar el HEAD actual.",
                                class_name="mt-2",
                            ),
                        ),
                        role="alert",
                        class_name="mt-5 flex gap-3 border border-red-200 bg-red-50 p-5 text-xs leading-5 text-red-700",
                    ),
                ),
                rx.cond(
                    G.error != "",
                    rx.el.p(
                        G.error,
                        role="alert",
                        class_name="mt-5 border border-red-200 bg-red-50 p-4 text-xs text-red-700",
                    ),
                ),
                rx.cond(
                    G.message != "",
                    rx.el.p(
                        G.message,
                        role="status",
                        class_name="mt-5 border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900",
                    ),
                ),
                rx.cond(
                    G.busy,
                    rx.el.div(
                        rx.icon(
                            "loader-circle", class_name="h-4 w-4 animate-spin"
                        ),
                        "Consultando GitHub…",
                        role="status",
                        class_name="my-4 flex items-center gap-3 text-xs text-amber-800",
                    ),
                ),
                rx.el.div(
                    rx.el.aside(
                        rx.el.div(
                            rx.el.h2(
                                f"Cambios · {G.changes.length()}",
                                class_name="text-sm font-semibold text-[#35413c]",
                            ),
                            rx.el.p(
                                G.comparison,
                                class_name="mt-2 break-all font-mono text-[10px] leading-5 text-[#85867e]",
                            ),
                            class_name="p-4 border-b border-[#dcd8ce] bg-[#f1eee6]",
                        ),
                        rx.foreach(G.changes, change_row),
                        rx.cond(
                            G.changes.length() == 0,
                            rx.el.p(
                                "Sin cambios comparables. Puedes consultar el historial de cualquier documento.",
                                class_name="p-5 text-xs leading-6 text-[#85867e]",
                            ),
                        ),
                        rx.el.div(
                            select_control(
                                "Todos los documentos",
                                G.paths,
                                G.selected,
                                G.select_document,
                                G.busy | G.pending,
                            ),
                            class_name="p-4",
                        ),
                        class_name="min-w-0 border border-[#dcd8ce] bg-[#fffdf8] self-start",
                    ),
                    rx.el.section(
                        rx.el.div(
                            rx.el.h2(
                                rx.cond(
                                    G.pending,
                                    "HEAD → restauración pendiente",
                                    "Diff / documentos remotos",
                                ),
                                class_name="text-sm font-semibold text-[#35413c]",
                            ),
                            rx.el.p(
                                G.selected,
                                class_name="mt-2 break-all font-mono text-[10px] text-[#85867e]",
                            ),
                            class_name="border-b border-[#dcd8ce] p-5 bg-[#f1eee6]",
                        ),
                        rx.el.p(
                            G.diff_note,
                            class_name="border-b border-[#dcd8ce] px-5 py-3 text-[11px] text-[#85867e]",
                        ),
                        rx.el.pre(
                            rx.foreach(G.lines, diff_line),
                            aria_label="Diff unificado del documento",
                            tab_index=0,
                            class_name="min-h-80 max-h-[650px] w-full overflow-auto py-4 font-mono text-xs leading-6 bg-[#fffdf8]",
                        ),
                        rx.cond(
                            G.selected != "",
                            rx.el.a(
                                "Abrir esta unidad en GitHub ↗",
                                href=G.document_url,
                                target="_blank",
                                rel="noopener noreferrer",
                                class_name="block border-t border-[#dcd8ce] p-4 text-xs text-amber-800 underline",
                            ),
                        ),
                        class_name="min-w-0 w-full border border-[#dcd8ce] bg-[#fffdf8]",
                    ),
                    class_name="mt-6 grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-5",
                ),
                restoration_form(),
                rx.el.section(
                    rx.el.h2(
                        "Historial por documento",
                        class_name="mb-3 text-lg font-medium text-[#35413c]",
                    ),
                    rx.el.p(
                        "Versiones de esta ruta y sus renombrados. El autor declarado y la cuenta GitHub vinculada pueden ser distintos. Seleccionar una versión no escribe en el remoto.",
                        class_name="mb-5 text-xs leading-5 text-[#85867e]",
                    ),
                    rx.cond(
                        G.history.length() == 0,
                        rx.el.p(
                            "Sin historial cargado. Selecciona un documento; si hubo un error, recarga.",
                            class_name="border border-[#dcd8ce] bg-[#fffdf8] p-6 text-xs text-[#85867e]",
                        ),
                    ),
                    rx.foreach(G.history, history_row),
                    rx.cond(
                        G.history_more,
                        rx.el.button(
                            "Cargar 50 versiones más",
                            on_click=G.more_history,
                            disabled=G.busy | G.pending,
                            class_name=BUTTON,
                        ),
                    ),
                    rx.cond(
                        G.version != "",
                        rx.el.details(
                            rx.el.summary(
                                f"Contenido histórico · {G.version}",
                                class_name="cursor-pointer break-all font-mono text-xs text-amber-800",
                            ),
                            rx.el.pre(
                                G.version_text,
                                class_name="mt-4 max-h-96 overflow-auto whitespace-pre-wrap break-all font-mono text-xs leading-6 text-[#626a61]",
                            ),
                            open=True,
                            class_name="mt-5 border border-[#dcd8ce] bg-[#fffdf8] p-5",
                        ),
                    ),
                    class_name="mt-8 mb-10",
                ),
                class_name="w-full px-5 md:px-9 pt-8",
            ),
            class_name="flex-1 w-full min-w-0 overflow-y-auto bg-[#faf9f3]",
        ),
        class_name="flex h-dvh w-full flex-col md:flex-row overflow-hidden font-['Inter'] text-[#3f4839] bg-[#faf9f3]",
    )
