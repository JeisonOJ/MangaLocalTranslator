# Instalación de desarrollo en Windows

Esta guía describe el entorno del equipo validado. La preparación de la publicación no instaló paquetes ni repitió una instalación desde cero. Las versiones pueden dejar de estar disponibles en sus proveedores. Un fallo de resolución debe revisarse antes de sustituir versiones, especialmente NumPy, PyDenseCRF y PyTorch.

## 1. Código y upstream fijado

Obtenga el código de MangaLocalTranslator y abra PowerShell en su raíz. Se necesita Git y micromamba o una herramienta compatible con entornos conda. Los comandos siguientes son instrucciones para una nueva instalación; no los ejecute sobre un entorno o checkout local que ya funciona.

```powershell
Set-Location C:\ruta\MangaLocalTranslator
git clone --filter=blob:none --no-checkout https://github.com/zyddnys/manga-image-translator.git upstream
git -C upstream sparse-checkout init --cone
git -C upstream sparse-checkout set manga_translator
git -C upstream checkout --detach 36fed8528d851f8e4cce8e35255e080f4138a8d3
git -C upstream rev-parse HEAD
```

La selección parcial obtiene los módulos y archivos raíz del upstream conservando sus avisos, y evita descargar sus directorios de ejemplos y fuentes. No ejecute sus requisitos completos encima del entorno descrito aquí. Incluyen componentes no utilizados y una variante de PyDenseCRF que requiere compilación.

## 2. Entorno local y dependencias

El archivo `setup/crf312-windows-explicit.lock` conserva las URLs y hashes del entorno conda-forge validado con Python 3.12, NumPy y PyDenseCRF. No contiene paquetes binarios. La sustitución de PyDenseCRF por la distribución conda-forge está documentada en `evaluation/COMPILER-FREE-RESULT.md`.

