import sqlite3
import os
import json
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "zair_audit.db")

def init_db():
    """Initialize the SQLite database for the ZAIR audit ledger."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            intent TEXT NOT NULL,
            ondo_apy REAL NOT NULL,
            aave_borrow REAL NOT NULL,
            spread REAL NOT NULL,
            action TEXT NOT NULL,
            agent_signature TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def log_decision(intent: str, ondo_apy: float, aave_borrow: float, spread: float, action: str, agent_signature: str):
    """Log a rebalance decision into the immutable ledger."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = int(datetime.now(timezone.utc).timestamp())
    cursor.execute('''
        INSERT INTO audit_log (timestamp, intent, ondo_apy, aave_borrow, spread, action, agent_signature)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, intent, ondo_apy, aave_borrow, spread, action, agent_signature))
    conn.commit()
    conn.close()

def get_audit_history(limit: int = 50) -> list:
    """Retrieve the latest decisions from the ledger."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, intent, ondo_apy, aave_borrow, spread, action, agent_signature 
        FROM audit_log 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
