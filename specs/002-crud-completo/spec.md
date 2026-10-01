# Feature Specification: CRUD completo de gastos y usuario

**Feature Branch**: `002-crud-completo`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "CRUD completo de la API de gastos y usuario: fecha en los gastos, consulta/edición (PUT y PATCH)/borrado por id, filtros, orden y resumen, gestión del propio usuario (/me), tools MCP equivalentes y chequeo de salud. Gasto ajeno => 403, inexistente => 404. El límite de 500 por categoría sigue siendo acumulado histórico. Los tokens anteriores al cambio dejan de valer."

## Clarifications

### Session 2026-10-01

- Q: ¿Cambiar el email o eliminar la cuenta debe exigir la contraseña actual del usuario, además de la credencial de sesión? → A: Sí, ambas acciones exigen la contraseña actual; si es incorrecta => regla de negocio (400) y si no se envía => datos inválidos (422); en ambos casos no cambia nada.
- Q: Si el usuario lista sus gastos sin indicar orden, ¿en qué orden deben venir? → A: Orden de creación ascendente (el más antiguo primero), igual que hoy.
- Q: En el resumen por categoría, ¿deben aparecer también las categorías en las que el usuario no tiene gastos? → A: Sí, siempre todas las categorías permitidas; las sin gastos van con total 0, cantidad 0 y disponible 500.
- Q: Si el mismo usuario envía dos gastos o ediciones al mismo tiempo que juntos superan el límite de 500, ¿el sistema debe garantizar que el límite nunca se supere? → A: Sí, garantizado: las operaciones que cambian el total de una categoría de un usuario no pueden superar el límite ni siendo simultáneas, y se verifica con una prueba de concurrencia.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Corregir o eliminar un gasto ya registrado (Priority: P1)

Un usuario registró un gasto con un dato equivocado (monto mal tipeado, categoría errónea) o que ya no quiere conservar. Hoy no puede consultarlo, corregirlo ni borrarlo. Quiere ver un gasto puntual, reemplazarlo por completo, modificar solo algunos campos o eliminarlo.

**Why this priority**: sin edición ni borrado, un error de captura es irrecuperable. Es el hueco funcional más importante y la base de las demás historias.

**Independent Test**: se prueba creando un gasto, consultándolo por su identificador, reemplazándolo, modificándolo parcialmente y eliminándolo; entrega valor por sí sola porque el usuario ya puede mantener sus datos.

**Acceptance Scenarios**:

1. **Given** un gasto propio, **When** el usuario lo consulta por su identificador, **Then** recibe descripción, monto, categoría y fecha.
2. **Given** un gasto propio, **When** lo reemplaza enviando descripción, monto, categoría y fecha válidos, **Then** el gasto queda con los valores nuevos.
3. **Given** un gasto propio, **When** intenta reemplazarlo sin enviar alguno de los cuatro campos, **Then** se rechaza por datos inválidos y el gasto no cambia.
4. **Given** un gasto propio, **When** modifica solo el monto, **Then** el monto cambia y los demás campos quedan igual.
5. **Given** un gasto propio, **When** envía una modificación parcial vacía, **Then** se rechaza por datos inválidos.
6. **Given** un gasto propio, **When** lo elimina, **Then** el gasto deja de existir y consultarlo después indica que no existe.
7. **Given** un identificador que no existe, **When** el usuario lo consulta, modifica o elimina, **Then** recibe "no existe".
8. **Given** un gasto de otro usuario, **When** el usuario intenta consultarlo, modificarlo o eliminarlo, **Then** recibe "acceso denegado" y el gasto no cambia.

---

### User Story 2 - Respetar el límite por categoría al editar (Priority: P1)

El límite de 500 por categoría (acumulado histórico) no debe poder esquivarse editando. Si un usuario cambia el monto o la categoría de un gasto, el sistema debe evaluar el límite como si ese gasto ya no estuviera en su categoría anterior y se contara en la resultante.

**Why this priority**: es una regla de negocio existente (spec 001); si la edición la rompe, el límite pierde sentido.

**Independent Test**: con gastos que suman 400 en una categoría, editar uno de ellos hacia arriba y hacia otra categoría y comprobar que se acepta o rechaza según el total resultante.

**Acceptance Scenarios**:

