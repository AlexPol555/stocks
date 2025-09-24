
"""Demo trading helpers: account balance, trades, and positions stored in SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
import sqlite3

from . import database

DEFAULT_STARTING_BALANCE = 1_000_000.0


@dataclass
class TradeResult:
    status: str
    message: str
    balance: float
    realized_pl: float = 0.0
    position: Optional[Dict] = None


def _ensure_account(conn: sqlite3.Connection) -> None:
    database.create_tables(conn)
    database.ensure_demo_account(conn, DEFAULT_STARTING_BALANCE)


def get_account(conn: sqlite3.Connection) -> Dict[str, float]:
    """Fetch demo account info, ensuring defaults exist."""
    _ensure_account(conn)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT balance, initial_balance, currency, updated_at
        FROM demo_accounts
        WHERE id = 1
        """
    )
    row = cursor.fetchone()
    if not row:
        return {
            "balance": DEFAULT_STARTING_BALANCE,
            "initial_balance": DEFAULT_STARTING_BALANCE,
            "currency": "RUB",
            "updated_at": None,
        }
    balance, initial_balance, currency, updated_at = row
    return {
        "balance": float(balance or 0),
        "initial_balance": float(initial_balance or 0),
        "currency": currency or "RUB",
        "updated_at": updated_at,
    }


