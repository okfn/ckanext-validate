# Lista completa de errores de tabla detectados

Este documento describe los errores de validacion que actualmente presenta
`ckanext-validate` al validar recursos CSV.

La extension usa Frictionless para inferir la estructura de la tabla y validar
el archivo. Tambien aplica reglas adicionales de deteccion para columnas
numericas y de fecha.

## Reglas de validacion

Antes de validar un archivo CSV, la extension aplica las siguientes reglas:

- Cada columna inferida se configura como obligatoria.
- Los valores `null`, `NULL` y `None` se tratan como valores faltantes.
- Una columna se considera numerica cuando al menos el 50% de sus valores no
  faltantes se pueden interpretar como numeros.
- Una columna numerica se infiere como `integer` cuando todos los valores
  numericos detectados son enteros. De lo contrario, se infiere como `number`.
- Una columna se considera de fecha cuando al menos el 50% de sus valores no
  faltantes usa el mismo formato de fecha admitido.
- Los formatos de fecha admitidos son:
  - `MM/DD/YYYY`, por ejemplo `04/25/2024`.
  - `DD/MM/YYYY`, por ejemplo `25/04/2024`.
  - `YYYY-MM-DD`, por ejemplo `2024-04-25`.

Despues de inferir el esquema, Frictionless valida cada fila contra ese
esquema. Los valores que no coinciden con el tipo inferido, el formato o la
restriccion requerida se reportan como errores de validacion.

## Errores que actualmente se muestran en el reporte

### Encabezado faltante

**Tipo de error:** `missing-label`

Una columna de la fila de encabezados no tiene nombre. Cada columna debe tener
un encabezado unico y no vacio.

### Encabezado duplicado

**Tipo de error:** `duplicate-label`

Dos o mas columnas comparten el mismo nombre. Los nombres de columna deben ser
unicos.

### Fila vacia

**Tipo de error:** `blank-row`

Esta fila no tiene datos. Las filas deben contener al menos una celda con
datos.

### Incompatibilidad de tipo

**Tipo de error:** `type-error`

El valor de una celda no coincide con el tipo de dato o el formato esperado
para la columna.

Por ejemplo, cuando la mayoria de los valores en una columna son numericos, un
valor de texto se reporta como invalido:

```csv
amount
100
250.50
300
invalid
```

La misma regla aplica para las fechas. Una vez que se detecta un formato de
fecha, los valores que no coinciden con ese formato se reportan como invalidos:

```csv
date
2024-04-25
2024-05-10
25/06/2024
```

### Valor faltante

**Tipo de error:** `missing-cell`

A esta celda le falta un dato.

### Celda extra

**Tipo de error:** `extra-cell`

Esta fila tiene mas valores que la fila de encabezados.

```csv
column_1,column_2
1,2
3,4,5
```

### Encabezado en blanco

**Tipo de error:** `blank-header`

Una columna de la fila de encabezados no tiene nombre. Cada columna debe tener
un encabezado unico y no vacio.

### Etiqueta en blanco

**Tipo de error:** `blank-label`

Una etiqueta en la fila de encabezados no tiene valor. Las etiquetas no deben
estar en blanco.

```csv
column_1,
1,2
3,4
```

### Error estructural de validacion

**Tipo de error:** `structure-error`

El validador no pudo extraer errores por fila del reporte de validacion.

Este es un error de respaldo generado por `ckanext-validate` cuando la
validacion falla pero Frictionless no proporciona errores detallados por fila.

## Comportamiento del reporte de errores

Los errores de validacion se agrupan por tipo de error.

Para cada grupo, el reporte muestra:

- Un titulo amigable para el usuario.
- Una descripcion del error.
- El numero total de ocurrencias.
- Una vista previa de las filas y celdas afectadas.
- Hasta 20 filas afectadas.

Cuando un grupo contiene mas de 20 filas, solo se muestran las primeras 20.