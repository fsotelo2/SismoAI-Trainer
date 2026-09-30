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

**Propósito:** diseñar, entrenar, optimizar, evaluar y versionar modelos
de clasificación sísmica destinados inicialmente a ejecutarse en
ESP32-S3. Esta fase se desarrolla en el entorno de PC; no realiza aún
la validación física en la placa, que corresponde a la Fase 11.

**Alcance funcional, en orden:**

1. **Perfil de destino ESP32-S3:** fijar el objetivo de despliegue y las
   restricciones relevantes de memoria, operadores y runtime. Mantener
   el diseño extensible mediante perfiles futuros para otras placas,
   sin implementar esos perfiles en esta fase.
2. **Catálogo de modelos:** baseline de reglas/características,
   clasificador de características y 1D-CNN. Registrar para cada
   arquitectura sus entradas, salidas, preprocesamiento y operaciones
   requeridas. La selección final queda condicionada a la compatibilidad
   documentada de ESP-DL.
3. **Configuración del experimento:** seleccionar dataset y versión de
   la Fase 8; definir particiones, semilla, hiperparámetros, métricas y
   configuración de entrenamiento. Conservar la referencia inmutable
   al dataset utilizado.
4. **Entrenamiento en PC:** ejecutar y registrar entrenamientos,
   configuraciones, logs, duración y artefactos. Python es responsable
   del estado, ejecución, validaciones y persistencia.
5. **Conversión y cuantización:** exportar el modelo entrenado a ONNX
   cuando corresponda y utilizar ESP-PPQ para calibración y cuantización
   conforme a la ruta soportada por Espressif. Contemplar esquemas
   como w8a8 y otros únicamente si la versión integrada los admite.
6. **Compatibilidad y recursos:** verificar operadores soportados,
   dimensiones de entrada, formato, tamaño de pesos y estimaciones de
   memoria. Mostrar advertencias o bloquear la preparación cuando haya
   incompatibilidades conocidas; no declarar aptitud de ejecución real
   solo por superar estas verificaciones.
7. **Evaluación y comparación:** calcular métricas sobre los conjuntos
   definidos, incluyendo precisión, recall, F1, matriz de confusión,
   falsos positivos y falsos negativos. Comparar el modelo de referencia
   con el cuantizado y registrar la variación de desempeño.
8. **Biblioteca y versionado:** conservar modelo fuente, configuración,
   versión de herramientas, dataset de origen, métricas y artefactos
   generados, incluyendo el modelo cuantizado y los archivos auxiliares
   disponibles (por ejemplo, .espdl, .info y .json).

**Límites:** no modificar BIN originales ni redefinir el dataset; no
entrenar en el ESP32-S3; no afirmar rendimiento de RAM, Flash o latencia
medido en placa; no implementar todavía soporte para otras placas; no
duplicar el empaquetado final que pertenece a la Fase 10.

**Integración con fases vecinas:**
- **Entrada desde Fase 8:** identificador/versión del dataset,
  particiones train/validation/test, etiquetas, forma de las señales y
  preprocesamiento. Evitar fuga de datos y preservar la separación por
  evento/sesión establecida en Dataset.
- **Salida hacia Fase 10:** versión seleccionada, modelo fuente y
  cuantizado, configuración, metadatos, clases, preprocesamiento,
  métricas, procedencia y archivos auxiliares. La Fase 10 se encarga del
  empaquetado y la generación del paquete de despliegue.
- **Relación con Fase 11:** la compatibilidad estática se revisa aquí;
  RAM/Flash/PSRAM, latencia, inferencia, estabilidad y pérdida de
  muestras se miden posteriormente en el dispositivo.

**Entregable:** modelos para ESP32-S3 evaluados, trazables y versionados,
con artefactos preparados para el empaquetado de la Fase 10.

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