1. **Given** gastos de `comida` por 400 en total, incluido uno de 100, **When** el usuario sube ese gasto a 150 (total 450), **Then** se acepta.
2. **Given** el mismo caso, **When** lo sube a 250 (total 550), **Then** se rechaza por límite excedido y el monto queda en 150.
3. **Given** 450 en `comida` y un gasto de 100 en `transporte`, **When** el usuario lo mueve a `comida`, **Then** se rechaza por límite excedido y el gasto sigue en `transporte`.
4. **Given** un gasto que no cambia de categoría ni de monto, **When** el usuario lo guarda otra vez, **Then** no se rechaza por contarse a sí mismo.
5. **Given** 400 acumulados en `comida`, **When** el mismo usuario envía a la vez dos gastos de 60 en `comida`, **Then** exactamente uno se acepta, el otro se rechaza por límite excedido y el total queda en 460 (nunca 520).

---

### User Story 3 - Buscar, ordenar y resumir mis gastos (Priority: P2)

Un usuario con muchos gastos quiere encontrar los de un período o categoría, ordenarlos por fecha o monto, saber cuántos hay en total y ver cuánto lleva gastado por categoría y cuánto le queda antes del límite.

**Why this priority**: mejora mucho la utilidad del listado, pero el sistema es usable sin esto.

**Independent Test**: con gastos de varias categorías, fechas y montos (propios y de otro usuario), listar con distintas combinaciones de filtros y orden y consultar el resumen.

**Acceptance Scenarios**:

1. **Given** gastos propios variados y gastos de otro usuario, **When** el usuario lista filtrando por categoría, rango de fechas y rango de montos, **Then** recibe solo gastos propios que cumplen todos los filtros.
2. **Given** un listado paginado, **When** la respuesta se entrega, **Then** informa el total de gastos que cumplen los filtros, sin importar la página pedida.
3. **Given** varios gastos, **When** pide orden por monto descendente, **Then** los recibe de mayor a menor monto.
4. **Given** un rango de fechas con inicio posterior al fin, o un orden desconocido, **When** lista, **Then** se rechaza por datos inválidos.
5. **Given** gastos en `comida` (120) y `transporte` (30), **When** consulta el resumen, **Then** ve las cuatro categorías permitidas, cada una con total, cantidad y cuánto falta para el límite (las categorías sin gastos con 0, 0 y 500), más un total general de 150.
6. **Given** un resumen acotado por rango de fechas, **When** se calcula, **Then** total y cantidad cuentan solo ese rango, pero "cuánto falta para el límite" se calcula sobre el total histórico de la categoría.
7. **Given** un usuario autenticado, **When** consulta las categorías, **Then** recibe exactamente las permitidas y el límite por categoría.

---

### User Story 4 - Fecha en cada gasto (Priority: P2)

Cada gasto tiene la fecha en que ocurrió, que el usuario puede indicar; si no lo hace, es hoy. No puede ser una fecha futura. Los gastos ya existentes quedan con la fecha en que se actualizó el sistema.

**Why this priority**: habilita filtrar por período y ordenar por fecha (Historia 3).

**Independent Test**: crear un gasto sin fecha y con fecha pasada y futura; verificar el resultado de cada caso.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado, **When** crea un gasto sin fecha, **Then** el gasto queda con la fecha de hoy.
2. **Given** un usuario autenticado, **When** crea o modifica un gasto con fecha futura, **Then** se rechaza por datos inválidos y no se guarda nada.
3. **Given** gastos creados antes de esta funcionalidad, **When** se actualiza el sistema, **Then** ninguno se pierde y todos quedan con la fecha de la actualización.

---

### User Story 5 - Administrar mi propia cuenta (Priority: P2)

Un usuario quiere ver su perfil, cambiar su email, cambiar su contraseña (demostrando que conoce la actual) y, si lo desea, eliminar su cuenta junto con todos sus gastos.

**Why this priority**: completa la gestión de usuario; no bloquea el uso diario de los gastos.

**Independent Test**: con un usuario registrado, consultar el perfil, cambiar email y contraseña, y eliminar la cuenta, verificando el acceso en cada paso.

**Acceptance Scenarios**:

