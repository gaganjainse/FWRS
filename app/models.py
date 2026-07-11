from dataclasses import dataclass
from typing import Optional

@dataclass
class Restaurant:
    id: str
    name: str
    lat: float
    lon: float
    supply: int
    expiry_hours: Optional[float] = None

@dataclass
class NGO:
    id: str
    name: str
    lat: float
    lon: float
    demand: int
    priority: int  # larger = higher priority

@dataclass
class Allocation:
    restaurant_id: str
    ngo_id: str
    amount: int
    cost_per_unit: float
