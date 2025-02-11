# models.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class LocationData:
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    timestamp: Optional[float] = None

@dataclass(frozen=True)
class Restaurant:
    name: str
    address: str
    rating: Optional[float]
    latitude: float
    longitude: float
    user_ratings_total: int
    primary_type: Optional[str]
    place_id: str
    all_reviews: List[str]
    latest_review: Optional[str] = None
    review_rating: Optional[float] = None
    review_date: Optional[str] = None
    photo_url: Optional[str] = None
    maps_url: Optional[str] = None
    opening_hours: Optional[str] = None

    def __post_init__(self):
        if not (-90 <= self.latitude <= 90) or not (-180 <= self.longitude <= 180):
            raise ValueError("Coordonnées invalides")
