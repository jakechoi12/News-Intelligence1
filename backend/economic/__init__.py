"""
Economic Indicators Module

BOK API integration for economic data (exchange rates, interest rates, stock indices).
"""

from .bok_api import (
    get_market_index,
    get_bok_statistics,
    get_category_info,
    calculate_statistics,
    BOK_MAPPING,
)

__all__ = [
    'get_market_index',
    'get_bok_statistics',
    'get_category_info',
    'calculate_statistics',
    'BOK_MAPPING',
]
