# Especificaciones fase 9 modelos

**Proyecto:** SismoAI-Trainer  
**Fase:** 9 — Modelos  
**Destino inicial:** ESP32-S3  
**Estado:** especificación base para implementación; validar versiones y compatibilidad de herramientas antes de fijar detalles dependientes del runtime.

## 1. Objetivo

Definir el flujo reproducible para configurar, entrenar en PC, convertir, cuantizar, evaluar y versionar modelos de clasificación sísmica destinados al ESP32-S3. La ejecución física y las mediciones reales en placa se realizan en la Fase 11.

## 2. Alcance y exclusiones

Incluye:
- Selección de dataset versionado y configuración de experimentos.
- Entrenamiento en PC y registro de resultados.
- Exportación intermedia y conversión según ruta compatible.
- Calibración y cuantización con ESP-PPQ cuando aplique.
- Verificación estática, evaluación comparativa y biblioteca de modelos.

No incluye:
- Entrenamiento dentro del ESP32-S3.
- Certificación de rendimiento físico o consumo real.
- Soporte implementado para otras placas.
- Empaquetado final de distribución, responsabilidad de la Fase 10.

## 3. Arquitectura y flujo de datos

`Fase 8 Dataset → Experimento → Entrenamiento PC → Exportación → ESP-PPQ/conversión → Verificación → Evaluación → Biblioteca → Fase 10`

Python será responsable de la lógica de dominio, ejecución, estado, validación, persistencia y trazabilidad. La interfaz únicamente configura operaciones, presenta estados y resultados, y solicita acciones mediante el puente de la aplicación.

## 4. Entrada contractual desde Fase 8

Cada experimento debe referenciar:
- ID y versión inmutable del dataset.
- Identificadores de particiones train, validation y test.
- Clases y codificación de etiquetas.
- Forma, tipo y frecuencia de muestreo de las señales.
- Transformaciones y preprocesamiento aplicados.
- Reglas de agrupación por evento/sesión y controles contra fuga de datos.

No se permite volver a repartir aleatoriamente ventanas ignorando la agrupación por evento/sesión. Las estadísticas aprendidas (por ejemplo, normalización) se ajustan únicamente con entrenamiento y se aplican sin reajuste a validación/test.

## 5. Catálogo inicial de modelos

El catálogo inicial contempla tres familias:
1. **Baseline de reglas/características:** referencia interpretable y de bajo costo, cuando el problema permita definirla.
2. **Clasificador de características:** recibe un vector de características calculadas mediante un procedimiento versionado.
3. **1D-CNN:** recibe señales o ventanas con forma fija, si las operaciones requeridas son compatibles con la ruta objetivo.

Para cada variante se documentará: ID, versión, framework, estructura, forma y tipo de entrada, salida, clases, preprocesamiento, operaciones requeridas, parámetros entrenables y artefactos. La inclusión en el catálogo no implica compatibilidad con ESP-DL.

## 6. Configuración del experimento

Como mínimo registrar:
- Identificador único del experimento y fecha/hora.
- Dataset y versión exacta.
- Arquitectura y versión.
- Semilla aleatoria.
- Hiperparámetros: épocas, batch size, optimizador, learning rate y función de pérdida, según el modelo.
- Estrategia de balanceo o ponderación de clases, si se utiliza.
- Framework, versiones de dependencias y entorno.
- Métricas, criterios de selección y ruta de salida.

Los cambios de configuración generan un experimento nuevo; no se sobrescribe el registro histórico.

## 7. Entrenamiento en PC

El proceso debe:
1. Validar que dataset, particiones, formas y etiquetas sean consistentes.
2. Construir el modelo desde una configuración registrada.
3. Entrenar usando exclusivamente la partición train.
4. Usar validation para selección de hiperparámetros, checkpoint y parada temprana, si aplica.
5. Mantener test aislado hasta la evaluación final.
6. Guardar pesos/checkpoint, configuración, logs, métricas por época y estado de ejecución.
7. Reportar errores de forma explícita y permitir identificar ejecuciones incompletas.

La reanudación de entrenamiento, si se implementa, debe registrar el checkpoint de origen y la configuración continuada.

## 8. Exportación y conversión

El formato intermedio depende del framework y de la ruta de despliegue. ONNX puede utilizarse cuando sea compatible, pero no se considera obligatorio para todos los modelos ni garantía de conversión.

Antes de cuantizar:
- Congelar y registrar el modelo fuente seleccionado.
- Definir entradas/salidas con nombres, dimensiones y tipos explícitos.
- Comprobar que la exportación carga y ejecuta con datos de prueba.
- Comparar salidas del modelo original y exportado dentro de tolerancias definidas para la ruta.
- Registrar versión del exportador, formato y archivo generado.

La conversión final debe seguir la documentación de la versión concreta de ESP-DL/ESP-PPQ integrada. No codificar supuestos de compatibilidad sin una prueba de conversión reproducible.

## 9. Calibración y cuantización

