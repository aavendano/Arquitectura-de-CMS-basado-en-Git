# Esquemas editoriales

Los esquemas se leen de archivos `.yaml`, `.yml` o `.json` bajo `schemas/` y `.cms/schemas/` en la rama seleccionada. Cada archivo declara un tipo. Sin archivos se usa `article` y campos base. Un esquema inválido bloquea la carga, no se ignora silenciosamente.

La raíz contiene `type` (identificador del tipo) y `fields`. `fields` puede ser una lista de definiciones con `name`, o un mapa cuya clave es el nombre del campo. Cada definición admite `label`, `type`, `required`, `options`, `default` y `rules`. Los campos base se incluyen siempre; pueden personalizarse. `id`, `type` y `body` están reservados.

Tipos: `string`, `text`, `markdown`, `number`, `integer`, `boolean`, `date` (AAAA-MM-DD), `select`, `relation`, `relations`, `array`, `object`. Objetos y listas se editan como JSON. Las opciones son valores de texto. Relaciones se guardan como UUID o lista de UUID, nunca como rutas. Solo los documentos que ya tienen UUID persistido aparecen en los selectores.

Reglas soportadas: `min`, `max`, `min_length`, `max_length`, `pattern` (expresión regular Python aplicada al valor completo). Usa límites numéricos y patrones de confianza, sencillos y acotados. Reglas desconocidas y tipos no soportados bloquean la carga. Los campos requeridos y las reglas se comprueban también al guardar borradores.

Los documentos heredados sin UUID reciben uno al abrirse y se persiste al guardar; el identificador provisional del enlace solo permite encontrarlos antes de esa migración. Mover o cambiar título/slug de un documento guardado no cambia su UUID. El cuerpo y todo el frontmatter permanecen en un único archivo Markdown. Metadatos adicionales se conservan y pueden editarse como objeto JSON; fechas YAML adicionales se normalizan a texto ISO. El formato y los comentarios YAML pueden cambiar al serializar.

Cada guardado compara el SHA remoto del archivo con el cargado, genera un árbol y un commit, y actualiza la rama sin force. Renombrar elimina la antigua entrada y crea la nueva en el mismo commit. Si la rama avanzó durante la operación, GitHub rechaza la actualización; conserva tus ediciones antes de recargar. Crear o duplicar no reemplaza rutas existentes. Duplicar prepara una copia local y requiere guardar explícitamente.

Cambiar el estado no despliega contenido externamente. Archivar no elimina archivos. `/preview/[id]` lee el archivo real, los esquemas y las referencias del mismo snapshot de GitHub. Stored muestra el archivo actual; validated habilita la lectura solo sin errores; published busca la última versión histórica con ese estado, siguiendo renombres registrados por GitHub. Un fallo de historial se distingue de un historial sin publicaciones.

El circuito permite draft → review → approved → published → archived; review puede volver a draft, approved y published a draft/review, archived a draft. También se permite archivar desde los estados de trabajo. La tabla WORKFLOW centraliza las transiciones. Review, approved y published requieren todos los controles, incluso al guardar desde el editor. Cada escritura vuelve a leer el esquema y referencias del snapshot que se usa como padre del commit y compara el SHA del archivo. No se fuerza la rama.

La validación acumula errores de tipos, campos requeridos, opciones, fechas y reglas del esquema; título, slug y H1 Markdown; UUID únicos y referencias existentes sin duplicados; locale, contenido y estado. Los bloques de código no cuentan como H1; se admiten encabezados ATX y Setext. Un documento ilegible del índice bloquea la certificación referencial. HTML crudo y fórmulas se desactivan al renderizar Markdown. El centro de operaciones Git continúa fuera de esta fase.
