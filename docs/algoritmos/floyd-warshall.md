# Floyd-Warshall

[← Inicio](../../README.md) · [Recorridos](../recorrido.md)

Calcula **todos los pares**, con independencia de los selectores de origen/destino. Estos solo consultan y resaltan una ruta del estado actual.

Inicialmente se muestra una **iteración completa de k** por paso. Activa **Por comparación** para ver todos los triples `(i,j,k)`, incluidos los que no mejoran o contienen ∞. Cada comparación y su actualización constituyen un único paso: distancia anterior, `D[i,k]`, `D[k,j]`, suma candidata, mejora/sin cambio y resultado.

Las dos matrices aparecen simultáneamente:

- **Distancias:** diagonal inicial 0; ∞ si no existe ruta. Entre conexiones paralelas se elige la de menor peso; los empates conservan la primera clave.
- **Recorridos:** inicialmente muestra el destino en rutas directas, el nodo propio en la diagonal y **—** si no hay ruta. Una mejora a través de k registra **k como intermedio**. No es una matriz de siguiente salto ni de predecesores. Internamente, composiciones inmutables de recorridos conservan las conexiones exactas y permiten reconstruir la ruta completa sin depender de entradas que cambien después.

Fila, columna y encabezados de **k**: verde. Mejoras acumuladas durante esa iteración: amarillo. Si coinciden, fondo amarillo y borde verde. La comparación actual tiene un borde violeta. Al comenzar otro k se limpian las mejoras; al retroceder se recuperan los colores del estado elegido.

La fase final identifica todos los pares que pueden atravesar un ciclo negativo, los marca **−∞** y retira su recorrido. Los pares no afectados siguen consultables. La reconstrucción tiene protecciones contra ciclos y recorridos inválidos.
