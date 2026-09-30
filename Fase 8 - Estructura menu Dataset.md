# SismoAI Trainer --- Fase 8: Dataset

## Especificación funcional y estructura del menú

**Documento de diseño para implementación**\
**Módulo:** Dataset\
**Fase siguiente:** Modelos

------------------------------------------------------------------------

## 1. Propósito del módulo

Dataset es el módulo que prepara y registra una composición de datos
para utilizarla en el entrenamiento y evaluación de modelos de
inteligencia artificial.

En SismoAI Trainer, las etapas **Ventanas** y **Etiquetado** ya generan
las unidades de trabajo y asignan sus etiquetas. Por tanto, Dataset **no
debe volver a segmentar señales ni volver a etiquetarlas**.

Su responsabilidad es:

1.  Consultar las ventanas ya existentes y etiquetadas.
2.  Determinar cuáles se incluirán en el conjunto de datos.
3.  Definir cómo se repartirán para entrenamiento, validación y prueba.
4.  Revisar automáticamente la integridad y advertir sobre limitaciones,
    como el desbalance de clases o la escasez de eventos sísmicos.
5.  Registrar el dataset y su configuración dentro de la herramienta.
6.  Transferir al módulo **Modelos** el dataset recién generado para
    configurar el entrenamiento.

**Concepto central:** una ventana es una muestra individual; un dataset
es una selección organizada de muestras, con etiquetas, particiones y
metadatos, destinada a un uso concreto.

------------------------------------------------------------------------

## 2. Principios de diseño

-   **Sencillez:** una sola pantalla, sin submenús ni un asistente de
    múltiples páginas.
-   **No duplicar funciones:** Ventanas genera segmentos; Etiquetado
    asigna clases; Dataset organiza y prepara.
-   **Trabajo interno:** el dataset se registra dentro de SismoAI
    Trainer. No se exige crear una carpeta física ni copiar archivos al
    sistema operativo.
-   **Trazabilidad:** cada dataset debe conservar qué ventanas utiliza y
    con qué configuración se generó.
-   **Transparencia:** los avisos sobre calidad y desbalance informan al
    usuario; no modifican silenciosamente los datos.
-   **Continuidad del flujo:** la acción principal genera el dataset y
    abre Modelos.

------------------------------------------------------------------------

## 3. Estructura visual de la pantalla

La pantalla mantiene el diseño general de la última propuesta visual:

1.  Barra lateral de navegación de SismoAI Trainer.
2.  Encabezado de página **Dataset**.
3.  Resumen del dataset en preparación.
4.  Sección **1. Ventanas disponibles**.
5.  Sección **2. División de datos**.
6.  Sección **3. Estado y recomendaciones**.
7.  Franja inferior con nombre del dataset y botón principal **Generar
    dataset e ir a Modelos**.

No se proponen pestañas internas. Las tres secciones se muestran en una
única vista vertical para que el usuario comprenda qué datos tiene, cómo
se repartirán y si existen advertencias antes de continuar.

------------------------------------------------------------------------

## 4. Encabezado y contexto del dataset

### Elementos

-   **Título:** Dataset.
-   **Subtítulo:** Preparación de datos para entrenamiento.
-   **Estado general de la aplicación:** por ejemplo, "Listo".

------------------------------------------------------------------------

## 5. Sección 1 --- Ventanas disponibles

### Objetivo

Mostrar qué ventanas existen en el proyecto y cuáles están disponibles
para incluir en el dataset. Las ventanas y sus etiquetas provienen de
las etapas anteriores.

### 5.1 Resumen de datos

La franja de indicadores puede mostrar:

-   **Ventanas etiquetadas:** total de ventanas disponibles que tienen
    una etiqueta válida.
-   **Clases:** cantidad de clases distintas presentes.
-   **Canales:** número y nombres de canales, cuando sean homogéneos en
    el conjunto mostrado.
-   **Frecuencia:** frecuencia de muestreo, si es común a las ventanas
    seleccionadas.
