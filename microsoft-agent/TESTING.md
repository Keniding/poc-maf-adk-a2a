# Testing Guide - Microsoft Account Agent

## Test Script

### Complete Test

Ejecuta el test completo:

```bash
python test_all.py
```

Este script verifica:
- Imports de módulos
- Configuración de settings
- Conectividad con la base de datos
- Funcionamiento de las herramientas (search_customer, get_customer_accounts, etc.)
- Autenticación con Azure
- Creación del FoundryAgent v2
- Configuración del A2aAgentExecutor
- Creación de la app Starlette

## Prerequisitos

### 1. Azure Authentication

Asegúrate de estar autenticado con Azure CLI:

```bash
az login
az account show
```

### 2. Environment Configuration

El archivo `.env` debe estar configurado con:

```env
FOUNDRY_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-4o
FOUNDRY_AGENT_NAME=account-agent
FOUNDRY_AGENT_VERSION=1.0
AZURE_CREDENTIAL_TYPE=AzureCliCredential
ACCOUNT_A2A_PORT=8002
```

### 3. Database

La base de datos debe estar inicializada:

```bash
cd ../shared/database
python setup_db.py
```

## Solución de Problemas

### Error: "Azure authentication failed"

```bash
az login
az account list
# Selecciona la suscripción correcta
az account set --subscription "tu-suscripción"
```

### Error: "Foundry project not found"

Verifica que:
- El endpoint sea correcto en `.env`
- Tengas acceso al proyecto en Azure AI Foundry
- El proyecto exista y esté activo

### Error: "Database not found"

```bash
cd ../shared/database
python setup_db.py
```

### Error: "Module not found"

Verifica que estés en el entorno virtual correcto:

```bash
..\.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución Exitosa

Cuando todos los tests pasan, verás:

```
============================================================
ALL TESTS PASSED!
============================================================

The Microsoft Account Agent is ready to run.

Available commands:
  1. A2A Server:      python server.py
```

Esto confirma que el agente está listo para producción.

## Siguiente Paso

Publica el agente en Azure AI Foundry (si no lo has hecho):

```bash
python -m agents.account_agent
```

Luego inicia el servidor A2A:

```bash
python server.py
```