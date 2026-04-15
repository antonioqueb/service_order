Con base estricta en los archivos adjuntos, esta es la documentación técnica compacta del módulo **`manifiesto_ambiental`**. En este código **no existe implementación** de **apartados/reservas**, ni de **fotos de lotes**, **foto principal del lote** o **carga múltiple de imágenes por lote**; por lo tanto, eso no puede documentarse como funcionalidad existente aquí. Lo que sí existe es carga de **documento físico** sobre el manifiesto. 

## Documentación técnica — módulo `manifiesto_ambiental`

### 1. Identificación del módulo

**Nombre técnico:** `manifiesto_ambiental`
**Versión:** `19.0.2.1.0`
**Autor:** Alphaqueb Consulting
**Dependencias:** `mail`, `base`, `contacts`, `service_order`, `stock`, `residuo_recepcion_sai`, `fleet`
**Objetivo:** gestión de manifiestos ambientales de residuos peligrosos con versionado, integración con orden de servicio, recepción y reporte de discrepancias. 

### 2. Modelos implementados

**Modelos nuevos**

* `manifiesto.ambiental`
* `manifiesto.ambiental.residuo`
* `manifiesto.ambiental.version`
* `manifiesto.discrepancia`
* `manifiesto.discrepancia.linea`

**Extensiones**

* `service.order`
* `res.partner`
* `product.template`
* `product.product`
* `residuo.recepcion` 

### 3. Flujo funcional principal

El flujo parte desde `service.order` mediante `action_create_manifiesto()`, que genera un registro `manifiesto.ambiental`, precarga generador, transportista, destinatario, vehículo, placa, chofer, ruta y construye `residuo_ids` a partir de `line_ids` de la orden de servicio. Se excluyen líneas sin producto y productos cuyo nombre inicie con `SERVICIO DE`. La cantidad del residuo se toma de `weight_kg` si es mayor a cero; en caso contrario, usa `product_uom_qty`. 

Una vez creado, el manifiesto trabaja con estados `draft`, `confirmed`, `in_transit`, `delivered` y `cancel`, controlados por `action_confirm()`, `action_in_transit()`, `action_delivered()` y `action_cancel()`. Desde estados `in_transit` o `delivered` puede generar recepción con `action_recibir_residuos()` y reporte de discrepancia con `action_crear_discrepancia()`. 

### 4. Estructura técnica de `manifiesto.ambiental`

El modelo `manifiesto.ambiental` hereda `mail.thread` y `mail.activity.mixin`, por lo que tiene chatter, tracking y actividades. Usa `_rec_name = numero_manifiesto` y orden `_order = 'numero_manifiesto desc, version desc'`. Contiene tres bloques funcionales principales: control documental, integración operativa y versionado. 

#### 4.1 Control documental

Los campos principales siguen la estructura del formato oficial:

* `numero_registro_ambiental`
* `numero_manifiesto`
* `pagina`
* datos del generador
* residuos
* instrucciones especiales
* datos del transportista
* autorizaciones SEMARNAT/SCT
* vehículo y placa
* ruta
* destinatario
* observaciones y responsables de firma. 

#### 4.2 Integración operativa

El manifiesto se relaciona con:

* `service_order_id`
* `recepcion_ids`
* `discrepancia_ids`
  y expone contadores `recepcion_count` y `discrepancia_count`. Además, `action_view_recepciones()` y `action_view_discrepancias()` abren los registros vinculados. 

#### 4.3 Versionado

El versionado usa:

* `version`
* `is_current_version`
* `original_manifiesto_id`
* `version_history_ids`
* `change_reason`
* `created_by_remanifest`
* `sequence_number` 

La remanifestación se ejecuta con `action_remanifestar()` o `action_remanifestar_sin_pdf()`. Ambas crean una nueva versión del manifiesto, marcan la versión anterior como no actual y conservan el mismo `numero_manifiesto` y `sequence_number`. La diferencia es que una guarda respaldo PDF y la otra guarda un TXT estructurado en historial. 

### 5. Numeración del manifiesto

