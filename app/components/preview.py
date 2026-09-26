import reflex as rx

from app.components.library import sidebar, select_control
from app.components.document import BUTTON
from app.states.preview import PreviewState as P


def issue_card(issue: dict[str, str]) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("circle-alert", class_name="h-4 w-4 shrink-0"),
            rx.el.span(
                issue["level"], class_name="uppercase font-mono text-[10px]"
            ),
            rx.el.span(issue["category"], class_name="ml-auto text-[10px]"),
            class_name=rx.cond(
                issue["level"] == "error",
                "flex items-center gap-2 text-red-700",
                "flex items-center gap-2 text-[#697864]",
            ),
        ),
        rx.el.p(
            issue["field"],
            class_name="mt-3 break-all font-mono text-[10px] text-[#9a7a3d]",
        ),
        rx.el.p(
            issue["message"], class_name="mt-1 text-xs leading-5 text-[#555e52]"
        ),
        class_name="border-b border-[#dcd8ce] p-4 bg-[#fffdf8]",
    )


def validation_panel() -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            rx.el.div(
                rx.icon("list-checks", class_name="h-4 w-4 text-amber-700"),
                rx.el.h2(
                    "Control editorial",
                    class_name="text-sm font-semibold text-[#394039]",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.p(
                "ESTRUCTURA / EDICIÓN / REFERENCIAS",
                class_name="mt-2 font-mono text-[9px] text-[#85867e]",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.p(
                        P.errors, class_name="text-2xl font-mono text-red-700"
                    ),
                    rx.el.p("Errores", class_name="text-[10px] text-[#737671]"),
                ),
                rx.el.div(
                    rx.el.p(
                        P.warnings,
                        class_name="text-2xl font-mono text-amber-700",
                    ),
                    rx.el.p("Avisos", class_name="text-[10px] text-[#737671]"),
                ),
                rx.el.div(
                    rx.el.p(
                        P.issues.length(),
                        class_name="text-2xl font-mono text-[#35413c]",
                    ),
                    rx.el.p(
                        "Resultados", class_name="text-[10px] text-[#737671]"
                    ),
                ),
                class_name="grid grid-cols-3 gap-3 mt-5",
            ),
            rx.el.p(
                rx.cond(P.valid, "✓ Apto para avanzar", "Avance bloqueado"),
                class_name=rx.cond(
                    P.valid,
                    "mt-5 text-xs font-semibold text-green-700",
                    "mt-5 text-xs font-semibold text-red-700",
                ),
            ),
            rx.el.p(
                "Todas las comprobaciones se aplican al archivo guardado y al esquema de la misma versión del repositorio.",
                class_name="mt-2 text-[11px] leading-5 text-[#85867e]",
            ),
            class_name="p-5 border-b border-[#dcd8ce] bg-[#f1eee6]",
        ),
        rx.foreach(P.issues, issue_card),
        class_name="min-w-0 border border-[#dcd8ce] self-start",
    )


def tab_button(value: str, title: str, number: str) -> rx.Component:
    return rx.el.button(
        rx.el.span(number, class_name="font-mono text-[10px] opacity-60"),
        title,
        on_click=P.set_tab(value),
        role="tab",
        aria_selected=P.tab == value,
        class_name=rx.cond(
            P.tab == value,
            "flex flex-1 items-center justify-center gap-2 border-b-2 border-amber-600 bg-[#fffdf8] px-3 py-4 text-xs font-semibold text-[#35413c]",
            "flex flex-1 items-center justify-center gap-2 border-b-2 border-transparent bg-[#eeece3] px-3 py-4 text-xs text-[#85867e] hover:bg-[#f6f0e2]",
        ),
    )


