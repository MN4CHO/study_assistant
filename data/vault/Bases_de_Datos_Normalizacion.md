# Normalización de Bases de Datos

La normalización es un proceso para organizar los datos en una base de datos
relacional con el fin de reducir la redundancia y mejorar la integridad.

## Primera Forma Normal (1FN)

Una tabla esta en 1FN si todos sus atributos son atomicos (no divisibles) y
no existen grupos repetitivos.

## Segunda Forma Normal (2FN)

Una tabla esta en 2FN si esta en 1FN y todos los atributos no clave dependen
completamente de la clave primaria (no hay dependencias parciales).

## Tercera Forma Normal (3FN)

Una tabla esta en 3FN si esta en 2FN y no existen dependencias transitivas
entre atributos no clave.

## Nota personal

Repasar bien la diferencia entre dependencia parcial y dependencia
transitiva, siempre me confundo en el examen.