-   **Última actualización:** fecha de modificación o generación de los
    datos de origen.

Los valores deben proceder de los datos reales de la aplicación. Los
números de la imagen son ilustrativos y no deben codificarse como
valores fijos.

### 5.2 Distribución de clases

Mostrar un gráfico sencillo ---por ejemplo, anillo--- con el número y
porcentaje de ventanas por etiqueta.

Ejemplo ilustrativo:

  Clase         Ventanas   Proporción
  ----------- ---------- ------------
  Sismo                3           3%
  Ruido               97          97%
  **Total**      **100**     **100%**

La distribución permite conocer la composición del conjunto. No es una
instrucción para que Dataset balancee automáticamente las clases.

#### Desbalance de clases

Cuando una clase tenga muchos menos ejemplos que otra, mostrar una
advertencia breve y contextual, por ejemplo:

> **Clases desbalanceadas.** La clase Sismo tiene pocos ejemplos
> respecto a Ruido. Esto puede afectar el aprendizaje y hacer que la
> exactitud global resulte engañosa.

La finalidad del aviso es que el usuario pueda interpretar las
limitaciones y considerar acciones posteriores, como incorporar más
eventos reales, revisar la estrategia de entrenamiento o elegir métricas
apropiadas.

**Dataset identifica y comunica el desbalance; no decide por sí solo
cómo corregirlo.** Las técnicas de ponderación, muestreo o ajuste del
entrenamiento pertenecen principalmente a Modelos o a la configuración
del experimento.

### 5.3 Vista de ejemplos

Incluir una tabla compacta con algunas ventanas existentes, por ejemplo:

-   ID de ventana.
-   Etiqueta.
-   Evento u origen.
-   Duración.
-   Canales.

La tabla es de consulta y verificación, no un editor de etiquetas. La
etiqueta mostrada debe ser la asignada en Etiquetado.

Acciones posibles:

-   **Ver más:** abrir una vista ampliada o la tabla completa.
-   **Filtrar:** filtrar las ventanas disponibles por etiqueta, origen,
    estado u otros metadatos.
-   **Ver en Etiquetado:** navegar al módulo Etiquetado para corregir o
    completar anotaciones. No se debe implementar un segundo editor
    aquí.

### 5.4 Selección de ventanas

El usuario debe poder decidir qué ventanas se incluirán. La interfaz
puede ofrecer:

-   Incluir todas las ventanas etiquetadas válidas.
-   Seleccionar un subconjunto mediante filtros o selección explícita.
-   Excluir ventanas concretas si la aplicación ya permite
    identificarlas y gestionarlas.

Si el flujo previsto del proyecto es utilizar siempre todas las ventanas
válidas, la selección puede ser automática y esta sección se limita a
mostrar el total y su distribución. No añadir controles de selección que
no tengan una necesidad real.

Las ventanas sin etiqueta no deben incorporarse silenciosamente a un
entrenamiento supervisado. Deben excluirse o generar una advertencia con
acceso a Etiquetado, según las reglas del proyecto.

------------------------------------------------------------------------

## 6. Sección 2 --- División de datos

### Objetivo

Definir qué muestras se utilizarán para ajustar el modelo, cuáles para
orientar las decisiones durante el desarrollo y cuáles se reservarán
para la evaluación final.

La división no cambia la señal ni su etiqueta: asigna cada muestra a una
partición.

### 6.1 Particiones

La pantalla contempla tres grupos:

-   **Entrenamiento:** datos que el algoritmo utiliza para aprender sus
    parámetros.
-   **Validación:** datos utilizados durante el desarrollo para comparar
    configuraciones y tomar decisiones, sin ajustar directamente los
    parámetros del modelo con sus etiquetas como en entrenamiento.
-   **Prueba:** datos reservados para la evaluación final, una vez
    fijado el modelo y su configuración.

Una distribución de ejemplo es **70% / 15% / 15%**. Debe tratarse como
valor inicial configurable, no como regla universal.

### 6.2 Controles visuales

