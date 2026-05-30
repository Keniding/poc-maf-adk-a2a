"""Account Agent Tools - RAG over SQLite database."""

import sqlite3
from pathlib import Path

# Database path (shared)
DB_PATH = Path(__file__).parent.parent.parent / "shared" / "database" / "banking.db"


def search_customer(query: str) -> str:
    """
    Search for customers by name, email, or phone.

    Args:
        query: Search term (name, email, or phone)

    Returns:
        Customer information or error message
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, email, phone, segment, created_at
        FROM customers
        WHERE name LIKE ? OR email LIKE ? OR phone LIKE ?
        LIMIT 5
        """,
        (f"%{query}%", f"%{query}%", f"%{query}%"),
    )

    results = cursor.fetchall()
    conn.close()

    if not results:
        return f"No customers found matching '{query}'"

    output = []
    for row in results:
        output.append(
            f"ID: {row[0]}, Name: {row[1]}, Email: {row[2]}, "
            f"Phone: {row[3] or 'N/A'}, Segment: {row[4]}, Since: {row[5]}"
        )

    return "\n".join(output)


def get_customer_accounts(customer_id: int) -> str:
    """
    Get all accounts for a customer.

    Args:
        customer_id: Customer ID

    Returns:
        Account information or error message
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, account_type, account_number, balance, currency, status, opened_at
        FROM accounts
        WHERE customer_id = ?
        """,
        (customer_id,),
    )

    results = cursor.fetchall()
    conn.close()

    if not results:
        return f"No accounts found for customer {customer_id}"

    output = [f"Accounts for customer {customer_id}:"]
    total = 0
    for row in results:
        account_id, acc_type, acc_num, balance, currency, status, opened_at = row
        output.append(
            f"  - Account {account_id} ({acc_type}): {currency} {balance:,.2f} "
            f"[{status}] (opened {opened_at})"
        )
        output.append(f"    Account Number: {acc_num}")
        total += balance

    output.append(f"\nTotal balance: {total:,.2f}")
    return "\n".join(output)


def get_account_transactions(account_id: int, limit: int = 10) -> str:
    """
    Get recent transactions for an account.

    Args:
        account_id: Account ID
        limit: Maximum number of transactions to return

    Returns:
        Transaction history or error message
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT created_at, type, amount, description, status, risk_flag
        FROM transactions
        WHERE account_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (account_id, limit),
    )

    results = cursor.fetchall()
    conn.close()

    if not results:
        return f"No transactions found for account {account_id}"

    output = [f"Last {len(results)} transactions for account {account_id}:"]
    for row in results:
        created_at, tx_type, amount, description, status, risk_flag = row
        flag = " [FLAGGED]" if risk_flag else ""
        status_msg = f" [{status.upper()}]" if status != 'completed' else ""
        output.append(
            f"  {created_at} - {tx_type}: ${amount:,.2f}{status_msg}{flag}"
        )
        if description:
            output.append(f"    {description}")

    return "\n".join(output)


def search_products(product_type: str = "") -> str:
    """
    Search banking products.

    Args:
        product_type: Filter by product category (optional)

    Returns:
        Product catalog
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if product_type:
        cursor.execute(
            """
            SELECT id, name, category, description, min_income, annual_rate
            FROM products
            WHERE category LIKE ? AND is_active = 1
            """,
            (f"%{product_type}%",),
        )
    else:
        cursor.execute(
            """
            SELECT id, name, category, description, min_income, annual_rate
            FROM products
            WHERE is_active = 1
            """
        )

    results = cursor.fetchall()
    conn.close()

    if not results:
        return f"No products found{' for ' + product_type if product_type else ''}"

    output = ["Available products:"]
    for row in results:
        product_id, name, category, description, min_income, annual_rate = row
        rate_info = f", Rate: {annual_rate}%" if annual_rate else ""
        output.append(
            f"  - {name} ({category}): {description}"
        )
        output.append(
            f"    [Min income: ${min_income:,.2f}{rate_info}]"
        )

    return "\n".join(output)