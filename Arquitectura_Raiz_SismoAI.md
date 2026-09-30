# SismoAI Trainer --- Arquitectura Raíz y Procedimiento de Implementación

**Documento raíz.** Define la arquitectura objetivo y el orden
estratégico de desarrollo desde cero. La arquitectura de interfaz se
basa en PyWebView + HTML/CSS/JavaScript; Python conserva el estado, el
dominio científico, los datos, los procesos y la persistencia.

## 1. Arquitectura objetivo

### Capa A --- Aplicación

Python coordina el estado global y los servicios mediante un `AppState`
o controlador equivalente, sin convertirlo en una clase monolítica.

Responsabilidades: - Estado único de aplicación, navegación y módulo
activo. - Contexto del proyecto/sesión. - Estado global, operaciones
activas y errores. - Registro y coordinación de servicios. - Ciclo de
vida de la aplicación y arranque de PyWebView.

### Capa B --- Dominio y servicios

Módulos especializados, implementados únicamente cuando se alcance su
fase:

`project/`, `dataengine/`, `datos/`, `analysis/`, `windowing/`,
`labeling/`, `dataset/`, `models/`, `export/`, `settings/`.

Cada servicio define entradas, salidas, errores, cambios de estado,
notificaciones necesarias y pruebas. La lógica científica y las
decisiones de flujo pertenecen a Python.

### Capa C --- Puente Python--JavaScript

`bridge/api_bridge.py` expone operaciones controladas mediante
PyWebView. Los métodos devuelven estructuras serializables en JSON; el
frontend consume las llamadas mediante Promises a través de
`ui/js/bridge.js`.

### Capa D --- Interfaz web

HTML5, CSS y JavaScript presentan el estado recibido, recogen entradas y
reenvían acciones. No mantienen una copia autoritativa del estado ni
ejecutan cálculos de dominio.

## 2. Estructura de directorios

``` text
SismoAI Trainer/
├── core/
│   ├── dataengine/
│   ├── datos/
│   ├── analysis/
│   ├── windowing/
│   ├── labeling/
│   ├── dataset/
│   ├── models/
│   ├── export/
│   ├── project/
│   └── settings/
├── bridge/
│   ├── __init__.py
│   └── api_bridge.py
├── ui/
│   ├── assets/
│   │   ├── icons/
│   │   └── fonts/
│   ├── css/
│   │   ├── variables.css
│   │   ├── layout.css
│   │   └── components.css
│   ├── js/
│   │   ├── bridge.js
│   │   ├── app.js
│   │   └── charts.js
│   ├── views/
│   │   ├── proyecto.html
│   │   ├── datos.html
│   │   └── analisis.html
│   └── index.html
├── main.py
└── requirements.txt
```

Todo el trabajo de implementación de esta arquitectura se limita a
`SismoAI Trainer/`. No modificar archivos externos a esa carpeta.

## 3. Contratos obligatorios

1.  **Fuente única de verdad:** Python es propietario del estado de
    aplicación, proyecto, datos, análisis y flujo. JavaScript solo
    conserva estado temporal de presentación cuando sea imprescindible.
2.  **Colecciones dinámicas reales:** tablas y listas se construyen a
    partir de respuestas/modelos de Python; nunca se inventan filas,
    opciones o resultados.
3.  **Decisiones en Python:** clasificaciones, conteos, validaciones,
    disponibilidad de acciones, filtros, paginación y errores se
    calculan en servicios Python.
4.  **Estados explícitos:** cada pantalla representa, según aplique,
    `empty`, `loading`, `ready`, `unavailable` y `error`.
5.  **Fronteras de servicio:** entradas, salidas, errores, mutaciones y
    pruebas quedan definidos por módulo.
6.  **Interfaz defensiva:** JavaScript selecciona elementos solo por
    `data-action` o `id`, nunca por clases CSS para enlazar eventos o
    leer datos. Si falta un elemento, lo omite sin excepción fatal.
7.  **Controles nativos:** usar `select/option`, `input`
    checkbox/radio/number/range y `form`. No simular controles con
    `div`/`span` ni reemplazarlos con librerías pesadas.
8.  **Integridad:** no corregir datos silenciosamente ni
    modificar/sobrescribir BIN originales. No cambiar especificaciones
    del dataset sin autorización.
9.  **Diseño:** Penpot y `Diseños/` son autoridad visual. Centralizar
    colores, tipografía, tamaños y radios en `ui/css/variables.css`;
    enlazar Inter Variable y copiar los SVG indicados a
    `ui/assets/icons/`.
