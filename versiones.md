# Versiones

## Fase 7 — Etiquetado
**Estado:** Validada funcionalmente por el usuario  
**Rama de implementación:** `feature/fase-7-etiquetado`

### Implementación
- Incorporación del módulo de etiquetado con modelo de datos, servicio de dominio y persistencia JSON versionada.
- Integración del backend con PyWebView mediante el puente de API para consultar el espacio de trabajo, recuperar señales por ventana y guardar etiquetas.
- Nueva vista de Etiquetado integrada en la navegación de la aplicación.
- Listado de ventanas incluidas desde la fase Ventanas, con filtros de pendientes, etiquetadas y en revisión.
- Visualización de señales GEO (geófono) y MPU (acelerómetro), con controles independientes.
- Clasificación principal binaria: `0 = TEMBLOR` y `1 = NO_SISMICO`.
- Categorías secundarias para NO_SISMICO: `RUIDO`, `VIBRACIONES`, `GOLPES` e `INDETERMINADO`. El modelo admite categorías textuales extensibles para futuras opciones configurables desde Ajustes.
- Estados de anotación, observaciones de hasta 200 caracteres y acciones de guardar/guardar y siguiente.
- Presentación de la categoría secundaria en una segunda línea del elemento de ventana cuando aplica.
- Codificación visual de clases: sísmico en verde y no sísmico en naranja.
- Corrección de la numeración visible de eventos para mostrar desde 1, manteniendo los índices internos desde 0.
- Limpieza de ventanas con reinicio de IDs desde `W-001` y eliminación de etiquetas asociadas a los IDs borrados para evitar herencias al reutilizarlos.
- Botón inferior «Continuar a Dataset», visible en Etiquetado y habilitado únicamente cuando todas las ventanas tienen una clase principal guardada y confirmada.

### Robustez y validación técnica incorporada
- Validación de clase, categoría secundaria, estado, observaciones y versión del esquema de etiqueta.
- Persistencia atómica de etiquetas y restauración de datos compatibles.
- Manejo de cambios sin guardar, cancelación del descarte y restauración del estado editado.
- Pruebas unitarias añadidas para modelos, servicio y comportamiento de restauración.

### Verificación
La fase fue validada funcionalmente por el usuario en su ejecución local. Los cambios de código y documentación se integran en `main`; no se declara una ejecución automatizada adicional de pruebas en este registro.