En la última propuesta, cada partición aparece como una tarjeta con:

-   Nombre de la partición.
-   Porcentaje.
-   Control de ajuste (slider o campo numérico).
-   Cantidad estimada de ventanas.

Una barra horizontal apilada resume la distribución total.

Las cantidades deben calcularse a partir del total incluido. Debido al
redondeo, la aplicación debe asignar las muestras restantes de forma
determinista para que la suma de las particiones sea exactamente igual
al total.

### 6.3 Criterio de división

Para datos sísmicos, el criterio debe considerar la procedencia de las
ventanas. La pantalla puede mostrar una opción de criterio, por ejemplo:

-   **Por evento de origen:** mantiene todas las ventanas de un mismo
    evento en una sola partición. Es el criterio preferible cuando se
    desea evaluar el desempeño sobre eventos no vistos.
-   **Aleatoria por ventana:** reparte ventanas individualmente. Solo
    debe utilizarse cuando sea metodológicamente apropiado, porque
    ventanas relacionadas pueden quedar en particiones distintas y
    producir fuga de información.

Si existen identificadores de evento, la opción por evento debe ser la
recomendada. Si no existen metadatos suficientes para agrupar por
evento, el sistema debe indicarlo y no afirmar que se ha evitado la fuga
por evento.

### 6.4 Restricciones y casos con pocos sismos

El número de ventanas no equivale necesariamente al número de eventos
independientes. Por ejemplo, 30 ventanas extraídas de un mismo terremoto
siguen representando un solo evento para una evaluación de
generalización a eventos nuevos.

Si solo existen tres eventos sísmicos reales, una partición convencional
puede dejar muy pocos eventos en validación o prueba. En ese caso:

-   Mostrar cuántos eventos independientes hay, si el origen está
    registrado.
-   Advertir que la evaluación puede ser inestable o insuficiente.
-   No afirmar que el modelo será fiable solo porque se generó la
    partición.
-   Permitir generar el dataset con advertencia, si la configuración
    sigue siendo técnicamente válida.
-   Dejar las decisiones metodológicas específicas del experimento para
    Modelos.

No forzar un balance artificial ni dividir ventanas del mismo evento
entre conjuntos para satisfacer porcentajes si ello contradice el
criterio de separación seleccionado.

------------------------------------------------------------------------

## 7. Sección 3 --- Estado y recomendaciones

### Objetivo

Dar una lectura rápida de si la composición está técnicamente preparada
y qué limitaciones debe conocer el usuario antes de enviarla a Modelos.

Debe ser una sección de indicadores, no un nuevo submenú ni un proceso
manual extenso.

### Indicadores sugeridos

**Etiquetas** - Completo: todas las ventanas incluidas tienen una
etiqueta válida. - Pendiente: existen ventanas sin etiqueta o etiquetas
no reconocidas. - La corrección se realiza en Etiquetado.

**División de datos** - Configurada: los porcentajes son válidos y suman
100%. - Pendiente: los valores son incompletos o inconsistentes.

**Balance de clases** - Informativo: distribución sin una alerta
relevante según el criterio definido. - Advertencia: una o más clases
tienen una representación muy baja. - No debe bloquear automáticamente
la generación por el solo hecho de existir desbalance.

**Eventos para evaluación** - Suficientes según el umbral metodológico
definido por el proyecto, o - Limitados/insuficientes cuando hay pocos
eventos independientes. - Si no hay metadatos de evento, indicar que no
se pudo verificar esta condición.

### Diferencia entre validez y suficiencia

Un dataset puede estar correctamente formado y, aun así, ser
insuficiente para evaluar un modelo de manera representativa.

Por eso, el estado debe distinguir: - **Validez técnica:** existen datos
utilizables, etiquetas y particiones coherentes. - **Limitaciones
metodológicas:** desbalance, pocos eventos, falta de metadatos o riesgo
de fuga.

Una advertencia no equivale necesariamente a un error que impida
continuar.

------------------------------------------------------------------------