def markdown_content(body: str, metadata: str) -> rx.Component:
    return rx.el.div(
        rx.markdown(
            body,
            use_raw=False,
            use_math=False,
            use_katex=False,
            component_map={
                "h1": lambda text: rx.el.h1(
                    text,
                    class_name="mb-6 mt-4 text-3xl font-semibold tracking-tight text-[#35413c]",
                ),
                "h2": lambda text: rx.el.h2(
                    text,
                    class_name="mb-3 mt-7 text-xl font-semibold text-[#35413c]",
                ),
                "h3": lambda text: rx.el.h3(
                    text,
                    class_name="mb-3 mt-6 text-lg font-semibold text-[#35413c]",
                ),
                "p": lambda text: rx.el.p(
                    text, class_name="my-4 text-sm leading-7 text-[#525c50]"
                ),
            },
            class_name="w-full break-words text-[#525c50] [&_table]:table-auto [&_table]:w-full [&_pre]:overflow-x-auto [&_a]:text-amber-700 [&_a]:underline",
        ),
        rx.el.details(
            rx.el.summary(
                "Frontmatter de esta versión",
                class_name="cursor-pointer text-xs text-[#85867e]",
            ),
            rx.el.pre(
                metadata,
                class_name="mt-4 whitespace-pre-wrap break-all font-mono text-[11px] leading-6 text-[#697460]",
            ),
            class_name="mt-10 border-t border-[#dcd8ce] pt-4",
        ),
        class_name="min-h-96 px-6 py-6 md:px-10 md:py-8 bg-[#fffdf8]",
    )


def preview_panel() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            tab_button("stored", "Almacenado", "01"),
            tab_button("validated", "Validado", "02"),
            tab_button("published", "Publicado", "03"),
            role="tablist",
            aria_label="Versión del contenido",
            class_name="hidden sm:flex border-b border-[#dcd8ce]",
        ),
        rx.el.div(
            select_control(
                "Versión de lectura",
                rx.Var.create(["stored", "validated", "published"]),
                P.tab,
                P.set_tab,
            ),
            class_name="sm:hidden p-4 bg-[#f1eee6]",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("layers", class_name="h-4 w-4"),
                rx.el.p(
                    rx.match(
                        P.tab,
                        ("stored", "ALMACENADO · fuente actual"),
                        ("validated", "VALIDADO · control acumulado"),
                        "PUBLICADO · memoria histórica",
                    ),
                    class_name="font-mono text-[10px] tracking-wide",
                ),
                class_name="flex items-center gap-2",
            ),
            rx.el.p(
                rx.match(
                    P.tab,
                    (
                        "stored",
                        "Lectura real de GitHub. Almacenado no significa válido ni publicado.",
                    ),
                    (
                        "validated",
                        "La misma versión almacenada, disponible solo al superar todos los controles.",
                    ),
                    "Último archivo con status published. No representa un despliegue externo ni se sustituye por el borrador actual.",
                ),
                class_name="mt-2 text-xs leading-5 opacity-80",
            ),
            class_name=rx.match(
                P.tab,
                (
                    "stored",
                    "border-b border-[#dcd8ce] bg-[#f1eee6] p-5 text-[#626a61]",
                ),
                (
                    "validated",
                    "border-b border-amber-300 bg-[#f6edda] p-5 text-amber-900",
                ),
                "border-b border-[#35413c] bg-[#35413c] p-5 text-[#fff5df]",
            ),
        ),
        rx.match(
            P.tab,
            ("stored", markdown_content(P.body, P.metadata_text)),
            (
                "validated",
                rx.cond(
                    P.valid,
                    markdown_content(P.body, P.metadata_text),
                    rx.el.div(
                        rx.icon(
                            "shield-alert", class_name="h-9 w-9 text-amber-700"
                        ),
                        rx.el.h3(
                            "Contenido validado no disponible",
                            class_name="text-lg text-[#35413c]",
                        ),
                        rx.el.p(
                            "Resuelve los errores del panel izquierdo, guarda en el editor y vuelve a validar.",
                            class_name="max-w-md text-sm leading-6 text-[#85867e]",
                        ),
                        class_name="flex min-h-96 flex-col items-center justify-center gap-5 p-8 text-center bg-[#fffdf8]",
                    ),
                ),
            ),
            rx.cond(
                P.history_error != "",
                rx.el.div(
                    P.history_error,
                    role="alert",
                    class_name="min-h-96 p-10 text-sm text-red-700 bg-[#fffdf8]",
                ),
                rx.cond(
                    P.published_found,
                    markdown_content(P.published_body, P.published_metadata),
                    rx.el.div(
                        rx.icon(
                            "book-open", class_name="h-9 w-9 text-[#8a8a7f]"
                        ),
                        rx.el.h3(
                            "Todavía no hay versión publicada",
                            class_name="text-lg text-[#35413c]",
                        ),
                        rx.el.p(
                            "El historial de este archivo no contiene ninguna versión con status published.",
                            class_name="max-w-md text-sm leading-6 text-[#85867e]",
                        ),
                        class_name="flex min-h-96 flex-col items-center justify-center gap-5 p-8 text-center bg-[#fffdf8]",
                    ),
                ),
            ),
        ),
        rx.el.div(
            rx.icon("git-commit-horizontal", class_name="h-4 w-4 shrink-0"),
            rx.el.p(
                rx.cond(P.tab == "published", P.published_version, P.version),
                class_name="break-all",
            ),
            class_name="flex gap-2 border-t border-[#dcd8ce] bg-[#f5f2ea] p-4 font-mono text-[10px] text-[#74796c]",
        ),
        class_name="w-full min-w-0 self-start border border-[#dcd8ce]",
    )


