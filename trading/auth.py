"""Wallet authentication and ClobClient initialization."""

from __future__ import annotations

import logging

from py_clob_client.client import ClobClient

from config.settings import settings

log = logging.getLogger(__name__)

# Contracts that require USDC + Conditional Token approvals for EOA wallets
_EXCHANGE_CONTRACTS = {
    "CTF Exchange": "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E",
    "Neg Risk CTF Exchange": "0xC5d563A36AE78145C45a50134d48A1215220f80a",
    "Neg Risk Adapter": "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296",
}

_USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
_CTF_ADDRESS = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"


def create_clob_client() -> ClobClient:
    """Create and authenticate a ClobClient for trading.

    Uses EOA signature_type=0 (standard private key wallet).
    If POLY_FUNDER is set, uses it as the funder address.
    """
    if not settings.poly_private_key:
        raise ValueError("POLY_PRIVATE_KEY not set in environment")

    funder = settings.poly_funder or None

    client = ClobClient(
        settings.clob_host,
        key=settings.poly_private_key,
        chain_id=settings.chain_id,
        signature_type=0,  # EOA
        funder=funder,
    )

    # Derive or retrieve API credentials from wallet signature
    creds = client.create_or_derive_api_creds()
    client.set_api_creds(creds)

    log.info("CLOB client authenticated (funder=%s)", funder or "self")

    if not settings.dry_run:
        _warn_allowances()

    return client


def _warn_allowances() -> None:
    """Log a reminder about required token allowances for EOA wallets.

    EOA wallets (signature_type=0) must approve USDC and Conditional
    Tokens for all three exchange contracts before trading. Without
    these approvals, orders will fail with INVALID_ORDER_NOT_ENOUGH_BALANCE.
    """
    log.info(
        "REMINDER: EOA wallets must have USDC (%s) and CTF (%s) "
        "approved for these exchange contracts:",
        _USDC_ADDRESS,
        _CTF_ADDRESS,
    )
    for name, addr in _EXCHANGE_CONTRACTS.items():
        log.info("  %s: %s", name, addr)
    log.info(
        "If orders fail with INVALID_ORDER_NOT_ENOUGH_BALANCE, "
        "approve tokens at https://polygonscan.com"
    )