1. **Given** un usuario autenticado, **When** consulta su perfil, **Then** ve su identificador y email, sin ningún dato de contraseña.
2. **Given** un email libre, **When** el usuario lo adopta dando su contraseña actual correcta, **Then** el cambio se aplica y recibe una credencial nueva válida para ese email.
3. **Given** un email ya usado por otro usuario, **When** intenta adoptarlo, **Then** se rechaza como regla de negocio y su email no cambia.
4. **Given** un cambio de email, **When** la contraseña actual es incorrecta o no se envía, **Then** se rechaza (400 si es incorrecta, 422 si no se envía) y su email no cambia.
5. **Given** un usuario que cambió su email, **When** usa la credencial anterior, **Then** es rechazado como no autenticado, aunque otro usuario haya registrado después el email anterior (nunca opera como esa otra persona).
6. **Given** un usuario autenticado, **When** cambia su contraseña dando la actual correcta y una nueva distinta, **Then** puede iniciar sesión con la nueva y no con la anterior.
7. **Given** una contraseña actual incorrecta o una nueva igual a la actual, **When** intenta el cambio, **Then** se rechaza como regla de negocio y la contraseña no cambia.
8. **Given** una contraseña nueva de menos de 8 o más de 72 caracteres, **When** intenta el cambio o el registro, **Then** se rechaza por datos inválidos.
9. **Given** un usuario con gastos, **When** elimina su cuenta dando su contraseña actual correcta, **Then** su cuenta y todos sus gastos desaparecen, los gastos de otros usuarios no se tocan y su credencial deja de servir.
10. **Given** una eliminación de cuenta, **When** la contraseña actual es incorrecta o no se envía, **Then** se rechaza (400 si es incorrecta, 422 si no se envía) y no se borra nada.

---

### User Story 6 - Gestionar gastos desde el asistente (MCP) (Priority: P3)

El usuario que trabaja con el asistente de IA quiere las mismas operaciones de gastos que tiene por API: consultar uno, actualizar (parcialmente), eliminar, ver el resumen, ver las categorías y listar con los filtros nuevos. Eliminar es destructivo: debe exigir confirmación explícita.

**Why this priority**: amplía el canal, pero depende de que las historias 1-4 existan.

**Independent Test**: invocar cada herramienta con datos válidos y con errores (gasto ajeno, inexistente, dato inválido) y comprobar que nunca falla con una excepción sin controlar.

**Acceptance Scenarios**:

1. **Given** un gasto propio, **When** el asistente lo consulta, actualiza o consulta el resumen y las categorías, **Then** recibe el resultado igual que por la API.
2. **Given** un gasto ajeno, inexistente o un valor inválido, **When** el asistente opera, **Then** recibe un mensaje de error estructurado y nada cambia.
3. **Given** un gasto propio, **When** el asistente pide eliminarlo sin confirmar, **Then** no se borra nada y recibe un error que pide confirmación.
4. **Given** el mismo gasto, **When** el asistente pide eliminarlo confirmando, **Then** el gasto se elimina.
5. **Given** gastos de varias categorías, **When** el asistente lista filtrando por categoría y ordenando, **Then** recibe solo los propios, filtrados y ordenados.

---

### User Story 7 - Saber si el servicio está sano (Priority: P3)

Quien opera el servicio quiere un chequeo, sin autenticación, que indique si la aplicación y su base de datos responden.

**Why this priority**: utilidad operativa; no afecta al usuario final.

**Independent Test**: consultar el chequeo con la base disponible y con la base detenida.

**Acceptance Scenarios**:

1. **Given** la aplicación y la base funcionando, **When** se consulta el chequeo, **Then** responde éxito indicando que ambas están bien.
2. **Given** la base de datos caída, **When** se consulta el chequeo, **Then** responde "servicio no disponible" y no un error genérico.

---

### Edge Cases

