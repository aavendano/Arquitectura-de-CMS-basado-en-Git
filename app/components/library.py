import reflex as rx

from app.states.library import LibraryState as S


def nav_item(label: str, icon: str, number: str) -> rx.Component:
    return rx.el.button(
        rx.icon(icon, class_name="h-4 w-4 shrink-0"),
        rx.el.span(label, class_name="flex-1 text-left whitespace-nowrap"),
        rx.el.span(number, class_name="font-mono text-[10px] opacity-50"),
        on_click=S.navigate(label),
        class_name=rx.cond(
            S.section == label,
            "flex w-full items-center gap-3 border-l-2 border-amber-600 bg-[#ebe6dc] px-4 py-3 text-sm font-semibold text-[#353b3b] transition-colors",
            "flex w-full items-center gap-3 border-l-2 border-transparent px-4 py-3 text-sm text-[#737671] hover:bg-[#eeeae2] transition-colors",
        ),
    )


def sidebar() -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            rx.el.div(
                rx.icon("notebook-pen", class_name="h-6 w-6"),
                class_name="flex h-10 w-10 items-center justify-center bg-[#343c3b] text-[#f5ebd6]",
            ),
            rx.el.div(
                rx.el.p(
                    "FOLIO",
                    class_name="text-lg font-semibold tracking-[0.16em] text-[#333b3a]",
                ),
                rx.el.p(
                    "MESA DE EDICIÓN",
                    class_name="font-mono text-[9px] tracking-widest text-[#84847b]",
                ),
            ),
            class_name="flex items-center gap-3 border-b border-[#dcd8ce] px-6 py-7",
        ),
        rx.el.div(
            rx.el.span(
                "ESPACIO EDITORIAL",
                class_name="font-mono text-[10px] tracking-widest text-[#96958c]",
            ),
            class_name="px-7 pb-3 pt-8 hidden md:block",
        ),
        rx.el.nav(
            nav_item("Biblioteca", "library", "01"),
            nav_item("Esquemas", "braces", "02"),
            nav_item("Validación / Preview", "scan-line", "03"),
            nav_item("Operaciones Git", "git-pull-request", "04"),
            class_name="flex flex-col gap-1 px-3 py-3 md:py-0 min-h-0 overflow-y-auto",
        ),
        rx.el.div(
            rx.el.div(
                rx.icon("git_fork", class_name="h-4 w-4"),
                "GITHUB · FUENTE CANÓNICA",
                class_name="flex items-center gap-2 font-mono text-[10px] tracking-wide text-[#646b64]",
            ),
            rx.el.p(
                "El repositorio es la fuente. Esta mesa es tu espacio de edición.",
                class_name="mt-3 text-xs leading-5 text-[#85867e]",
            ),
            rx.el.div(
                rx.el.span(
                    class_name=rx.cond(
                        S.connected,
                        "h-1.5 w-1.5 rounded-full bg-green-500",
                        "h-1.5 w-1.5 rounded-full bg-amber-500",
                    )
                ),
                rx.cond(
                    S.connected, "Conexión disponible", "Conexión pendiente"
                ),
                class_name="mt-5 flex items-center gap-2 text-xs text-[#656c65]",
            ),
            class_name="mt-auto border-t border-[#dcd8ce] px-6 py-6 hidden md:block",
        ),
        class_name="flex w-full shrink-0 flex-col border-b md:border-b-0 md:border-r border-[#dcd8ce] bg-[#f1eee6] md:w-60 md:h-full",
    )


def select_control(
    label: str,
    options: list[str],
    value: str,
    handler: rx.event.EventType,
    disabled: bool = False,
) -> rx.Component:
    return rx.el.label(
        rx.el.span(
            label,
            class_name="text-[10px] uppercase tracking-widest font-mono text-[#8a8a7f]",
        ),
        rx.el.div(
            rx.el.select(
                rx.cond(
                    options.length() == 0,
                    rx.el.option("No disponible", value=""),
                ),
                rx.foreach(
                    options, lambda option: rx.el.option(option, value=option)
                ),
                value=value,
                on_change=handler,
                disabled=disabled,
                aria_label=label,
                class_name="h-10 w-full appearance-none rounded-sm border border-[#dcd8ce] bg-[#fffdf8] pl-3 pr-8 text-xs text-[#424942] focus:outline-none focus:ring-2 focus:ring-amber-500/30 disabled:opacity-50",
            ),
            rx.icon(
                "chevron-down",
                class_name="pointer-events-none absolute right-3 top-3.5 h-3 w-3 text-[#7c8178]",
            ),
            class_name="relative w-full",
        ),
        class_name="flex min-w-0 flex-col gap-2",
    )


