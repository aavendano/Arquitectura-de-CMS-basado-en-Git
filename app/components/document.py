import reflex as rx

from app.components.library import sidebar, select_control
from app.states.document import DocumentState as D, Field


CONTROL = "w-full rounded-sm border border-[#dcd8ce] bg-[#fffdf8] px-3 py-2 text-sm text-[#424942] focus:outline-hidden focus:ring-2 focus:ring-amber-500/30 disabled:opacity-50"
BUTTON = "flex items-center justify-center gap-2 rounded-sm border border-[#dcd8ce] bg-[#fffdf8] px-4 py-2 text-xs text-[#424942] hover:bg-[#eee8db] disabled:opacity-50"


def relation_options(field: Field) -> rx.Component:
    return rx.el.div(
        rx.foreach(
            D.choices,
            lambda doc: rx.el.button(
                rx.icon("link", class_name="h-3 w-3 shrink-0"),
                doc["title"],
                rx.el.span(
                    doc["id"], class_name="font-mono text-[9px] break-all"
                ),
                on_click=D.toggle_relation(field["name"], doc["id"]),
                class_name=rx.cond(
                    D.values.get(field["name"], "").contains(doc["id"]),
                    "flex w-full items-center gap-2 border-b border-[#dcd8ce] bg-[#f6edda] p-2 text-left text-xs text-amber-800",
                    "flex w-full items-center gap-2 border-b border-[#dcd8ce] bg-[#fffdf8] p-2 text-left text-xs text-[#74796c]",
                ),
            ),
        ),
        rx.el.p(
            "Solo documentos con UUID guardado. Pulsa para añadir o quitar.",
            class_name="p-2 text-[10px] text-[#85867e]",
        ),
        class_name="max-h-48 overflow-y-auto border border-[#dcd8ce]",
    )


def schema_field(field: Field) -> rx.Component:
    return rx.el.div(
        rx.el.label(
            field["label"],
            rx.cond(
                field["required"], rx.el.span(" *", class_name="text-amber-700")
            ),
            html_for=field["name"],
            class_name="text-xs font-medium text-[#646b60]",
        ),
        rx.match(
            field["kind"],
            (
                "relation",
                rx.el.div(
                    rx.el.select(
                        rx.el.option("Sin documento de origen", value=""),
                        rx.foreach(
                            D.choices,
                            lambda doc: rx.el.option(
                                f"{doc['title']} · {doc['id']}", value=doc["id"]
                            ),
                        ),
                        value=D.values.get(field["name"], ""),
                        on_change=lambda value: D.edit(field["name"], value),
                        id=field["name"],
                        class_name="w-full appearance-none border border-[#dcd8ce] bg-[#fffdf8] py-2 pl-3 pr-8 text-xs text-[#424942]",
                    ),
                    rx.icon(
                        "chevron-down",
                        class_name="pointer-events-none absolute right-3 top-3 h-3 w-3 text-[#7c8178]",
                    ),
                    class_name="relative",
                ),
            ),
            ("relations", relation_options(field)),
            (
                "boolean",
                select_control(
                    "Valor",
                    rx.Var.create(["true", "false"]),
                    D.values.get(field["name"], "false"),
                    lambda value: D.edit(field["name"], value),
                ),
            ),
            (
                "select",
                select_control(
                    "Opción",
                    field["options"],
                    D.values.get(field["name"], ""),
                    lambda value: D.edit(field["name"], value),
                ),
            ),
            rx.cond(
                field["options"].length() > 0,
                select_control(
                    "Opción",
                    field["options"],
                    D.values.get(field["name"], ""),
                    lambda value: D.edit(field["name"], value),
                ),
                rx.cond(
                    rx.Var.create(
                        ["text", "markdown", "array", "object"]
                    ).contains(field["kind"]),
                    rx.el.textarea(
                        default_value=D.values.get(field["name"], ""),
                        on_change=lambda value: D.edit(field["name"], value),
                        id=field["name"],
                        rows=4,
                        class_name=CONTROL,
                    ),
                    rx.el.input(
                        default_value=D.values.get(field["name"], ""),
                        on_change=lambda value: D.edit(field["name"], value),
                        id=field["name"],
                        type=rx.match(
                            field["kind"],
                            ("number", "number"),
                            ("integer", "number"),
                            ("date", "date"),
                            "text",
                        ),
                        step="any",
                        class_name=CONTROL,
                    ),
                ),
            ),
        ),
        rx.cond(
            field["rules"] != "{}",
            rx.el.p(
                field["rules"],
                class_name="font-mono text-[10px] text-[#8a8a7f] break-all",
            ),
        ),
        class_name="flex flex-col gap-2",
        key=field["name"],
    )