10. **Dependencias:** evitar dependencias innecesarias y mantener
    `main.py` como inicializador, no como módulo monolítico.

## 4. Contrato inicial del puente

  -------------------------------------------------------------------------------------------
  Método                                                  Función
  ------------------------------------------------------- -----------------------------------
  `select_data_folder()`                                  Diálogo nativo para elegir carpeta
                                                          de datos; devuelve ruta, conteo y
                                                          estado.

  `get_project_state()`                                   Devuelve el estado persistente de
                                                          sesión/proyecto.

  `scan_files()`                                          Lista BIN con metadatos.

  `get_quality_summary(file_name)`                        Métricas de calidad y continuidad.

  `get_channel_series(file_name, event_index, channel)`   Tiempos, amplitudes y frecuencia de
                                                          muestreo.

  `run_stalta(params)`                                    CFS y disparos STA/LTA.

  `run_spectrum(params)`                                  Frecuencias y magnitudes, con
                                                          ventana Hann/Hamming.

  `run_spectrogram(params)`                               Matriz de intensidades y ejes
                                                          temporal/frecuencial.
  -------------------------------------------------------------------------------------------

Este contrato se amplía por fases conforme aparezcan los servicios
correspondientes.

## 5. Procedimiento de implementación por fases

No desarrollar varias fases simultáneamente. Cada fase debe quedar
implementada, probada y aprobada antes de avanzar.

### Fase 0 --- Arquitectura técnica

-   Definir estructura de paquetes, responsabilidades y comunicación
    Python--JavaScript.
-   Especificar `AppState`, límites de servicios y formato de datos.
-   Documentar contratos y reglas de arquitectura.

**Entregable:** arquitectura técnica aprobada. No implementar módulos de
dominio.

### Fase 1 --- Sistema de diseño

-   Tomar Penpot como autoridad visual.
-   Definir colores, tipografía, espaciado, dimensiones, tarjetas,
    botones, tablas, inputs e indicadores.
-   Definir apariencias de estados vacíos, carga, no disponible, éxito y
    error.

**Entregable:** sistema visual aprobado.

### Fase 2 --- Shell + estado de aplicación

-   Crear el estado central Python y la navegación.
-   Exponer módulo/vista activa, estado global y errores mediante el
    puente.
-   Construir el Shell web: sidebar fija de 240 px, topbar y contenedor
    de vistas.
-   Enlazar acciones de navegación con Python; no duplicar el
    controlador en JavaScript.

**Aceptación:** arranque y navegación sin errores; estado de navegación
y status propiedad de Python.

**Entregable:** Shell funcional con estado central.

### Fase 3 --- Motor de datos

Implementar el procesamiento BIN según las especificaciones del
proyecto: - Encabezado y metadata. - Eventos y registros. - CRC y
commit. - Secuencias y marcas temporales. - Frecuencias y
discontinuidades. - Hallazgos de calidad y procedencia.

Preservar los archivos originales y no reparar ni reinterpretar datos
silenciosamente.

**Entregable:** motor Python validado.

### Fase 4 --- Proyecto y Datos

**Proyecto:** crear, abrir, guardar y cerrar proyectos; mantener
identidad y referencias de sesión; informar referencias faltantes o
inválidas.

**Datos:** importar y validar BIN; mantener la colección de archivos;
exponer archivos y eventos; mostrar detalles, calidad y validación;
permitir selección y filtrado sin duplicar estado en la interfaz.

**Aceptación:** acumular múltiples archivos; filas basadas en datos
reales; selección actualiza detalles; estados vacíos/error veraces; BIN
originales intactos.

**Entregable:** módulos Proyecto y Datos funcionales.

### Fase 5 --- Análisis

Implementar análisis sobre datos validados, en este orden: 1. Geófono.
2. Magnitud MPU únicamente. 3. Sincronización temporal. 4. Selección
visual. 5. Estadísticas. 6. Análisis de frecuencias. 7. Espectrograma.

Python conserva cálculos y estado; JavaScript representa series y
selecciones visuales.

**Entregable:** análisis de eventos con trazabilidad científica.

### Fase 6 --- Ventaneo

-   Duración e inicio/fin.
-   Solapamiento.
-   Ventanas fijas y deslizantes.
-   Selección manual.
-   Sincronización GEO/MPU.
-   Vínculo con evento fuente.