- Una modificación parcial que intenta poner un campo en vacío/nulo explícito se trata como dato inválido.
- Campos que el cliente no debe controlar (`id`, `usuario_id`) enviados en el cuerpo se rechazan al reemplazar o modificar; al crear se ignoran, igual que en la spec 001 (el dueño siempre sale de la credencial).
- El mismo email con distinta capitalización se considera el mismo email (se guarda en minúsculas).
- Descripción con espacios en los extremos se guarda sin ellos; solo espacios cuenta como vacía.
- Monto con más de dos decimales, cero, negativo o mayor a 1.000.000 es inválido.
- Listar sin resultados devuelve lista vacía y total 0, no un error.
- Eliminar la cuenta con una credencial ya usada para eliminarla devuelve "no autenticado".
- Las rutas fijas (resumen, categorías) no deben confundirse con un identificador de gasto.
- Si dos peticiones editan a la vez el mismo gasto, gana la última sin dejar el gasto en estado intermedio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir al dueño consultar un gasto por identificador; inexistente => "no existe" (404); de otro usuario => "acceso denegado" (403).
- **FR-002**: El sistema MUST permitir reemplazar un gasto completo exigiendo descripción, monto, categoría y fecha; si falta alguno => datos inválidos (422).
- **FR-003**: El sistema MUST permitir modificar parcialmente un gasto exigiendo al menos un campo; el resultado combinado debe ser válido.
- **FR-004**: El sistema MUST permitir eliminar un gasto propio, respondiendo sin contenido (204); un acceso posterior indica que no existe.
- **FR-005**: Cada gasto MUST tener una fecha, por defecto la de hoy, que no puede ser futura.
- **FR-006**: Los gastos existentes MUST conservarse al incorporar la fecha, con la fecha de la actualización.
- **FR-007**: Al crear, reemplazar o modificar, el límite de 500 por categoría (acumulado histórico) MUST evaluarse excluyendo el gasto editado y sobre la categoría resultante, y MUST cumplirse también cuando varias peticiones del mismo usuario llegan a la vez: el total de una categoría nunca supera el límite por simultaneidad.
- **FR-008**: El listado MUST aceptar filtros opcionales por categoría, rango de fechas y rango de montos, y orden por fecha o monto ascendente/descendente; sin orden indicado MUST devolverlos por orden de creación ascendente (el más antiguo primero), y si el orden pedido empata MUST desempatar por orden de creación, para que la paginación sea estable; MUST mantener paginación y MUST informar el total sin paginar en el encabezado `X-Total-Count`.
- **FR-009**: Un rango de fechas con inicio posterior al fin, un rango de montos con mínimo mayor al máximo o un orden desconocido MUST rechazarse como datos inválidos.
- **FR-010**: El sistema MUST ofrecer un resumen que incluya siempre todas las categorías permitidas (las sin gastos con total 0, cantidad 0 y disponible igual al límite), con total, cantidad y cuánto falta para el límite (calculado sobre el total histórico), más el total general; el rango de fechas opcional solo acota total y cantidad.
- **FR-011**: El sistema MUST ofrecer la lista de categorías permitidas y el límite por categoría, tomados de la misma fuente que usa la validación.
- **FR-012**: Los datos de gasto MUST validarse: descripción sin espacios en los extremos de 1 a 200 caracteres; monto mayor que 0, hasta dos decimales y hasta 1.000.000; categoría solo de las permitidas; fecha no futura; campos desconocidos rechazados al reemplazar o modificar (al crear se ignoran, contrato 001). Descripción vacía, monto menor o igual a 0 y categoría inválida siguen siendo reglas de negocio (400), como en 001.
- **FR-013**: Las contraseñas MUST tener entre 8 y 72 caracteres y los emails MUST guardarse y compararse en minúsculas.
- **FR-014**: El usuario MUST poder consultar su perfil sin que se exponga ningún dato de contraseña.
- **FR-015**: El usuario MUST poder cambiar su email dando su contraseña actual; contraseña incorrecta o email en uso => regla de negocio (400); contraseña no enviada => datos inválidos (422); si se acepta, recibe una credencial nueva.
- **FR-016**: El usuario MUST poder cambiar su contraseña dando la actual; actual incorrecta o nueva igual a la actual => regla de negocio (400); éxito sin contenido (204).
- **FR-017**: El usuario MUST poder eliminar su cuenta dando su contraseña actual, lo que elimina también todos sus gastos y ninguno ajeno (204); contraseña incorrecta => regla de negocio (400) y contraseña no enviada => datos inválidos (422), sin borrar nada en ambos casos.
- **FR-018**: Una credencial emitida antes de un cambio de email o de la eliminación de la cuenta MUST ser rechazada (401) y nunca MUST operar como otro usuario que registre después ese email; para ello la credencial identifica además al usuario por su id y ambos datos se verifican.
- **FR-019**: Las credenciales emitidas antes de esta funcionalidad MUST dejar de ser válidas; los usuarios vuelven a iniciar sesión.
- **FR-020**: El asistente (MCP) MUST disponer de herramientas para consultar un gasto, actualizarlo parcialmente, eliminarlo, ver el resumen y ver las categorías; y el listado MUST aceptar los filtros nuevos.
- **FR-021**: La herramienta de eliminar MUST no borrar nada salvo confirmación explícita; los errores de negocio, de inexistencia o de dueño MUST devolverse como mensaje estructurado y nunca como excepción sin controlar.
- **FR-022**: El sistema MUST ofrecer un chequeo de salud sin autenticación: éxito con base disponible; "servicio no disponible" (503) si la base falla.
- **FR-023**: Toda operación sobre gastos MUST limitarse a los del usuario autenticado; el identificador de usuario nunca proviene del cliente.
- **FR-024**: Lo existente de la spec 001 (rutas, herramientas MCP, comportamiento, límite de 500) MUST mantenerse sin cambios incompatibles; solo se agrega.
- **FR-025**: Los códigos de respuesta (200, 204, 400, 401, 403, 404, 422, 503) MUST quedar reflejados en la constitución del proyecto, que hoy no lista 204 ni PUT/PATCH.

