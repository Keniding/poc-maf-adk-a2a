# Testing Guide - Google ADK Compliance Agent

## Test Scripts

Este módulo incluye varios scripts de test para verificar que todo funcione correctamente.

### Quick Test

Ejecuta el test completo:

```bash
python test_all.py
```

Este script verifica:
- Imports de módulos
- Configuración de settings
- Conectividad con la base de datos
- Funcionamiento de las herramientas
- Configuración del agente ADK
- Creación de la app A2A

### Tests Individuales

**Test de Imports:**
```bash
python test_imports.py
```
Verifica que todos los imports funcionen correctamente.

**Test del Servidor:**
```bash
python test_server.py
```
Verifica que el servidor A2A pueda inicializarse.

**Test de Base de Datos:**
```bash
python test_database.py
```
Verifica que las herramientas puedan acceder a la base de datos.

**Ver Esquema de BD:**
```bash
python check_schema.py
```
Muestra el esquema completo de la base de datos.

## Solución de Problemas

### Error: "GOOGLE_API_KEY is required"

Asegúrate de tener el archivo `.env` configurado:

```bash
cp .env.example .env
# Edita .env y añade tu GOOGLE_API_KEY
```

### Error: "Database not found"

Inicializa la base de datos:

```bash
cd ../shared/database
python setup_db.py
```

### Error: "Module not found"

Verifica que estés en el entorno virtual correcto:

```bash
..\.venv-google\Scripts\activate
pip install -r requirements.txt
```

## Estructura de Tests

```
google-agent/
├── test_all.py          # Test suite completo
├── test_imports.py      # Test de imports
├── test_server.py       # Test de servidor
├── test_database.py     # Test de base de datos
└── check_schema.py      # Utilidad para ver esquema DB
```

## Ejecución Exitosa

Cuando todos los tests pasan, verás:

```
============================================================
ALL TESTS PASSED!
============================================================

The Google ADK Compliance Agent is ready to run.

Available commands:
  1. A2A Server:      python server.py
  2. ADK CLI:         adk run google-agent
  3. ADK Web UI:      adk web --port 8000
```

Esto confirma que el agente está listo para uso en producción.