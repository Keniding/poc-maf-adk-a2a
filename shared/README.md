# Shared Resources

This directory contains resources shared between both agent modules.

## Database

`database/banking.db` - SQLite database with:

- **customers** - Customer profiles, risk scores, KYC/AML flags
- **accounts** - Bank accounts and balances
- **transactions** - Transaction history with AML flags
- **compliance_rules** - AML/KYC rules and thresholds
- **products** - Banking product catalog

### Setup Database

```bash
cd shared/database
python setup_db.py
```

This creates and populates `banking.db` with sample data:
- 5 customers with different risk profiles
- Multiple accounts per customer
- Transaction history with some flagged transactions
- Compliance rules for AML/KYC

### Database Schema

```sql
-- Customers
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    segment TEXT,  -- retail, premium, corporate
    onboarding_date DATE,
    kyc_verified BOOLEAN,
    aml_flagged BOOLEAN,
    risk_score INTEGER  -- 0-100
);

-- Accounts
CREATE TABLE accounts (
    account_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    account_type TEXT,  -- checking, savings, investment
    balance REAL,
    status TEXT,
    opening_date DATE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Transactions
CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY,
    account_id INTEGER,
    transaction_date DATETIME,
    transaction_type TEXT,  -- deposit, withdrawal, transfer
    amount REAL,
    description TEXT,
    flagged_aml BOOLEAN,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- Compliance Rules
CREATE TABLE compliance_rules (
    rule_id INTEGER PRIMARY KEY,
    rule_name TEXT,
    category TEXT,  -- aml, kyc, structuring
    threshold REAL,
    description TEXT
);

-- Products
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT,
    product_type TEXT,  -- account, loan, credit_card
    description TEXT,
    min_balance REAL,
    interest_rate REAL
);
```

### Test Customers

| ID | Name | Risk Score | Description |
|----|------|------------|-------------|
| 1 | Maria Garcia Lopez | 15 (LOW) | Standard customer, no alerts |
| 2 | Carlos Rodriguez Perez | 45 (MEDIUM) | Structuring pattern (4 withdrawals $8k-$10k) |
| 3 | Ana Martinez Silva | 22 (LOW) | Premium customer, good credit history |
| 4 | Jose Fernandez Torres | 72 (HIGH) | High risk score, 3 flagged transactions |
| 5 | Luis Chen Vasquez | 18 (LOW) | Corporate customer |

### Usage from Agents

Both agent modules use relative paths to access the database:

```python
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "shared" / "database" / "banking.db"
```

This allows both `microsoft-agent` and `google-agent` to query the same data source.