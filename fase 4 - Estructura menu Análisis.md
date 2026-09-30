# SismoAI Trainer --- Estructura funcional de menú Análisis

**Estado:** propuesta funcional para revisión\
**Módulo:** Análisis\
**Alcance:** inspección científica de eventos BIN antes de Windowing y
Labeling.

## 1. Objetivo

Permitir visualizar e inspeccionar las señales de un evento sísmico y
calcular representaciones útiles para comprender su comportamiento. El
módulo no genera etiquetas de entrenamiento ni modifica el archivo BIN
de origen.

## 2. Estructura de navegación

La sección **Análisis** tendrá cuatro submenús:

1.  **Señales**
2.  **STA-LTA**
3.  **Espectrograma**
4.  **Frecuencia**

No se incluirá un submenú independiente de Métricas. Los datos numéricos
complementarios que sean útiles podrán mostrarse dentro del submenú
correspondiente, sin crear una sección genérica.

## 3. Elementos comunes de la sección

### 3.1 Encabezado y contexto

-   Título: **Análisis**.
-   Descripción breve del módulo.
-   Selector de archivo BIN disponible para análisis.
-   Navegación entre eventos del archivo seleccionado.
-   Resumen temporal del evento: inicio, duración y fin.

El contexto de archivo y evento debe mantenerse al cambiar entre los
cuatro submenús.

### 3.2 Panel de información del evento

Mostrar, como mínimo, los datos disponibles y validados:

-   Archivo.
-   Identificador o secuencia del evento.
-   Inicio y fin.
-   Duración.
-   Número de muestras, indicando el criterio si corresponde a un sensor
    específico.
-   Frecuencia observada del geófono.
-   Frecuencia observada del MPU.

No presentar valores de ejemplo como resultados reales. Si un dato no
está disponible o no es válido, indicarlo explícitamente.

### 3.3 Panel de acciones

Acciones comunes previstas:

-   **Ir a Ventanas:** transferir el contexto del evento y, cuando
    exista, el intervalo seleccionado.


## 4. Submenú Señales

### Propósito

Inspeccionar la forma de onda temporal de los sensores del evento.

### Visualización principal

Dos gráficas temporales apiladas y sincronizadas:

-   **Geófono --- señal principal:** velocidad corregida en mm/s como
    señal principal de la aplicación. El voltaje en mV podrá exponerse
    como dato alternativo si se define su utilidad en la interfaz.
-   **MPU --- señal auxiliar:** mostrar únicamente la magnitud en m/s²,
    no los ejes X, Y y Z por separado.

Ambas gráficas comparten el eje de tiempo del evento y permiten comparar
visualmente la actividad.

### Controles y datos

-   Ejes con unidades explícitas.
-   Frecuencia observada de cada sensor.
-   Navegación y zoom/pan, según el componente gráfico adoptado.
-   Información del evento en el panel lateral.
-   Métricas básicas de apoyo solo si aportan contexto a la inspección;
    no crear una tarjeta genérica extensa por defecto.

## 5. Submenú STA-LTA

### Propósito

Calcular y visualizar STA, LTA y su Ratio para ayudar a identificar
incrementos de actividad respecto al nivel de referencia de la señal.

STA-LTA será una herramienta de **detección asistida**. Una detección
candidata no equivale a una etiqueta de entrenamiento.

### Visualización principal

Mantener las dos gráficas temporales de Señales:

-   **Geófono:** velocidad corregida en mm/s.
-   **MPU:** magnitud en m/s².

Sobre cada gráfica se mostrarán las curvas calculadas correspondientes:

-   Señal original.
-   STA.
-   LTA.
-   Ratio STA/LTA.

El ratio podrá utilizar un eje vertical secundario claramente
identificado para no confundir su escala con la unidad física de la
señal. La leyenda debe identificar cada curva.

No superponer ventanas de selección sobre las gráficas en la vista
normal.

### Parámetros configurables

-   Ventana STA.
-   Ventana LTA.
-   Umbral de activación.
-   Umbral de desactivación, si se adopta histéresis.
-   Tipo de cálculo (por ejemplo, amplitud absoluta o energía),
    pendiente de decisión.

### Resultados

-   Curvas STA, LTA y ratio.
-   Umbrales visibles en la representación del ratio.
-   Intervalos candidatos detectados, si el algoritmo está definido.
-   Resumen tabular de candidatos: inicio, fin, duración y pico del
    ratio.

Las detecciones deben poder inspeccionarse y, si se decide, transferirse
a Windowing como intervalos candidatos. No asignar etiquetas
automáticamente.

## 6. Submenú Espectrograma

### Propósito

Mostrar cómo cambia el contenido frecuencial de la señal a lo largo del
tiempo y ayudar a localizar tramos con actividad espectral distinta.

### Visualización principal

-   Espectrograma del **geófono** como visualización principal.
-   Eje horizontal: tiempo (s).
-   Eje vertical: frecuencia (Hz).
-   Escala de color: intensidad espectral, con leyenda visible.
-   Rango de frecuencia configurable mediante opciones sencillas.

### Controles esenciales

-   Duración de ventana de análisis.
-   Solapamiento entre ventanas.
-   Rango de frecuencia mostrado.

Los controles deben usar opciones comprensibles y evitar exponer
parámetros avanzados innecesarios en la vista principal.

