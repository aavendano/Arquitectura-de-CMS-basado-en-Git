import reflex as rx

import json
import logging
import math
import re
from collections import Counter
from datetime import date, datetime
from uuid import UUID

from app.states.document import Field


WORKFLOW = {
    "draft": ["review", "archived"],
    "review": ["draft", "approved", "archived"],
    "approved": ["draft", "review", "published", "archived"],
    "published": ["draft", "review", "archived"],
    "archived": ["draft"],
}


def canonical_id(value) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError):
        return str(value)


def heading_lines(body: str) -> list[int]:
    headings = []
    fence = ""
    previous = ""
    for number, line in enumerate(body.splitlines(), 1):
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence:
            if re.fullmatch(
                r" {0,3}"
                + re.escape(fence[0])
                + "{"
                + str(len(fence))
                + r",}\s*",
                line,
            ):
                fence = ""
            previous = ""
            continue
        if opening:
            fence = opening.group(1)
            previous = ""
            continue
        if re.match(r"^ {0,3}#(?:\s|$)", line):
            headings.append(number)
        elif previous.strip() and re.fullmatch(r" {0,3}=+\s*", line):
            headings.append(number - 1)
        previous = line if not line.startswith(("    ", "\t", ">")) else ""
    return headings


def validate_document(
    meta: dict,
    body: str,
    fields: list[Field],
    documents: list[dict],
    known_type: bool = True,
    broken: bool = False,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []

    def issue(category: str, field: str, message: str, level: str = "error"):
        issues.append(
            {
                "level": level,
                "category": category,
                "field": field,
                "message": message,
            }
        )

    if broken:
        issue(
            "Estructural",
            "frontmatter",
            "YAML ilegible o ausente. Corrige el archivo en GitHub.",
        )
    if not known_type:
        issue("Estructural", "type", "El tipo no tiene un esquema cargado.")
    if (
        not isinstance(meta.get("type"), str)
        or not meta.get("type", "").strip()
    ):
        issue("Estructural", "type", "Se requiere un tipo de contenido.")
    try:
        UUID(meta.get("id", ""))
    except (ValueError, TypeError) as e:
        logging.exception(f"Error: {e}")
        issue(
            "Estructural",
            "id",
            "Se requiere un UUID estable válido; guárdalo desde el editor.",
        )
    ids = Counter(
        canonical_id(d["meta"].get("id", ""))
        for d in documents
        if d["meta"].get("id")
    )
    if ids[canonical_id(meta.get("id", ""))] > 1:
        issue(
            "Referencial",
            "id",
            "El ID del documento está duplicado en el repositorio.",
        )
    if any(d.get("broken") for d in documents):
        issue(
            "Referencial",
            "content/",
            "Hay archivos ilegibles: no se puede garantizar la unicidad de los IDs.",
        )
    for field in fields:
        name, kind = field["name"], field["kind"]
        value = meta.get(name)
        empty = value is None or value == "" or value == [] or value == {}
        if field["required"] and (
            empty or isinstance(value, str) and not value.strip()
        ):
            issue("Estructural", name, "Campo requerido.")
        if empty:
            continue
        expected = {
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "relations": list,
            "object": dict,
            "date": (str, date),
        }.get(kind, str)
        if (
            not isinstance(value, expected)
            or kind in ("integer", "number")
            and isinstance(value, bool)
        ):
            issue("Estructural", name, f"Tipo inválido: se esperaba {kind}.")
            continue
        if field["options"] and str(value) not in field["options"]:
            issue(
                "Estructural", name, "Valor fuera de las opciones del esquema."
            )
        try:
            if kind == "date":
                date.fromisoformat(value)
            if kind in ("number", "integer") and not math.isfinite(value):
                raise ValueError("El número debe ser finito.")
            for rule, limit in json.loads(field["rules"]).items():
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
                    failed = re.fullmatch(limit, value) is None
                if failed:
                    issue("Estructural", name, f"No cumple {rule}: {limit}.")
        except (ValueError, TypeError, OverflowError) as e:
            logging.exception(f"Error: {e}")
            issue(
                "Estructural",
                name,
                "Formato inválido o regla incompatible con el valor.",
            )
        if kind in ("relation", "relations"):
            refs = [value] if kind == "relation" else value
            seen = set()
            for index, ref in enumerate(refs):
                uid = canonical_id(ref)
                location = f"{name}[{index}]"
                try:
                    UUID(ref)
                except (ValueError, TypeError) as e:
                    logging.exception(f"Error: {e}")
                    issue(
                        "Referencial",
                        location,
                        "La referencia debe ser un UUID.",
                    )
                if uid in seen:
                    issue(
                        "Referencial", location, "ID repetido en la relación."
                    )
                seen.add(uid)
                if ids[uid] != 1:
                    issue(
                        "Referencial",
                        location,
                        "El ID debe existir exactamente una vez en content/.",
                    )
                if uid == canonical_id(meta.get("id", "")):
                    issue(
                        "Referencial",
                        location,
                        "El documento no puede relacionarse consigo mismo.",
                    )
    if (
        not isinstance(meta.get("title"), str)
        or not str(meta.get("title", "")).strip()
    ):
        issue("Editorial", "title", "Añade un título no vacío.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", meta.get("slug", "")):
        issue(
            "Editorial",
            "slug",
            "Usa minúsculas ASCII, números y guiones simples.",
        )
    headings = heading_lines(body)
    if len(headings) != 1:
        issue(
            "Editorial",
            "Markdown / H1",
            f"Se requiere exactamente un H1; encontrados {len(headings)}. Líneas: {', '.join(map(str, headings)) or '—'}.",
        )
    if not re.fullmatch(
        r"[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8})*", meta.get("locale", "")
    ):
        issue(
            "Publicación",
            "locale",
            "Se requiere un locale válido, por ejemplo es o es-MX.",
        )
    if meta.get("status") not in WORKFLOW:
        issue("Publicación", "status", "Estado editorial no permitido.")
    if not body.strip():
        issue("Publicación", "Markdown", "El contenido no puede estar vacío.")
    if any(i["level"] == "error" for i in issues):
        issue(
            "Publicación",
            "requisitos acumulados",
            "Avance bloqueado hasta resolver todos los errores estructurales, editoriales y referenciales.",
        )
    else:
        issue(
            "Publicación",
            "destino",
            "Validación completa. published registra un estado en GitHub, no despliega contenido.",
            "info",
        )
    return issues


def check_transition(current: str, target: str, issues: list[dict[str, str]]):
    if target != current and target not in WORKFLOW.get(current, ["draft"]):
        raise ValueError(
            f"Transición no permitida: {current} → {target}. Sigue el circuito editorial."
        )
    if target in ("review", "approved", "published") and any(
        i["level"] == "error" for i in issues
    ):
        raise ValueError(
            "Avance bloqueado por errores publicables. Abre Validación / Preview para resolverlos."
        )
