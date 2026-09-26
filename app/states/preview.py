import reflex as rx

import asyncio
import base64
import logging
from datetime import datetime, timezone
from urllib.parse import quote

import yaml
from github import GithubException

from app.states.document import DocumentState
from app.states.library import LibraryState
from app.states.validation import WORKFLOW, validate_document, check_transition


class PreviewState(rx.State):
    repository: str = ""
    branch: str = ""
    identifier: str = ""
    path: str = ""
    sha: str = ""
    title: str = ""
    status: str = ""
    body: str = ""
    metadata_text: str = ""
    version: str = ""
    published_body: str = ""
    published_title: str = ""
    published_version: str = ""
    published_metadata: str = ""
    history_error: str = ""
    published_found: bool = False
    issues: list[dict[str, str]] = []
    tab: str = "stored"
    busy: bool = False
    ready: bool = False
    error: str = ""
    message: str = ""
    target: str = ""
    document_options: list[dict[str, str]] = []

    @rx.var
    def errors(self) -> int:
        return sum(i["level"] == "error" for i in self.issues)

    @rx.var
    def warnings(self) -> int:
        return sum(i["level"] == "warning" for i in self.issues)

    @rx.var
    def valid(self) -> bool:
        return self.ready and not self.error and self.errors == 0

    @rx.var
    def transitions(self) -> list[str]:
        return WORKFLOW.get(self.status, ["draft"])

    @rx.var
    def blocked(self) -> bool:
        return (
            not self.ready
            or bool(self.error)
            or self.target not in self.transitions
            or (
                self.target in ("review", "approved", "published")
                and not self.valid
            )
        )

    @rx.var
    def git_url(self) -> str:
        return f"/git?repo={quote(self.repository, safe='')}&branch={quote(self.branch, safe='')}&path={quote(self.path, safe='')}"

    @rx.var
    def editor_url(self) -> str:
        return f"/documents/{self.identifier}?repo={quote(self.repository, safe='')}&branch={quote(self.branch, safe='')}"

    @rx.event
    def set_tab(self, value: str):
        if value in ("stored", "validated", "published"):
            self.tab = value

    @rx.event
    def set_target(self, value: str):
        if not self.busy and value in self.transitions:
            self.target = value

    @rx.event
    def select_document(self, value: str):
        if not self.busy and value in [d["id"] for d in self.document_options]:
            return rx.redirect(
                f"/preview/{value}?repo={quote(self.repository, safe='')}&branch={quote(self.branch, safe='')}"
            )

    def _read(self, reader, repository: str, branch: str, identifier: str):
        with reader._client() as client:
            repo = client.get_repo(repository)
            head = repo.get_branch(branch).commit.sha
            docs, schemas, configured = reader._snapshot(
                repository, branch, head
            )
            matching = [
                d for d in docs if reader._route_id(d, repository) == identifier
            ]
            if len(matching) != 1:
                raise ValueError(
                    "Documento no encontrado o ID duplicado. Corrige la identidad en GitHub."
                )
            doc = matching[0]
            meta = doc["meta"]
            kind = str(meta.get("type", ""))
            fields = schemas.get(kind, reader._base())
            issues = validate_document(
                meta, doc["body"], fields, docs, kind in schemas, doc["broken"]
            )
            commit = next(
                iter(repo.get_commits(path=doc["path"], sha=head)), None
            )
            version = (
                f"{commit.sha[:12]} · {commit.commit.message.splitlines()[0]} · {commit.commit.author.date}"
                if commit
                else f"Snapshot {head[:12]}"
            )
            published = {"body": "", "title": "", "version": "", "metadata": ""}
            history_error = ""
            found = False
            try:
                history_path = doc["path"]
                history_head = head
                visited = set()
                while history_path not in visited:
                    visited.add(history_path)
                    previous_path = ""
                    for historical in repo.get_commits(
                        path=history_path, sha=history_head
                    ):
                        try:
                            file = repo.get_contents(
                                history_path, ref=historical.sha
                            )
                            if file.size > 2_000_000:
                                raise ValueError(
                                    "Versión histórica demasiado grande."
                                )
                            historical_meta, historical_body = reader._parse(
                                file.decoded_content.decode("utf-8-sig")
                            )
                            if historical_meta.get("status") == "published":
                                published = {
                                    "body": historical_body,
                                    "title": str(
                                        historical_meta.get(
                                            "title", history_path
                                        )
                                    ),
                                    "version": f"{historical.sha[:12]} · {historical.commit.message.splitlines()[0]} · {historical.commit.author.date}",
                                    "metadata": yaml.safe_dump(
                                        historical_meta,
                                        allow_unicode=True,
                                        sort_keys=False,
                                    ),
                                }
                                found = True
                                break
                        except GithubException as e:
                            logging.exception(f"Error: {e}")
                            if e.status != 404:
                                raise
                        except (ValueError, yaml.YAMLError) as e:
                            logging.exception(f"Error: {e}")
                            raise ValueError(
                                "Una versión histórica no se pudo interpretar; no se puede certificar la última publicación."
                            ) from e
                        for changed in historical.files:
                            if (
                                changed.filename == history_path
                                and changed.status == "renamed"
                            ):
                                previous_path = changed.previous_filename
                                history_head = historical.parents[0].sha
                    if found or not previous_path:
                        break
                    history_path = previous_path
            except Exception as e:
                logging.exception(f"Error: {e}")
                history_error = "No se pudo completar el historial publicado. Reintenta la lectura; no equivale a ‘nunca publicado’."
            options = [
                {
                    "id": reader._route_id(d, repository),
                    "title": str(d["meta"].get("title", d["path"])),
                }
                for d in docs
            ]
            return (
                doc,
                issues,
                version,
                published,
                found,
                history_error,
                options,
            )

    @rx.event(background=True)
    async def load(self):
        async with self:
            if self.busy:
                return
            reader = await self.get_state(DocumentState)
            library = await self.get_state(LibraryState)
            library.section = "Validación / Preview"
            query = self.router.url.query_parameters
            repository = (
                query.get("repo", "").strip()
                or self.repository
                or reader.repository
                or library.repository
            )
            branch = (
                query.get("branch", "").strip()
                or self.branch
                or reader.branch
                or library.branch
            )
            route_parts = self.router.url.path.strip("/").split("/")
            identifier = self.identifier
            if len(route_parts) == 2 and route_parts[0] == "preview":
                identifier = route_parts[1] or self.identifier
            self.busy, self.ready = True, False
            self.error, self.history_error = "", ""
            self.tab = "stored"
        try:
            if not repository or not branch:
                raise ValueError(
                    "Selecciona un repositorio y una rama en Biblioteca."
                )
            result = await asyncio.to_thread(
                self._read, reader, repository, branch, identifier
            )
            doc, issues, version, published, found, history_error, options = (
                result
            )
            async with self:
                self.repository, self.branch, self.identifier = (
                    repository,
                    branch,
                    identifier,
                )
                self.path, self.sha = doc["path"], doc["sha"]
                self.body = doc["body"]
                self.title = str(doc["meta"].get("title", doc["path"]))
                self.status = str(doc["meta"].get("status", "Sin estado"))
                self.metadata_text = yaml.safe_dump(
                    doc["meta"], allow_unicode=True, sort_keys=False
                )
                self.issues, self.version = issues, version
                self.published_body, self.published_title = (
                    published["body"],
                    published["title"],
                )
                self.published_metadata, self.published_version = (
                    published["metadata"],
                    published["version"],
                )
                self.published_found, self.history_error = found, history_error
                self.document_options = options
                self.target = WORKFLOW.get(self.status, ["draft"])[0]
                library = await self.get_state(LibraryState)
                library.repository, library.branch = repository, branch
                self.ready = True
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.error = reader._error(e)
        finally:
            async with self:
                self.busy = False

    def _transition(
        self,
        reader,
        repository: str,
        branch: str,
        path: str,
        sha: str,
        target: str,
    ):
        with reader._client() as client:
            repo = client.get_repo(repository)
            file = repo.get_contents(path, ref=branch)
            if file.sha != sha:
                raise ValueError(
                    "Conflicto SHA: el documento cambió. Recarga y valida la nueva versión antes de avanzar."
                )
            meta, body = reader._parse(file.decoded_content.decode("utf-8-sig"))
            check_transition(str(meta.get("status", "draft")), target, [])
            meta["status"] = target
            meta["updated_at"] = datetime.now(timezone.utc).isoformat()
            text = f"---\n{yaml.safe_dump(meta, allow_unicode=True, sort_keys=False)}---\n{body}"
            reader._write(repository, branch, path, sha, path, text, meta)

    @rx.event(background=True)
    async def transition(self):
        async with self:
            if self.busy or self.blocked:
                return
            reader = await self.get_state(DocumentState)
            args = (
                self.repository,
                self.branch,
                self.path,
                self.sha,
                self.target,
            )
            self.busy = True
            self.error, self.message = "", ""
        success = False
        try:
            await asyncio.to_thread(self._transition, reader, *args)
            success = True
            async with self:
                self.message = f"Estado {args[-1]} guardado: commit creado y referencia remota actualizada sin force (commit + push). Sin publicación externa."
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.error = reader._error(e)
        finally:
            async with self:
                self.busy = False
        if success:
            yield PreviewState.load