### Lectura rápida

Puede mostrar observaciones calculadas, por ejemplo:

-   Tramo temporal con mayor intensidad espectral.
-   Banda de frecuencia con mayor actividad, si se define el método de
    cálculo.

Estas observaciones deben derivarse de los datos procesados y no
redactarse como interpretaciones automáticas no verificadas.

### Acciones

-   Ir a Ventanas, conservando el contexto temporal si el usuario ha
    seleccionado un intervalo.
-   Exportar espectrograma.

## 7. Submenú Frecuencia

### Propósito

Inspeccionar la distribución de amplitud o energía de la señal en
función de la frecuencia para el evento o tramo analizado.

### Visualización principal

Dos gráficas de espectro apiladas:

-   **Geófono:** señal principal.
-   **MPU:** magnitud como señal auxiliar.

Cada gráfica muestra:

-   Eje horizontal: frecuencia (Hz).
-   Eje vertical: amplitud espectral, con unidad y definición
    explícitas.
-   Frecuencia de muestreo observada.
-   Rango de frecuencia visible.

### Información complementaria

Mostrar solo indicadores directamente relacionados con el espectro,
cuando estén definidos:

-   Frecuencia dominante.
-   Amplitud en el pico dominante.
-   Pico secundario, opcional.
-   Resolución frecuencial del análisis.

### Parámetros de análisis

-   Tipo de ventana.
-   Tamaño de ventana o longitud de segmento.
-   Rango de frecuencia.

La definición matemática de amplitud, normalización, detrend,
tratamiento de DC y algoritmo espectral debe quedar especificada antes
de implementar resultados definitivos.

### Acciones

-   Ir a Ventanas.

## 8. Reglas de datos y procesamiento

-   Analizar únicamente eventos que hayan sido validados por el Data
    Engine.
-   Separar los registros por `tipoSensor` antes de ordenar por
    `timestampUs`.
-   Geófono: `datos[1]` es velocidad corregida en mm/s; `datos[0]` es
    voltaje en mV.
-   MPU: mostrar `datos[3]`, magnitud en m/s², como señal de la
    aplicación.
-   Calcular la frecuencia efectiva a partir de timestamps; no asumir
    que la frecuencia configurada en META coincide exactamente con la
    observada.
-   Respetar discontinuidades y problemas de calidad. Marcar segmentos
    defectuosos; no interpolar ni corregir silenciosamente.
-   No asumir que el BIN contiene características calculadas o
    etiquetas. STA, LTA, ratio, espectros y espectrogramas que se
    muestren en Análisis son resultados calculados por la aplicación.
-   Mantener trazabilidad entre cada resultado y el archivo, evento,
    sensor, intervalo y parámetros utilizados.

## 9. Responsabilidades de software

### Python --- dominio y servicios

Python será responsable de:

-   Obtener los datos validados desde Data Engine.
-   Preparar las series por sensor y su eje temporal.
-   Calcular frecuencias observadas y validar continuidad.
-   Calcular espectros, espectrogramas y STA/LTA.
-   Gestionar parámetros, resultados, detecciones y errores.
-   Exponer datos y estados a la interfaz mediante modelos y propiedades
    Qt.

### QML --- presentación

QML será responsable de:

-   Presentar los cuatro submenús y sus controles.
-   Renderizar las gráficas, leyendas, tablas e indicadores.
-   Recoger parámetros y acciones del usuario.
-   Mostrar estados, resultados y errores proporcionados por Python.

QML no debe calcular resultados científicos ni mantener una copia
autoritativa del estado del análisis.

## 10. Estados de interfaz

Cada submenú debe contemplar, según corresponda:

-   **Vacío:** no hay archivo o evento seleccionado.
-   **Cargando:** se está preparando la información.
-   **Listo:** los datos y resultados están disponibles.
-   **No disponible:** faltan datos o condiciones para ese cálculo.
-   **Error:** falló la lectura, validación o el procesamiento.

No mostrar gráficas, métricas o detecciones ficticias como si fueran
resultados reales.

## 11. Pendientes de especificación antes de implementar

1.  Definir algoritmos y normalización de espectro y espectrograma.
2.  Definir parámetros iniciales y opciones permitidas para ambos
    análisis.
3.  Definir fórmula STA/LTA, inicialización de LTA, manejo de ceros y
    discontinuidades.
4.  Definir umbrales, histéresis y reglas para delimitar detecciones.
5.  Definir si STA/LTA se calcula en ambos sensores o solo en geófono en
    la primera versión.
6.  Definir formato y alcance de exportación.
7.  Definir cómo se transfiere un intervalo desde Análisis a Windowing.

Hasta resolver estos puntos, la estructura de pantallas y el flujo
funcional pueden considerarse una propuesta, pero no deben darse por
aprobadas las fórmulas, valores predeterminados ni criterios de
detección.

## 12. Relación con las fases siguientes

**Análisis → Windowing → Labeling**

-   **Análisis:** inspección y cálculo de información derivada.
-   **Windowing:** definición y generación de ventanas temporales
    vinculadas al evento fuente.
-   **Labeling:** asignación de etiquetas humanas a las ventanas.

Análisis prepara información para las fases posteriores, pero no las
sustituye ni las ejecuta automáticamente.
