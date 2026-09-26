import reflex as rx

from app.components.library import workspace
from app.states.library import LibraryState
from app.components.document import document_page
from app.states.document import DocumentState
from app.components.preview import preview_page
from app.states.preview import PreviewState
from app.components.git import git_page
from app.states.git import GitState


def index() -> rx.Component:
    return workspace()


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(
            rel="preconnect",
            href="https://fonts.gstatic.com",
            cross_origin="",
        ),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(
    preview_page,
    route="/preview/[id]",
    title="Folio · Validación / Preview",
    on_load=PreviewState.load,
)
app.add_page(
    document_page,
    route="/documents/[id]",
    title="Folio · Documento",
    on_load=DocumentState.load,
)
app.add_page(
    git_page,
    route="/git",
    title="Folio · Operaciones Git",
    on_load=GitState.load,
)
app.add_page(
    index,
    route="/",
    title="Folio · Biblioteca editorial",
    on_load=LibraryState.connect,
)