def repository_bar() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.icon("folder-git-2", class_name="h-5 w-5 text-[#757d72]"),
            class_name="hidden lg:flex h-10 w-10 items-center justify-center border border-[#dcd8ce] bg-[#f1eee6] mt-6",
        ),
        rx.el.div(
            select_control(
                "Repositorio",
                S.repositories,
                S.repository,
                S.select_repository,
                S.busy,
            ),
            class_name="min-w-0 flex-1",
        ),
        rx.el.div(
            select_control(
                "Rama activa", S.branches, S.branch, S.select_branch, S.busy
            ),
            class_name="w-full sm:w-44",
        ),
        rx.el.div(
            rx.el.span(
                "ÚLTIMA LECTURA",
                class_name="font-mono text-[10px] tracking-widest text-[#8a8a7f]",
            ),
            rx.el.p(
                S.synced_at, class_name="mt-3 text-xs text-[#626a61] font-mono"
            ),
            class_name="hidden xl:block px-5",
        ),
        rx.el.button(
            rx.icon(
                "refresh-cw",
                class_name=rx.cond(S.busy, "h-4 w-4 animate-spin", "h-4 w-4"),
            ),
            rx.cond(S.busy, "Leyendo…", "Sincronizar"),
            on_click=S.connect,
            disabled=S.busy,
            class_name="mt-6 flex h-10 shrink-0 items-center justify-center gap-2 rounded-sm bg-[#35413c] px-5 text-xs font-medium text-white hover:bg-[#4b5950] disabled:opacity-60 transition-colors",
        ),
        class_name="flex flex-col sm:flex-row sm:items-end gap-4 border-y border-[#dcd8ce] py-5",
    )


def operation_step(
    number: str,
    icon: str,
    title: str,
    description: str,
    status: str,
    active: bool,
) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(
                number, class_name="font-mono text-[10px] text-[#95978b]"
            ),
            rx.icon(
                icon,
                class_name=rx.cond(
                    active, "h-5 w-5 text-[#a97623]", "h-5 w-5 text-[#a5a79d]"
                ),
            ),
            class_name="flex items-center justify-between",
        ),
        rx.el.h3(title, class_name="mt-4 text-sm font-semibold text-[#394039]"),
        rx.el.p(
            description, class_name="mt-1 text-[11px] leading-5 text-[#888a7e]"
        ),
        rx.el.div(
            rx.el.span(
                class_name=rx.cond(
                    active,
                    "h-1.5 w-1.5 rounded-full bg-amber-600",
                    "h-1.5 w-1.5 rounded-full bg-[#b6b8ae]",
                )
            ),
            status,
            class_name="mt-4 flex items-center gap-2 font-mono text-[10px] text-[#73786d]",
        ),
        class_name=rx.cond(
            active,
            "relative flex-1 min-w-0 bg-[#f6f0e2] border-t-2 border-amber-600 px-5 py-4",
            "relative flex-1 min-w-0 bg-[#f1f1e9] border-t-2 border-[#cfd1c5] px-5 py-4",
        ),
    )


