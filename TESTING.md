# Testing Guide - POC MAF-ADK-A2A

Guía completa de testing para el proyecto de comunicación cross-framework vía A2A.

## Estructura de Tests

```
poc-maf-adk-a2a/
├── microsoft-agent/
│   ├── test_all.py          # Test suite completo Microsoft
│   └── TESTING.md           # Guía de testing Microsoft
├── google-agent/
│   ├── test_all.py          # Test suite completo Google
│   ├── test_imports.py      # Tests de imports
│   ├── test_server.py       # Tests de servidor
│   ├── test_database.py     # Tests de base de datos
│   ├── check_schema.py      # Utilidad esquema BD
│   └── TESTING.md           # Guía de testing Google
└── demo/
    └── test_integration.py  # Tests de integración A2A
```

## Quick Test - Todo el Sistema

### 1. Test Google Agent

```bash
cd google-agent
..\.venv-google\Scripts\activate
python test_all.py
```

Verifica:
- Imports y dependencias
- Configuración (settings, API key)
- Base de datos y herramientas
- Agente ADK (root_agent)
- Servidor A2A (to_a2a)

### 2. Test Microsoft Agent

```bash
cd microsoft-agent
..\.venv\Scripts\activate
python test_all.py
```

Verifica:
- Imports y dependencias
- Configuración Azure
- Base de datos y herramientas RAG
- Autenticación Azure (az login)
- FoundryAgent v2
- A2A Executor
- App Starlette

### 3. Test Integración A2A

**Prerequisito:** Ambos servidores deben estar corriendo

```bash
# Terminal 1
cd microsoft-agent
..\.venv\Scripts\activate
python server.py

# Terminal 2
cd google-agent
..\.venv-google\Scripts\activate
python server.py

# Terminal 3
cd demo
python test_integration.py
```

Verifica:
- Disponibilidad de servidores A2A
- Agent Cards accesibles
- Microsoft Agent funcional
- Google Agent funcional
- Flujo secuencial (Account → Compliance)
- Flujo concurrente (ambos en paralelo)

## Tests por Módulo

### Google Agent Tests

**Test Completo:**
```bash
python test_all.py
```

**Test de Imports:**
```bash
python test_imports.py
```

**Test de Servidor:**
```bash
python test_server.py
```

**Test de Base de Datos:**
```bash
python test_database.py
```

**Ver Esquema BD:**
```bash
python check_schema.py
```

### Microsoft Agent Tests

**Test Completo:**
```bash
python test_all.py
```

## Prerequisitos

### Base de Datos

Inicializar la base de datos compartida:

```bash
cd shared/database
python setup_db.py
```

### Google Agent

1. Archivo `.env` configurado:
```env
GOOGLE_API_KEY=your-key-here
GOOGLE_MODEL=gemini-flash-latest
COMPLIANCE_A2A_PORT=8001
```

2. Entorno virtual activado:
```bash
..\.venv-google\Scripts\activate
pip install -r requirements.txt
```

### Microsoft Agent

1. Archivo `.env` configurado:
```env
FOUNDRY_PROJECT_ENDPOINT=https://...
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-4o
FOUNDRY_AGENT_NAME=account-agent
AZURE_CREDENTIAL_TYPE=AzureCliCredential
ACCOUNT_A2A_PORT=8002
```

2. Azure CLI autenticado:
```bash
az login
```

3. Entorno virtual activado:
```bash
..\.venv\Scripts\activate
pip install -r requirements.txt
```

## Solución de Problemas Comunes

### Error: "Database not found"

```bash
cd shared/database
python setup_db.py
```

### Error: "GOOGLE_API_KEY is required"

```bash
cd google-agent
cp .env.example .env
# Editar .env y agregar GOOGLE_API_KEY
```

### Error: "Azure authentication failed"

```bash
az login
az account show
```

### Error: "Connection refused" (tests de integración)

Asegúrate de que ambos servidores estén corriendo:

```bash
# Terminal 1
cd microsoft-agent && python server.py

# Terminal 2
cd google-agent && python server.py
```

### Error: "no such column"

El esquema de la base de datos fue actualizado. Reinicializa:

```bash
cd shared/database
rm banking.db  # Si existe
python setup_db.py
```

## Ejecución Exitosa

Cuando todos los tests pasan, verás mensajes como:

```
============================================================
ALL TESTS PASSED!
============================================================
```

Esto confirma que:
- Todos los módulos están correctamente configurados
- Las dependencias están instaladas
- La base de datos está accesible
- Los agentes funcionan correctamente
- El protocolo A2A está operativo

## Test Coverage

### Unit Tests
- Google Agent: Imports, Settings, Database Tools, Agent, A2A Server
- Microsoft Agent: Imports, Settings, Database Tools, Azure Auth, Agent, A2A Executor

### Integration Tests
- Server availability (Agent Cards)
- Single agent invocation
- Sequential cross-framework flow
- Concurrent cross-framework flow

### End-to-End
- Run `demo/orchestrator.py` para ver los flujos completos en acción
- Incluye casos de uso reales con datos de ejemplo

## Continuous Testing

Durante desarrollo, ejecuta tests frecuentemente:

```bash
# Quick check - Google Agent
cd google-agent && python test_all.py

# Quick check - Microsoft Agent
cd microsoft-agent && python test_all.py

# Full integration (con servidores corriendo)
cd demo && python test_integration.py
```

## Next Steps

Después de que todos los tests pasen:

1. Inicia ambos servidores A2A
2. Ejecuta el demo: `python demo/orchestrator.py`
3. Prueba con tus propios casos de uso
4. Personaliza los agentes según necesidades

## Documentación Adicional

- `google-agent/TESTING.md` - Detalles de testing Google ADK
- `microsoft-agent/TESTING.md` - Detalles de testing Microsoft
- `demo/README.md` - Información sobre flujos de demo