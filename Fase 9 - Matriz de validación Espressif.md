# Fase 9 — Matriz de validación Espressif

**Estado:** pendiente de ejecución reproducible.  
**Objetivo:** impedir que la exportación o cuantización se integre como ruta soportada sin comprobar versiones, formatos y operadores en un entorno controlado.

## 1. Versiones que deben fijarse

Completar con versiones exactas y origen de instalación antes de integrar:
- Sistema operativo y arquitectura del entorno de desarrollo:
- Python:
- Framework de entrenamiento y versión:
- Exportador/formato intermedio y versión:
- ESP-IDF:
- ESP-DL:
- ESP-PPQ (versión o commit):
- Dependencias transitivas relevantes:

No sustituir estos valores por rangos abiertos en la configuración de una ruta de despliegue validada.

## 2. Pruebas de aceptación de la ruta

| ID | Prueba | Evidencia requerida | Estado |
|---|---|---|---|
| E-01 | Instalar entorno limpio con versiones fijadas | Archivo de dependencias y log de instalación | PENDIENTE |
| E-02 | Importar ESP-DL y ESP-PPQ según su documentación | Log de importación y versiones detectadas | PENDIENTE |
| E-03 | Exportar un modelo mínimo de referencia | Artefacto intermedio y configuración de I/O | PENDIENTE |
| E-04 | Ejecutar modelo original y exportado con el mismo lote | Error máximo/medio y tolerancia definida | PENDIENTE |
| E-05 | Convertir modelo de referencia con la ruta oficial | Comando/configuración y artefactos resultantes | PENDIENTE |
| E-06 | Comprobar operadores, atributos, tipos y dimensiones | Reporte de compatibilidad estática | PENDIENTE |
| E-07 | Calibrar con muestras de train/calibración, nunca test | Identidad del conjunto y log de calibración | PENDIENTE |
| E-08 | Evaluar fuente y cuantizado con protocolo idéntico | Métricas por clase y matriz de confusión | PENDIENTE |
| E-09 | Repetir desde entorno limpio | Evidencia de reproducibilidad y hashes | PENDIENTE |

## 3. Reglas de decisión

- No declarar compatibilidad con ESP32-S3 por el mero hecho de que el modelo entrene o se exporte.
- No asumir que ONNX es obligatorio ni que cualquier ONNX es convertible.
- No asumir que una opción de cuantización está soportada hasta confirmarla en la versión fijada y probarla.
- Registrar los fallos y las operaciones no soportadas; no ocultarlos mediante conversiones silenciosas.
- Separar compatibilidad estática (Fase 9) de mediciones reales de RAM, Flash, PSRAM, latencia y estabilidad (Fase 11).
- No marcar una prueba como aprobada sin adjuntar la evidencia indicada.

## 4. Criterio para habilitar la integración

La ruta se puede implementar como opción soportada cuando E-01 a E-09 tengan resultado documentado, se hayan fijado las tolerancias de equivalencia y degradación, y el formato de salida esté confirmado para la versión objetivo de ESP-DL.

Hasta entonces, la interfaz debe presentar conversión/cuanti­zación como no habilitada o experimental, sin generar un estado de compatibilidad positivo.