def pipeline() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.h2(
                "Del repositorio a la lectura",
                class_name="text-sm font-semibold text-[#434a40]",
            ),
            rx.el.span(
                "CIRCUITO EDITORIAL / 01",
                class_name="font-mono text-[10px] tracking-wider text-[#8d8f82]",
            ),
            class_name="flex flex-wrap items-center justify-between gap-2 mb-4",
        ),
        rx.el.div(
            operation_step(
                "01",
                "git_fork",
                "GitHub",
                "Fuente canónica · content/",
                rx.cond(
                    S.connected, "Conectado · lectura", "Pendiente de conexión"
                ),
                S.connected,
            ),
            rx.icon(
                "arrow-right",
                class_name="hidden lg:block h-4 w-4 shrink-0 text-[#a5a68f]",
            ),
            operation_step(
                "02",
                "files",
                "Índice editorial",
                "Markdown + frontmatter YAML",
                rx.cond(
                    S.busy,
                    "Leyendo repositorio…",
                    rx.cond(
                        S.indexed,
                        f"{S.documents.length()} documentos leídos",
                        "Sin índice",
                    ),
                ),
                S.indexed,
            ),
            rx.icon(
                "arrow-right",
                class_name="hidden lg:block h-4 w-4 shrink-0 text-[#a5a68f]",
            ),
            operation_step(
                "03",
                "list-checks",
                "Validación",
                "Solo lectura sintáctica de YAML",
                rx.cond(
                    S.indexed,
                    rx.cond(
                        S.errors > 0,
                        f"{S.errors} errores de lectura",
                        "Sin errores de lectura",
                    ),
                    "Pendiente de índice",
                ),
                S.indexed,
            ),
            rx.icon(
                "arrow-right",
                class_name="hidden lg:block h-4 w-4 shrink-0 text-[#a5a68f]",
            ),
            operation_step(
                "04",
                "panel-top",
                "Preview",
                "Stored · Validated · Published",
                "Disponible por documento",
                S.indexed,
            ),
            class_name="grid grid-cols-1 sm:grid-cols-2 lg:flex items-center gap-3",
        ),
        rx.el.p(
            "Un YAML legible no equivale a contenido validado o publicado. El estado editorial procede del documento.",
            class_name="mt-3 text-[11px] text-[#8a8d80]",
        ),
        class_name="py-7",
    )


def stat(label: str, value: str, icon: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.span(label, class_name="text-xs text-[#828679]"),
            rx.icon(icon, class_name="h-4 w-4 text-[#989e8e]"),
            class_name="flex justify-between items-center",
        ),
        rx.el.p(
            value,
            class_name="mt-2 text-2xl font-medium tracking-tight text-[#3c453a] font-mono",
        ),
        class_name="px-5 py-4 border-r last:border-r-0 border-[#dcd8ce] bg-[#fffdf8] w-full",
    )


def filters() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(
                "search",
                class_name="absolute left-3 top-3 h-4 w-4 text-[#8f9288]",
            ),
            rx.el.input(
                placeholder="Buscar título o ruta…",
                default_value=S.search,
                on_change=S.set_search.debounce(350),
                aria_label="Buscar documentos",
                class_name="w-full h-10 bg-[#fffdf8] text-xs text-[#424942] rounded-sm border border-[#dcd8ce] pl-10 pr-3 focus:outline-none focus:ring-2 focus:ring-amber-500/30",
            ),
            class_name="relative min-w-0 lg:col-span-2 self-end",
        ),
        select_control("Tipo", S.types, S.kind, S.set_kind),
        select_control("Estado", S.statuses, S.status, S.set_status),
        select_control("Locale", S.locales, S.locale, S.set_locale),
        select_control(
            "Cambios",
            rx.Var.create(
                ["Todos", "Sin comparar", "Sin cambios", "Nuevo", "Modificado"]
            ),
            S.changes,
            S.set_changes,
        ),
        class_name="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 items-end gap-3 py-5",
    )