def editor_content() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.div(
                rx.el.p(
                    "02 / DOCUMENTO AUTOCONTENIDO",
                    class_name="font-mono text-[10px] tracking-widest text-[#9a7a3d]",
                ),
                rx.el.h1(
                    D.values.get("title", ""),
                    class_name="mt-3 text-3xl font-medium tracking-tight text-[#354132]",
                ),
                rx.el.p(
                    D.schema_note, class_name="mt-3 text-xs text-[#838b74]"
                ),
            ),
            rx.el.div(
                rx.el.p(
                    f"Commit cargado · {D.loaded_commit}",
                    class_name="break-all font-mono text-[10px] text-[#85867e]",
                ),
                rx.el.button(
                    "Git / diff / historial →",
                    on_click=D.open_git,
                    disabled=D.busy,
                    class_name="mt-2 text-xs text-amber-800 hover:underline disabled:opacity-50",
                ),
            ),
            rx.el.span(
                rx.cond(
                    D.modified.length() > 0,
                    "● Cambios sin guardar",
                    "✓ Sin cambios locales",
                ),
                class_name="text-xs text-amber-700",
            ),
            class_name="flex flex-wrap items-end justify-between gap-4 pb-6",
        ),
        rx.el.fieldset(
            rx.el.div(
                rx.el.section(
                    rx.el.h2(
                        "Frontmatter / esquema",
                        class_name="border-b border-[#dcd8ce] pb-4 text-sm font-semibold text-[#434a40]",
                    ),
                    rx.el.p(
                        f"UUID · {D.document_uuid}",
                        class_name="break-all font-mono text-[10px] text-[#85867e]",
                    ),
                    select_control(
                        "Tipo de contenido",
                        D.types,
                        D.values.get("type", ""),
                        D.select_type,
                    ),
                    rx.foreach(D.fields, schema_field),
                    rx.el.label(
                        "Ruta del archivo",
                        rx.el.input(
                            default_value=D.path,
                            on_change=D.set_path,
                            class_name=CONTROL,
                        ),
                        class_name="flex flex-col gap-2 text-xs text-[#646b60]",
                    ),
                    rx.el.p(
                        "Una ruta distinta mueve el archivo en un único commit. El UUID se conserva.",
                        class_name="text-[10px] leading-5 text-[#85867e]",
                    ),
                    rx.el.details(
                        rx.el.summary(
                            "Metadatos extensibles · JSON",
                            class_name="cursor-pointer text-xs text-[#646b60]",
                        ),
                        rx.el.textarea(
                            default_value=D.extras,
                            on_change=D.set_extras,
                            rows=9,
                            aria_label="Metadatos adicionales JSON",
                            class_name=CONTROL,
                        ),
                        class_name="border-t border-[#dcd8ce] pt-4",
                    ),
                    class_name="flex min-w-0 flex-col gap-5 bg-[#f5f2ea] p-5 lg:border-r border-[#dcd8ce]",
                ),
                rx.el.section(
                    rx.el.div(
                        rx.el.h2(
                            "Cuerpo Markdown",
                            class_name="text-sm font-semibold text-[#434a40]",
                        ),
                        rx.el.span(
                            ".MD / UTF-8",
                            class_name="font-mono text-[10px] text-[#8a8a7f]",
                        ),
                        class_name="flex items-center justify-between border-b border-[#dcd8ce] px-5 py-4",
                    ),
                    rx.el.textarea(
                        default_value=D.body,
                        on_change=D.set_body,
                        placeholder="Escribe el contenido en Markdown…",
                        aria_label="Cuerpo Markdown",
                        spell_check=False,
                        class_name="min-h-[560px] w-full flex-1 resize-y bg-[#fffdf8] p-6 font-mono text-sm leading-7 text-[#3f4839] focus:outline-hidden",
                    ),
                    rx.el.p(
                        "El contenido y sus metadatos se guardan juntos. Abre Validación / Preview tras guardar para revisar el archivo real de GitHub.",
                        class_name="border-t border-[#dcd8ce] p-4 text-[11px] text-[#8a8a7f]",
                    ),
                    class_name="flex min-w-0 flex-col bg-[#fffdf8]",
                ),
                class_name="grid w-full grid-cols-1 border border-[#dcd8ce] lg:grid-cols-[minmax(280px,0.8fr)_minmax(0,1.7fr)]",
            ),
            disabled=D.busy,
            class_name="min-w-0 w-full",
        ),
        rx.el.footer(
            rx.el.div(
                rx.el.p(
                    "RESUMEN DE CAMBIOS",
                    class_name="font-mono text-[10px] text-[#9a7a3d]",
                ),
                rx.el.p(
                    rx.cond(
                        D.modified.length() > 0,
                        D.modified.join(" · "),
                        "Ningún campo modificado",
                    ),
                    class_name="mt-2 text-xs text-[#646b60]",
                ),
                class_name="flex-1 min-w-0",
            ),
            rx.el.button(
                rx.icon("scan-line", class_name="h-4 w-4"),
                "Validación / Preview",
                on_click=D.open_preview,
                disabled=D.busy,
                class_name=BUTTON,
            ),
            rx.el.button(
                rx.icon("copy", class_name="h-4 w-4"),
                "Duplicar",
                on_click=D.duplicate,
                disabled=D.busy,
                class_name=BUTTON,
            ),
            rx.el.button(
                rx.icon("archive", class_name="h-4 w-4"),
                "Archivar",
                on_click=D.save("archived"),
                disabled=D.busy | (D.sha == ""),
                class_name=BUTTON,
            ),
            rx.el.button(
                "Guardar estado seleccionado",
                on_click=D.save("current"),
                disabled=D.busy,
                class_name=BUTTON,
            ),
            rx.el.button(
                rx.icon("save", class_name="h-4 w-4"),
                rx.cond(D.busy, "Guardando…", "Guardar borrador"),
                on_click=D.save("draft"),
                disabled=D.busy,
                class_name="flex items-center justify-center gap-2 bg-[#35413c] px-5 py-2 text-xs text-white hover:bg-[#4b5950] disabled:opacity-50",
            ),
            class_name="mt-5 flex flex-wrap items-center gap-3 border-y border-[#dcd8ce] py-5",
        ),
        rx.el.p(
            "Cada guardado crea un commit y actualiza la referencia remota (commit + push real). Guardar borrador establece draft. Archivar conserva el archivo y guarda las ediciones actuales. No hay sobrescritura forzada.",
            class_name="py-4 text-[11px] leading-5 text-[#85867e]",
        ),
        class_name="w-full",
    )


