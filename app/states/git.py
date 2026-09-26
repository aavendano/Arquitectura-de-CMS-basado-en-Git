import reflex as rx

import asyncio
import base64
import difflib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

from github import (
    Auth,
    Github,
    GithubException,
    InputGitAuthor,
    InputGitTreeElement,
)


class GitState(rx.State):
    repository: str = ""
    branch: str = ""
    base: str = ""
    head: str = ""
    remote_head: str = ""
    base_head: str = ""
    ahead: int = 0
    behind: int = 0
    checked: str = ""
    comparison: str = ""
    changes: list[dict[str, str]] = []
    paths: list[str] = []
    selected: str = ""
    lines: list[str] = []
    diff_note: str = "Selecciona un documento."
    history: list[dict[str, str]] = []
    history_limit: int = 50
    history_more: bool = False
    version: str = ""
    version_text: str = ""
    pending: bool = False
    conflict: bool = False
    busy: bool = False
    ready: bool = False
    error: str = ""
    message: str = ""
    _snapshots: dict[str, dict[str, str]] = {}
    _heads: dict[str, str] = {}
    _current: dict[str, str] = {}
    _before: dict[str, str] = {}
    _modes: dict[str, str] = {}
    _restore_sha: str = ""
    _restore_mode: str = "100644"
    _expected_sha: str = ""

    def _client(self):
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise ValueError("Conexión GitHub no disponible.")
        return Github(auth=Auth.Token(token), per_page=100, timeout=30)

    def _error(self, exc: Exception) -> str:
        if isinstance(exc, ValueError):
            return str(exc)
        if isinstance(exc, GithubException):
            if exc.status in (403, 429):
                return "GitHub ha limitado o denegado la operación. Revisa cuota, permisos de Contents y protección de rama. Recarga antes de reintentar."
            if exc.status in (409, 422):
                return "Conflicto o regla de rama: actualización bloqueada. No se fuerza la referencia. Cancela y recarga."
            if exc.status == 404:
                return "Repositorio, rama o versión no disponible, o sin permisos de lectura."
            if exc.status == 401:
                return "La conexión GitHub no está autorizada."
        return "No se pudo confirmar la operación. Puede haberse perdido la respuesta de GitHub: comprueba el remoto antes de reintentar."

    def _tree(self, repo, head):
        tree = repo.get_git_tree(head, recursive=True)
        if tree.truncated:
            raise ValueError(
                "Árbol incompleto: lectura y restauración bloqueadas por seguridad."
            )
        return {
            e.path: e
            for e in tree.tree
            if e.type == "blob"
            and e.path.startswith("content/")
            and e.path.lower().endswith((".md", ".markdown"))
        }

    def _text(self, repo, sha):
        if not sha:
            return "", False
        blob = repo.get_git_blob(sha)
        if blob.size > 2_000_000:
            raise ValueError(
                "Archivo mayor de 2 MB: visualización y preparación bloqueadas."
            )
        raw = base64.b64decode(blob.content)
        try:
            text = raw.decode("utf-8")
            return text, "\x00" in text
        except UnicodeError as e:
            logging.exception(f"Error: {e}")
            return "", True

    def _diff(self, repo, old, new, old_path, new_path):
        left, binary_left = self._text(repo, old)
        right, binary_right = self._text(repo, new)
        if binary_left or binary_right:
            return (
                [],
                "Archivo binario o no UTF-8. No hay diff textual; la restauración conserva el blob exacto.",
            )
        lines = list(
            difflib.unified_diff(
                left.splitlines(keepends=True),
                right.splitlines(keepends=True),
                fromfile=old_path or "/dev/null",
                tofile=new_path or "/dev/null",
            )
        )
        result = []
        for line in lines:
            result.append(line.rstrip("\n"))
            if not line.endswith("\n"):
                result.append("\\ Sin salto de línea al final")
        return (
            result,
            "Sin diferencias de contenido."
            if not result
            else "Patch unificado · − eliminado / + añadido",
        )

    def _read(self, repository, branch, previous, previous_head):
        with self._client() as client:
            repo = client.get_repo(repository)
            branch = branch or repo.default_branch
            head = repo.get_branch(branch).commit.sha
            base = repo.default_branch
            base_head = repo.get_branch(base).commit.sha
            entries = self._tree(repo, head)
            current = {p: e.sha for p, e in entries.items()}
            modes = {p: e.mode for p, e in entries.items()}
            comparison = repo.compare(base_head, head)
            before = (
                {p: e.sha for p, e in self._tree(repo, base_head).items()}
                if branch != base
                else previous
            )
            note = (
                f"{base} → {branch}"
                if branch != base
                else (
                    f"Snapshot {previous_head[:12]} → HEAD"
                    if previous_head
                    else "Primera lectura: snapshot inicial, sin comparación previa"
                )
            )
            changes = []
            removed = set(before) - set(current)
            added = set(current) - set(before)
            rename_hints = {}
            if branch != base or previous_head:
                compared = (
                    comparison
                    if branch != base
                    else repo.compare(previous_head, head)
                )
                rename_hints = {
                    f.filename: f.previous_filename
                    for f in compared.files
                    if f.status == "renamed"
                }
            for path in sorted(added):
                old = rename_hints.get(path, "")
                if old not in removed:
                    old = next(
                        (
                            p
                            for p in sorted(removed)
                            if before[p] == current[path]
                        ),
                        "",
                    )
                if old:
                    removed.remove(old)
                changes.append(
                    {
                        "path": path,
                        "old_path": old,
                        "kind": "renamed" if old else "added",
                    }
                )
            for path in sorted(removed):
                changes.append(
                    {"path": path, "old_path": path, "kind": "removed"}
                )
            for path in sorted(set(before) & set(current)):
                if before[path] != current[path]:
                    changes.append(
                        {"path": path, "old_path": path, "kind": "modified"}
                    )
            if branch == base and not previous_head:
                changes = []
            return (
                branch,
                base,
                head,
                base_head,
                comparison.ahead_by,
                comparison.behind_by,
                current,
                modes,
                before,
                changes,
                note,
            )

    @rx.event(background=True)
    async def load(self):
        async with self:
            if self.busy:
                return
            if self.pending:
                self.error = "Cancela la restauración pendiente antes de Pull. No se descarta trabajo en memoria."
                return
            from app.states.library import LibraryState

            library = await self.get_state(LibraryState)
            library.section = "Operaciones Git"
            query = self.router.url.query_parameters
            repository = str(query.get("repo", library.repository))
            branch = str(query.get("branch", library.branch))
            path = str(query.get("path", self.selected))
            key = f"{repository}@{branch}"
            previous = dict(self._snapshots.get(key, {}))
            previous_head = self._heads.get(key, "")
            self.busy, self.error = True, ""
        try:
            if not repository:
                raise ValueError(
                    "Selecciona repositorio y rama en Biblioteca para abrir Operaciones Git."
                )
            result = await asyncio.to_thread(
                self._read, repository, branch, previous, previous_head
            )
            (
                branch,
                base,
                head,
                base_head,
                ahead,
                behind,
                current,
                modes,
                before,
                changes,
                note,
            ) = result
            async with self:
                self.repository, self.branch, self.base = (
                    repository,
                    branch,
                    base,
                )
                self.head = self.remote_head = head
                self.base_head, self.ahead, self.behind = (
                    base_head,
                    ahead,
                    behind,
                )
                self._current, self._modes, self._before = (
                    current,
                    modes,
                    before,
                )
                self._snapshots[f"{repository}@{branch}"] = current
                self._heads[f"{repository}@{branch}"] = head
                self.changes, self.comparison = changes, note
                self.paths = sorted(set(current) | set(before))
                self.selected = (
                    path
                    if path in self.paths
                    else (changes[0]["path"] if changes else "")
                )
                self.history, self.lines = [], []
                self.version, self.version_text = "", ""
                self.diff_note = "Selecciona un documento."
                self.conflict, self.ready = False, True
                self.checked = datetime.now(timezone.utc).strftime(
                    "%d/%m/%Y %H:%M UTC"
                )
                selected = self.selected
                library.repository, library.branch = repository, branch
                library.connected = True
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.error = self._error(e)
                self.ready = False
            selected = ""
        finally:
            async with self:
                self.busy = False
        if selected:
            yield GitState.select_document(selected)

    def _document(
        self, repository, head, path, old_path, old_sha, new_sha, limit
    ):
        with self._client() as client:
            repo = client.get_repo(repository)
            lines, note = self._diff(repo, old_sha, new_sha, old_path, path)
            history = []
            seen = set()
            cursor, history_path = head, path
            while history_path not in seen:
                seen.add(history_path)
                previous = ""
                for commit in repo.get_commits(path=history_path, sha=cursor):
                    author = commit.commit.author
                    history.append(
                        {
                            "sha": commit.sha,
                            "path": history_path,
                            "author": author.name or "Sin autor declarado",
                            "github": commit.author.login
                            if commit.author
                            else "Sin cuenta vinculada",
                            "date": str(author.date),
                            "message": commit.commit.message,
                            "url": commit.html_url,
                        }
                    )
                    if len(history) > limit:
                        return lines, note, history[:limit], True
                    for file in commit.files:
                        if (
                            file.filename == history_path
                            and file.status == "renamed"
                            and commit.parents
                        ):
                            previous, cursor = (
                                file.previous_filename,
                                commit.parents[0].sha,
                            )
                    if previous:
                        break
                if not previous:
                    break
                history_path = previous
            return lines, note, history, False

    @rx.event(background=True)
    async def select_document(self, path: str):
        async with self:
            if (
                self.busy
                or self.pending
                or not self.ready
                or path not in self.paths
            ):
                return
            self.busy, self.error = True, ""
            self.selected, self.version, self.version_text = path, "", ""
            self.history, self.lines = [], []
            change = next((c for c in self.changes if c["path"] == path), {})
            old_path = change.get("old_path", path)
            args = (
                self.repository,
                self.head,
                path,
                old_path,
                self._before.get(old_path, ""),
                self._current.get(path, ""),
                self.history_limit,
            )
        try:
            lines, note, history, more = await asyncio.to_thread(
                self._document, *args
            )
            async with self:
                self.lines, self.diff_note, self.history, self.history_more = (
                    lines,
                    note,
                    history,
                    more,
                )
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.error = self._error(e)
        finally:
            async with self:
                self.busy = False

    @rx.event
    def more_history(self):
        if not self.busy and not self.pending:
            self.history_limit += 50
            yield GitState.select_document(self.selected)

    def _version(self, repository, version, historical_path, path, expected):
        with self._client() as client:
            repo = client.get_repo(repository)
            entries = self._tree(repo, version)
            entry = entries.get(historical_path)
            sha = entry.sha if entry else ""
            mode = entry.mode if entry else "100644"
            if mode not in ("100644", "100755"):
                raise ValueError(
                    "Se restauran únicamente archivos regulares, no enlaces simbólicos."
                )
            text, binary = self._text(repo, sha)
            lines, note = self._diff(repo, expected, sha, path, path)
            return (
                sha,
                mode,
                text if not binary else "Versión binaria / no UTF-8",
                lines,
                note,
            )

    @rx.event(background=True)
    async def prepare(self, version: str):
        async with self:
            item = next((h for h in self.history if h["sha"] == version), None)
            if self.busy or self.pending or self.conflict or not item:
                return
            self.busy, self.error = True, ""
            expected = self._current.get(self.selected, "")
            args = (
                self.repository,
                version,
                item["path"],
                self.selected,
                expected,
            )
        try:
            sha, mode, text, lines, note = await asyncio.to_thread(
                self._version, *args
            )
            async with self:
                self.version, self.version_text = (
                    version,
                    text or "Versión vacía o archivo ausente en este commit.",
                )
                self._restore_sha, self._restore_mode, self._expected_sha = (
                    sha,
                    mode,
                    expected,
                )
                self.lines, self.diff_note = lines, note
                self.pending = sha != expected
                self.message = (
                    "Restauración preparada solo en memoria. Revisa el diff contra HEAD."
                    if self.pending
                    else "Esta versión ya coincide con HEAD."
                )
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.error = self._error(e)
        finally:
            async with self:
                self.busy = False

    @rx.event
    def cancel(self):
        if self.busy:
            return
        self.pending = False
        self.version = self.version_text = self.message = self.error = ""
        self._restore_sha = self._expected_sha = ""
        yield GitState.select_document(self.selected)

    def _remote(self, repository, branch):
        with self._client() as client:
            return client.get_repo(repository).get_branch(branch).commit.sha

    @rx.event(background=True)
    async def check_remote(self):
        async with self:
            if self.busy or not self.ready:
                return
            self.busy, self.error = True, ""
            repository, branch, head = self.repository, self.branch, self.head
        try:
            remote = await asyncio.to_thread(self._remote, repository, branch)
            async with self:
                self.remote_head = remote
                self.conflict = remote != head
                self.message = (
                    "Cambios externos detectados. Cancela cualquier restauración y haz Pull."
                    if self.conflict
                    else "HEAD remoto coincide con el snapshot cargado."
                )
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.error = self._error(e)
        finally:
            async with self:
                self.busy = False

    def _restore(
        self,
        repository,
        branch,
        head,
        path,
        expected,
        sha,
        mode,
        message,
        name,
        email,
        version,
    ):
        with self._client() as client:
            repo = client.get_repo(repository)
            if repo.get_branch(branch).commit.sha != head:
                raise ValueError(
                    "Conflicto: HEAD cambió. No se actualizó la rama."
                )
            entries = self._tree(repo, head)
            entry = entries.get(path)
            if (entry.sha if entry else "") != expected:
                raise ValueError(
                    "Conflicto: SHA del archivo cambió o fue eliminado."
                )
            parent = repo.get_git_commit(head)
            actor = InputGitAuthor(name, email)
            tree = repo.create_git_tree(
                [InputGitTreeElement(path, mode, "blob", sha=sha or None)],
                base_tree=parent.tree,
            )
            commit = repo.create_git_commit(
                f"{message}\n\nFolio restore: {path}\nSource: {version}\nExpected-HEAD: {head}",
                tree,
                [parent],
                author=actor,
                committer=actor,
            )
            if repo.get_branch(branch).commit.sha != head:
                raise ValueError(
                    "Conflicto: HEAD cambió durante la preparación. Commit no aplicado a la rama."
                )
            repo.get_git_ref(f"heads/{branch}").edit(commit.sha, force=False)
            return commit.sha

    @rx.event(background=True)
    async def commit_restore(self, form_data: dict[str, Any]):
        async with self:
            if self.busy or not self.pending or self.conflict or self.error:
                return
            message = str(form_data.get("message", "")).strip()
            name = str(form_data.get("name", "")).strip()
            email = str(form_data.get("email", "")).strip()
            if (
                not message
                or not name
                or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", email)
                or any(c in name for c in "\r\n<>")
                or not form_data.get("confirm")
            ):
                self.error = "Se requieren mensaje, nombre/email válidos y confirmación explícita."
                return
            args = (
                self.repository,
                self.branch,
                self.head,
                self.selected,
                self._expected_sha,
                self._restore_sha,
                self._restore_mode,
                message,
                name,
                email,
                self.version,
            )
            self.busy, self.error = True, ""
        success = False
        try:
            commit = await asyncio.to_thread(self._restore, *args)
            async with self:
                self.pending = False
                self.message = f"Commit {commit} creado y referencia remota actualizada sin force (commit + push)."
                success = True
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.error = self._error(e)
                self.conflict = True
        finally:
            async with self:
                self.busy = False
        if success:
            yield GitState.load

    @rx.var
    def commit_url(self) -> str:
        return f"https://github.com/{self.repository}/commit/{self.head}"

    @rx.var
    def document_url(self) -> str:
        return f"https://github.com/{self.repository}/blob/{self.head}/{quote(self.selected, safe='/')}"
