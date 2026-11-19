# Revisión manual previa a publicar

La publicación prevista incluye `desktop/`, `extension/`, `MangaLocalTranslator.vbs`, las pruebas, `setup/`, los textos legales y la documentación. `evaluation/` conserva scripts e informes técnicos históricos. Sus artefactos grandes y muestras privadas quedan excluidos. El checkout `upstream/` se obtiene por separado en la revisión documentada.

No se han preparado instaladores, ejecutables congelados, modelos, fuentes, capítulos ni traducciones para redistribución. Los patrones de `.gitignore` excluyen también imágenes y fuentes por extensión para reducir inclusiones accidentales en otras rutas. Un futuro recurso visual autorizado requerirá una inclusión explícita revisada. Las exclusiones no eliminan archivos existentes ni dejan de rastrear automáticamente archivos ya confirmados.

Antes de agregar archivos, revise `git status --short`, `git ls-files` y `git ls-files --others --exclude-standard`. Compruebe que los archivos públicos son texto esperado y que no hay claves, resultados de usuarios ni rutas personales. Evite agregar el workspace entero desde el Explorador o subir un ZIP de la carpeta local, pues contendría archivos excluidos de Git. Revise el diff preparado manualmente antes de confirmar.

## Correo de autor en el historial

El commit `679edf324f10d12d08972d801ece0f1de6e11e75` contiene un correo personal en los metadatos de autor y committer. No se reproduce aquí. Opciones disponibles:

- Conservar el historial y aceptar expresamente que ese correo se publique.
- Configurar un correo `noreply` de GitHub para futuros commits. Esto no cambia el commit existente.
- Autorizar por separado una modificación del commit raíz para cambiar autor/committer. Esto cambiaría su hash y cualquier descendiente.
- Crear más adelante un repositorio público nuevo desde un conjunto de fuentes revisado, con una identidad pública elegida y conservando este repositorio local. Es otra decisión explícita, no un paso ejecutado por esta preparación.

No se ha cambiado la identidad Git ni reescrito el historial. La revisión debe resolver esta decisión antes de publicar la rama que contiene el commit original. Los refs locales de herramientas bajo `refs/codex/` no forman parte de la publicación prevista. Cuando se autorice una publicación futura, seleccione únicamente la rama y etiquetas revisadas, sin usar un espejo de todos los refs.

## Licencias pendientes

Para publicar estas fuentes se han añadido GPL-3.0-only, el texto oficial y las atribuciones. Los checkpoints y las fuentes están fuera del conjunto previsto. La falta de una concesión específica verificada para ciertos pesos debe aclararse antes de redistribuirlos. La fuente Arial Unicode MS requiere una licencia externa para ejecutar el renderizador actual. La ficha MIT del checkpoint afinado de LaMa no sustituye a la licencia Apache-2.0 de su código ni demuestra derechos sobre cada imagen de entrenamiento.

Una revisión jurídica exhaustiva de dependencias y un empaquetado de binarios pueden posponerse mientras la publicación se limite a fuentes y documentos. Los derechos de los componentes externos y la decisión sobre el correo del historial deben permanecer explícitos.