## 8. Acción principal --- Generar dataset e ir a Modelos

### Etiqueta del botón

**Generar dataset e ir a Modelos**

Es la acción final principal de la pantalla. Evita obligar al usuario a
guardar y después navegar manualmente a la siguiente sección.

### Comportamiento esperado

Al pulsar el botón:

1.  Comprobar que existe una selección de ventanas válida.
2.  Verificar que las ventanas incluidas tienen etiquetas compatibles
    con la tarea supervisada configurada.
3.  Validar la división y comprobar que los porcentajes suman 100%.
4.  Ejecutar las comprobaciones automáticas de integridad y registrar
    advertencias.
5.  Crear un registro interno del dataset con nombre, ID, versión,
    selección de ventanas, etiquetas de origen, particiones, criterio de
    división, metadatos y resultado de validación.
6.  Confirmar la creación y navegar a Modelos.
7.  Dejar seleccionado el dataset recién generado, para que el usuario
    continúe con la configuración del entrenamiento.

### Cuándo bloquear y cuándo advertir

**Bloquear la generación** ante errores estructurales que impidan usar
el dataset, como: - No hay ventanas seleccionadas. - La configuración de
particiones es inválida. - No se puede resolver la referencia a las
muestras seleccionadas. - El formato o estructura de las muestras no es
compatible con el contrato de entrada definido.

**Permitir con advertencia**, cuando corresponda, ante limitaciones que
no impiden crear la composición: - Clases desbalanceadas. - Pocos
eventos sísmicos independientes. - Distribuciones de clase muy
diferentes entre particiones. - Metadatos incompletos que limitan la
evaluación.

La aplicación debe explicar la advertencia y conservarla asociada al
dataset para que Modelos también pueda mostrarla.

------------------------------------------------------------------------

## 9. Almacenamiento: registro interno, no carpeta física

Actualmente, Ventanas trabaja dentro de la herramienta y no crea una
carpeta por cada resultado. Dataset debe seguir el mismo patrón, salvo
que el proyecto adopte posteriormente una política explícita de
exportación.

Al generar un dataset, la aplicación crea un **registro interno** que
referencia las ventanas existentes. No es necesario copiar las señales a
una nueva carpeta.

El registro debe conservar como mínimo:

-   ID único del dataset.
-   Nombre legible.
-   Número de versión.
-   Fecha de creación.
-   Identificadores de las ventanas incluidas.
-   Referencia a sus etiquetas.
-   Partición asignada a cada muestra.
-   Porcentajes y criterio de división.
-   Metadatos relevantes: canales, frecuencia, duración, origen, etc.
-   Resultado de controles y advertencias.
-   Estado de disponibilidad para Modelos.

Si una ventana de origen se modifica o elimina posteriormente, el
sistema debe poder detectar que la composición puede haber cambiado o
quedado incompleta. Para reproducibilidad, conviene que la versión
generada conserve una referencia estable a los datos y, cuando sea
viable, una huella o identificador de la versión de origen.

La exportación física a CSV, NumPy u otros formatos puede considerarse
una función futura o formar parte de Exportar; no es un requisito para
el botón de generación descrito aquí.

------------------------------------------------------------------------

## 10. Relación con la Fase 9 --- Modelos

Dataset entrega a Modelos una composición identificada y consistente.
Modelos no debería reconstruir la selección ni volver a decidir las
particiones sin registrar el cambio.

El contrato de entrada entre módulos debe incluir:

-   ID y versión del dataset.
-   Referencias a las muestras de entrenamiento, validación y prueba.
-   Forma y formato de las entradas.
-   Etiquetas/clases y su codificación.
-   Metadatos necesarios para cargar las señales.
-   Configuración de la división.
-   Advertencias de calidad y limitaciones.

En Modelos, el usuario selecciona la arquitectura, los hiperparámetros y
la estrategia de entrenamiento. Cada experimento debe registrar qué
versión de dataset utilizó.

