# Lista completa de errores de tabla detectados

Este documento describe los errores de validación actualmente detectados por
`ckanext-validate` al validar recursos CSV.

La extensión utiliza Frictionless para inferir la estructura de la tabla y validar el
archivo. También aplica reglas de detección adicionales para columnas numéricas y de fechas.

## Reglas de validación actuales

Antes de validar un archivo CSV, la extensión aplica las siguientes reglas:

- Todas las columnas son requeridas.
- Los valores `null`, `NULL` y `None` se tratan como valores faltantes.
- Una columna se considera numérica cuando al menos el 50% de sus valores no faltantes
  pueden ser analizados como números.
- Una columna numérica se infiere como `integer` cuando todos los valores numéricos detectados
  son números enteros. De lo contrario, se infiere como `number`.
- Una columna se considera una columna de fecha cuando al menos el 50% de sus valores no faltantes
  utilizan el mismo formato de fecha compatible.
- Los formatos de fecha soportados son:
  - `MM/DD/YYYY`, por ejemplo `04/25/2024`.
  - `DD/MM/YYYY`, por ejemplo `25/04/2024`.
  - `YYYY-MM-DD`, por ejemplo `2024-04-25`.

Después de que se infiere el esquema, Frictionless valida cada fila en contra del mismo.
Los valores que no coinciden con el tipo o formato inferido se reportan como errores.

## Errores detectados

### Encabezado faltante

**Tipo de error:** `blank-header`

Este error ocurre cuando la fila de encabezado del CSV está vacía. La primera fila debe contener
los nombres de las columnas.

```csv
,
1,2
3,4
```

### Nombre de columna faltante

**Tipo de error:** `blank-label`

Este error ocurre cuando una o más columnas en el encabezado no tienen nombre. Cada
columna debe tener un nombre no vacío.

```csv
column_1,
1,2
3,4
```

### Nombre de columna duplicado

**Tipo de error:** `duplicate-label`

Este error ocurre cuando dos o más columnas tienen el mismo nombre. Cada nombre de
columna debe ser único.

```csv
column_1,column_1
1,2
3,4
```

### Fila vacía

**Tipo de error:** `blank-row`

Este error ocurre cuando una fila completamente vacía está presente en los datos del CSV.

```csv
column_1,column_2
1,2

3,4
```

### Valor faltante

**Tipo de error:** `missing-cell`

Este error ocurre cuando una fila tiene menos celdas que la fila de encabezado.

```csv
column_1,column_2
1,2
3
```

### Celda extra

**Tipo de error:** `extra-cell`

Este error ocurre cuando una fila tiene más celdas que la fila de encabezado. Cada fila de datos
debe tener el mismo número de celdas que el encabezado.

```csv
column_1,column_2
1,2
3,4,5
```

### Desajuste de tipo

**Tipo de error:** `type-error`

Este error ocurre cuando un valor no coincide con el tipo de dato inferido para su
columna.

Por ejemplo, cuando la mayoría de valores en una columna son numéricos, un valor de texto se
reporta como inválido:

```csv
amount
100
250.50
300
invalid
```

La misma regla se aplica a columnas de fechas. Una vez que se infiere un formato de fecha, los valores
que utilizan otro formato o contienen fechas inválidas se reportan como errores:

```csv
date
2024-04-25
2024-05-10
25/06/2024
```

### Valor requerido faltante

**Tipo de error:** `constraint-error`

Cada campo inferido está configurado como requerido. Este error ocurre cuando una
celda requerida contiene un valor faltante.

Los valores `null`, `NULL` y `None` se tratan explícitamente como faltantes:

```csv
column_1,column_2
1,2
3,null
4,None
```

### Error de validación estructural

**Tipo de error:** `structure-error`

Este es un error de reserva generado por `ckanext-validate` cuando Frictionless
marca el recurso como inválido pero no proporciona detalles de errores a nivel de fila.

Indica que el archivo contiene un problema estructural que no pudo ser
representado como uno de los errores detallados enumerados arriba.

## Comportamiento del informe de errores

Los errores de validación se agrupan por tipo de error en el informe.

Para cada grupo, el informe muestra:

- El título y descripción del error.
- El número total de ocurrencias.
- Una vista previa de las filas y celdas afectadas.
- Hasta 20 filas afectadas.

Cuando un grupo de errores contiene más de 20 filas, el informe indica que solo
se están mostrando los primeros 20.