### Key Entities

- **Gasto**: descripción, monto, categoría, fecha y dueño. Un gasto pertenece a un único usuario; dejar de existir el usuario implica dejar de existir sus gastos.
- **Usuario**: identificador, email único (en minúsculas) y contraseña protegida. Es dueño de cero o más gastos.
- **Credencial de acceso**: acredita a un usuario; identifica tanto su email como su id y caduca.
- **Categoría**: valor de un conjunto fijo permitido, con un límite acumulado de 500 por usuario.
- **Resumen de categoría**: total, cantidad y disponible de una categoría para un usuario.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un usuario puede corregir o eliminar un gasto equivocado en una sola operación, sin necesidad de ayuda externa.
- **SC-002**: En 100% de los intentos de crear, editar o mover gastos, incluso simultáneos, nunca se supera el límite de 500 por categoría ni se rechaza un cambio que sí lo respeta.
- **SC-003**: En 100% de los intentos de acceder a gastos o cuentas de otro usuario, ningún dato ajeno se muestra ni se modifica.
- **SC-004**: Un usuario encuentra los gastos de un período y categoría concretos con una sola consulta y conoce cuánto lleva gastado por categoría sin cálculos manuales.
- **SC-005**: Ninguna credencial anterior a un cambio de email o eliminación de cuenta permite operar, ni como el mismo usuario ni como otro.
- **SC-006**: Al actualizar el sistema con gastos ya registrados, se conserva el 100% de ellos.
- **SC-007**: Cada una de las operaciones nuevas tiene al menos un caso exitoso y un caso de error verificados automáticamente, con cobertura de pruebas igual o mayor a la exigida por la constitución.
- **SC-008**: Quien opera el servicio distingue en una consulta si la aplicación y su base están sanas o no.

## Assumptions

- El límite de 500 por categoría sigue siendo acumulado histórico, no mensual (decisión de la spec 001, reafirmada); la fecha no lo afecta.
- Un gasto ajeno responde "acceso denegado" (403) y uno inexistente "no existe" (404), según la constitución; se acepta que esto permite saber si un identificador existe.
- No hay rol de administrador; nadie accede a gastos ajenos (regla de la spec 001).
- La fecha de hoy es la del servidor; no hay zonas horarias por usuario.
- Se mantiene el reset administrativo de contraseñas ya existente; no se agrega recuperación por email.
- Fuera de alcance: invalidar credenciales al cambiar contraseña, renovación/revocación de credenciales, borrado lógico, historial de cambios, exportación, paginación por cursor y herramientas MCP de gestión de usuario.
- Las credenciales emitidas antes del cambio dejan de valer; los clientes REST y MCP vuelven a iniciar sesión (caducan en pocos minutos de todas formas).
- Registrarse con contraseña de menos de 8 caracteres pasa a rechazarse; los usuarios existentes no se ven afectados.
- Requiere enmendar el Art. V.1 de la constitución (PUT/PATCH => 200, DELETE => 204) y aclarar el Art. VI.2 ("límite acumulado", no "mensual").
- Es aditivo sobre lo existente: se conservan firmas, rutas y herramientas de la spec 001 (Art. VIII).
