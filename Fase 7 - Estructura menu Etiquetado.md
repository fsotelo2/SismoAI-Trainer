# Fase 7 --- Etiquetado

## 1. Objetivo

Definir e implementar el flujo de etiquetado de ventanas GEO/MPU para
construir un conjunto de datos consistente, trazable y utilizable en
entrenamiento y evaluación de modelos.

El etiquetado se realiza sobre ventanas ya generadas en la fase de
análisis. Esta fase no modifica los archivos BIN originales.

## 2. Principio de clasificación

La **clase principal tiene exactamente dos opciones**:

  Código   Clase
  -------- --------------
  `0`      `TEMBLOR`
  `1`      `NO_SISMICO`

La categoría `INDETERMINADO` puede utilizarse únicamente como categoría
secundaria de `NO_SISMICO`, cuando se ha determinado que el evento no es
sísmico, pero se desconoce su causa.

Si no es posible decidir entre `TEMBLOR` y `NO_SISMICO`, la ventana
permanece **pendiente y sin clase asignada**. No se debe resolver esa
incertidumbre asignándole `INDETERMINADO` ni preseleccionando una clase.

## 3. Unidad de etiquetado

La unidad primaria es la **ventana**. Cada ventana recibe como máximo
una clase principal.

Los datos GEO y MPU asociados pueden conservar atributos o anotaciones
complementarias por sensor, sin alterar la regla de una sola clase
principal por ventana.

Cada etiqueta debe mantener una referencia inequívoca a la ventana de
origen y a los datos necesarios para recuperarla.

## 4. Categorías secundarias

Las categorías secundarias describen la causa o naturaleza del evento
cuando corresponda. No sustituyen ni amplían las clases principales.

Para `NO_SISMICO`, `INDETERMINADO` significa: *se confirmó que no es
sísmico, pero no se pudo identificar la causa*.

Otras categorías posibles ---por ejemplo, maquinaria, tránsito, impacto,
objetos o ruido--- son ilustrativas y quedan pendientes de definición y
aprobación. No deben considerarse un catálogo cerrado ni implementarse
como taxonomía definitiva sin esa decisión.

No se debe asignar una categoría secundaria que contradiga la clase
principal.

## 5. Estados de etiquetado

El estado de etiquetado debe distinguir entre una decisión tomada y una
ventana aún no resuelta:

-   **Pendiente:** no tiene clase principal asignada. No se
    preselecciona ninguna clase.
-   **Etiquetada:** tiene una clase principal válida (`TEMBLOR` o
    `NO_SISMICO`).
-   **Revisión**, si se habilita como estado de flujo: indica que la
    etiqueta requiere comprobación; no es una clase ni una categoría
    física.

La incertidumbre sobre la clase principal se representa mediante el
estado pendiente, no mediante una etiqueta adicional.

## 6. Elegibilidad para entrenamiento

La elegibilidad para entrenamiento es una propiedad del registro de
etiquetado, separada de la clase principal y de la categoría secundaria.

Una ventana pendiente no es elegible para entrenamiento supervisado
porque carece de clase principal.

Las reglas definitivas de elegibilidad para ventanas etiquetadas,
revisadas o con incidencias de calidad deben especificarse y validarse
antes de cerrar las validaciones de esta fase. No se debe inferir
elegibilidad únicamente a partir del código de clase.

## 7. Flujo funcional

1.  Recibir las ventanas seleccionadas desde la fase de análisis
    mediante un manifiesto y referencias a los rangos de muestras de los
    BIN.
2.  Mostrar la ventana y permitir consultar la señal recuperada bajo
    demanda, con caché temporal acotada.
3.  Permitir asignar una de las dos clases principales, sin selección
    inicial automática.
4.  Si la clase es `NO_SISMICO`, permitir una categoría secundaria
    cuando la taxonomía esté definida. `INDETERMINADO` solo estará
    disponible en este nivel y con el significado establecido en la
    sección 4.
5.  Permitir mantener la ventana pendiente cuando no exista evidencia
    suficiente para decidir la clase principal.
6.  Guardar las etiquetas y sus cambios de forma versionada y atómica,
    conservando la trazabilidad con la ventana de origen.

## 8. Integridad y persistencia

-   No modificar ni sobrescribir los BIN originales.
-   Mantener identificadores estables de ventana y referencias a sus
    datos de origen.
-   Persistir clase principal, categoría secundaria (si aplica), estado
    de etiquetado y metadatos de trazabilidad en un formato versionado.
-   Validar que la clase principal solo admita los códigos `0` y `1`.
-   Validar que `INDETERMINADO` solo pueda aparecer como categoría
    secundaria de `NO_SISMICO`.
-   Rechazar una ventana marcada como etiquetada si no tiene una clase
    principal válida.
-   Guardar de forma atómica para evitar estados parciales o archivos
    corruptos.

## 9. Decisiones pendientes antes de cerrar la fase

1.  Aprobar el catálogo de categorías secundarias y sus códigos.
2.  Definir cómo se marca y gestiona una ventana que requiere revisión,
    sin confundir revisión con clase.
3.  Cerrar los criterios de elegibilidad para entrenamiento, incluyendo
    el tratamiento de incidencias de calidad.
4.  Confirmar los metadatos de auditoría necesarios (por ejemplo, autor,
    fecha y motivo de modificación).

Estas decisiones no cambian el principio ya establecido: **solo existen
dos clases principales; `INDETERMINADO` es una categoría secundaria de
`NO_SISMICO`, y una clase principal no resuelta permanece pendiente**.

## 10. Criterios de aceptación

-   La interfaz ofrece exactamente `TEMBLOR` y `NO_SISMICO` como clases
    principales.
-   Ninguna ventana aparece con una clase preseleccionada por defecto.
-   Una ventana cuya clase no se puede determinar puede permanecer
    pendiente y sin clase.
-   `INDETERMINADO` no aparece en el selector de clase principal ni
    tiene código de clase.
-   `INDETERMINADO` solo puede asignarse como categoría secundaria
    cuando la clase principal sea `NO_SISMICO`.
-   La persistencia conserva la relación entre etiqueta, ventana y datos
    de origen, sin modificar los BIN.
-   Las validaciones impiden combinaciones incompatibles y registros
    etiquetados sin clase principal válida.