```powershell
micromamba create --yes --prefix .\evaluation\envs\crf312 --file .\setup\crf312-windows-explicit.lock
& .\evaluation\envs\crf312\python.exe -m pip install --index-url https://download.pytorch.org/whl/cu130 --constraint .\setup\constraints-tested.txt "torch==2.14.1+cu130" "torchvision==0.29.1+cu130"
& .\evaluation\envs\crf312\python.exe -m pip install --constraint .\setup\constraints-tested.txt --requirement .\setup\requirements.txt
& .\evaluation\envs\crf312\python.exe -I .\evaluation\scripts\validate_crf_api.py
& .\evaluation\envs\crf312\python.exe -m pip check
& .\evaluation\envs\crf312\python.exe -B -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

Micromamba puede registrar el entorno en su configuración de usuario. No hace falta activar el entorno, modificar el PATH del sistema ni instalar un compilador para esta combinación validada. PyTorch incluye su runtime CUDA. Un controlador NVIDIA compatible debe estar instalado por el usuario.

`requirements.txt` conserva las dependencias directas utilizadas, incluida PySide6 Essentials 6.10.1. `constraints-tested.txt` registra las versiones instaladas observadas, también las transitivas. Algunas bibliotecas de otros proveedores de traducción son necesarias por importaciones anticipadas del upstream; la aplicación selecciona exclusivamente Google Basic v2. `langdetect` y `unidic-lite` pueden construirse desde distribuciones de código Python/datos. La evaluación previa los construyó sin un compilador C++.

La instalación histórica de dependencias descargó aproximadamente 2,46 GB y ocupó unos 4,6 GB antes de añadir Qt. Las cifras no incluyen el checkout, los modelos ni los capítulos y no garantizan el espacio de futuras instalaciones.

## 3. Modelos locales

Revise las licencias e incertidumbres en `THIRD_PARTY_NOTICES.md`. `setup/models.json` contiene exactamente los cuatro artefactos usados por el flujo actual, con origen, revisión, ruta relativa, tamaño y SHA-256. Suman 717.401.692 bytes, aproximadamente 717 MB. No contiene los pesos ni selecciona NLLB o M2M100.

Para descargarlos voluntariamente en una nueva instalación y verificar su integridad:

```powershell
$modelos = Get-Content .\setup\models.json -Raw | ConvertFrom-Json
foreach ($modelo in $modelos) {
    $destino = Join-Path (Get-Location) $modelo.path
    New-Item -ItemType Directory -Force -Path (Split-Path $destino) | Out-Null
    if (-not (Test-Path -LiteralPath $destino)) {
        Invoke-WebRequest -Uri $modelo.url -OutFile $destino
    }
    $hash = (Get-FileHash -LiteralPath $destino -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $modelo.sha256 -or (Get-Item -LiteralPath $destino).Length -ne $modelo.size) {
        throw "Tamaño o SHA-256 incorrecto en $($modelo.path)"
    }
}
```

Fuentes verificadas por el historial local:

| Ruta relativa bajo `evaluation/models/` | SHA-256 |
|---|---|
| `detection/detect-20241225.ckpt` | `67ce1c4ed4793860f038c71189ba9630a7756f7683b1ee5afb69ca0687dc502e` |
| `ocr/ocr_ar_48px.ckpt` | `29daa46d080818bb4ab239a518a88338cbccff8f901bef8c9db191a7cb97671d` |
| `ocr/alphabet-all-v7.txt` | `f5722368146aa0fbcc9f4726866e4efc3203318ebb66c811d8cbbe915576538a` |
| `inpainting/lama_large_512px.ckpt` | `11d30fbb3000fb2eceae318b75d9ced9229d99ae990a7f8b3ac35c8d31f2c935` |

Detector, OCR y alfabeto proceden de la release upstream `beta-0.3`. LaMa procede de `dreMaz/AnimeMangaInpainting`, revisión `2953a4e935bf01ad1471f6cbfd26ab81abeeb92d`. Los checkpoints son archivos de terceros y deben proceder de fuentes de confianza. El hash comprueba identidad e integridad, no una licencia ni la seguridad absoluta de un modelo serializado.

## 4. Fuente tipográfica suministrada por el usuario

El renderizador validado espera una copia de **Arial Unicode MS** en `upstream/fonts/Arial-Unicode-Regular.ttf`. Esa fuente es externa y restringida. Obtenga una copia legítima y compruebe que su licencia autoriza el uso previsto. Cree el directorio `upstream/fonts` y coloque su copia legal en esa ruta. No publique el archivo ni lo incluya en un ZIP del proyecto. Los términos pueden consultarse con su proveedor. https://learn.microsoft.com/en-us/typography/font-list/arial-unicode-ms

No use un archivo hallado en un repositorio como prueba de permiso. Esta preparación conserva el renderizador actual; no incorpora ni afirma haber validado una fuente libre de reemplazo. Sin una fuente disponible legalmente, esta instalación no está lista para procesar páginas. La publicación del código fuente excluye todos los archivos tipográficos.

## 5. Aplicación, clave y pruebas

Abra `MangaLocalTranslator.vbs`, o ejecute `evaluation\envs\crf312\python.exe -B -m desktop.gui` desde la raíz. Si Windows deshabilita VBScript, cree un acceso directo al comando siguiente:

```text
"C:\ruta\MangaLocalTranslator\evaluation\envs\crf312\pythonw.exe" -B "C:\ruta\MangaLocalTranslator\desktop\launch.pyw"
```

Configure una clave propia desde **Configure Google API Key**. La aplicación usa el Administrador de credenciales de Windows bajo `MangaLocalTranslator/GoogleCloudTranslation`. El borrado afecta a la clave guardada. Una variable de entorno `MANGA_GOOGLE_TRANSLATE_API_KEY` no vacía sigue teniendo prioridad y debe retirarse por separado si se desea usar la guardada. No coloque claves en archivos del repositorio ni en comandos guardados.

Comience con la casilla de Google desmarcada y una carpeta de salida de prueba. El texto `Texto de prueba.` permite revisar el proceso local. Para un trabajo real, elija otra base de salida, habilite Google y pulse **Start**, que autoriza las solicitudes de ese trabajo. Los informes registran caracteres y resultados. Los errores ambiguos no se reintentan automáticamente.

Las pruebas locales están en el README principal. Las pruebas unitarias de escritorio no cargan modelos ni llaman a Google. Los ensayos históricos con manga usaron muestras privadas excluidas. Para repetir ensayos de imagen, aporte sus propias muestras autorizadas.
