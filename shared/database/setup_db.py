"""
Setup y seed de la base de datos SQLite para RAG bancario.

Tablas:
- customers: Datos de clientes
- accounts: Cuentas bancarias
- transactions: Historial de transacciones
- products: Productos bancarios disponibles
- compliance_rules: Reglas de cumplimiento/riesgo
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "banking.db"


def create_database() -> None:
    """Crea y llena la base de datos bancaria para RAG."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # -- Esquema ----------------------------------------------
    cursor.executescript("""
        DROP TABLE IF EXISTS transactions;
        DROP TABLE IF EXISTS accounts;
        DROP TABLE IF EXISTS customers;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS compliance_rules;

        CREATE TABLE customers (
            id          INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            email       TEXT NOT NULL,
            phone       TEXT,
            segment     TEXT CHECK(segment IN ('retail', 'premium', 'business')),
            risk_score  REAL DEFAULT 0.0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE accounts (
            id              INTEGER PRIMARY KEY,
            customer_id     INTEGER REFERENCES customers(id),
            account_type    TEXT CHECK(account_type IN ('savings', 'checking', 'credit_card', 'loan')),
            account_number  TEXT UNIQUE NOT NULL,
            balance         REAL DEFAULT 0.0,
            currency        TEXT DEFAULT 'PEN',
            status          TEXT CHECK(status IN ('active', 'blocked', 'closed')) DEFAULT 'active',
            opened_at       TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE transactions (
            id              INTEGER PRIMARY KEY,
            account_id      INTEGER REFERENCES accounts(id),
            type            TEXT CHECK(type IN ('deposit', 'withdrawal', 'transfer', 'payment', 'fee')),
            amount          REAL NOT NULL,
            description     TEXT,
            merchant        TEXT,
            category        TEXT,
            status          TEXT CHECK(status IN ('completed', 'pending', 'failed', 'flagged')) DEFAULT 'completed',
            risk_flag       BOOLEAN DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE products (
            id              INTEGER PRIMARY KEY,
            name            TEXT NOT NULL,
            category        TEXT CHECK(category IN ('credit', 'savings', 'investment', 'insurance')),
            description     TEXT,
            min_income      REAL DEFAULT 0.0,
            annual_rate     REAL,
            requirements    TEXT,
            is_active       BOOLEAN DEFAULT 1
        );

        CREATE TABLE compliance_rules (
            id              INTEGER PRIMARY KEY,
            rule_code       TEXT UNIQUE NOT NULL,
            description     TEXT NOT NULL,
            threshold       REAL,
            action          TEXT,
            severity        TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical'))
        );
    """)

    # -- Seed: Clientes ---------------------------------------
    customers = [
        (1, "María García López", "maria.garcia@email.com", "+51999111222", "premium", 15.0),
        (2, "Carlos Rodríguez Perez", "carlos.rod@email.com", "+51999333444", "retail", 45.0),
        (3, "Ana Martínez Silva", "ana.martinez@empresa.com", "+51999555666", "business", 8.0),
        (4, "Jose Fernández Torres", "jose.fern@email.com", "+51999777888", "retail", 72.0),
        (5, "Laura Sánchez Morales", "laura.sanchez@email.com", "+51999999000", "premium", 5.0),
    ]
    cursor.executemany(
        "INSERT INTO customers (id, name, email, phone, segment, risk_score) VALUES (?,?,?,?,?,?)",
        customers,
    )

    # -- Seed: Cuentas ----------------------------------------
    accounts = [
        (1, 1, "savings", "1001-0001-0001", 25430.50, "PEN", "active"),
        (2, 1, "credit_card", "4532-XXXX-XXXX-1234", -3200.00, "PEN", "active"),
        (3, 2, "checking", "1001-0002-0001", 1850.75, "PEN", "active"),
        (4, 2, "savings", "1001-0002-0002", 500.00, "USD", "active"),
        (5, 3, "checking", "2001-0003-0001", 145000.00, "PEN", "active"),
        (6, 3, "loan", "3001-0003-0001", -85000.00, "PEN", "active"),
        (7, 4, "savings", "1001-0004-0001", 320.00, "PEN", "blocked"),
        (8, 4, "credit_card", "4532-XXXX-XXXX-5678", -12500.00, "PEN", "active"),
        (9, 5, "savings", "1001-0005-0001", 78900.00, "PEN", "active"),
        (10, 5, "checking", "1001-0005-0002", 15600.00, "USD", "active"),
    ]
    cursor.executemany(
        "INSERT INTO accounts (id, customer_id, account_type, account_number, balance, currency, status) VALUES (?,?,?,?,?,?,?)",
        accounts,
    )

    # -- Seed: Transacciones ----------------------------------
    transactions = [
        # María - transacciones normales
        (1, 1, "deposit", 5000.00, "Depósito nómina mayo", None, "income", "completed", 0, "2026-05-01"),
        (2, 1, "withdrawal", 200.00, "Retiro cajero ATM", None, "cash", "completed", 0, "2026-05-03"),
        (3, 2, "payment", 450.00, "Pago restaurante", "La Mar Cebichería", "dining", "completed", 0, "2026-05-05"),
        (4, 2, "payment", 89.90, "Suscripción streaming", "Netflix", "entertainment", "completed", 0, "2026-05-06"),

        # Carlos - patrón sospechoso
        (5, 3, "deposit", 9500.00, "Transferencia recibida", None, "transfer", "completed", 0, "2026-05-10"),
        (6, 3, "withdrawal", 9000.00, "Retiro ventanilla", None, "cash", "flagged", 1, "2026-05-10"),
        (7, 3, "deposit", 9800.00, "Transferencia recibida", None, "transfer", "completed", 0, "2026-05-11"),
        (8, 3, "withdrawal", 9700.00, "Retiro ventanilla", None, "cash", "flagged", 1, "2026-05-11"),

        # Ana - empresa
        (9, 5, "deposit", 50000.00, "Pago factura cliente", "Empresa XYZ", "business", "completed", 0, "2026-05-01"),
        (10, 5, "payment", 25000.00, "Pago proveedor", "Distribuidora ABC", "business", "completed", 0, "2026-05-08"),
        (11, 6, "payment", 4500.00, "Cuota prestamo mayo", None, "loan_payment", "completed", 0, "2026-05-15"),

        # Jose - alto riesgo
        (12, 7, "deposit", 15000.00, "Depósito efectivo", None, "cash", "flagged", 1, "2026-05-12"),
        (13, 8, "payment", 8500.00, "Compra electrónica", "TechStore Online", "shopping", "completed", 0, "2026-05-13"),
        (14, 8, "payment", 3200.00, "Compra joyería", "Gold & Silver Shop", "luxury", "flagged", 1, "2026-05-14"),
        (15, 7, "withdrawal", 14000.00, "Retiro urgente", None, "cash", "flagged", 1, "2026-05-14"),

        # Laura - premium, normal
        (16, 9, "deposit", 12000.00, "Depósito nómina mayo", None, "income", "completed", 0, "2026-05-01"),
        (17, 9, "transfer", 5000.00, "Transferencia a plazo fijo", None, "investment", "completed", 0, "2026-05-02"),
        (18, 10, "deposit", 3000.00, "Transferencia internacional", None, "transfer", "completed", 0, "2026-05-05"),
    ]
    cursor.executemany(
        "INSERT INTO transactions (id, account_id, type, amount, description, merchant, category, status, risk_flag, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        transactions,
    )

    # -- Seed: Productos --------------------------------------
    products = [
        (1, "Cuenta Ahorro Simple", "savings", "Cuenta de ahorro sin costo de mantenimiento para segmento retail.", 0, 3.5, "DNI vigente, comprobante de domicilio"),
        (2, "Cuenta Ahorro Premium", "savings", "Cuenta de ahorro con tasa preferencial para clientes premium. Incluye seguro de desgravamen.", 5000, 5.2, "DNI vigente, ingresos mínimos S/5,000"),
        (3, "Tarjeta Visa Clásica", "credit", "Tarjeta de credito con línea desde S/1,000. Sin membresía el primer año.", 1500, 42.0, "DNI, boleta de pago, antigüedad laboral 6 meses"),
        (4, "Tarjeta Visa Signature", "credit", "Tarjeta premium con acceso a salas VIP y concierge. Cashback 2%.", 8000, 28.0, "DNI, ingresos mínimos S/8,000, historial crediticio A"),
        (5, "Prestamo Personal", "credit", "Prestamo desde S/1,000 hasta S/100,000. Plazo 12-60 meses.", 2000, 18.5, "DNI, boleta de pago, clasificación SBS normal"),
        (6, "Depósito a Plazo Fijo", "investment", "Depósito a plazo desde 30 días. Tasa competitiva según monto y plazo.", 1000, 6.8, "DNI, cuenta de ahorro activa"),
        (7, "Seguro de Vida", "insurance", "Seguro de vida con cobertura desde S/50,000. Prima mensual desde S/35.", 0, None, "DNI, declaración de salud"),
        (8, "Cuenta Empresa", "savings", "Cuenta corriente empresarial con chequera y banca digital.", 0, 1.5, "RUC activo, escritura de constitución, poderes vigentes"),
    ]
    cursor.executemany(
        "INSERT INTO products (id, name, category, description, min_income, annual_rate, requirements) VALUES (?,?,?,?,?,?,?)",
        products,
    )

    # -- Seed: Reglas de Cumplimiento -------------------------
    compliance_rules = [
        (1, "AML-001", "Transacciones en efectivo >= S/10,000 requieren reporte UIF", 10000.0, "report_to_uif", "high"),
        (2, "AML-002", "Múltiples transacciones < S/10,000 en 24h (structuring)", 10000.0, "flag_and_review", "critical"),
        (3, "AML-003", "Transferencias internacionales > US$5,000 requieren declaración de origen", 5000.0, "request_declaration", "high"),
        (4, "RISK-001", "Cliente con risk_score > 70 requiere revisión periódica", 70.0, "periodic_review", "high"),
        (5, "RISK-002", "Cuenta bloqueada: no permitir operaciones sin autorización compliance", None, "block_operations", "critical"),
        (6, "FRAUD-001", "Compras inusuales en categoría luxury para perfil retail", None, "alert_fraud_team", "medium"),
        (7, "FRAUD-002", "Retiro inmediato post-depósito (>80% monto) en mismo día", None, "flag_and_review", "high"),
        (8, "KYC-001", "Actualización de datos obligatoria cada 12 meses", None, "request_update", "low"),
    ]
    cursor.executemany(
        "INSERT INTO compliance_rules (id, rule_code, description, threshold, action, severity) VALUES (?,?,?,?,?,?)",
        compliance_rules,
    )

    conn.commit()
    conn.close()
    print(f"[OK] Base de datos creada en: {DB_PATH}")


if __name__ == "__main__":
    create_database()
