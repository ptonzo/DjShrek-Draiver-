#!/usr/bin/env python3
"""Minimal standard-library license API for DjShrek-Draiver Cyber Club.

Run: LICENSE_DB=licenses.sqlite3 python server.py
This is an API starter, not a payment integration. Never issue a license from
an unverified browser redirect; call the issue command only after a verified
provider webhook/payment reconciliation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

DB_PATH = os.environ.get("LICENSE_DB", "licenses.sqlite3")
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 32 symbols; no ambiguous 0/O/1/I
KEY_LENGTH = 20


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def key_digest(key: str) -> str:
    return hashlib.sha256(key.upper().encode("ascii")).hexdigest()


def db():
    con = sqlite3.connect(DB_PATH, timeout=20, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    with db() as con:
        con.execute("""
          CREATE TABLE IF NOT EXISTS licenses (
            key_hash TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            payment_reference TEXT UNIQUE,
            status TEXT NOT NULL DEFAULT 'unused'
              CHECK(status IN ('unused','active','expired','revoked')),
            activated_at TEXT,
            expires_at TEXT,
            machine_hash TEXT
          )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status)")


def generate_key() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(KEY_LENGTH))


def add_license(payment_reference: str | None = None) -> str:
    """Create one key. Persist only its SHA-256 digest; show plaintext once."""
    init_db()
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        for _ in range(10):
            key = generate_key()
            try:
                con.execute(
                    "INSERT INTO licenses(key_hash,created_at,payment_reference) VALUES(?,?,?)",
                    (key_digest(key), now_utc().isoformat(), payment_reference),
                )
                con.commit()
                return key
            except sqlite3.IntegrityError:
                if payment_reference:
                    raise ValueError("payment reference already issued")
        raise RuntimeError("could not generate a unique key")
    finally:
        con.close()


def add_calendar_year(start: date) -> date:
    try:
        return start.replace(year=start.year + 1)
    except ValueError:  # 29 February -> 28 February in the following year
        return start.replace(year=start.year + 1, day=28)


def activate(key: str, machine_id: str) -> dict:
    if len(key) != KEY_LENGTH or any(c not in ALPHABET for c in key.upper()):
        return {"ok": False, "error": "invalid_key"}
    if not machine_id or len(machine_id) > 256:
        return {"ok": False, "error": "invalid_machine_id"}
    init_db()
    con = db()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT * FROM licenses WHERE key_hash=?", (key_digest(key),)).fetchone()
        if row is None:
            con.rollback()
            return {"ok": False, "error": "license_not_found"}
        if row["status"] != "unused":
            con.rollback()
            return {"ok": False, "error": "already_activated_or_unavailable"}
        activated = now_utc()
        expiry_date = add_calendar_year(activated.date())
        expiry = datetime.combine(expiry_date, activated.timetz()).isoformat()
        machine_hash = hashlib.sha256(machine_id.encode("utf-8")).hexdigest()
        con.execute(
            """UPDATE licenses SET status='active',activated_at=?,expires_at=?,machine_hash=?
               WHERE key_hash=? AND status='unused'""",
            (activated.isoformat(), expiry, machine_hash, key_digest(key)),
        )
        con.commit()
        return {"ok": True, "status": "active", "activated_at": activated.isoformat(),
                "expires_at": expiry}
    finally:
        con.close()


def verify(key: str, machine_id: str) -> dict:
    init_db()
    con = db()
    try:
        row = con.execute("SELECT status,expires_at,machine_hash FROM licenses WHERE key_hash=?",
                          (key_digest(key),)).fetchone()
        if row is None:
            return {"ok": False, "status": "not_found"}
        if row["status"] != "active":
            return {"ok": False, "status": row["status"]}
        expected = hashlib.sha256(machine_id.encode("utf-8")).hexdigest()
        if not secrets.compare_digest(row["machine_hash"] or "", expected):
            return {"ok": False, "status": "machine_mismatch"}
        if datetime.fromisoformat(row["expires_at"]) <= now_utc():
            with db() as update_con:
                update_con.execute("UPDATE licenses SET status='expired' WHERE key_hash=?",
                                   (key_digest(key),))
            return {"ok": False, "status": "expired"}
        return {"ok": True, "status": "active", "expires_at": row["expires_at"]}
    finally:
        con.close()


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 8192:
            raise ValueError("invalid request size")
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if urlparse(self.path).path == "/health":
            return self.send_json(200, {"ok": True, "service": "djshrek-license-api"})
        return self.send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        try:
            payload = self.read_json()
            route = urlparse(self.path).path
            if route == "/v1/activate":
                result = activate(str(payload.get("key", "")), str(payload.get("machine_id", "")))
                return self.send_json(200 if result.get("ok") else 400, result)
            if route == "/v1/verify":
                result = verify(str(payload.get("key", "")), str(payload.get("machine_id", "")))
                return self.send_json(200 if result.get("ok") else 403, result)
            return self.send_json(404, {"ok": False, "error": "not_found"})
        except (ValueError, json.JSONDecodeError):
            return self.send_json(400, {"ok": False, "error": "bad_request"})

    def log_message(self, fmt, *args):
        # Avoid logging request bodies, keys, or machine identifiers.
        super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="initialize the SQLite database")
    parser.add_argument("--issue", action="store_true", help="issue exactly one key after payment verification")
    parser.add_argument("--payment-reference", help="unique provider payment/order ID")
    parser.add_argument("--serve", action="store_true", help="start HTTP API")
    args = parser.parse_args()
    if args.init:
        init_db()
        print("Database initialized.")
    if args.issue:
        print(add_license(args.payment_reference))
    if args.serve:
        init_db()
        host = os.environ.get("LICENSE_HOST", "127.0.0.1")
        port = int(os.environ.get("LICENSE_PORT", "8765"))
        print(f"Listening on {host}:{port}")
        ThreadingHTTPServer((host, port), Handler).serve_forever()
    if not (args.init or args.issue or args.serve):
        parser.print_help()


if __name__ == "__main__":
    main()