def workflow_actions() -> rx.Component:
    return rx.el.footer(
        rx.el.div(
            rx.el.p(
                "SIGUIENTE MOVIMIENTO",
                class_name="font-mono text-[10px] text-[#9a7a3d]",
            ),
            rx.el.p(
                rx.cond(
                    P.blocked,
                    "Transición bloqueada. Resuelve los errores o vuelve a un estado de trabajo.",
                    "Se volverán a verificar el documento, sus referencias y el SHA antes de guardar.",
                ),
                class_name="mt-2 text-xs leading-5 text-[#74796c]",
            ),
            class_name="flex-1 min-w-56",
        ),
        rx.el.div(
            select_control(
                "Cambiar estado a",
                P.transitions,
                P.target,
                P.set_target,
                P.busy,
            ),
            class_name="w-full sm:w-44",
        ),
        rx.el.button(
            rx.icon("git-commit-horizontal", class_name="h-4 w-4"),
            "Confirmar transición · commit + push",
            on_click=P.transition,
            disabled=P.busy | P.blocked,
            class_name="flex h-10 items-center justify-center gap-2 bg-[#35413c] px-5 text-xs text-white hover:bg-[#4b5950] disabled:opacity-40",
        ),
        class_name="mt-6 flex flex-wrap items-end gap-4 border-y border-[#dcd8ce] py-5",
    )


