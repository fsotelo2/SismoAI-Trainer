# SismoAI Trainer

## Fase 6 --- Ventanas

**Especificación funcional y técnica**\
**Estado:** Propuesta consolidada para revisión previa a implementación\
**Versión del documento:** 0.1.0

------------------------------------------------------------------------

## 1. Propósito

La Fase 6 convierte registros y eventos validados en segmentos
temporales trazables, revisables y preparados para la Fase 7 ---
Etiquetado.

El módulo debe permitir dos estrategias complementarias:

1.  **Segmentación automática:** generar ventanas a lo largo de un
    registro mediante modo fijo o deslizante.
2.  **Selección manual:** marcar un intervalo arbitrario del registro y
    extraerlo como ventana, especialmente útil para recuperar eventos
    sísmicos reales poco frecuentes.

La fase no determina si una señal es un sismo ni asigna etiquetas. Esa
decisión corresponde a Etiquetado.

## 2. Alcance y límites

### Incluye

-   Selección del archivo BIN y del evento de origen.
-   Visualización temporal del registro completo y de las ventanas.
-   Configuración y ejecución de segmentación fija y deslizante.
-   Selección manual de intervalos por interacción gráfica o ingreso
    numérico.
-   Inspección de señales GEO y MPU.
-   Validaciones técnicas, estados de calidad y selección de ventanas.
-   Trazabilidad de cada ventana hasta su archivo, evento, intervalo y
    configuración.
-   Transferencia de ventanas elegibles a Etiquetado.

### No incluye

-   Clasificación sísmica automática ni asignación de etiquetas
    oficiales.
-   Modificación del BIN original.
-   Corrección silenciosa de discontinuidades o alteraciones de la
    señal.
-   Construcción o entrenamiento de modelos.
-   Definición definitiva de umbrales científicos no validados.

## 3. Principios de diseño

-   **Python es autoritativo:** controla estado, dominio, segmentación,
    validaciones y persistencia.
-   **La interfaz presenta y solicita acciones:** no implementa lógica
    científica ni altera por sí sola los datos.
-   **Integridad del origen:** los BIN se conservan intactos.
-   **Trazabilidad completa:** toda ventana conserva la procedencia y
    los parámetros que la generaron.
-   **Separación de conceptos:** registro, evento, intervalo de interés,
    ventana y etiqueta son entidades distintas.
-   **Sin mezcla accidental:** no se combinan eventos diferentes en una
    misma ventana salvo que una configuración experimental lo permita
    explícitamente.
-   **Configuración explícita:** los parámetros aún no validados se
    exponen como configurables y se documentan.

## 4. Arquitectura funcional

### 4.1 Python --- motor de ventanas

Responsabilidades: - Recibir archivo, evento, modo y parámetros. -
Recuperar las señales y metadatos necesarios. - Generar los intervalos
de ventana. - Resolver la correspondencia temporal entre sensores cuando
proceda. - Evaluar reglas de calidad. - Crear identificadores y
registros de ventana. - Mantener la colección derivada de ventanas. -
Proporcionar a la interfaz datos de resumen, detalle y vista previa. -
Preparar la transferencia a Etiquetado.

### 4.2 Interfaz

Responsabilidades: - Seleccionar archivo y evento. - Cambiar entre
segmentación automática y selección manual. - Configurar parámetros
habilitados para la operación. - Visualizar el registro completo y los
límites de ventanas/intervalos. - Seleccionar, inspeccionar, incluir,
excluir o marcar para revisión. - Mostrar incidencias y procedencia. -
Solicitar la generación, extracción y envío.

### 4.3 Integración

Las ventanas deben exponerse como una colección derivada gestionada por
Python. La Fase 7 recibe identificadores y datos/referencias
recuperables, junto con procedencia, sensores, calidad y configuración.

## 5. Estructura visual propuesta

La pantalla mantiene el lenguaje visual del módulo Análisis: navegación
lateral, encabezado, tarjetas de contenido, señales en azul/violeta,
estados de calidad y barra de acciones inferior.

### 5.1 Selector de operación