def document_row(doc: dict[str, str]) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.el.div(
                rx.icon(
                    "file-text", class_name="h-4 w-4 shrink-0 text-[#929881]"
                ),
                rx.el.div(
                    rx.el.a(
                        doc["title"],
                        href=doc["href"],
                        class_name="font-medium text-[#3d463a] break-words hover:text-amber-700 underline-offset-4 hover:underline",
                    ),
                    rx.el.a(
                        "Validar / Preview →",
                        href=doc["preview_href"],
                        class_name="mt-2 block text-[10px] text-amber-700 hover:underline",
                    ),
                    rx.el.a(
                        "Git / diff / historial →",
                        href=doc.get("git_href", "/git"),
                        class_name="mt-2 block text-[10px] text-amber-700 hover:underline",
                    ),
                    rx.el.p(
                        doc["path"],
                        class_name="mt-1 font-mono text-[10px] text-[#929585] break-all",
                    ),
                ),
                class_name="flex items-start gap-3",
            ),
            class_name="px-4 py-4 min-w-56",
        ),
        rx.el.td(doc["type"], class_name="p-4 text-[#6c7563]"),
        rx.el.td(
            rx.el.span(
                doc["status"],
                class_name="inline-block w-fit border border-[#dddccc] bg-[#f3f0e5] px-2 py-1 rounded-sm text-[10px] text-[#6f715c]",
            ),
            class_name="p-4",
        ),
        rx.el.td(
            doc["locale"], class_name="p-4 font-mono text-[11px] text-[#7a816e]"
        ),
        rx.el.td(
            rx.el.details(
                rx.el.summary(
                    rx.el.span(
                        doc["validation"],
                        class_name=rx.cond(
                            doc["validation"] == "Legible",
                            "text-[#587458]",
                            "text-red-500",
                        ),
                    ),
                    class_name="cursor-pointer text-[11px] whitespace-nowrap",
                ),
                rx.el.p(
                    doc["detail"],
                    class_name="mt-2 max-w-60 text-[11px] leading-5 text-[#7a816e]",
                ),
            ),
            class_name="p-4",
        ),
        rx.el.td(
            doc["date"],
            class_name="p-4 text-[10px] font-mono text-[#7a816e] max-w-44 break-words",
        ),
        rx.el.td(
            doc["change"],
            class_name="p-4 text-[10px] text-[#8a7952] whitespace-nowrap",
        ),
        class_name="border-t border-[#e5e3d8] odd:bg-[#fffdf8] even:bg-[#f9f8f1] hover:bg-[#f5efdf] transition-colors text-xs align-top",
        key=doc["path"],
    )


def table_header(label: str, icon: str) -> rx.Component:
    return rx.el.th(
        rx.el.div(
            rx.icon(icon, class_name="h-3 w-3"),
            label,
            class_name="flex gap-2 items-center",
        ),
        class_name="px-4 py-3 text-left font-normal text-[10px] text-[#8a8f7d] uppercase tracking-wider whitespace-nowrap",
    )


def empty_state(icon: str, title: str, description: str) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon(icon, class_name="h-7 w-7 text-[#9a9f87]"),
            class_name="mb-5 flex h-16 w-16 items-center justify-center rounded-full border border-[#dedfd0] bg-[#f4f3e9]",
        ),
        rx.el.h3(title, class_name="text-base font-medium text-[#4b5442]"),
        rx.el.p(
            description,
            class_name="mt-2 text-xs leading-6 text-[#8a8f7d] max-w-md",
        ),
        class_name="flex flex-col items-center justify-center text-center px-6 py-14 bg-[#fffdf8]",
    )