Cada ventana conserva archivo, evento e intervalo temporal de origen. No
mezclar eventos salvo configuración experimental explícita. Exponer
ventanas como colección derivada de Python.

**Entregable:** ventanas trazables listas para etiquetado.

### Fase 7 --- Etiquetado

Clases oficiales: - `0 = TEMBLOR` - `1 = NO_SISMICO` -
`2 = INDETERMINADO`

Gestionar fuente, confianza, perturbación, calidad, revisión y
observaciones según requisitos. Distinguir anotación humana de
sugerencia automática; una etiqueta automática no es verdad de terreno
verificada por defecto.

**Entregable:** ventanas etiquetadas y trazables.

### Fase 8 --- Dataset

-   Dataset maestro.
-   Distribución de clases.
-   Calidad y estadísticas.
-   Particiones train/validation/test.
-   Controles contra fuga de datos.

Ventanas del mismo evento/sesión no pueden repartirse entre
entrenamiento y prueba. Exponer registros y resúmenes desde Python.

**Entregable:** dataset reproducible.

### Fase 9 --- Modelos (objetivo inicial: ESP32-S3)

**Propósito:** diseñar, entrenar, optimizar, evaluar y versionar modelos de clasificación sísmica destinados inicialmente a ESP32-S3. El trabajo se ejecuta en PC; la validación física corresponde a la Fase 11.

**Flujo técnico y alcance, en orden:**

1. **Perfil de destino:** definir ESP32-S3 como hardware objetivo y registrar restricciones relevantes de memoria, runtime, operadores y formatos. Otras placas quedan fuera del alcance inicial.
2. **Entrada desde Dataset:** seleccionar una versión inmutable de la Fase 8 y recibir particiones train/validation/test, etiquetas, dimensiones, frecuencia de muestreo y preprocesamiento. Mantener separación por evento/sesión para evitar fuga de datos.
3. **Catálogo y contrato del modelo:** iniciar con baseline de reglas/características, clasificador de características y 1D-CNN. Cada modelo debe declarar forma y tipo de entrada, salida, clases, operaciones y preprocesamiento requerido. La selección se limita a arquitecturas cuya ruta de conversión pueda verificarse.
4. **Experimento y entrenamiento en PC:** registrar arquitectura, hiperparámetros, semilla, versión de librerías, configuración, logs, duración y artefactos. Python controla ejecución, estado, validaciones y persistencia.
5. **Exportación intermedia:** exportar desde el framework de entrenamiento a un formato admitido por la ruta seleccionada; utilizar ONNX cuando corresponda y comprobar equivalencia de entradas/salidas antes de continuar.
6. **Conversión y cuantización:** integrar ESP-PPQ conforme a la versión y flujo soportados por Espressif. Definir conjunto representativo de calibración separado de test; registrar esquema de cuantización, precisión, parámetros y versión de herramienta. Para ESP32-S3 considerar cuantización por tensor y estrategia simétrica basada en potencias de dos cuando aplique y esté soportada. No asumir compatibilidad universal ni fijar w8a8 como requisito sin verificarlo.
7. **Compatibilidad estática y recursos estimados:** revisar operadores, dimensiones, tipos, formato de pesos y requisitos del runtime ESP-DL. Registrar tamaño de artefactos y estimaciones de memoria; mostrar incompatibilidades y advertencias. Estas comprobaciones no certifican ejecución en placa.
8. **Evaluación comparativa:** evaluar modelo fuente y cuantizado sobre las particiones establecidas. Registrar accuracy, precision, recall, F1, matriz de confusión y falsos positivos/negativos, según pertinencia. Comparar degradación por cuantización y conservar resultados por clase.
9. **Preparación y biblioteca:** almacenar modelo fuente, modelo convertido/cuanti­zado, configuración, metadatos, procedencia, métricas, versiones de herramientas y auxiliares disponibles (por ejemplo, .espdl, .info y .json). Cada versión debe tener identificador único y vínculo al dataset/experimento.

**Criterios de salida:** modelo reproducible y trazable; contrato de entrada/salida documentado; conversión y cuantización registradas; evaluación comparativa disponible; compatibilidad estática revisada; artefactos y metadatos completos para que la Fase 10 pueda empaquetarlos. Los umbrales de aceptación de desempeño y degradación deben definirse antes de implementar las pruebas, no suponerse.