En la parte superior se muestran dos opciones principales: -
**Segmentación automática:** abre los controles de modo
fijo/deslizante. - **Selección manual:** abre las herramientas de
selección de intervalo.

El resumen del registro puede permanecer visible en ambas operaciones:
archivo, duración total, evento seleccionado y sensores/frecuencias
disponibles.

### 5.2 Vista de segmentación automática

-   Panel de configuración.
-   Vista general del registro con marcas de ventanas generadas.
-   Lista de ventanas generadas.
-   Vista previa de la ventana seleccionada.
-   Panel de información y calidad.
-   Barra inferior con selección, exclusión y envío a Etiquetado.

### 5.3 Vista de selección manual

-   Gráficas del registro completo, con eje temporal global.
-   Marcadores de inicio y fin del intervalo seleccionado.
-   Herramientas para seleccionar, limpiar y ajustar el intervalo.
-   Campos numéricos de inicio y fin; duración calculada.
-   Selección de sensores disponibles.
-   Acción **Añadir ventana a la lista**.
-   Tabla de ventanas extraídas manualmente.
-   Vista previa de la ventana seleccionada y sus metadatos.

La selección manual debe permitir intervalos de duración arbitraria
dentro de los límites del registro, sin obligar a que coincidan con una
cuadrícula automática.

## 6. Operación A --- Segmentación automática

### 6.1 Parámetros comunes

-   Archivo BIN.
-   Evento validado.
-   Modo: fijo o deslizante.
-   Duración de ventana.
-   Sensores: GEO y/o MPU, según disponibilidad y configuración.
-   Parámetros de calidad aplicables.

La duración del registro no limita la segmentación a una longitud
estándar. Debe funcionar con registros de distintas duraciones,
incluidos registros de hasta varios minutos, dentro de las capacidades
del sistema.

### 6.2 Modo fijo

Las ventanas se generan consecutivamente. En la configuración base, el
paso es igual a la duración y no existe solapamiento.

Ejemplo: duración 5 s, paso 5 s: - W-001: 0--5 s - W-002: 5--10 s -
W-003: 10--15 s

Si el final del registro no completa otra ventana, el comportamiento
(descartar, conservar como ventana parcial o configurar) debe definirse
explícitamente antes de implementar y probarse.

### 6.3 Modo deslizante

Las ventanas tienen duración constante y el inicio avanza según un paso
configurable. Puede existir solapamiento.

Ejemplo: duración 5 s, paso 2.5 s: - W-001: 0--5 s - W-002: 2.5--7.5 s -
W-003: 5--10 s

El solapamiento se calcula a partir de duración y paso. Debe mostrarse
al usuario. La validación de valores (por ejemplo, paso mayor que cero y
no mayor que la duración si se requiere solapamiento) se implementará en
Python y se reflejará en la interfaz.

### 6.4 Resultado automático

La ejecución produce una colección de ventanas con límites temporales,
sensores, muestras/referencias, calidad, configuración y procedencia. El
listado permite filtrar por calidad, sensores y estado de selección.

## 7. Operación B --- Selección manual

### 7.1 Objetivo

Extraer un intervalo de interés directamente del registro original. Esta
operación es esencial cuando los eventos reales son escasos y no
coinciden con los límites de la segmentación automática.

Ejemplo: registro de 180 s; evento identificado entre 72 y 77 s. El
usuario extrae 72--77 s como ventana de 5 s, sin procesar los 180 s como
una sola muestra.

### 7.2 Interacción

El usuario puede: - Arrastrar sobre la señal para definir inicio y
fin. - Ajustar ambos tiempos en campos numéricos. - Limpiar la selección
y volver a marcar. - Inspeccionar el segmento antes de añadirlo. -
Elegir GEO, MPU o ambos, de acuerdo con los sensores disponibles. -
Añadir el intervalo a la lista de ventanas manuales.

Los límites deben validarse contra el intervalo temporal del registro.
La duración se calcula como fin menos inicio. El módulo debe impedir
intervalos invertidos, vacíos o fuera de rango.

### 7.3 Intervalo del evento y ventana extraída

