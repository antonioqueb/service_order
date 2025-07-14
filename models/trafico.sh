#!/bin/bash

# Nombre base del módulo
MODULE_NAME="trafico_logistica"

# Crear directorio raíz del módulo
mkdir -p $MODULE_NAME

# Crear archivos raíz
touch $MODULE_NAME/__init__.py
touch $MODULE_NAME/__manifest__.py

# Crear subdirectorios y archivos
mkdir -p $MODULE_NAME/data
touch $MODULE_NAME/data/trafico_data.xml
touch $MODULE_NAME/data/trafico_sequences.xml

mkdir -p $MODULE_NAME/models
touch $MODULE_NAME/models/__init__.py
touch $MODULE_NAME/models/trafico_operador.py
touch $MODULE_NAME/models/trafico_unidad.py
touch $MODULE_NAME/models/trafico_contenedor.py
touch $MODULE_NAME/models/trafico_tipo_servicio.py
touch $MODULE_NAME/models/trafico_tipo_licencia.py
touch $MODULE_NAME/models/trafico_orden_servicio.py
touch $MODULE_NAME/models/trafico_programacion.py
touch $MODULE_NAME/models/trafico_alerta.py
touch $MODULE_NAME/models/fleet_vehicle_inherit.py
touch $MODULE_NAME/models/service_order_inherit.py

mkdir -p $MODULE_NAME/views
touch $MODULE_NAME/views/trafico_menus.xml
touch $MODULE_NAME/views/trafico_operador_views.xml
touch $MODULE_NAME/views/trafico_unidad_views.xml
touch $MODULE_NAME/views/trafico_contenedor_views.xml
touch $MODULE_NAME/views/trafico_orden_servicio_views.xml
touch $MODULE_NAME/views/trafico_programacion_views.xml
touch $MODULE_NAME/views/trafico_dashboard_views.xml

mkdir -p $MODULE_NAME/wizard
touch $MODULE_NAME/wizard/__init__.py
touch $MODULE_NAME/wizard/trafico_programar_servicio_wizard.py
touch $MODULE_NAME/wizard/trafico_programar_servicio_views.xml

mkdir -p $MODULE_NAME/security
touch $MODULE_NAME/security/ir.model.access.csv
touch $MODULE_NAME/security/trafico_security.xml

mkdir -p $MODULE_NAME/static/description
touch $MODULE_NAME/static/description/icon.png

echo "Estructura del módulo '$MODULE_NAME' creada correctamente."
