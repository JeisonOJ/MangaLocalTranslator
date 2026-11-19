# Atribuciones y componentes externos

Fecha de revisión: 18 de noviembre de 2026. Este archivo distingue declaraciones verificadas de cuestiones pendientes. Las dependencias se instalan por separado. Sus textos legales originales y avisos deben conservarse si se redistribuyen copias de ellas.

| Componente | Procedencia y licencia verificada | Uso y alcance |
|---|---|---|
| Manga Image Translator | https://github.com/zyddnys/manga-image-translator, revisión `36fed8528d851f8e4cce8e35255e080f4138a8d3`; `pyproject.toml` declara GPL-3.0-only y `LICENSE` contiene GPLv3 | Detección, OCR, agrupación, CRF y LaMa mediante sus módulos. Se reconoce a sus autores y colaboradores. El checkout externo conserva sus avisos originales. |
| LaMa | https://github.com/advimman/lama/blob/main/LICENSE; Apache-2.0 | Implementación de inpainting utilizada a través del upstream. Conservar los avisos de autor y `NOTICE` aplicables al distribuir ese código. |
| PyDenseCRF | https://github.com/lucasb-eyer/pydensecrf; MIT, copyright (c) 2015 Lucas Beyer | La distribución conda-forge auditada es 1.0rc3, build `py312h72972c8_6`. Las bibliotecas nativas transitivas conservan sus términos. |
| PySide6 Essentials y Shiboken6 | Metadatos instalados 6.10.1: `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`; https://doc.qt.io/qtforpython-6/licenses.html | Qt Widgets. GPLv3 es compatible con esta aplicación. Revisar licencias de módulos y avisos al redistribuir Qt. |
| PyTorch y torchvision | Metadatos instalados: PyTorch incluye Apache-2.0, LLVM-exception, BSD, BSL-1.0 y MIT; torchvision declara BSD | Dependencias externas. Conservar la licencia compuesta y avisos de cada rueda si se distribuyen. CUDA y NVIDIA conservan sus condiciones propias. |
| NumPy, Pillow, OpenCV, psutil, Shapely y pyclipper | Metadatos instalados: NumPy BSD-3-Clause y componentes adicionales; Pillow MIT-CMU; OpenCV Apache-2.0; psutil y Shapely BSD-3-Clause; pyclipper MIT | Procesamiento, composición y monitorización locales. |
| einops, timm y Transformers | Metadatos instalados: MIT, Apache-2.0 y Apache-2.0, respectivamente | Dependencias del upstream, incluidas importaciones de backends que la aplicación no selecciona. |

La lista de versiones observadas está en `setup/constraints-tested.txt`. Esta tabla no es una auditoría legal exhaustiva de todas las dependencias transitivas. Para la publicación actual no se incluyen ruedas, DLL, entornos ni bibliotecas copiadas. Una futura distribución binaria requiere revisar los avisos completos de lo que se empaquete, incluidos Python, FreeType, bibliotecas numéricas y CUDA.

## Adaptaciones propias

`desktop/layout.py` adapta los experimentos locales `evaluation/scripts/typography_run02.py` y `page11_render_experiment.py`. Los parámetros y la secuencia de OCR, CRF y LaMa proceden de la integración evaluada con Manga Image Translator. Los scripts y la aplicación conservan estas referencias de procedencia. La extensión es un componente independiente desarrollado para este proyecto y se publica bajo la licencia general GPL-3.0-only.

## Pesos y datos de modelos — excluidos de la publicación

- Detector `detect-20241225.ckpt`, OCR `ocr_ar_48px.ckpt` y `alphabet-all-v7.txt` se obtienen de la release `beta-0.3` del upstream. Hay hashes de integridad conocidos. **Pendiente**: no se verificó una licencia específica independiente para cada artefacto o sus datos de entrenamiento. La licencia GPL del código no basta para afirmar que los pesos tienen la misma licencia. Antes de redistribuirlos debe aclararse el permiso con su proveedor.
- `dreMaz/AnimeMangaInpainting` declara MIT en su ficha de Hugging Face. El archivo usado es `lama_large_512px.ckpt` en la revisión `2953a4e935bf01ad1471f6cbfd26ab81abeeb92d`. **Verificado**: esa declaración del proveedor. **Pendiente**: alcance de los derechos del conjunto de entrenamiento y permisos adicionales que pudieran ser necesarios para redistribuir pesos o datos. https://huggingface.co/dreMaz/AnimeMangaInpainting
- Los experimentos históricos de NLLB declaran CC-BY-NC-4.0 y los de M2M100, MIT. Ninguno forma parte del flujo actual con Google ni se distribuye en este repositorio. https://huggingface.co/facebook/nllb-200-distilled-600M y https://huggingface.co/facebook/m2m100_418M

Las referencias y hashes permiten que un usuario obtenga los archivos del proveedor tras revisar sus términos. No se ofrecen garantías sobre derechos no expresamente concedidos. Estas incertidumbres no implican que se estén distribuyendo pesos en esta publicación de código fuente.

## Fuente tipográfica — requisito externo restringido

La aplicación actual espera `upstream/fonts/Arial-Unicode-Regular.ttf`. El archivo local se identifica como **Arial Unicode MS**, con el aviso original siguiente:

> Digitized data copyright (C) 1993-2000 Agfa Monotype Corporation. All rights reserved.

Sus metadatos contienen una notificación de licencia que restringe copia y distribución salvo derechos adicionales. El archivo y el resto de fuentes locales están excluidos. La presencia del archivo en un repositorio de terceros no acredita permiso de redistribución. El usuario debe disponer de una copia y licencia válidas para su uso. La instalación documentada conserva el renderizador y requiere suministrar legalmente esa fuente por separado. https://learn.microsoft.com/en-us/typography/font-list/arial-unicode-ms

No se ha elegido ni incluido una fuente libre alternativa en esta preparación. Reemplazarla exigiría verificar su licencia y revisar el resultado tipográfico. Tampoco se han autorizado para redistribución otras fuentes presentes en el checkout local.

## Servicios y contenido

Google Cloud Translation Basic v2 es un servicio externo sujeto a las condiciones de Google y del proyecto del usuario. Las solicitudes contienen texto japonés. Las claves propias, credenciales, originales de manga, respuestas y capítulos traducidos quedan fuera de la publicación. Los nombres de tecnologías y marcas pertenecen a sus titulares.