La secuencia interna real se controla con `sequence_number`, calculado por SQL con `SELECT COALESCE(MAX(sequence_number), 0) + 1 FROM manifiesto_ambiental`. El campo visible `numero_manifiesto` se genera en `_generate_manifiesto_number()` tomando iniciales significativas de la razón social del generador más la fecha en formato `DDMMYYYY`; si ya existe una base igual, agrega sufijo `-NN`. Si no hay generador, usa el consecutivo numérico como fallback. 

### 6. Autofill y onchanges

El módulo tiene onchanges para:

* `generador_id`
* `generador_responsable_id`
* `transportista_id`
* `transportista_responsable_id`
* `vehicle_id`
* `destinatario_id`

Estos copian datos de `res.partner` y `fleet.vehicle` hacia el manifiesto: dirección, CP, calle, números exterior/interior, colonia, municipio, estado, teléfono, correo, autorizaciones, tipo de vehículo y placa. `vehicle_id` completa `tipo_vehiculo` usando marca y modelo, y solo llena `numero_placa` si el campo aún está vacío. 

### 7. Integración con `service.order`

La extensión `service.order` agrega:

* `manifiesto_ids`
* `manifiesto_count`
* smart button `action_view_manifiestos`
* botón header `action_create_manifiesto` 

Reglas importantes del generador desde OS:

* `generador` para dirección = `generador_id` si existe, si no `partner_id`
* `generador_nombre` del campo 4 = siempre `partner_id.name` o fallback al generador
* `fecha_servicio` = `date_start`, `scheduled_date`, `service_date`, `date_order` o fecha actual
* `ruta_empresa` = `pickup_location_id.contact_address_complete` o `pickup_location`
* `destinatario` = `destinatario_id` o `partner_id`
* `numero_placa` = prioridad al campo de la OS; luego `vehicle.license_plate` 

### 8. Residuos y lotes

El detalle de residuos vive en `manifiesto.ambiental.residuo`. Cada línea contiene:

* `product_id`
* `nombre_residuo`
* `residue_type` (`rsu`, `rme`, `rp`)
* flags CRETIB (`clasificacion_corrosivo`, `reactivo`, `explosivo`, `toxico`, `inflamable`, `biologico`)
* `clasificaciones_display`
* `packaging_id`
* `envase_tipo`
* `envase_cantidad`
* `envase_capacidad`
* `cantidad`
* `unidad='kg'`
* `etiqueta_si` / `etiqueta_no`
* `lot_id` readonly. 

#### 8.1 Cómo funcionan los lotes en este módulo

Aquí **no hay “lotes personalizados” con campos custom sobre `stock.lot`**. Lo que existe es **generación automática de lote estándar de Odoo** desde la línea de residuo. El método `_create_lot_for_residuo()` busca o crea un `stock.lot` con esta llave lógica:

* `name = manifiesto.numero_manifiesto`
* `product_id = residuo.product_id`
* `company_id = manifiesto.company_id`

Si ya existe un lote con esa combinación, lo reutiliza; si no, lo crea y lo asigna en `lot_id`. Eso significa que el lote queda técnicamente identificado por **número de manifiesto + producto + compañía**. 

#### 8.2 Qué sí se personaliza alrededor del residuo

La personalización real está en producto y en la línea del manifiesto:

* clasificación CRETIB
* tipo de residuo
* embalaje/envase
* capacidad de envase
* etiquetado sí/no

Eso fluye desde `product.template` hacia `manifiesto.ambiental.residuo`, no directamente a `stock.lot`. 

### 9. Productos de residuos peligrosos

La extensión de `product.template` agrega:

* `es_residuo_peligroso`
* flags CRETIB
* `envase_tipo_default`
* `envase_capacidad_default`

Cuando `es_residuo_peligroso=True`, en `create()` y `write()` se fuerza:

* `type='product'`
* `product_variant_ids.tracking='lot'`

Además, al seleccionar un producto en una línea de residuo, `_onchange_product_id()` copia automáticamente nombre, CRETIB y defaults de envase/capacidad al residuo del manifiesto. 

### 10. Recepción desde manifiesto

`action_recibir_residuos()` genera un `residuo.recepcion` a partir del manifiesto. Las líneas de recepción se crean con:

