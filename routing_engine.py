import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import quote_plus
import requests
import streamlit as st
from geopy.geocoders import ArcGIS

# --- BATCH PLANT DIRECTORY (41 Florida Ready-Mix Locations: Plant #01 - #41) ---
PLANT_LOCATIONS = [
    {"plant_number": "4062", "name": "56TH ST", "address": "5503 E Diana St, Tampa, FL 33610"},
    {"plant_number": "4058", "name": "78TH ST", "address": "6725 78th St, Riverview, FL 33569"},
    {"plant_number": "1036", "name": "BERTH 150", "address": "3711 Causeway Blvd, Tampa, FL 33619"},
    {"plant_number": "4061", "name": "BIG BEND", "address": "6002 Big Bend Rd, Gibsonton, FL 33534"},
    {"plant_number": "1148", "name": "BROOKSVILLE", "address": "10206 Cobb Rd, Brooksville, FL 34601"},
    {"plant_number": "1033", "name": "EHREN CUTOFF", "address": "11121 Ehren Cutoff Rd, Land O Lakes, FL 34639"},
    {"plant_number": "4048", "name": "LARGO", "address": "2195 Lake Ave SE, Largo, FL 33771"},
    {"plant_number": "1173", "name": "LECANTO", "address": "2975 South Lecanto Hwy (491), Lecanto, FL 34461"},
    {"plant_number": "1037", "name": "ODESSA", "address": "2430 Marathon Rd, Odessa, FL 33556"},
    {"plant_number": "4049", "name": "ST PETE", "address": "601 24th Street South, Saint Petersburg, FL 33733"},
    {"plant_number": "4059", "name": "WATERS", "address": "9117 Florida Mining Blvd, Tampa, FL 33634"},
    {"plant_number": "1142", "name": "ZEPHYRHILLS", "address": "3946 Copeland Dr, Zephyrhills, FL 33542"},
    {"plant_number": "1136", "name": "LEESBURG", "address": "2711 C.R. 33, Okahumpka, FL 34746"},
    {"plant_number": "1124", "name": "WILDWOOD", "address": "4270 County Rd 124, Wildwood, FL 34785"},
    {"plant_number": "1155", "name": "OCALA WEST", "address": "2355 SW 60th Ave, Ocala, FL 34474"},
    {"plant_number": "4010", "name": "OCALA", "address": "619 SW 17th Street, Ocala, FL 34471"},
    {"plant_number": "1139", "name": "GAINESVILLE", "address": "820 NW 53rd Ave, Gainesville, FL 32609"},
    {"plant_number": "4042", "name": "AUBURNDALE", "address": "326 Recker Hwy, Auburndale, FL 33823"},
    {"plant_number": "1145", "name": "LAKELAND", "address": "3770 Main Ave, Lakeland, FL 33801"},
    {"plant_number": "1106", "name": "LAKE WALES", "address": "534 Story Road, Lake Wales, FL 33853"},
    {"plant_number": "1144", "name": "PLANT CITY", "address": "2680 US Hwy 92 East, Plant City, FL 33566"},
]

ROUTING_DISCLAIMER = (
    "Disclaimer: Assigned batch plant, mileage, and estimated travel times are based on standard "
    "traffic conditions and are subject to batch plant availability, truck scheduling, and weather "
    "at the time of dispatch."
)


@dataclass
class RouteEstimate:
    plant_number: str
    plant_name: str
    plant_address: str
    plant_lat: float
    plant_lon: float
    customer_formatted_address: str
    customer_lat: float
    customer_lon: float
    distance_miles: float
    duration_minutes: int
    is_live_road_route: bool
    route_coords: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def google_maps_url(self) -> str:
        origin = quote_plus(self.plant_address)
        dest = quote_plus(self.customer_formatted_address)
        return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={dest}&travelmode=driving"


@st.cache_data(show_spinner=False)
def _get_geocoded_plants() -> List[dict]:
    """Resolves and caches lat/lon coordinates for all batch plants once per server session."""
    geolocator = ArcGIS(timeout=5)
    resolved = []
    for p in PLANT_LOCATIONS:
        loc = geolocator.geocode(p["address"])
        if loc:
            resolved.append({**p, "lat": loc.latitude, "lon": loc.longitude})
    return resolved


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * r_miles * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def _query_osrm_drive(
    origin_lon: float, origin_lat: float, dest_lon: float, dest_lat: float
) -> Optional[Tuple[float, int, List[Tuple[float, float]]]]:
    """Queries public OSRM server for driving miles, minutes, and full GeoJSON path."""
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}?overview=full&geometries=geojson"
    )
    try:
        resp = requests.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                miles = route["distance"] / 1609.344
                minutes = max(1, round(route["duration"] / 60.0))
                raw_coords = route.get("geometry", {}).get("coordinates", [])
                lat_lon_path = [(lat, lon) for lon, lat in raw_coords]
                return round(miles, 1), minutes, lat_lon_path
    except Exception:
        pass
    return None


def find_nearest_plant(customer_address: str) -> RouteEstimate:
    cleaned = customer_address.strip()
    if not cleaned:
        raise ValueError("Please enter a valid street address, city, and state or ZIP code.")

    geolocator = ArcGIS(timeout=5)
    location = geolocator.geocode(cleaned)
    if not location:
        raise ValueError(
            "Could not locate that address. Please include street address, city, and state/ZIP."
        )

    cust_lat, cust_lon = location.latitude, location.longitude

    ranked = sorted(
        _get_geocoded_plants(),
        key=lambda p: _haversine_miles(p["lat"], p["lon"], cust_lat, cust_lon),
    )

    best_route: Optional[RouteEstimate] = None
    for plant in ranked[:2]:
        osrm_res = _query_osrm_drive(plant["lon"], plant["lat"], cust_lon, cust_lat)
        if osrm_res is not None:
            miles, mins, path_coords = osrm_res
            candidate = RouteEstimate(
                plant_number=plant["plant_number"],
                plant_name=plant["name"],
                plant_address=plant["address"],
                plant_lat=plant["lat"],
                plant_lon=plant["lon"],
                customer_formatted_address=location.address,
                customer_lat=cust_lat,
                customer_lon=cust_lon,
                distance_miles=miles,
                duration_minutes=mins,
                is_live_road_route=True,
                route_coords=path_coords,
            )
        else:
            straight_miles = _haversine_miles(plant["lat"], plant["lon"], cust_lat, cust_lon)
            est_miles = round(straight_miles * 1.28, 1)
            est_mins = max(5, round((est_miles / 32.0) * 60.0))
            candidate = RouteEstimate(
                plant_number=plant["plant_number"],
                plant_name=plant["name"],
                plant_address=plant["address"],
                plant_lat=plant["lat"],
                plant_lon=plant["lon"],
                customer_formatted_address=location.address,
                customer_lat=cust_lat,
                customer_lon=cust_lon,
                distance_miles=est_miles,
                duration_minutes=est_mins,
                is_live_road_route=False,
                route_coords=[(plant["lat"], plant["lon"]), (cust_lat, cust_lon)],
            )

        if best_route is None or candidate.duration_minutes < best_route.duration_minutes:
            best_route = candidate

    assert best_route is not None
    return best_route