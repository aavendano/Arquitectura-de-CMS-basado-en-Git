import reflex as rx

import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath
from urllib.parse import quote
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL
from typing import TypedDict

import yaml
from github import Auth, Github, GithubException, InputGitTreeElement


class Field(TypedDict):
    name: str
    label: str
    kind: str
    required: bool
    options: list[str]
    default: str
    rules: str


class DocumentState(rx.State):
    repository: str = ""
    branch: str = ""
    document_uuid: str = ""
    path: str = ""
    original_path: str = ""
    sha: str = ""
    loaded_commit: str = ""
    body: str = ""
    extras: str = "{}"
    values: dict[str, str] = {}
    baseline: dict[str, str] = {}
    fields: list[Field] = []
    schemas: dict[str, list[Field]] = {}
    choices: list[dict[str, str]] = []
    busy: bool = False
    ready: bool = False
    error: str = ""
    message: str = ""
    schema_note: str = ""
    generation: int = 0
    confirm_leave: bool = False

    def _client(self):
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise ValueError("Connexion GitHub indisponible.")
        return Github(auth=Auth.Token(token), timeout=30, per_page=100)

    def _base(self) -> list[Field]:
        result = []
        for name, label, kind, required, default, options in [
            ("title", "Título", "string", True, "", []),
            ("slug", "Slug", "string", True, "", []),
            (
                "status",
                "Estado editorial",
                "select",
                True,
                "draft",
                ["draft", "review", "approved", "published", "archived"],
            ),
            ("locale", "Localización", "string", True, "es", []),
            (
                "translation_group",
                "Grupo de traducción",
                "string",
                False,
                "",
                [],
            ),
            (
                "source_document",
                "Documento de origen",
                "relation",
                False,
                "",
                [],
            ),
            ("relations", "Relaciones · IDs", "relations", False, "[]", []),
        ]:
            result.append(
                Field(
                    name=name,
                    label=label,
                    kind=kind,
                    required=required,
                    default=default,
                    options=options,
                    rules="{}",
                )
            )
        return result

    def _string(self, value) -> str:
        if isinstance(value, (dict, list, bool)):
            return json.dumps(value, ensure_ascii=False, default=str)
        return "" if value is None else str(value)

    def _parse(self, text: str):
        match = re.match(
            r"\A\ufeff?---\s*\r?\n(.*?)\r?\n(?:---|\.\.\.)[^\S\n]*(?:\r?\n|$)",
            text,
            re.S,
        )
        if not match:
            raise ValueError(
                "Falta frontmatter válido; corrige el archivo en GitHub antes de editarlo."
            )
        metadata = yaml.safe_load(match.group(1))
        if not isinstance(metadata, dict) or not all(
            isinstance(k, str) for k in metadata
        ):
            raise ValueError(
                "El frontmatter debe ser un mapa con claves de texto."
            )
        return metadata, text[match.end() :]

    def _snapshot(self, repository: str, branch: str, ref: str = ""):
        with self._client() as client:
            repo = client.get_repo(repository)
            head = ref or repo.get_branch(branch).commit.sha
            tree = repo.get_git_tree(head, recursive=True)
            if tree.truncated:
                raise ValueError(
                    "El árbol supera el límite de GitHub; no es seguro editar un índice incompleto."
                )
            documents = []
            schemas = {}
            for entry in tree.tree:
                path = entry.path
                content = path.startswith("content/") and PurePosixPath(
                    path
                ).suffix.lower() in (".md", ".markdown")
                schema = path.startswith(
                    ("schemas/", ".cms/schemas/")
                ) and PurePosixPath(path).suffix.lower() in (
                    ".yaml",
                    ".yml",
                    ".json",
                )
                if entry.type != "blob" or not (content or schema):
                    continue
                blob = repo.get_git_blob(entry.sha)
                if blob.size > 2_000_000:
                    raise ValueError(
                        "Un archivo excede el límite seguro de lectura de 2 MB."
                    )
                text = base64.b64decode(blob.content).decode("utf-8-sig")
                if content:
                    try:
                        meta, body = self._parse(text)
                    except (ValueError, yaml.YAMLError) as e:
                        logging.exception(f"Error: {e}")
                        documents.append(
                            {
                                "path": path,
                                "sha": entry.sha,
                                "meta": {},
                                "body": text,
                                "broken": True,
                            }
                        )
                        continue
                    documents.append(
                        {
                            "path": path,
                            "sha": entry.sha,
                            "meta": meta,
                            "body": body,
                            "broken": False,
                        }
                    )
                else:
                    definition = yaml.safe_load(text)
                    if not isinstance(definition, dict) or not isinstance(
                        definition.get("fields"), (dict, list)
                    ):
                        raise ValueError(
                            f"Esquema inválido en {path}: se requiere fields."
                        )
                    kind = str(definition.get("type", PurePosixPath(path).stem))
                    if kind in schemas:
                        raise ValueError(f"Tipo duplicado en esquemas: {kind}.")
                    fields = {f["name"]: f for f in self._base()}
                    raw = definition["fields"]
                    entries = (
                        [dict(spec, name=name) for name, spec in raw.items()]
                        if isinstance(raw, dict)
                        else raw
                    )
                    for spec in entries:
                        name = str(spec.get("name", ""))
                        if not re.fullmatch(
                            r"[A-Za-z_][A-Za-z0-9_]*", name
                        ) or name in ("id", "type", "body"):
                            raise ValueError(
                                f"Campo reservado o inválido en {path}."
                            )
                        field_kind = str(spec.get("type", "string"))
                        if field_kind not in (
                            "string",
                            "text",
                            "markdown",
                            "number",
                            "integer",
                            "boolean",
                            "date",
                            "select",
                            "relation",
                            "relations",
                            "array",
                            "object",
                        ):
                            raise ValueError(
                                f"Tipo de campo no soportado: {field_kind}."
                            )
                        rules = spec.get("rules", {})
                        if not isinstance(rules, dict) or set(rules) - {
                            "min",
                            "max",
                            "min_length",
                            "max_length",
                            "pattern",
                        }:
                            raise ValueError(f"Reglas no soportadas en {name}.")
                        if rules.get("pattern"):
                            re.compile(str(rules["pattern"]))
                        base = fields.get(name, {})
                        fields[name] = Field(
                            name=name,
                            label=str(spec.get("label", name)),
                            kind=field_kind,
                            required=bool(
                                spec.get(
                                    "required", base.get("required", False)
                                )
                            ),
                            options=[
                                str(v)
                                for v in spec.get(
                                    "options", base.get("options", [])
                                )
                            ],
                            default=self._string(
                                spec.get("default", base.get("default", ""))
                            ),
                            rules=json.dumps(rules),
                        )
                    schemas[kind] = list(fields.values())
            return (
                documents,
                schemas or {"article": self._base()},
                bool(schemas),
            )

    def _route_id(self, doc: dict, repository: str) -> str:
        try:
            return str(UUID(str(doc["meta"].get("id", ""))))
        except ValueError:
            return str(uuid5(NAMESPACE_URL, f"{repository}:{doc['path']}"))

    def _head(self, repository: str, branch: str) -> str:
        with self._client() as client:
            return client.get_repo(repository).get_branch(branch).commit.sha

    @rx.event
    def open_git(self):
        if self.busy or self.modified:
            return rx.toast(
                "Guarda tus cambios antes de abrir Operaciones Git."
            )
        return rx.redirect(
            f"/git?repo={quote(self.repository, safe='')}&branch={quote(self.branch, safe='')}&path={quote(self.original_path, safe='')}"
        )

    @rx.event(background=True)
    async def load(self):
        async with self:
            if self.busy:
                return
            from app.states.library import LibraryState

            library = await self.get_state(LibraryState)
            query = self.router.url.query_parameters
            repository = str(query.get("repo", library.repository))
            branch = str(query.get("branch", library.branch))
            identifier = str(self.router.page.params.get("id", ""))
            self.busy, self.ready = True, False
            self.error, self.message = "", ""
        try:
            if not repository or not branch:
                raise ValueError(
                    "Vuelve a Biblioteca y selecciona repositorio y rama."
                )
            head = await asyncio.to_thread(self._head, repository, branch)
            documents, schemas, configured = await asyncio.to_thread(
                self._snapshot, repository, branch, head
            )
            matching = [
                d
                for d in documents
                if self._route_id(d, repository) == identifier
            ]
            if identifier != "new" and len(matching) != 1:
                raise ValueError(
                    "Documento no encontrado o ID duplicado. Sin cambios en GitHub."
                )
            doc = (
                matching[0]
                if matching
                else {
                    "meta": {},
                    "body": "",
                    "path": "",
                    "sha": "",
                    "broken": False,
                }
            )
            if doc["broken"]:
                raise ValueError(
                    "Frontmatter ilegible. Corrígelo en GitHub para evitar pérdida de datos."
                )
            meta = doc["meta"]
            kind = str(meta.get("type", next(iter(schemas))))
            if kind not in schemas:
                schemas[kind] = self._base()
            fields = schemas[kind]
            stable_id = str(meta.get("id", ""))
            try:
                stable_id = str(UUID(stable_id))
            except ValueError:
                stable_id = str(uuid4())
            values = {
                f["name"]: self._string(meta.get(f["name"], f["default"]))
                for f in fields
            }
            values["type"] = kind
            extras = {
                k: v for k, v in meta.items() if k not in values and k != "id"
            }
            choices = []
            for other in documents:
                try:
                    uid = str(UUID(str(other["meta"].get("id", ""))))
                    if uid != stable_id:
                        choices.append(
                            {
                                "id": uid,
                                "title": str(
                                    other["meta"].get("title", other["path"])
                                ),
                            }
                        )
                except ValueError:
                    continue
            async with self:
                self.repository, self.branch = repository, branch
                self.loaded_commit = head
                self.document_uuid, self.fields, self.schemas = (
                    stable_id,
                    fields,
                    schemas,
                )
                self.values, self.body = values, doc["body"]
                self.extras = json.dumps(
                    extras, ensure_ascii=False, indent=2, default=str
                )
                self.path = doc["path"] or f"content/{stable_id}.md"
                self.original_path, self.sha = doc["path"], doc["sha"]
                self.choices = choices
                self.baseline = self._current()
                if not meta.get("id"):
                    self.baseline["id"] = ""
                self.schema_note = (
                    "Esquemas del repositorio"
                    if configured
                    else "Esquema base seguro · no hay esquemas configurados"
                )
                self.generation += 1
                self.ready = True
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.error = self._error(e)
        finally:
            async with self:
                self.busy = False

    def _error(self, e: Exception) -> str:
        if isinstance(e, ValueError):
            return str(e)
        if isinstance(e, GithubException) and e.status in (409, 422):
            return "Conflicto remoto: no se ha sobrescrito el documento. Conserva tus cambios y recarga la versión de GitHub."
        return "No se pudo completar la operación en GitHub. Comprueba permisos, conexión y rama. Si la respuesta se perdió, recarga antes de reintentar."

    def _current(self) -> dict[str, str]:
        return {
            **self.values,
            "id": self.document_uuid,
            "ruta": self.path,
            "Markdown": self.body,
            "metadatos": self.extras,
        }

    @rx.var
    def modified(self) -> list[str]:
        current = self._current()
        return [
            k
            for k in sorted(set(current) | set(self.baseline))
            if current.get(k) != self.baseline.get(k)
        ]

    @rx.var
    def types(self) -> list[str]:
        return list(self.schemas)

    @rx.event
    def edit(self, name: str, value: str):
        if not self.busy:
            self.values[name] = value
            self.message = ""

    @rx.event
    def set_body(self, value: str):
        if not self.busy:
            self.body = value

    @rx.event
    def set_path(self, value: str):
        if not self.busy:
            self.path = value

    @rx.event
    def set_extras(self, value: str):
        if not self.busy:
            self.extras = value

    @rx.event
    def select_type(self, value: str):
        if self.busy or value not in self.schemas:
            return
        self.fields = self.schemas[value]
        for field in self.fields:
            self.values.setdefault(field["name"], field["default"])
        self.values["type"] = value
        self.generation += 1

    @rx.event
    def toggle_relation(self, name: str, uid: str):
        if self.busy:
            return
        try:
            selected = json.loads(self.values.get(name, "[]") or "[]")
            if not isinstance(selected, list):
                raise ValueError("Las relaciones deben ser una lista de IDs.")
            selected = (
                [v for v in selected if v != uid]
                if uid in selected
                else [*selected, uid]
            )
            self.values[name] = json.dumps(selected)
        except Exception as e:
            logging.exception(f"Error: {e}")
            self.error = "Corrige la lista de relaciones antes de seleccionar documentos."

    @rx.event
    def duplicate(self):
        if self.busy or not self.ready:
            return
        uid = str(uuid4())
        self.document_uuid = uid
        self.sha, self.original_path = "", ""
        self.path = (
            f"content/{self.values.get('slug', 'documento')}-copia-{uid[:8]}.md"
        )
        self.values["slug"] = (
            f"{self.values.get('slug', 'documento')}-copia-{uid[:8]}"
        )
        self.values["title"] = f"{self.values.get('title', '')} · copia"
        self.values["status"] = "draft"
        self.baseline = {}
        self.generation += 1
        self.message = "Copia preparada con nuevo UUID. Guarda para crear el archivo en GitHub."

    def _build_document_text(self, values, fields, uid, body, extras, path):
        if (
            not re.fullmatch(
                r"content/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+\.(?:md|markdown)",
                path,
            )
            or ".." in path
        ):
            raise ValueError(
                "La ruta debe estar dentro de content/, sin .., espacios ni segmentos vacíos, y terminar en .md o .markdown."
            )
        metadata = json.loads(extras)
        if not isinstance(metadata, dict):
            raise ValueError(
                "Los metadatos adicionales deben ser un objeto JSON."
            )
        if set(metadata) & (set(values) | {"id", "type"}):
            raise ValueError(
                "Los metadatos adicionales no pueden sobrescribir campos del formulario."
            )
        metadata.update(values)
        for field in fields:
            name, kind = field["name"], field["kind"]
            raw = values.get(name, "")
            if field["required"] and not raw.strip():
                raise ValueError(f"{field['label']}: campo requerido.")
            value = raw
            if raw:
                if kind in (
                    "array",
                    "relations",
                    "object",
                    "boolean",
                    "number",
                    "integer",
                ):
                    value = json.loads(raw)
                    expected = {
                        "array": list,
                        "relations": list,
                        "object": dict,
                        "boolean": bool,
                        "number": (int, float),
                        "integer": int,
                    }[kind]
                    if not isinstance(value, expected) or (
                        kind in ("integer", "number")
                        and isinstance(value, bool)
                    ):
                        raise ValueError(f"{name}: tipo inválido ({kind}).")
                if kind == "date":
                    datetime.strptime(raw, "%Y-%m-%d")
                if field["options"] and raw not in field["options"]:
                    raise ValueError(
                        f"{name}: selecciona una opción permitida."
                    )
                rules = json.loads(field["rules"])
                for rule, limit in rules.items():
                    failed = False
                    if rule == "min":
                        failed = float(value) < float(limit)
                    elif rule == "max":
                        failed = float(value) > float(limit)
                    elif rule == "min_length":
                        failed = len(value) < int(limit)
                    elif rule == "max_length":
                        failed = len(value) > int(limit)
                    elif rule == "pattern":
                        failed = re.fullmatch(str(limit), str(value)) is None
                    if failed:
                        raise ValueError(f"{name}: no cumple {rule} = {limit}.")
            metadata[name] = value
        for required in ("title", "slug", "type", "locale"):
            if not str(metadata.get(required, "")).strip():
                raise ValueError(f"{required}: campo requerido.")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", str(metadata["slug"])):
            raise ValueError("Slug: usa minúsculas, números y guiones.")
        if metadata.get("status") not in (
            "draft",
            "review",
            "approved",
            "published",
            "archived",
        ):
            raise ValueError("Estado editorial no permitido.")
        metadata["id"] = str(UUID(uid))
        metadata["updated_at"] = datetime.now(timezone.utc).isoformat()
        return (
            f"---\n{yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False)}---\n{body}",
            metadata,
        )

    def _write(self, repository, branch, old_path, sha, path, text, metadata):
        with self._client() as client:
            repo = client.get_repo(repository)
            head = repo.get_branch(branch).commit.sha
            parent = repo.get_git_commit(head)
            tree = repo.get_git_tree(head, recursive=True)
            if tree.truncated:
                raise ValueError("Índice incompleto: escritura bloqueada.")
            entries = {e.path: e for e in tree.tree}
            if old_path and (
                old_path not in entries or entries[old_path].sha != sha
            ):
                raise ValueError(
                    "Conflicto SHA: el archivo remoto cambió o fue eliminado. Tus cambios siguen en el editor; copia el texto antes de recargar."
                )
            if path != old_path and path in entries:
                raise ValueError(
                    "La ruta de destino ya existe. Elige otra; no se sobrescribió ningún archivo."
                )
            from app.states.validation import (
                validate_document,
                check_transition,
            )

            documents, schemas, configured = self._snapshot(
                repository, branch, head
            )
            original = next(
                (d for d in documents if d["path"] == old_path), None
            )
            current_status = (
                str(original["meta"].get("status", "draft"))
                if original
                else "draft"
            )
            candidate = {
                "path": path,
                "sha": sha,
                "meta": metadata,
                "body": self._parse(text)[1],
                "broken": False,
            }
            candidates = [d for d in documents if d["path"] != old_path]
            candidates.append(candidate)
            kind = str(metadata.get("type", ""))
            active_fields = schemas.get(kind, self._base())
            issues = validate_document(
                metadata,
                candidate["body"],
                active_fields,
                candidates,
                kind in schemas,
            )
            check_transition(
                current_status, str(metadata.get("status", "")), issues
            )
            ids = set()
            for entry in tree.tree:
                if (
                    entry.type != "blob"
                    or not entry.path.startswith("content/")
                    or PurePosixPath(entry.path).suffix.lower()
                    not in (".md", ".markdown")
                    or entry.path == old_path
                ):
                    continue
                blob = repo.get_git_blob(entry.sha)
                try:
                    meta, _ = self._parse(
                        base64.b64decode(blob.content).decode("utf-8-sig")
                    )
                except (ValueError, yaml.YAMLError) as e:
                    logging.exception(f"Error: {e}")
                    continue
                ids.add(str(meta.get("id", "")))
                if str(meta.get("id", "")) == metadata["id"]:
                    raise ValueError("Ya existe otro documento con este UUID.")
            for field in active_fields:
                if field["kind"] in ("relation", "relations"):
                    refs = metadata.get(field["name"], [])
                    refs = [refs] if isinstance(refs, str) and refs else refs
                    if any(str(ref) not in ids for ref in refs):
                        raise ValueError(
                            f"{field['label']}: selecciona IDs existentes, distintos del propio documento."
                        )
            blob = repo.create_git_blob(text, "utf-8")
            changes = [
                InputGitTreeElement(path, "100644", "blob", sha=blob.sha)
            ]
            if old_path and old_path != path:
                changes.append(
                    InputGitTreeElement(old_path, "100644", "blob", sha=None)
                )
            updated_tree = repo.create_git_tree(changes, base_tree=parent.tree)
            commit = repo.create_git_commit(
                f"Folio: {metadata['status']} · {metadata['id']}",
                updated_tree,
                [parent],
            )
            repo.get_git_ref(f"heads/{branch}").edit(commit.sha, force=False)
            return blob.sha, commit.sha

    @rx.event(background=True)
    async def save(self, action: str):
        async with self:
            if self.busy or not self.ready:
                return
            self.busy, self.error, self.message = True, "", ""
            values = dict(self.values)
            if action in ("draft", "archived"):
                values["status"] = action
            args = (
                values,
                list(self.fields),
                self.document_uuid,
                self.body,
                self.extras,
                self.path,
            )
            target = (
                self.repository,
                self.branch,
                self.original_path,
                self.sha,
                self.path,
            )
        try:
            text, metadata = self._build_document_text(*args)
            sha, commit = await asyncio.to_thread(
                self._write, *target, text, metadata
            )
            async with self:
                self.values = values
                self.sha, self.original_path = sha, self.path
                self.loaded_commit = commit
                self.baseline = self._current()
                self.generation += 1
                self.message = f"Commit {commit} creado y referencia remota actualizada sin force (commit + push). El estado editorial no implica publicación externa."
                url = f"/documents/{self.document_uuid}?repo={quote(self.repository, safe='')}&branch={quote(self.branch, safe='')}"
            yield rx.call_script(
                f"window.history.replaceState(null, '', {json.dumps(url)})"
            )
        except Exception as e:
            logging.exception(f"Error: {e}")
            async with self:
                self.error = self._error(e)
        finally:
            async with self:
                self.busy = False

    @rx.event
    def open_preview(self):
        if self.busy:
            return
        if not self.sha or self.modified:
            return rx.toast(
                "Guarda los cambios antes de abrir el preview. Solo se muestra contenido real de GitHub."
            )
        return rx.redirect(
            f"/preview/{self.document_uuid}?repo={quote(self.repository, safe='')}&branch={quote(self.branch, safe='')}"
        )

    @rx.event
    def leave(self):
        if self.modified:
            self.confirm_leave = True
        else:
            return rx.redirect("/")

    @rx.event
    def cancel_leave(self):
        self.confirm_leave = False