def document_page() -> rx.Component:
    return rx.el.div(
        sidebar(),
        rx.el.main(
            rx.el.header(
                rx.el.button(
                    rx.icon("arrow-left", class_name="h-4 w-4"),
                    "Biblioteca / Documento",
                    on_click=D.leave,
                    class_name="flex items-center gap-3 text-xs text-[#636e56]",
                ),
                rx.el.span(
                    f"{D.repository} · {D.branch}",
                    class_name="font-mono text-[10px] text-[#858e73] break-all",
                ),
                class_name="flex flex-wrap items-center justify-between gap-3 border-b border-[#dcd8ce] px-5 md:px-9 py-5",
            ),
            rx.el.div(
                rx.cond(
                    D.error != "",
                    rx.el.div(
                        rx.el.p(D.error),
                        rx.el.button(
                            "Recargar GitHub (descarta cambios locales)",
                            on_click=D.load,
                            disabled=D.busy,
                            class_name="mt-3 underline",
                        ),
                        role="alert",
                        class_name="mb-5 border border-red-200 bg-red-50 p-4 text-xs leading-5 text-red-700",
                    ),
                ),
                rx.cond(
                    D.message != "",
                    rx.el.div(
                        D.message,
                        role="status",
                        class_name="mb-5 border border-green-200 bg-green-50 p-4 text-xs text-green-700",
                    ),
                ),
                rx.cond(
                    D.ready,
                    editor_content(),
                    rx.el.div(
                        rx.icon(
                            "loader-circle",
                            class_name=rx.cond(
                                D.busy,
                                "h-6 w-6 animate-spin text-amber-600",
                                "h-6 w-6 text-amber-600",
                            ),
                        ),
                        rx.el.p(
                            rx.cond(
                                D.busy,
                                "Leyendo documento y esquemas de GitHub…",
                                "Documento no disponible",
                            )
                        ),
                        class_name="flex min-h-64 items-center justify-center gap-4 text-sm text-[#646b60]",
                    ),
                ),
                class_name="w-full px-5 md:px-9 pt-8",
            ),
            rx.cond(
                D.confirm_leave,
                rx.el.div(
                    rx.el.div(
                        rx.el.h2(
                            "Hay cambios sin guardar",
                            class_name="text-lg text-[#354132]",
                        ),
                        rx.el.p(
                            "Salir descartará los cambios locales. GitHub no se modificará.",
                            class_name="my-5 text-sm text-[#74796c]",
                        ),
                        rx.el.div(
                            rx.el.button(
                                "Seguir editando",
                                on_click=D.cancel_leave,
                                class_name=BUTTON,
                            ),
                            rx.el.a(
                                "Salir sin guardar", href="/", class_name=BUTTON
                            ),
                            class_name="flex gap-3",
                        ),
                        class_name="max-w-md border border-[#dcd8ce] bg-[#faf9f3] p-6",
                    ),
                    class_name="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4",
                ),
            ),
            class_name="flex-1 w-full min-w-0 overflow-y-auto bg-[#faf9f3]",
        ),
        class_name="flex h-dvh w-full flex-col md:flex-row overflow-hidden font-['Inter'] text-[#3f4839] bg-[#faf9f3]",
    )
