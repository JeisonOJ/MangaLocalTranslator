# MangaLocalTranslator — traductor experimental de manga al español

Proyecto personal desarrollado como hobby para capturar capítulos y traducir manga japonés al español en Windows. Utiliza detección, OCR y reconstrucción locales con NVIDIA CUDA, y Google Cloud Translation Basic v2 para traducir únicamente el texto japonés. Su creador ha probado manualmente el flujo completo, incluida la lectura del capítulo resultante. Se comparte de forma experimental, sin garantía de calidad, mantenimiento ni soporte.

## Funciones

- Extensión independiente para Microsoft Edge que descarga imágenes originales mediante una selección manual y navegación con flechas o un control elegido por el usuario.
- Aplicación PySide6 que procesa un capítulo secuencialmente, muestra el progreso y permite detener el trabajo.
- Detección y OCR japoneses locales, refinamiento CRF y reconstrucción con LaMa Large.
- Traducción de texto con Google y composición local en español con ajuste de palabras completas.
- Modo de prueba sin solicitudes a Google y registro de errores y aspectos que requieren revisión.
- Conservación de los originales y organización automática de la salida por manga y capítulo.

## Requisitos

Windows de 64 bits, Python 3.12 en el entorno local del proyecto y una GPU NVIDIA compatible con la versión de PyTorch instalada. El equipo probado tiene una RTX 3050 de 8 GB, 16 GB de RAM y Ryzen 5 5600X. El entorno validado usa PyTorch 2.14.1 con CUDA 13.0. No se ha validado funcionamiento con GPU AMD, macOS, Linux ni configuraciones de menor memoria. Reserve varias decenas de GB para dependencias, modelos y capítulos.

Google requiere un proyecto con Cloud Translation API habilitada, facturación y una clave propia. Las solicitudes pueden generar cargos. Las imágenes permanecen en el equipo. El texto japonés extraído se envía a Google cuando se autoriza un trabajo real.

## Instalación

La publicación contiene código fuente y documentación. El entorno, los modelos y las fuentes se obtienen por separado. Consulte la [guía de instalación](docs/INSTALACION.md) para reproducir el entorno de Windows, obtener el upstream fijado, verificar los modelos y resolver el requisito de la fuente tipográfica.

La revisión de Manga Image Translator utilizada es `36fed8528d851f8e4cce8e35255e080f4138a8d3`. Los requisitos y los cuatro archivos necesarios del modelo están documentados en `setup/`. Los scripts antiguos de `evaluation/` conservan el historial de experimentación y algunas rutas del equipo original. La aplicación actual utiliza Google y el entorno documentado en la guía.

## Configuración y uso

1. Abra `MangaLocalTranslator.vbs` desde el Explorador de Windows. El lanzador utiliza `evaluation\envs\crf312\pythonw.exe` y muestra la aplicación sin una consola permanente.
2. En **Configure Google API Key**, elija introducir o reemplazar la clave. La entrada está enmascarada y se guarda en el Administrador de credenciales de Windows. También puede eliminarla desde esa acción. Una variable de entorno `MANGA_GOOGLE_TRANSLATE_API_KEY` no vacía tiene prioridad sobre la clave guardada.
3. Seleccione la carpeta del capítulo y la carpeta base de salida. La aplicación muestra el destino calculado antes de comenzar.
4. Para un trabajo real, marque la casilla de Google y pulse **Start**. Con la casilla desmarcada, el modo local utiliza texto de prueba para comprobar el flujo.
5. Revise las páginas y el archivo `.manga-review-*.json` al terminar. **Stop** detiene el trabajo en el siguiente punto de control y conserva las páginas completadas.

La jerarquía de entrada determina la salida. Por ejemplo, `Mangas\nue no onmyouji\Capítulo 01`, con base `Mangas Español`, produce `Mangas Español\nue no onmyouji\Capítulo 01`. Se conservan los nombres y formatos JPG, PNG y WebP. Las páginas de salida existentes se omiten. El destino debe estar separado del capítulo original. Para probar el modo local y después Google, utilice bases de salida distintas.

Para crear un acceso directo, use **Nuevo → Acceso directo** en el escritorio, asígnele el nombre **MangaLocalTranslator** y utilice este destino ajustado a la ubicación del proyecto:

```text
wscript.exe "C:\ruta\MangaLocalTranslator\MangaLocalTranslator.vbs"
```

También puede iniciar la aplicación desde la raíz del proyecto:

```powershell
& .\evaluation\envs\crf312\python.exe -B -m desktop.gui
```

Para capturar capítulos, abra `edge://extensions`, active el modo de desarrollador y cargue la carpeta `extension/` como extensión descomprimida. Seleccione la imagen y el método de navegación, pruebe una descarga y limite el número de páginas. Los controles y permisos se describen en la documentación existente de la extensión.

## Limitaciones y privacidad

El OCR y Google pueden omitir o interpretar mal texto, expresiones coloquiales y términos propios de la historia. La reconstrucción puede dejar caracteres japoneses, furigana, manchas o daños en ilustraciones. La composición puede invadir bordes o perder legibilidad. La detección de efectos sonoros es limitada. La evaluación final corresponde al usuario.

El procesamiento requiere memoria disponible y puede detenerse por falta de RAM o VRAM. No se reintentan automáticamente solicitudes ambiguas de Google. Revise el registro antes de repetir un trabajo que haya fallado. Los informes locales contienen texto reconocido y traducciones. No los publique junto con capítulos sin revisar su contenido y los derechos correspondientes.

Los derechos sobre manga, traducciones, modelos y fuentes pertenecen a sus respectivos titulares. Utilice contenido que esté autorizado a procesar o descargar. Las fuentes y los pesos de terceros tienen condiciones independientes de la licencia del programa.

## Pruebas sin conexión

Con el entorno instalado, desde la raíz:

```powershell
& .\evaluation\envs\crf312\python.exe -B -m unittest discover -s desktop/tests -v
node --test extension/tests/*.test.js
npm --prefix extension run check
```

Las pruebas de escritorio usan almacenamiento de credenciales simulado y solicitudes de Google simuladas. No necesitan claves reales ni ejecutan traducciones facturables. Las pruebas de la extensión requieren Node.js y utilizan un navegador simulado.

## Desarrollo asistido por IA

Este proyecto fue desarrollado como hobby con la ayuda de herramientas de inteligencia artificial, utilizadas principalmente para asistir en la programación y resolución de problemas. Las decisiones sobre su funcionamiento, las pruebas y la dirección del proyecto fueron realizadas por su creador.

## Licencia y atribuciones

El código del proyecto se publica bajo **GPL-3.0-only**. El texto oficial se conserva en inglés en [LICENSE](LICENSE). Manga Image Translator y los demás componentes mantienen sus autores y condiciones originales. Consulte [LICENSING.md](LICENSING.md) y [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) para conocer el alcance, las atribuciones verificadas y las cuestiones pendientes.