* `descripcion_origen`
* `cantidad`
* `lote_asignado = numero_manifiesto`
* flags CRETIB copiados desde el residuo

La recepción queda enlazada con `manifiesto_id`, agregado por `_inherit` sobre `residuo.recepcion`. También se insertó `manifiesto_id` en vistas form, list y search del modelo de recepción. 

### 11. Discrepancias

El módulo implementa `manifiesto.discrepancia` y `manifiesto.discrepancia.linea` para comparar lo manifestado contra lo realmente recibido. El encabezado se rellena por `related` desde el manifiesto y cada línea puede autocompletarse con `residuo_manifiesto_id`. La diferencia se calcula en `_compute_tiene_diferencia()` comparando cantidad y contenedor. Los tipos contemplados son:

* `ok`
* `cantidad`
* `contenedor`
* `no_manifestado`
* `faltante`
* `ambos`
* `otro` 

### 12. Documento físico

La única funcionalidad de archivo/imagen implementada en este módulo es `documento_fisico` en `manifiesto.ambiental`, con:

* `documento_fisico`
* `documento_fisico_filename`
* `tiene_documento_fisico`

En la vista se presenta con `widget="pdf_viewer"` y acepta extensiones `.pdf`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`. Esto significa que el manifiesto puede almacenar un archivo escaneado y visualizarlo en la pestaña **Documento Físico**. 

### 13. Fotos de lotes / foto principal / múltiples fotos

**No existe en el código adjunto**:

* campo de imagen en `stock.lot`
* galería de imágenes por lote
* campo `main_image` o equivalente
* one2many de fotos
* controlador de carga múltiple
* assets JS para galería de lote
* vista de lote con imágenes

Técnicamente, en este módulo **no hay implementación de fotos de lotes**. La única binaria relacionada a archivos es `documento_fisico` del manifiesto y el resguardo de ese documento en `manifiesto.ambiental.version`. 

### 14. Apartados

En el código adjunto **no existe lógica de apartados/reservas comerciales** tipo hold order, carrito o separación de inventario. Si con “apartados” te refieres a las secciones del documento/interfaz, sí están implementadas como:

* pestañas del formulario: `Resumen`, `Generador`, `Residuos`, `Transportista`, `Destinatario`, `Documento Físico`, `Versiones`
* secciones del reporte: 1 a 19 según el formato del manifiesto. 

### 15. UI y vistas

La vista principal del manifiesto usa clase `o_manifiesto_ambiental_form_v2` y SCSS propio en `static/src/scss/manifiesto_ambiental.scss`, cargado en `web.assets_backend`. La UI incluye:

* header con acciones de estado
* smart buttons de versión, discrepancias, recepciones y documento físico
* aviso de versión histórica
* hero con número de manifiesto, tipo y fecha
* notebook por secciones
* chatter al final. 

### 16. Reportes

Se implementan dos reportes QWeb PDF:

* `action_report_manifiesto_ambiental` para manifiesto de entrada
* `action_report_discrepancia` para discrepancias

`action_print_manifiesto()` selecciona dinámicamente el reporte según `tipo_manifiesto`; para `salida` intenta usar el reporte del módulo `salida_acopio_manifiesto`. El historial de versiones puede almacenar PDF o TXT estructurado, además del documento físico original. 

### 17. Tracking y auditoría

Las líneas `manifiesto.ambiental.residuo` registran cambios en chatter del manifiesto padre. En `write()` se comparan campos rastreados y se publica un resumen legible con valores anteriores y nuevos. En `create()` y `unlink()` también se publican mensajes automáticos de alta y baja de residuos. Esto convierte al chatter del manifiesto en bitácora funcional del detalle de residuos. 

### 18. Resumen técnico ejecutivo

Este módulo implementa un flujo completo de manifiesto ambiental sobre Odoo 19: creación manual o desde orden de servicio, autollenado de actores ambientales, captura de residuos, generación automática/reutilización de lotes estándar por número de manifiesto, integración con recepción, discrepancias, documento físico escaneado, reportes PDF y versionado por remanifestación. No implementa apartados comerciales ni gestión de fotografías por lote. 