Deben distinguirse: - **Intervalo del evento:** rango identificado como
correspondiente al fenómeno. - **Intervalo extraído:** rango que se
guarda como ventana para el Dataset.

Pueden coincidir. Si se decide incluir contexto previo o posterior,
ambos intervalos deben registrarse por separado. La extracción no debe
cambiar automáticamente la etiqueta ni asumir que todo el intervalo
seleccionado es sísmico.

### 7.4 Resultado manual

Cada extracción manual crea un registro de ventana con origen «manual»,
intervalo exacto, sensores y procedencia. Debe usar la misma estructura
de salida que una ventana automática para que Etiquetado no necesite dos
formatos diferentes.

## 8. Sensores y sincronización

-   Los sensores considerados son geófono (GEO) y unidad de medición
    inercial (MPU).
-   La interfaz muestra disponibilidad y permite elegir los canales que
    se incluirán.
-   GEO es el canal principal de referencia para la configuración
    inicial; MPU puede ser opcional.
-   La ausencia de un sensor debe diferenciarse de una discontinuidad o
    defecto de señal.
-   La sincronización temporal debe basarse en los timestamps
    disponibles y documentar la política aplicada.
-   No se deben interpolar, corregir ni descartar muestras
    silenciosamente.
-   Las frecuencias observadas deben registrarse por sensor; no asumir
    que coinciden con la frecuencia nominal de META.

## 9. Calidad y estados

Estados propuestos: - **Aceptada:** cumple las reglas técnicas
aplicables. - **Requiere revisión:** hay una condición que debe
inspeccionarse antes de decidir su uso. - **Bloqueada:** no puede
enviarse a Etiquetado hasta resolver o aceptar explícitamente la
incidencia conforme a una regla definida.

La calidad técnica no equivale a la etiqueta semántica. Una ventana
aceptada puede ser TEMBLOR, NO_SISMICO o INDETERMINADO; la etiqueta se
asigna después.

Las reglas deben poder identificar, según la configuración validada: -
Sensor faltante. - Discontinuidad temporal. - Frecuencia observada
inesperada. - Datos insuficientes o intervalo no válido. - Otras
incidencias definidas por el proyecto.

Los umbrales numéricos y las consecuencias de cada incidencia quedan
pendientes de validación con los datos. No se deben inventar valores por
defecto como criterios científicos.

## 10. Selección, revisión y acciones

Cada ventana mantiene un estado de selección independiente de su
calidad: - **Incluir:** candidata para transferencia. - **Revisar:**
requiere decisión del usuario. - **Excluir:** no se enviará en esta
operación.

La tabla debe permitir selección individual y múltiple, filtrado y
navegación. Las acciones por lote no deben borrar datos fuente ni
destruir registros de ventana.

Acciones principales: - Generar ventanas. - Añadir ventana manual. -
Inspeccionar ventana. - Cambiar estado de selección. - Excluir de la
selección. - Enviar a Etiquetado.

## 11. Estructura de salida propuesta

Cada ventana debe contener, como mínimo, los campos siguientes:

  -----------------------------------------------------------------------
  Campo                               Descripción
  ----------------------------------- -----------------------------------
  `window_id`                         Identificador único y estable de la
                                      ventana.

  `source_file`                       Archivo BIN de origen.

  `source_event_id`                   Identificador del evento de origen,
                                      si aplica.

  `origin_mode`                       `fixed`, `sliding` o `manual`.

  `start_us` / `end_us`               Límites temporales en microsegundos
                                      respecto al origen temporal
                                      definido.

  `duration_ms`                       Duración efectiva.

  `sensors`                           Sensores presentes e incluidos.

  `samples`                           Conteo de muestras por sensor.

  `sampling_info`                     Frecuencia observada y datos de
                                      muestreo por sensor.

  `quality`                           Estado e incidencias de calidad.

  `window_config`                     Parámetros usados para generar o
                                      extraer la ventana.

  `selection_status`                  Incluir, revisar o excluir.

  `extractor_version`                 Versión del extractor.

  `source_hash`                       Hash del archivo fuente, cuando
                                      esté disponible.

  `event_interval`                    Intervalo del evento identificado,
                                      si se conoce y es distinto del
                                      intervalo extraído.

  `notes`                             Observaciones pertinentes.
  -----------------------------------------------------------------------

