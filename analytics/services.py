from __future__ import annotations

from typing import Optional


def ctr(clicks: int, impressions: int) -> float:
    if impressions <= 0:
        return 0.0
    return clicks / impressions


def conversion_rate(conversions: int, sessions: int) -> float:
    if sessions <= 0:
        return 0.0
    return conversions / sessions


def roi(revenue: float, cost: float) -> Optional[float]:
    if cost == 0:
        return None
    return (revenue - cost) / cost


def cac(cost: float, customers: int) -> Optional[float]:
    if customers <= 0:
        return None
    return cost / customers


def ltv(aov: float, purchase_frequency: float, gross_margin: float) -> float:
    # Simple heuristic LTV formula
    return aov * purchase_frequency * gross_margin