**Límites:** no modificar BIN originales ni redefinir el dataset; no entrenar en ESP32-S3; no reportar RAM/Flash/PSRAM o latencia como mediciones reales sin prueba física; no implementar soporte para otras placas; no duplicar el empaquetado final de la Fase 10.

**Integración:**
- **Fase 8:** consume dataset versionado, particiones, etiquetas, formas de señal y preprocesamiento.
- **Fase 10:** entrega versión seleccionada, modelos fuente/convertido, configuración, clases, preprocesamiento, métricas, procedencia y artefactos auxiliares. La Fase 10 genera y verifica el paquete de despliegue.
- **Fase 11:** mide en el dispositivo memoria real, latencia, estabilidad, inferencia y posibles pérdidas de muestras.

**Entregable:** modelos para ESP32-S3 evaluados, trazables y versionados, preparados para empaquetado y posterior validación física.

### Fase 10 --- Exportación

-   Recibir una versión de modelo seleccionada desde la biblioteca de
    la Fase 9.
-   Empaquetar el artefacto compatible con la ruta de despliegue
    ESP32-S3 definida por Espressif (inicialmente ESP-DL / formato
    .espdl, sujeto a la compatibilidad real del modelo y herramientas).
-   Incluir metadata, preprocesamiento, definiciones de clases,
    configuración de cuantización, versiones de herramientas y hash.
-   Validar integridad del paquete y documentar instrucciones de uso.

La implementación inicial debe seguir la documentación de Espressif
para ESP-DL y ESP-PPQ. Mantener una frontera de backend/perfil de destino
que permita incorporar otras placas más adelante, sin asumir que sus
formatos, operadores o restricciones son intercambiables.

**Entregable:** paquete de despliegue reproducible para ESP32-S3.

### Fase 11 --- Validación ESP32-S3

Verificar RAM, Flash y PSRAM; latencia e inferencia; frecuencia de
adquisición y pérdida de muestras; estabilidad y comportamiento de
clasificación.

**Entregable:** validación documentada en dispositivo.

### Fase 12 --- Integración final

Validar el flujo completo:

`BIN → Parser → Analysis → Windowing → Labeling → Dataset → Model → Export → ESP32-S3`

Comprobar trazabilidad de extremo a extremo y transiciones de estado
consistentes.

### Fase 13 --- Pruebas

Ejecutar pruebas unitarias, integración, BIN reales, GUI, recuperación
de errores, dataset, modelos y exportación. No avanzar con fallos
críticos sin resolver.

### Fase 14 --- Ejecutable

-   Congelar dependencias.
-   Configurar PyInstaller.
-   Incluir recursos web, fuentes e iconos.
-   Verificar rutas y ejecución.
-   Probar en Windows limpio.
-   Generar distribución y documentación mínima.

**Entregable:** `SismoAI_Trainer.exe`.

**Nota sobre numeración:** el documento de arquitectura de trabajo de
referencia define fases 0 a 14. No especifica una Fase 15; no se añade
ni se redefine sin una decisión explícita.

## 6. Ciclo obligatorio de trabajo

Para cada fase: 1. Definir objetivo y alcance. 2. Revisar dependencias y
especificaciones aplicables. 3. Implementar únicamente el alcance
aprobado. 4. Ejecutar la aplicación o ruta ejecutable pertinente. 5.
Ejecutar pruebas automatizadas. 6. Corregir fallos. 7. Documentar
archivos, comportamiento, pruebas, resultados y pendientes. 8. Solicitar
aprobación antes de la siguiente fase.

Mantener la aplicación ejecutable al cierre de cada fase. No combinar
fases ni implementar funcionalidades posteriores antes de disponer de
sus dependencias.

## 7. Protocolo Git y versionado

-   Crear la rama `feature/migracion-web-html`.
-   No trabajar directamente sobre ramas de producción sin autorización.
-   Registrar hitos en `Versiones.md` con formato estricto
    `MAJOR.MINOR.PATCH`.
-   Realizar commits atómicos por componente completado; no hacer
    commits sin autorización explícita.
-   No etiquetar, publicar ni desplegar sin autorización.

## 8. Informe de cierre por fase

Informar: 1. Archivos creados y modificados. 2. Arquitectura y
comportamiento implementados. 3. Responsabilidades Python e interfaz. 4.
Pruebas ejecutadas y resultados exactos. 5. Verificación GUI y
evidencia. 6. Pendientes y decisiones. 7. Confirmación de preservación
de especificaciones protegidas y BIN originales.
