"""Test configuration — mock py_clob_client if not installed."""

import sys
from unittest.mock import MagicMock

# Mock py_clob_client and its submodules if not available
# (requires Python >=3.9.10 to install)
try:
    import py_clob_client
except ImportError:
    mock_clob = MagicMock()
    mock_clob.clob_types.OrderType.FOK = "FOK"
    mock_clob.clob_types.OrderType.GTC = "GTC"
    mock_clob.clob_types.MarketOrderArgs = MagicMock
    mock_clob.order_builder.constants.BUY = "BUY"
    mock_clob.order_builder.constants.SELL = "SELL"

    sys.modules["py_clob_client"] = mock_clob
    sys.modules["py_clob_client.client"] = mock_clob.client
    sys.modules["py_clob_client.clob_types"] = mock_clob.clob_types
    sys.modules["py_clob_client.order_builder"] = mock_clob.order_builder
    sys.modules["py_clob_client.order_builder.constants"] = mock_clob.order_builder.constants
    sys.modules["py_order_utils"] = MagicMock()
    sys.modules["py_order_utils.model"] = MagicMock()

# Ensure project root is in path
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