**Relación funcional:** - Dataset responde: "¿Con qué datos y
particiones voy a trabajar?" - Modelos responde: "¿Qué modelo entrenaré
con esos datos y cómo evaluaré su desempeño?"

------------------------------------------------------------------------

## 11. Ejemplo de funcionamiento de principio a fin

Supóngase que el proyecto contiene 100 ventanas etiquetadas: - 3
ventanas de Sismo, procedentes de 3 eventos independientes. - 97
ventanas de Ruido.

El usuario abre Dataset y revisa el resumen. El gráfico muestra el
desbalance y la aplicación advierte que la clase Sismo tiene pocos
ejemplos.

El usuario configura una división inicial. Si el criterio es por evento,
el sistema considera los grupos de origen, no solo las ventanas. Detecta
que hay únicamente tres eventos sísmicos y muestra que la evaluación
será limitada.

El usuario puede continuar si no hay errores estructurales. Pulsa
**Generar dataset e ir a Modelos**. La herramienta registra la
composición, las particiones y las advertencias, y abre Modelos con ese
dataset seleccionado.

En Modelos, el usuario define el entrenamiento. Las advertencias
permanecen visibles para evitar interpretar la exactitud global como
evidencia suficiente de capacidad de detección de sismos.

Este ejemplo es ilustrativo: las cifras, los umbrales y la división
definitiva deben determinarse con los datos y objetivos reales del
proyecto.

------------------------------------------------------------------------

## 12. Qué queda fuera del alcance de Dataset

Para mantener el módulo sencillo y evitar duplicar funcionalidades, no
incluir en esta fase:

-   Generación de ventanas.
-   Edición o asignación de etiquetas.
-   Procesamiento avanzado de señales que ya pertenezca a otra etapa.
-   Selección de arquitectura o hiperparámetros del modelo.
-   Ejecución del entrenamiento.
-   Evaluación final del modelo.
-   Gestión obligatoria de carpetas físicas.

Dataset puede mostrar datos resumidos y navegar a las etapas de origen
cuando se requiera corregir algo, pero no debe reemplazar esos módulos.

------------------------------------------------------------------------

## 13. Criterios de aceptación funcional

La implementación se considerará alineada con este diseño si:

1.  Dataset consulta las ventanas y etiquetas ya existentes.
2.  No crea ni edita ventanas o etiquetas.
3.  Muestra cantidades y distribución por clase usando datos reales.
4.  Permite definir o confirmar la selección de muestras.
5.  Permite configurar las particiones y su criterio de separación.
6.  Calcula correctamente las cantidades de cada partición.
7.  Advierte sobre desbalance y escasez de eventos sin confundirlos con
    errores estructurales.
8.  Registra internamente el dataset sin exigir una carpeta física.
9.  Conserva la configuración y las referencias necesarias para
    reproducir la composición.
10. El botón **Generar dataset e ir a Modelos** genera el registro y
    abre Modelos con el dataset seleccionado.
11. Modelos puede recuperar las particiones, etiquetas, metadatos y
    advertencias del dataset.
12. Los cambios posteriores en los datos de origen no alteran
    silenciosamente una versión ya generada.

------------------------------------------------------------------------

## 14. Resumen ejecutivo

Dataset debe ser una pantalla única y sencilla que consolide las
ventanas ya etiquetadas, permita definir su uso en
entrenamiento/validación/prueba, muestre controles automáticos y
registre una versión interna reproducible.

La interfaz se organiza en tres bloques: 1. **Ventanas disponibles:**
qué datos existen y cómo se distribuyen las clases. 2. **División de
datos:** cómo se asignan las muestras a cada partición, preferentemente
respetando el evento de origen cuando sea pertinente. 3. **Estado y
recomendaciones:** qué está completo y qué limitaciones deben tenerse
presentes.

La acción final es única: **Generar dataset e ir a Modelos**.

El módulo no crea carpetas ni vuelve a procesar o etiquetar señales. Su
finalidad es definir exactamente qué datos utilizará cada experimento y
dejar esa decisión registrada.