ESP-PPQ se utilizará únicamente en los flujos y formatos admitidos por la versión seleccionada. La configuración debe registrar:
- Precisión objetivo y esquema aplicado (por ejemplo, pesos/activaciones si corresponde).
- Estrategia de cuantización y granularidad (incluida por tensor cuando aplique).
- Método simétrico basado en potencias de dos para ESP32-S3, si la ruta y versión lo soportan.
- Dataset de calibración, procedencia y cantidad de muestras.
- Criterios de selección de muestras y cobertura de clases/condiciones.
- Parámetros de calibración, versión de ESP-PPQ y logs.
- Advertencias, capas/operaciones no cuantizadas y excepciones, si existen.

El conjunto de calibración debe ser representativo y no debe usar el conjunto test para ajustar rangos. La cuantización no se declara exitosa solo porque el proceso termine: el artefacto debe pasar validación estructural y evaluación posterior.

## 10. Compatibilidad estática y recursos

Verificaciones previas a la Fase 10:
- Operadores y atributos requeridos frente a los soportados por la versión objetivo.
- Dimensiones, orden de ejes, tipos y rangos de entrada/salida.
- Compatibilidad del formato generado con el runtime ESP-DL previsto.
- Tamaño del modelo y de los archivos auxiliares.
- Estimaciones de memoria claramente marcadas como estimaciones.
- Registro de incompatibilidades, restricciones y acciones pendientes.

Estados sugeridos: `PENDIENTE`, `COMPATIBLE_ESTÁTICAMENTE`, `COMPATIBLE_CON_ADVERTENCIAS`, `NO_COMPATIBLE`. Ningún estado estático equivale a validación en hardware.

## 11. Evaluación y comparación

Evaluar el modelo fuente y el cuantizado con las mismas particiones y protocolo. Registrar, según pertinencia:
- Accuracy, precision, recall y F1 (macro y por clase cuando corresponda).
- Matriz de confusión.
- Falsos positivos y falsos negativos, con especial atención a la clase de interés.
- Métricas por clase y soporte de cada clase.
- Diferencia absoluta/relativa entre modelo fuente y cuantizado.
- Resultados sobre validation y, una vez fijado el modelo, evaluación final sobre test.

Definir los umbrales de aceptación antes de ejecutar la campaña formal. No elegir un modelo solo por accuracy global si oculta errores relevantes en clases minoritarias.

## 12. Versionado y estructura de artefactos

Cada modelo registrado debe tener un ID único y conservar:
- Configuración y arquitectura.
- Referencia exacta al dataset y experimento.
- Pesos/modelo fuente.
- Exportación intermedia, si aplica.
- Modelo convertido/cuanti­zado y archivos auxiliares disponibles (por ejemplo, `.espdl`, `.info`, `.json`).
- Métricas, logs y reporte de compatibilidad.
- Versiones de framework, exportador, ESP-PPQ y ESP-DL.
- Hashes de integridad y fecha de generación.

No sobrescribir versiones aprobadas. Una modificación de pesos, cuantización, preprocesamiento o configuración de entrada produce una nueva versión.

## 13. Contrato de salida hacia Fase 10

Entregar un paquete de referencia compuesto por:
- ID/versión del modelo seleccionado.
- Artefacto fuente y artefacto de despliegue disponible.
- Configuración de entrada/salida y clases.
- Preprocesamiento completo y orden de operaciones.
- Dataset/experimento de origen y métricas.
- Configuración y reporte de cuantización.
- Versiones de herramientas, compatibilidad estática y hashes.
- Dependencias o instrucciones requeridas para el empaquetado.

La Fase 10 valida integridad y estructura del paquete de despliegue. La Fase 9 no duplica ese empaquetado.

## 14. Criterios de aceptación de la Fase 9

La fase podrá considerarse completada cuando:
1. El experimento referencia un dataset inmutable y particiones válidas.
2. El entrenamiento es reproducible desde la configuración registrada.
3. La exportación/conversión tiene una ruta documentada y verificable.
4. La cuantización, si aplica, registra calibración y configuración.
5. Existe comparación de desempeño antes/después de cuantizar.
6. La compatibilidad estática y sus limitaciones están documentadas.
7. Artefactos, metadatos, logs y hashes están versionados.
8. La salida cumple el contrato requerido por Fase 10.
9. Los pendientes de validación física están explícitamente transferidos a Fase 11.

Los valores numéricos de tolerancia de degradación, memoria y latencia se definirán mediante requisitos del proyecto y pruebas; no se inventan en esta especificación base.

## 15. Decisiones pendientes antes de implementar

- Versiones concretas de ESP-IDF, ESP-DL y ESP-PPQ y su compatibilidad mutua.
- Framework y versión de entrenamiento.
- Arquitecturas/opciones de operadores confirmadas por prueba.
- Forma definitiva de ventana, canales y normalización del problema.
- Esquema de cuantización exacto y requisitos del runtime.
- Umbrales de desempeño y degradación aceptables.
- Especificaciones de memoria objetivo y condiciones de prueba en placa.

## 16. Referencias técnicas

La implementación debe contrastarse con la documentación oficial de Espressif correspondiente a las versiones fijadas:
- ESP-DL: https://docs.espressif.com/projects/esp-dl/
- ESP-PPQ: https://github.com/espressif/esp-ppq

Las capacidades, formatos y restricciones se consideran confirmados únicamente después de verificar la documentación de la versión integrada y ejecutar pruebas reproducibles.
