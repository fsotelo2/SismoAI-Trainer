# Arquitectura global de layout

## Auditoría resumida

La interfaz se carga desde `ui/index.html` y cada vista se inserta en
`#view-container` mediante `ui/js/app.js`. El shell reserva tres regiones
verticales: navegación lateral, topbar y workspace, con un footer global
para acciones contextuales.

Antes de esta migración, el workspace era un contenedor Flex global. Las
vistas Ventanas y Etiquetado apilaban sus regiones con `flex: 1`; el panel
de gestión de Etiquetado tenía una altura accidental fija de `230px`.
Dataset y Modelos acumulaban reglas de densidad posteriores que sobrescribían
las reglas base. Datos usaba Flexbox para el panel principal y el detalle.
Análisis tenía varios bloques Flex y reglas responsive superpuestas. Las
tablas ya contaban con scroll local, pero algunos padres no tenían
`min-height: 0`, por lo que el contenido podía forzar el crecimiento del
workspace.

No se modificaron scripts de dominio, IDs HTML ni contratos del puente.

## Convenciones

- `workspace-view`: raíz de una vista que ocupa el workspace disponible.
- `workspace-panel`: región hija con límites independientes.
- `workspace-scroll`: contenido que puede desplazarse sin cambiar la
  posición de su región.
- El nivel A se declara en `ui/css/workspace.css` mediante variables
  `--x`, `--y`, `--w` y `--h` para cada contenedor principal.
- El nivel B se declara dentro de cada panel con Grid o Flexbox,
  `min-width: 0`, `min-height: 0` y `overflow` local.
- `position: absolute` se usa únicamente en los contenedores principales
  dentro del lienzo; no se usa para los controles internos.

## Modelo de coordenadas

Cada `workspace-view` usa un lienzo base de referencia de `1200px × 756px`.
Si la ventana disponible es menor, el lienzo conserva sus dimensiones mínimas
y el workspace permite desplazamiento. Las coordenadas se editan en
`ui/css/workspace.css`:

```css
.windows-saved-region {
  --x: 0px;
  --y: 618px;
  --w: 1200px;
  --h: 130px;
}
```

El contenedor se posiciona con `left: var(--x)`, `top: var(--y)`,
`width: var(--w)` y `height: var(--h)`. El contenido interno se mantiene
en el flujo normal del contenedor y puede usar Grid/Flexbox y scroll.

## Distribución final

| Menú | Regiones principales |
| --- | --- |
| Proyecto | Carpeta y resumen, dos contenedores absolutos |
| Datos | Tabla de archivos y detalle, dos contenedores absolutos |
| Análisis | Estado vacío, encabezado, pestañas, submenú/gráficas y tarjetas laterales, con coordenadas independientes |
| Ventanas | Configuración, gráficos, ventanas extraídas y selecciones guardadas |
| Etiquetado | Barra superior, lista, señales, editor, contador y “Etiquetados guardados” |
| Dataset | Ventanas disponibles, división y estado/recomendaciones |
| Modelos | Configuración, ejecución/resultados y biblioteca |

Las tablas y listas mantienen scroll interno. En pantallas estrechas las
regiones que necesitan ancho mínimo se apilan o permiten desplazamiento
local; no se cambian sus identificadores ni acciones.

## Inventario de esta fase

- `ui/css/workspace.css`: motor estructural común del workspace e inspector F7.
- `ui/css/proyecto.css`: regiones y componentes visuales de Proyecto.
- `ui/css/datos.css`: regiones y componentes visuales de Datos.
- `ui/css/analisis.css`: regiones, gráficos, pestañas y panel lateral de Análisis.
- `ui/css/ventanas.css`: filas explícitas de Ventanas.
- `ui/css/etiquetado.css`: filas explícitas y eliminación de la altura accidental.
- `ui/css/dataset.css`: filas explícitas de Dataset.
- `ui/css/modelos.css`: regiones explícitas de Modelos.
- `ui/css/layout.css` y `ui/css/components.css`: estilos globales reutilizables,
  sin selectores específicos de un menú.
