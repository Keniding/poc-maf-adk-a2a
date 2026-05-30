"""Compliance Agent Tools - Risk analysis over SQLite database."""

import sqlite3
from pathlib import Path

# Database path (shared)
DB_PATH = Path(__file__).parent.parent.parent / "shared" / "database" / "banking.db"


def get_customer_risk_profile(customer_id: int) -> str:
    """
    Get customer risk profile including risk score and flags.

    Args:
        customer_id: Customer ID

    Returns:
        Risk profile information
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT c.name, c.segment, c.risk_score, c.created_at,
               COUNT(DISTINCT a.id) as num_accounts,
               COALESCE(SUM(a.balance), 0) as total_balance
        FROM customers c
        LEFT JOIN accounts a ON c.id = a.customer_id
        WHERE c.id = ?
        GROUP BY c.id
        """,
        (customer_id,),
    )

    result = cursor.fetchone()
    conn.close()

    if not result:
        return f"Customer {customer_id} not found"

    name, segment, risk_score, created_at, num_accounts, total_balance = result

    # Determine risk level
    if risk_score >= 70:
        risk_level = "ALTO RIESGO"
    elif risk_score >= 40:
        risk_level = "RIESGO MEDIO"
    else:
        risk_level = "BAJO RIESGO"

    return f"""PERFIL DE RIESGO - Cliente {customer_id}

Información Básica:
- Nombre: {name}
- Segmento: {segment}
- Fecha Alta: {created_at}

Evaluación de Riesgo:
- Score de Riesgo: {risk_score}/100
- Nivel: {risk_level}

Actividad Bancaria:
- Número de Cuentas: {num_accounts}
- Balance Total: {total_balance:,.2f}
"""


def check_transaction_risk(customer_id: int, days: int = 30) -> str:
    """
    Analyze recent transactions for risk patterns.

    Detects:
    - Flagged transactions
    - Structuring patterns (multiple transactions near $10,000)
    - Large cash transactions
    - High-frequency activity

    Args:
        customer_id: Customer ID
        days: Number of days to analyze

    Returns:
        Risk analysis report
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all transactions
    cursor.execute(
        """
        SELECT t.created_at, t.type, t.amount,
               t.description, t.risk_flag, a.id, t.status
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE a.customer_id = ?
        AND t.created_at >= datetime('now', '-' || ? || ' days')
        ORDER BY t.created_at DESC
        """,
        (customer_id, days),
    )

    transactions = cursor.fetchall()
    conn.close()

    if not transactions:
        return f"No transactions found for customer {customer_id} in last {days} days"

    # Analyze patterns
    flagged_count = sum(1 for t in transactions if t[4])
    total_count = len(transactions)
    total_volume = sum(t[2] for t in transactions)

    # Detect structuring (multiple transactions between $8k-$10k)
    structuring = [t for t in transactions if 8000 <= t[2] < 10000]

    # Large cash transactions
    large_cash = [t for t in transactions if t[2] > 50000 and (t[3] and "cash" in str(t[3]).lower())]

    # Flagged or failed transactions
    problematic = [t for t in transactions if t[4] or t[6] == 'flagged']

    report = [f"Transaction Risk Analysis (last {days} days):"]
    report.append(f"Total transactions: {total_count}")
    report.append(f"Total volume: ${total_volume:,.2f}")
    report.append(f"Flagged transactions: {flagged_count}")

    if structuring:
        report.append(f"\n[ALERT] STRUCTURING PATTERN DETECTED:")
        report.append(f"Found {len(structuring)} transactions between $8,000-$10,000")
        for t in structuring[:5]:
            report.append(f"  {t[0]}: ${t[2]:,.2f} - {t[3] or 'N/A'}")

    if large_cash:
        report.append(f"\n[ALERT] LARGE CASH TRANSACTIONS:")
        for t in large_cash:
            report.append(f"  {t[0]}: ${t[2]:,.2f} - {t[3]}")

    if problematic:
        report.append(f"\n[ALERT] FLAGGED/PROBLEMATIC TRANSACTIONS:")
        for t in problematic[:10]:
            status_msg = f"[{t[6].upper()}]" if t[6] in ('flagged', 'failed') else ""
            report.append(f"  {t[0]}: ${t[2]:,.2f} {status_msg} - {t[3] or 'N/A'}")

    return "\n".join(report)


def get_compliance_rules(category: str = "all") -> str:
    """
    Get compliance rules and thresholds.

    Args:
        category: Rule category (aml, kyc, structuring, all)

    Returns:
        Compliance rules information
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if category.lower() == "all":
        cursor.execute("""
            SELECT rule_code, description, threshold, action, severity
            FROM compliance_rules
            ORDER BY severity DESC
        """)
    else:
        cursor.execute(
            """
            SELECT rule_code, description, threshold, action, severity
            FROM compliance_rules
            WHERE rule_code LIKE ? OR description LIKE ?
            ORDER BY severity DESC
            """,
            (f"%{category}%", f"%{category}%"),
        )

    results = cursor.fetchall()
    conn.close()

    if not results:
        return f"No compliance rules found for category '{category}'"

    output = [f"Compliance Rules ({category}):"]
    for row in results:
        rule_code, description, threshold, action, severity = row
        output.append(f"\n{rule_code} [{severity.upper()}]:")
        output.append(f"  {description}")
        if threshold:
            output.append(f"  Threshold: ${threshold:,.2f}")
        if action:
            output.append(f"  Action: {action}")

    return "\n".join(output)