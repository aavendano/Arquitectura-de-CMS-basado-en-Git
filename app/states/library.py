import reflex as rx

import asyncio
import base64
import logging
import os
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import UUID, NAMESPACE_URL, uuid5

import yaml
from github import Auth, Github, GithubException


class LibraryState(rx.State):
    repositories: list[str] = []
    repository: str = ""
    branches: list[str] = []
    branch: str = ""
    documents: list[dict[str, str]] = []
    busy: bool = False
    connected: bool = False
    indexed: bool = False
    has_content: bool = False
    error: str = ""
    progress: str = "Esperando conexión"
    synced_at: str = "Sin sincronizar"
    commit: str = ""
    deleted: int = 0
    search: str = ""
    kind: str = "Todos"
    status: str = "Todos"
    locale: str = "Todos"
    changes: str = "Todos"
    section: str = "Biblioteca"
    _snapshots: dict[str, dict[str, str]] = {}

    def _client(self) -> Github:
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise RuntimeError("missing_token")
        return Github(auth=Auth.Token(token), per_page=100, timeout=25)

    def _message(self, exc: Exception) -> str:
        if isinstance(exc, GithubException):
            if exc.status == 401:
                return "La conexión no está autorizada. Revisa la credencial de GitHub configurada en el entorno."
            if exc.status in (403, 429):
                remaining = (exc.headers or {}).get("x-ratelimit-remaining", "")
                if remaining == "0" or exc.status == 429:
                    return "GitHub ha limitado las solicitudes. Espera a que se restablezca la cuota y vuelve a sincronizar."
                return "GitHub ha denegado la lectura. Comprueba los permisos de contenido y las restricciones de la organización; también puede haber un límite temporal."
            if exc.status == 404:
                return "El repositorio o la rama ya no están disponibles, o no tienes permiso para leerlos."
            if exc.status == 409:
                return "Este repositorio todavía no tiene commits o ramas disponibles."
        if isinstance(exc, RuntimeError) and str(exc) == "missing_token":
            return "No hay una credencial de GitHub configurada en el entorno."
        return "No se pudo completar la lectura de GitHub. Comprueba la conexión y vuelve a intentarlo. No se ha escrito ningún cambio."

    def _repositories(self) -> list[str]:
        with self._client() as client:
            return sorted(
                repo.full_name for repo in client.get_user().get_repos()
            )

    def _read_index(
        self, name: str, selected_branch: str
    ) -> tuple[list[str], str, list[dict[str, str]], bool, str]:
        with self._client() as client:
            repo = client.get_repo(name)
            branches = sorted(branch.name for branch in repo.get_branches())
            branch = selected_branch or repo.default_branch
            if branch not in branches:
                raise GithubException(404, {"message": "Branch unavailable"})
            head = repo.get_branch(branch).commit.sha
            tree = repo.get_git_tree(head, recursive=True)
            paths: list[tuple[str, str]] = []
            has_content = False
            if tree.truncated:
                root = repo.get_git_tree(head)
                content = next(
                    (
                        entry
                        for entry in root.tree
                        if entry.path == "content" and entry.type == "tree"
                    ),
                    None,
                )
                if content:
                    has_content = True
                    stack = [(content.sha, "content")]
                    while stack:
                        sha, prefix = stack.pop()
                        subtree = repo.get_git_tree(sha)
                        if subtree.truncated:
                            raise RuntimeError("incomplete_tree")
                        for entry in subtree.tree:
                            path = f"{prefix}/{entry.path}"
                            if entry.type == "tree":
                                stack.append((entry.sha, path))
                            elif entry.type == "blob" and PurePosixPath(
                                path
                            ).suffix.lower() in (".md", ".markdown"):
                                paths.append((path, entry.sha))
            else:
                for entry in tree.tree:
                    if entry.path == "content" and entry.type == "tree":
                        has_content = True
                    if (
                        entry.path.startswith("content/")
                        and entry.type == "blob"
                        and PurePosixPath(entry.path).suffix.lower()
                        in (".md", ".markdown")
                    ):
                        paths.append((entry.path, entry.sha))
            documents: list[dict[str, str]] = []
            for path, sha in sorted(paths):
                blob = repo.get_git_blob(sha)
                doc = {
                    "id": str(uuid5(NAMESPACE_URL, f"{name}:{path}")),
                    "title": PurePosixPath(path).stem,
                    "type": "Sin tipo",
                    "status": "Sin estado",
                    "locale": "Sin locale",
                    "path": path,
                    "validation": "Legible",
                    "detail": "Frontmatter YAML legible; no implica validación editorial.",
                    "date": "—",
                    "sha": sha,
                    "change": "Sin comparar",
                }
                try:
                    if blob.size > 2_000_000:
                        raise ValueError(
                            "El documento supera el límite de lectura de 2 MB."
                        )
                    text = base64.b64decode(blob.content).decode("utf-8-sig")
                    lines = text.splitlines()
                    if not lines or lines[0].strip() != "---":
                        raise ValueError(
                            "Falta el bloque de frontmatter YAML inicial."
                        )
                    end = next(
                        (
                            i
                            for i in range(1, len(lines))
                            if lines[i].strip() in ("---", "...")
                        ),
                        -1,
                    )
                    if end < 0:
                        raise ValueError(
                            "El bloque de frontmatter no tiene cierre."
                        )
                    metadata = yaml.safe_load("\n".join(lines[1:end]))
                    if not isinstance(metadata, dict):
                        raise ValueError(
                            "El frontmatter debe ser un mapa de campos YAML."
                        )
                    if metadata.get("id"):
                        try:
                            doc["id"] = str(UUID(str(metadata["id"])))
                        except ValueError as e:
                            logging.exception(f"Error: {e}")
                    for key in ("title", "type", "status", "locale"):
                        value = metadata.get(key)
                        if value is not None:
                            if not isinstance(value, str):
                                raise ValueError(
                                    f"El campo {key} debe ser texto."
                                )
                            if value.strip():
                                doc[key] = value.strip()
                    date = metadata.get("updated_at", metadata.get("date", "—"))
                    if isinstance(date, (str, datetime)) or hasattr(
                        date, "isoformat"
                    ):
                        doc["date"] = str(date)
                except (
                    ValueError,
                    UnicodeError,
                    yaml.YAMLError,
                    RecursionError,
                ) as e:
                    logging.exception(
                        f"Error: {type(e).__name__}: frontmatter no legible"
                    )
                    doc["validation"] = "Error de lectura"
                    doc["detail"] = (
                        str(e)
                        if isinstance(e, ValueError)
                        and not isinstance(e, UnicodeError)
                        else "YAML inválido o codificación distinta de UTF-8. Revisa el documento en GitHub."
                    )
                doc["href"] = (
                    f"/documents/{doc['id']}?repo={quote(name, safe='')}&branch={quote(branch, safe='')}"
                )
                doc["git_href"] = (
                    f"/git?repo={quote(name, safe='')}&branch={quote(branch, safe='')}&path={quote(path, safe='')}"
                )
                doc["preview_href"] = (
                    f"/preview/{doc['id']}?repo={quote(name, safe='')}&branch={quote(branch, safe='')}"
                )
                documents.append(doc)
            return branches, branch, documents, has_content, head

    @rx.event
    def select_repository(self, value: str):
        if self.busy or value == self.repository:
            return
        self.repository = value
        self.branch = ""
        self.branches = []
        self.documents = []
        self.indexed = False
        self.synced_at = "Sin sincronizar"
        self.commit = ""
        self.deleted = 0
        self.kind = self.status = self.locale = self.changes = "Todos"
        yield LibraryState.sync

    @rx.event
    def select_branch(self, value: str):
        if self.busy or value == self.branch:
            return
        self.branch = value
        self.documents = []
        self.indexed = False
        self.synced_at = "Sin sincronizar"
        self.commit = ""
        self.deleted = 0
        yield LibraryState.sync

    @rx.event(background=True)
    async def connect(self):
        async with self:
            if self.busy:
                return
            self.busy = True
            self.error = ""
            self.progress = "Consultando repositorios accesibles…"
        try:
            repositories = await asyncio.to_thread(self._repositories)
            async with self:
                self.repositories = repositories
                self.connected = True
                if self.repository not in repositories:
                    self.repository = repositories[0] if repositories else ""
                    self.branch = ""
                    self.documents = []
                    self.indexed = False
                self.progress = (
                    "Conexión disponible"
                    if repositories
                    else "Sin repositorios accesibles"
                )
        except Exception as e:
            logging.exception(
                f"Error: {type(e).__name__}: conexión GitHub fallida"
            )
            async with self:
                self.error = self._message(e)
                self.connected = False
        finally:
            async with self:
                self.busy = False
        async with self:
            should_sync = self.connected and bool(self.repository)
        if should_sync:
            yield LibraryState.sync

    @rx.event(background=True)
    async def sync(self):
        async with self:
            if self.busy or not self.repository:
                return
            self.busy = True
            self.error = ""
            self.progress = "Leyendo content/ y frontmatter…"
            name, branch = self.repository, self.branch
        try:
            (
                branches,
                branch,
                documents,
                has_content,
                head,
            ) = await asyncio.to_thread(self._read_index, name, branch)
            async with self:
                key = f"{name}@{branch}"
                previous = self._snapshots.get(key)
                current = {doc["path"]: doc["sha"] for doc in documents}
                for doc in documents:
                    doc["change"] = (
                        "Sin comparar"
                        if previous is None
                        else "Nuevo"
                        if doc["path"] not in previous
                        else "Modificado"
                        if previous[doc["path"]] != doc["sha"]
                        else "Sin cambios"
                    )
                self.deleted = len(set(previous or {}) - set(current))
                self._snapshots[key] = current
                self.branches, self.branch = branches, branch
                self.documents, self.has_content = documents, has_content
                self.commit = head[:7]
                self.indexed = True
                self.connected = True
                self.synced_at = datetime.now(timezone.utc).strftime(
                    "%d/%m/%Y · %H:%M UTC"
                )
                self.progress = "Índice actualizado"
        except Exception as e:
            logging.exception(
                f"Error: {type(e).__name__}: lectura GitHub fallida"
            )
            async with self:
                self.error = self._message(e)
                self.progress = "Sincronización incompleta"
        finally:
            async with self:
                self.busy = False

    @rx.event
    def set_search(self, value: str):
        self.search = value

    @rx.event
    def set_kind(self, value: str):
        self.kind = value

    @rx.event
    def set_status(self, value: str):
        self.status = value

    @rx.event
    def set_locale(self, value: str):
        self.locale = value

    @rx.event
    def set_changes(self, value: str):
        self.changes = value

    @rx.event
    def clear_filters(self):
        self.search = ""
        self.kind = self.status = self.locale = self.changes = "Todos"

    @rx.event
    def navigate(self, section: str):
        self.section = section
        if section == "Operaciones Git":
            return rx.redirect(
                f"/git?repo={quote(self.repository, safe='')}&branch={quote(self.branch, safe='')}"
            )
        return rx.redirect("/")

    @rx.event
    def create_document(self):
        if not self.repository or not self.branch or self.busy:
            return rx.toast(
                "Selecciona un repositorio y una rama antes de crear."
            )
        return rx.redirect(
            f"/documents/new?repo={quote(self.repository, safe='')}&branch={quote(self.branch, safe='')}"
        )

    @rx.var
    def types(self) -> list[str]:
        return ["Todos", *sorted({doc["type"] for doc in self.documents})]

    @rx.var
    def statuses(self) -> list[str]:
        return ["Todos", *sorted({doc["status"] for doc in self.documents})]

    @rx.var
    def locales(self) -> list[str]:
        return ["Todos", *sorted({doc["locale"] for doc in self.documents})]

    @rx.var
    def filtered(self) -> list[dict[str, str]]:
        query = self.search.casefold().strip()
        return [
            doc
            for doc in self.documents
            if (
                not query or query in f"{doc['title']} {doc['path']}".casefold()
            )
            and (self.kind == "Todos" or doc["type"] == self.kind)
            and (self.status == "Todos" or doc["status"] == self.status)
            and (self.locale == "Todos" or doc["locale"] == self.locale)
            and (self.changes == "Todos" or doc["change"] == self.changes)
        ]

    @rx.var
    def errors(self) -> int:
        return sum(doc["validation"] != "Legible" for doc in self.documents)

    @rx.var
    def changed(self) -> int:
        return sum(
            doc["change"] in ("Nuevo", "Modificado") for doc in self.documents
        )