def reset_account(conn: sqlite3.Connection, starting_balance: float) -> None:
    """Clear demo trades and positions, set a new starting balance."""
    _ensure_account(conn)
    with conn:
        conn.execute("DELETE FROM demo_trades")
        conn.execute("DELETE FROM demo_positions")
        conn.execute(
            """
            UPDATE demo_accounts
            SET balance = ?, initial_balance = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (float(starting_balance), float(starting_balance)),
        )


def adjust_balance(conn: sqlite3.Connection, delta: float) -> float:
    """Apply deposit/withdrawal and return the new balance."""
    _ensure_account(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM demo_accounts WHERE id = 1")
    balance = float(cursor.fetchone()[0])
    new_balance = balance + float(delta)
    if new_balance < 0:
        raise ValueError("Недостаточно средств для списания.")
    with conn:
        conn.execute(
            "UPDATE demo_accounts SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
            (new_balance,),
        )
    return new_balance


def _fetch_position(conn: sqlite3.Connection, contract_code: str) -> Optional[Dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, contract_code, quantity, avg_price, realized_pl
        FROM demo_positions
        WHERE contract_code = ?
        """,
        (contract_code,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    pid, code, qty, avg_price, realized_pl = row
    return {
        "id": pid,
        "contract_code": code,
        "quantity": float(qty or 0),
        "avg_price": float(avg_price or 0),
        "realized_pl": float(realized_pl or 0),
    }


def place_trade(
    conn: sqlite3.Connection,
    contract_code: str,
    side: str,
    quantity: float,
    price: float,
    fee: float = 0.0,
) -> TradeResult:
    """Execute a demo trade, update balances and positions."""
    if not contract_code:
        return TradeResult(status="error", message="Тикер не указан", balance=0.0)
    side_norm = (side or "").upper()
    if side_norm not in {"BUY", "SELL"}:
        return TradeResult(status="error", message="Сторона должна быть BUY или SELL", balance=0.0)
    if quantity <= 0:
        return TradeResult(status="error", message="Количество должно быть > 0", balance=0.0)
    if price <= 0:
        return TradeResult(status="error", message="Цена должна быть > 0", balance=0.0)

    _ensure_account(conn)
    company_id = database.get_or_create_company_id(conn, contract_code)

    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM demo_accounts WHERE id = 1")
    balance = float(cursor.fetchone()[0])

    position = _fetch_position(conn, contract_code)
    prev_qty = position["quantity"] if position else 0.0
    prev_avg = position["avg_price"] if position else 0.0
    prev_realized = position["realized_pl"] if position else 0.0

    fee = float(fee or 0.0)
    quantity = float(quantity)
    price = float(price)
    trade_value = quantity * price
    realized_pl = 0.0

    if side_norm == "BUY":
        cost = trade_value + fee
        if balance < cost:
            return TradeResult(status="error", message="Недостаточно средств", balance=balance)
        new_balance = balance - cost
        new_qty = prev_qty + quantity
        if new_qty == 0:
            new_avg = 0.0
        elif prev_qty == 0:
            new_avg = price
        else:
            new_avg = ((prev_qty * prev_avg) + trade_value) / new_qty
    else:  # SELL
        if prev_qty <= 0:
            return TradeResult(status="error", message="Нет позиции для продажи", balance=balance)
        if quantity > prev_qty:
            return TradeResult(status="error", message="Недостаточно лотов для продажи", balance=balance)
        proceeds = trade_value - fee
        new_balance = balance + proceeds
        realized_pl = quantity * (price - prev_avg)
        new_qty = prev_qty - quantity
        new_avg = prev_avg if new_qty > 0 else 0.0
        prev_realized += realized_pl

    with conn:
        conn.execute(
            """
            INSERT INTO demo_trades (contract_code, company_id, side, quantity, price, value, fee, realized_pl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contract_code,
                company_id,
                side_norm,
                quantity,
                price,
                trade_value,
                fee,
                realized_pl,
            ),
        )
        conn.execute(
            "UPDATE demo_accounts SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
            (new_balance,),
        )

        if new_qty > 0:
            if position:
                conn.execute(
                    """
                    UPDATE demo_positions
                    SET quantity = ?, avg_price = ?, realized_pl = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE contract_code = ?
                    """,
                    (new_qty, new_avg, prev_realized, contract_code),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO demo_positions (contract_code, company_id, quantity, avg_price, realized_pl)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (contract_code, company_id, new_qty, new_avg, prev_realized),
                )
        else:
            conn.execute(
                "DELETE FROM demo_positions WHERE contract_code = ?",
                (contract_code,),
            )

    new_position = _fetch_position(conn, contract_code)
    return TradeResult(
        status="success",
        message="Сделка выполнена",
        balance=new_balance,
        realized_pl=realized_pl,
        position=new_position,
    )


def get_trades(conn: sqlite3.Connection, limit: Optional[int] = None) -> pd.DataFrame:
    """Return trade history sorted by newest first."""
    _ensure_account(conn)
    query = """
        SELECT contract_code, side, quantity, price, value, fee, realized_pl, executed_at
        FROM demo_trades
        ORDER BY executed_at DESC, id DESC
    """
    df = pd.read_sql_query(query, conn)
    if limit:
        df = df.head(limit)
    return df


def _latest_price(conn: sqlite3.Connection, contract_code: str) -> Optional[float]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT dd.close
        FROM daily_data dd
        JOIN companies c ON dd.company_id = c.id
        WHERE c.contract_code = ?
        ORDER BY dd.date DESC
        LIMIT 1
        """,
        (contract_code,),
    )
    row = cursor.fetchone()
    return float(row[0]) if row and row[0] is not None else None


def get_positions(conn: sqlite3.Connection) -> pd.DataFrame:
    """Return current positions with market value and P/L."""
    _ensure_account(conn)
    df = pd.read_sql_query(
        """
        SELECT contract_code, quantity, avg_price, realized_pl, updated_at
        FROM demo_positions
        ORDER BY contract_code
        """,
        conn,
    )
    if df.empty:
        return df
    df["quantity"] = df["quantity"].astype(float)
    df["avg_price"] = df["avg_price"].astype(float)
    df["invested_value"] = df["quantity"] * df["avg_price"]
    market_prices: List[Optional[float]] = []
    market_values: List[Optional[float]] = []
    for ticker, qty in zip(df["contract_code"], df["quantity"]):
        price = _latest_price(conn, ticker)
        market_prices.append(price)
        market_values.append(price * qty if price is not None else None)
    df["market_price"] = market_prices
    df["market_value"] = market_values
    df["unrealized_pl"] = df["market_value"] - df["invested_value"]
    return df


def get_account_snapshot(conn: sqlite3.Connection) -> Dict[str, float]:
    """Aggregate account metrics for dashboards/statistics."""
    info = get_account(conn)
    balance = info["balance"]
    positions = get_positions(conn)
    invested = float(positions["invested_value"].sum()) if not positions.empty else 0.0
    market_value = float(
        positions["market_value"].fillna(0).sum()
    ) if not positions.empty else 0.0
    unrealized = market_value - invested
    realized = float(
        pd.read_sql_query("SELECT COALESCE(SUM(realized_pl), 0) AS total FROM demo_trades", conn)["total"].iloc[0]
    )
    equity = balance + market_value
    return {
        "balance": balance,
        "initial_balance": info["initial_balance"],
        "invested_value": invested,
        "market_value": market_value,
        "equity": equity,
        "unrealized_pl": unrealized,
        "realized_pl": realized,
        "total_pl": realized + unrealized,
    }