- `ui/index.html`: carga de la hoja común.
- `ui/views/*.html`: clases estructurales, sin cambiar IDs.

### Regiones explícitas de Análisis

Cuando hay datos disponibles, la vista Análisis utiliza cuatro regiones
posicionables dentro de `#analysis-content`:

| Región | Selector | Variables |
| --- | --- | --- |
| Encabezado | `.analysis-header` | `--x`, `--y`, `--w`, `--h` |
| Gráficas y pestañas | `.analysis-visual-panel` | `--x`, `--y`, `--w`, `--h` |
| Panel lateral | `.analysis-sidebar` | `--x`, `--y`, `--w`, `--h` |

Las coordenadas y la distribución interna de estas regiones están definidas en
`ui/css/analisis.css`. El contenido interno de gráficos y tarjetas continúa
usando Flexbox/Grid y desplazamiento local.

### Regiones explícitas de Etiquetado

La vista Etiquetado separa el área central en tres contenedores editables:

| Región | Selector | Variables |
| --- | --- | --- |
| Barra de navegación y filtros | `.label-toolbar` | `--x`, `--y`, `--w`, `--h` |
| Contenedor central | `.label-layout` | `--x`, `--y`, `--w`, `--h` |
| Lista de ventanas | `.label-list-panel` | `--x`, `--y`, `--w`, `--h` |
| Señales | `.label-signal-panel` | `--x`, `--y`, `--w`, `--h` |
| Editor | `.label-editor` | `--x`, `--y`, `--w`, `--h` |
| Contador | `.label-footer` | `--x`, `--y`, `--w`, `--h` |
| Etiquetados guardados | `.label-batches-panel` | `--x`, `--y`, `--w`, `--h` |

Las tres regiones internas se posicionan respecto a `.label-layout`. Sus
elementos internos conservan Flexbox/Grid y scroll local.

### Regiones explícitas internas de Análisis

Además del estado vacío y del contenedor de contenido, Análisis separa las
regiones anidadas que se ven en pantalla:

| Región | Selector |
| --- | --- |
| Encabezado | `#analysis-content > .analysis-header` |
| Área principal | `#analysis-content > .analysis-main` |
| Área visual | `#analysis-content .analysis-visual-panel` |
| Pestañas | `#analysis-content .analysis-tabs` |
| Submenú activo | `#analysis-content .submenu-content` |
| Cada gráfica | `#analysis-content .analysis-chart-card` |
| Panel lateral | `#analysis-content .analysis-sidebar` |
| Tarjetas laterales | `#analysis-content .analysis-sidebar > .analysis-info-card` |

Cada selector tiene variables `--x`, `--y`, `--w` y `--h` en
`ui/css/workspace.css`. Los submenús conservan sus IDs y el cambio de pestaña
existente.

## Inspector visual de regiones

Con la aplicación abierta, la tecla `F7` activa o desactiva un modo de
inspección visual. El modo resalta las regiones configurables del menú activo
con un borde discontinuo y muestra su nombre junto con los valores actuales
de `--x`, `--y`, `--w` y `--h`. La tecla `F7` no modifica las coordenadas ni
la lógica funcional. También identifica controles y bloques internos como
botones, campos, selectores, tablas, canvas, encabezados y tarjetas mediante
su selector CSS real. La etiqueta incluye además las rutas relativas de la
vista HTML y de las hojas CSS que deben buscarse para modificar el elemento.

Los elementos internos admiten desplazamiento relativo mediante las variables
opcionales `--layout-x` y `--layout-y`. Estas variables no sacan el elemento
del flujo de Grid/Flexbox. El ancho y el alto se modifican en la regla CSS
indicada por el inspector, usando `width` y `height`.

## Validaciones pendientes

- Ejecutar la aplicación PyWebView y comprobar visualmente varias
  resoluciones, especialmente Análisis y tablas extensas.
- Verificar manualmente la navegación a Exportar y Ajustes: el menú existe
  en `index.html`, pero no hay vistas HTML correspondientes en este estado
  del repositorio.
- Ejecutar la suite de pruebas de Python y una comprobación de sintaxis CSS/HTML.