def document_table() -> rx.Component:
    return rx.el.section(
        rx.el.div(
            rx.el.div(
                rx.el.h2(
                    "Documentos",
                    class_name="text-base font-semibold text-[#404a39]",
                ),
                rx.el.span(
                    f"{S.filtered.length()}",
                    class_name="rounded-sm bg-[#e9eade] px-2 py-0.5 font-mono text-xs text-[#798167]",
                ),
                class_name="flex items-center gap-3",
            ),
            rx.el.button(
                rx.icon("plus", class_name="h-4 w-4"),
                "Crear documento",
                on_click=S.create_document,
                disabled=S.busy | (S.branch == ""),
                class_name="ml-auto flex items-center gap-2 rounded-sm bg-[#35413c] px-4 py-2 text-xs text-white hover:bg-[#4b5950] disabled:opacity-50",
            ),
            rx.el.button(
                rx.icon("filter-x", class_name="h-3.5 w-3.5"),
                "Limpiar filtros",
                on_click=S.clear_filters,
                class_name="flex items-center gap-2 text-xs text-[#7e876d] hover:text-amber-700",
            ),
            class_name="flex items-center justify-between gap-4 pt-7",
        ),
        filters(),
        rx.el.div(
            rx.cond(
                S.busy,
                rx.el.div(
                    rx.icon(
                        "loader-circle",
                        class_name="h-6 w-6 animate-spin text-amber-600",
                    ),
                    rx.el.p(S.progress, class_name="text-sm text-[#6e7861]"),
                    rx.el.div(
                        class_name="h-2 w-60 bg-[#e8e8dc] rounded-full animate-pulse"
                    ),
                    class_name="flex min-h-60 flex-col items-center justify-center gap-5 bg-[#fffdf8]",
                ),
                rx.cond(
                    S.filtered.length() > 0,
                    rx.el.div(
                        rx.el.table(
                            rx.el.thead(
                                rx.el.tr(
                                    table_header(
                                        "Documento / ruta", "file-text"
                                    ),
                                    table_header("Tipo", "shapes"),
                                    table_header("Estado", "circle-dot"),
                                    table_header("Locale", "languages"),
                                    table_header("Lectura YAML", "check-check"),
                                    table_header("Fecha¹", "calendar-days"),
                                    table_header(
                                        "Cambios²", "git-compare-arrows"
                                    ),
                                ),
                                class_name="bg-[#f3f3e9]",
                            ),
                            rx.el.tbody(rx.foreach(S.filtered, document_row)),
                            class_name="table-auto w-full",
                        ),
                        class_name="overflow-x-auto",
                    ),
                    rx.cond(
                        S.indexed,
                        rx.cond(
                            S.documents.length() > 0,
                            empty_state(
                                "search-x",
                                "Sin coincidencias",
                                "Prueba otro término o limpia los filtros para ver todos los documentos.",
                            ),
                            rx.cond(
                                S.has_content,
                                empty_state(
                                    "files",
                                    "La carpeta content/ está vacía de documentos",
                                    "No se encontraron archivos .md o .markdown en esta rama. Añade documentos con frontmatter YAML en GitHub y sincroniza.",
                                ),
                                empty_state(
                                    "folder-open",
                                    "Este repositorio aún no tiene content/",
                                    "Selecciona otro repositorio o añade una carpeta content/ con documentos Markdown y frontmatter YAML en GitHub. Aquí no se generan documentos de ejemplo.",
                                ),
                            ),
                        ),
                        empty_state(
                            "folder-git-2",
                            "Tu biblioteca empieza en GitHub",
                            "Selecciona un repositorio accesible para leer sus documentos. Si no hay repositorios, comprueba los permisos de la conexión.",
                        ),
                    ),
                ),
            ),
            class_name="overflow-hidden rounded-sm border border-[#dcd8ce]",
        ),
        rx.el.div(
            rx.el.span(
                f"{S.filtered.length()} de {S.documents.length()} documentos"
            ),
            rx.el.span(
                "CONTENT/ · .MD / .MARKDOWN",
                class_name="font-mono text-[9px] tracking-wider",
            ),
            class_name="flex items-center justify-between mt-3 text-[10px] text-[#8a907b]",
        ),
        rx.el.p(
            "¹ Fecha declarada en updated_at o date; — si no está disponible. ² Cambios remotos desde la lectura anterior de esta rama en esta sesión, no cambios locales. La primera lectura no tiene comparación.",
            class_name="mt-4 text-[10px] leading-5 text-[#929683]",
        ),
        rx.cond(
            S.deleted > 0,
            rx.el.p(
                f"{S.deleted} documentos eliminados desde la lectura anterior; ya no forman parte del índice.",
                class_name="mt-2 text-xs text-amber-700",
            ),
        ),
    )