Los datos de señal pueden conservarse mediante referencias al BIN y
límites de extracción, con recuperación bajo demanda y caché temporal si
resulta conveniente. La decisión de materialización persistente de
arrays queda pendiente; no debe duplicarse información innecesariamente.

Los nombres y tipos definitivos de campos deben ajustarse al modelo de
dominio acordado antes de programar.

## 12. Transferencia a Fase 7 --- Etiquetado

La transferencia incluye: - Identificador de ventana. - Señales o
referencias suficientes para recuperarlas. - Archivo y evento de
origen. - Intervalo temporal exacto. - Sensores y conteos/frecuencias
observadas. - Estado e incidencias de calidad. - Modo y parámetros de
extracción. - Intervalo del evento identificado, si está disponible.

Condiciones propuestas: - Solo ventanas seleccionadas como **Incluir**
pueden proponerse para envío. - Las **Bloqueadas** no se envían. - Las
que **Requieren revisión** necesitan una decisión explícita según la
política aprobada. - La etiqueta no se asigna en esta fase; Etiquetado
mantiene sus categorías oficiales y distingue anotación humana de
sugerencia automática.

## 13. Prevención de fuga de datos

Las ventanas derivadas de un mismo evento deben permanecer agrupadas al
dividir el Dataset en entrenamiento, validación y prueba. Esto es
especialmente importante en modo deslizante, donde ventanas consecutivas
pueden compartir muestras, y también en extracciones manuales cercanas
del mismo evento.

La regla de agrupación debe conservar la relación con el evento o
registro fuente y quedar disponible para las fases de Dataset y
entrenamiento.

## 14. Criterios de aceptación

La Fase 6 podrá considerarse funcionalmente aceptada cuando se verifique
que:

1.  Se puede seleccionar un archivo y evento validado conservando el
    contexto de origen.
2.  El modo fijo genera intervalos consecutivos conforme a la duración
    configurada.
3.  El modo deslizante genera intervalos conforme a duración y paso, y
    calcula el solapamiento correctamente.
4.  La selección manual permite marcar un intervalo arbitrario dentro
    del registro y añadirlo como ventana.
5.  Las ventanas manuales y automáticas comparten estructura de salida.
6.  GEO y MPU se gestionan según disponibilidad y configuración, sin
    confundir ausencia con discontinuidad.
7.  La vista previa muestra el intervalo correcto y los canales
    incluidos.
8.  Cada ventana conserva trazabilidad, configuración y versión del
    extractor.
9.  Las incidencias de calidad se muestran y afectan al envío según
    reglas aprobadas.
10. La selección y exclusión no modifican el BIN original.
11. Etiquetado recibe las ventanas elegibles con sus metadatos y
    referencias recuperables.
12. Las ventanas de un mismo evento pueden agruparse para evitar fuga de
    datos en las particiones posteriores.

## 15. Parámetros pendientes de validación

No fijar como definitivos hasta probar con los BIN reales: - Duraciones
recomendadas de ventana. - Paso recomendado para modo deslizante. -
Política para ventanas parciales al final del registro. - Reglas de
sincronización entre GEO y MPU. - Umbrales y consecuencias de calidad. -
Política de caché y materialización de señales. - Criterio para asociar
intervalo de evento e intervalo extraído.

## 16. Secuencia de implementación

1.  Revisar esta especificación y aprobar alcance y decisiones
    pendientes.
2.  Confirmar modelo de datos e interfaz con las fases Análisis,
    Etiquetado y Dataset.
3.  Implementar el motor Python de generación/extracción y validación.
4.  Implementar la interfaz de configuración, selección, tabla, vista
    previa y trazabilidad.
5.  Integrar el envío a Etiquetado.
6.  Probar integridad temporal, sensores, calidad, procedencia y casos
    límite con los BIN del proyecto.
7.  Documentar resultados y solicitar aprobación antes de avanzar a la
    siguiente fase.