def preview_page() -> rx.Component:
    return rx.el.div(
        sidebar(),
        rx.el.main(
            rx.el.header(
                rx.el.a(
                    rx.icon("arrow-left", class_name="h-4 w-4"),
                    "Volver al editor",
                    href=P.editor_url,
                    class_name="flex items-center gap-2 text-xs text-[#636e56]",
                ),
                rx.el.span(
                    f"{P.repository} · {P.branch}",
                    class_name="break-all font-mono text-[10px] text-[#858e73]",
                ),
                class_name="flex flex-wrap justify-between gap-4 border-b border-[#dcd8ce] px-5 py-5 md:px-9",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.p(
                            "03 / VALIDACIÓN Y PREVIEW",
                            class_name="font-mono text-[10px] tracking-widest text-[#9a7a3d]",
                        ),
                        rx.el.h1(
                            "Del archivo a la lectura",
                            class_name="mt-3 text-3xl font-medium tracking-tight text-[#354132]",
                        ),
                        rx.el.p(
                            P.title, class_name="mt-3 text-sm text-[#838b74]"
                        ),
                    ),
                    rx.el.button(
                        rx.icon(
                            "refresh-cw",
                            class_name=rx.cond(
                                P.busy, "h-4 w-4 animate-spin", "h-4 w-4"
                            ),
                        ),
                        "Releer y validar",
                        on_click=P.load,
                        disabled=P.busy,
                        class_name=BUTTON,
                    ),
                    class_name="flex flex-wrap items-end justify-between gap-4 mb-6",
                ),
                rx.cond(
                    P.error != "",
                    rx.el.div(
                        P.error,
                        role="alert",
                        class_name="mb-5 border border-red-200 bg-red-50 p-4 text-xs text-red-700",
                    ),
                ),
                rx.cond(
                    P.message != "",
                    rx.el.div(
                        P.message,
                        role="status",
                        class_name="mb-5 border border-green-200 bg-green-50 p-4 text-xs text-green-700",
                    ),
                ),
                rx.cond(
                    P.busy,
                    rx.el.div(
                        rx.icon(
                            "loader-circle",
                            class_name="h-6 w-6 animate-spin text-amber-600",
                        ),
                        "Leyendo GitHub, esquemas e historial…",
                        role="status",
                        class_name="flex min-h-64 items-center justify-center gap-4 text-sm text-[#74796c]",
                    ),
                    rx.cond(
                        P.ready,
                        rx.el.div(
                            rx.el.div(
                                rx.el.div(
                                    rx.el.label(
                                        "Documento guardado",
                                        html_for="preview-document",
                                        class_name="font-mono text-[10px] text-[#85867e]",
                                    ),
                                    rx.el.div(
                                        rx.el.select(
                                            rx.foreach(
                                                P.document_options,
                                                lambda doc: rx.el.option(
                                                    doc["title"],
                                                    value=doc["id"],
                                                ),
                                            ),
                                            value=P.identifier,
                                            on_change=P.select_document,
                                            id="preview-document",
                                            class_name="mt-2 h-10 w-full appearance-none border border-[#dcd8ce] bg-[#fffdf8] pl-3 pr-8 text-xs text-[#424942]",
                                        ),
                                        rx.icon(
                                            "chevron-down",
                                            class_name="pointer-events-none absolute right-3 top-5 h-3 w-3 text-[#74796c]",
                                        ),
                                        class_name="relative",
                                    ),
                                    class_name="w-full lg:w-72",
                                ),
                                rx.el.div(
                                    rx.foreach(
                                        rx.Var.create(
                                            [
                                                "draft",
                                                "review",
                                                "approved",
                                                "published",
                                                "archived",
                                            ]
                                        ),
                                        lambda step: rx.el.span(
                                            step,
                                            class_name=rx.cond(
                                                P.status == step,
                                                "border-b-2 border-amber-600 px-3 py-3 font-mono text-xs font-semibold text-amber-800",
                                                "border-b border-[#dcd8ce] px-3 py-3 font-mono text-xs text-[#85867e]",
                                            ),
                                        ),
                                    ),
                                    class_name="flex flex-wrap items-center",
                                ),
                                class_name="flex flex-wrap items-end justify-between gap-5 border-y border-[#dcd8ce] py-5 mb-6",
                            ),
                            rx.el.p(
                                f"{P.path} · blob {P.sha}",
                                class_name="mb-4 break-all font-mono text-[10px] text-[#85867e]",
                            ),
                            rx.el.a(
                                "Git / diff / historial del documento →",
                                href=P.git_url,
                                class_name="mb-5 block text-xs text-amber-800 hover:underline",
                            ),
                            rx.el.div(
                                validation_panel(),
                                preview_panel(),
                                class_name="grid grid-cols-1 gap-5 xl:grid-cols-[300px_minmax(0,1fr)]",
                            ),
                            workflow_actions(),
                            rx.el.p(
                                "GitHub canónico · Sin publicación externa · HTML crudo desactivado · Cada pestaña conserva su versión",
                                class_name="py-5 font-mono text-[10px] text-[#85867e]",
                            ),
                        ),
                        rx.el.a(
                            "Volver a Biblioteca",
                            href="/",
                            class_name="text-sm text-amber-700 underline",
                        ),
                    ),
                ),
                class_name="w-full px-5 pt-8 md:px-9",
            ),
            class_name="flex-1 w-full min-w-0 overflow-y-auto bg-[#faf9f3]",
        ),
        class_name="flex h-dvh w-full flex-col md:flex-row overflow-hidden font-['Inter'] text-[#3f4839] bg-[#faf9f3]",
    )