def workspace() -> rx.Component:
    return rx.el.div(
        sidebar(),
        rx.el.main(
            rx.el.header(
                rx.el.div(
                    rx.el.span(
                        "ESPACIO DE TRABAJO",
                        class_name="font-mono text-[9px] tracking-[0.14em] text-[#979c88]",
                    ),
                    rx.el.span("/", class_name="text-[#bdc0ac]"),
                    rx.el.span(S.section, class_name="text-xs text-[#636e56]"),
                    class_name="flex items-center gap-3",
                ),
                rx.el.div(
                    rx.icon("lock-keyhole", class_name="h-3 w-3"),
                    "Edición conectada",
                    class_name="flex items-center gap-2 text-[10px] font-mono text-[#858e73]",
                ),
                class_name="flex shrink-0 items-center justify-between gap-3 border-b border-[#dcd8ce] px-5 md:px-9 py-5",
            ),
            rx.el.div(
                rx.el.div(
                    rx.el.div(
                        rx.el.p(
                            "01 / ARCHIVO EDITORIAL",
                            class_name="font-mono text-[10px] tracking-[0.17em] text-[#9a7a3d]",
                        ),
                        rx.el.h1(
                            S.section,
                            class_name="mt-3 text-3xl md:text-4xl font-medium tracking-[-0.045em] text-[#354132]",
                        ),
                        rx.el.p(
                            "Contenido versionado. Una fuente, una lectura clara.",
                            class_name="mt-3 text-sm text-[#838b74]",
                        ),
                    ),
                    rx.el.div(
                        rx.el.span(
                            class_name=rx.cond(
                                S.error != "",
                                "h-2 w-2 rounded-full bg-red-500",
                                rx.cond(
                                    S.busy,
                                    "h-2 w-2 rounded-full bg-amber-500 animate-pulse",
                                    "h-2 w-2 rounded-full bg-[#8a9c76]",
                                ),
                            )
                        ),
                        rx.cond(
                            S.error != "", "Lectura interrumpida", S.progress
                        ),
                        class_name="flex items-center gap-2 text-[11px] text-[#7b866b]",
                    ),
                    class_name="flex flex-wrap items-end justify-between gap-5 mb-7",
                ),
                repository_bar(),
                rx.cond(
                    S.error != "",
                    rx.el.div(
                        rx.icon(
                            "triangle-alert",
                            class_name="h-4 w-4 shrink-0 text-red-500",
                        ),
                        rx.el.div(
                            rx.el.p(S.error),
                            rx.cond(
                                S.indexed,
                                rx.el.p(
                                    "Se conserva el último índice completo. Puede estar desactualizado.",
                                    class_name="mt-1 font-medium",
                                ),
                            ),
                        ),
                        role="alert",
                        class_name="mt-5 flex gap-3 border border-red-200 bg-red-50 px-4 py-3 text-xs leading-5 text-red-700",
                    ),
                ),
                pipeline(),
                rx.cond(
                    (S.section == "Biblioteca")
                    | (S.section == "Validación / Preview"),
                    rx.el.div(
                        rx.el.div(
                            stat(
                                "Documentos indexados",
                                S.documents.length().to_string(),
                                "files",
                            ),
                            stat(
                                "Tipos de contenido",
                                (S.types.length() - 1).to_string(),
                                "shapes",
                            ),
                            stat(
                                "Errores de lectura",
                                S.errors.to_string(),
                                "file-warning",
                            ),
                            stat(
                                "Nuevos / modificados",
                                S.changed.to_string(),
                                "git-compare-arrows",
                            ),
                            class_name="grid grid-cols-2 md:grid-cols-4 border border-[#dcd8ce]",
                        ),
                        document_table(),
                    ),
                    empty_state(
                        "construction",
                        "Sección preparada · próxima fase",
                        rx.match(
                            S.section,
                            (
                                "Esquemas",
                                "Los formularios cargan esquemas YAML/JSON desde schemas/ o .cms/schemas/ de la rama activa. Abre o crea un documento para editar sus campos. Consulta el contrato de esquemas en la documentación de la aplicación.",
                            ),
                            (
                                "Validación / Preview",
                                "Abre Validar / Preview en un documento para comprobar su versión guardada, avanzar el workflow y consultar su última versión publicada.",
                            ),
                            "Consulta los diffs, commits e historial en Operaciones Git.",
                        ),
                    ),
                ),
                rx.el.footer(
                    rx.el.div(
                        rx.icon("git-branch", class_name="h-3 w-3"),
                        rx.el.a(
                            rx.cond(
                                S.commit != "",
                                f"Snapshot {S.commit} · Operaciones Git →",
                                "Operaciones Git →",
                            ),
                            href="/git",
                            class_name="hover:underline text-amber-800",
                        ),
                        class_name="flex items-center gap-2 font-mono",
                    ),
                    rx.el.span(
                        "Edición por documento · Sin publicación · GitHub canónico"
                    ),
                    class_name="mt-9 flex flex-wrap justify-between gap-2 border-t border-[#dcd8ce] pt-4 pb-6 text-[10px] text-[#989d88]",
                ),
                class_name="w-full px-5 md:px-9 pt-8",
            ),
            class_name="w-full min-w-0 flex-1 overflow-y-auto bg-[#faf9f3]",
        ),
        class_name="flex h-dvh w-full flex-col md:flex-row overflow-hidden font-['Inter'] text-[#3f4839] bg-[#faf9f3]",
    )
