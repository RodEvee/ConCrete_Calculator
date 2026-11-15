import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import quote_plus
import requests
import streamlit as st
from geopy.geocoders import ArcGIS

# --- BATCH PLANT DIRECTORY (41 Florida Ready-Mix Locations: Plant #01 - #41) ---
PLANT_LOCATIONS = [
    {"plant_number": "Plant #01", "name": "Bradenton (Ready-Mix)", "address": "4415 15th St E, Bradenton, FL 34203"},
    {"plant_number": "Plant #02", "name": "Clermont (Ready-Mix)", "address": "16000 Johns Lake Rd, Clermont, FL 34712"},
    {"plant_number": "Plant #03", "name": "Davenport (Ready-Mix)", "address": "100 Lem Carnes Rd, Davenport, FL 33837"},
    {"plant_number": "Plant #04", "name": "Delray Beach (Ready-Mix)", "address": "1700 W Atlantic Ave, Delray Beach, FL 33444"},
    {"plant_number": "Plant #05", "name": "Florida City (Concrete & Materials)", "address": "15900 SW 408th St, Florida City, FL 33034"},
    {"plant_number": "Plant #06", "name": "Fort Lauderdale (South Lauderdale Ready-Mix)", "address": "SE 28th St, Fort Lauderdale, FL 33316"},
    {"plant_number": "Plant #07", "name": "Fort Myers (Ready-Mix)", "address": "2225 Rockfill Rd, Fort Myers, FL 33916"},
    {"plant_number": "Plant #08", "name": "Fort Pierce (Ready-Mix & Block)", "address": "6100 W Midway Rd, Fort Pierce, FL 34981"},
    {"plant_number": "Plant #09", "name": "Gainesville (South Ready-Mix)", "address": "305 SW Depot Ave, Gainesville, FL 32601"},
    {"plant_number": "Plant #10", "name": "Gibsonton (Big Bend Ready-Mix)", "address": "6002 Big Bend Rd, Gibsonton, FL 33534"},
    {"plant_number": "Plant #11", "name": "Lakeland (Ready-Mix)", "address": "3770 Maine Ave, Lakeland, FL 33801"},
    {"plant_number": "Plant #12", "name": "Largo (Ready-Mix)", "address": "2195 Lake Ave SE, Largo, FL 33771"},
    {"plant_number": "Plant #13", "name": "Lecanto (Ready-Mix)", "address": "2975 S Lecanto Hwy, Lecanto, FL 34461"},
    {"plant_number": "Plant #14", "name": "Miami (Sweetwater Ready-Mix)", "address": "1200 NW 137th Ave, Miami, FL 33182"},
    {"plant_number": "Plant #15", "name": "Miami (Sweetwater Concrete)", "address": "1600 SW 137th Ct, Miami, FL 33182"},
    {"plant_number": "Plant #16", "name": "Naples (Wiggins Pass North Naples)", "address": "1425 Wiggins Pass Rd, Naples, FL 34110"},
    {"plant_number": "Plant #17", "name": "New Smyrna Beach (Aggregates & Ready-Mix)", "address": "507 S Myrtle Ave, New Smyrna Beach, FL 32168"},
    {"plant_number": "Plant #18", "name": "Ocala (West Ocala)", "address": "2355 SW 60th Ave, Ocala, FL 34474"},
    {"plant_number": "Plant #19", "name": "Odessa (Ready-Mix)", "address": "2430 Marathon Rd, Odessa, FL 33556"},
    {"plant_number": "Plant #20", "name": "Oldsmar (Ready-Mix)", "address": "501 Douglas Rd, Oldsmar, FL 34677"},
    {"plant_number": "Plant #21", "name": "Orlando (Grant St Ready-Mix)", "address": "435 W Grant St, Orlando, FL 32806"},
    {"plant_number": "Plant #22", "name": "Orlando (East Orlando Ready-Mix)", "address": "7244 Narcoossee Rd, Orlando, FL 32822"},
    {"plant_number": "Plant #23", "name": "Orlando (Regency Park Ready-Mix)", "address": "11525 United Way, Orlando, FL 32824"},
    {"plant_number": "Plant #24", "name": "Orlando (Lockhart Ready-Mix)", "address": "4004 Clarcona Ocoee Rd, Orlando, FL 32810"},
    {"plant_number": "Plant #25", "name": "Palmetto (Ready-Mix)", "address": "600 9th St W, Palmetto, FL 34221"},
    {"plant_number": "Plant #26", "name": "Pembroke Pines / Hollywood (Ready-Mix)", "address": "17301 Pines Blvd, Pembroke Pines, FL 33029"},
    {"plant_number": "Plant #27", "name": "Plant City (Ready-Mix)", "address": "2680 US-92, Plant City, FL 33566"},
    {"plant_number": "Plant #28", "name": "Pompano Beach (Ready-Mix)", "address": "1150 NW 24th Ct, Pompano Beach, FL 33064"},
    {"plant_number": "Plant #29", "name": "Port Charlotte (Ready-Mix)", "address": "19300 Peachland Blvd, Port Charlotte, FL 33948"},
    {"plant_number": "Plant #30", "name": "Sanford (Ready-Mix)", "address": "2210 W 25th St, Sanford, FL 32771"},
    {"plant_number": "Plant #31", "name": "Sarasota (Central South Ready-Mix)", "address": "1022 Central Ave, Sarasota, FL 34236"},
    {"plant_number": "Plant #32", "name": "Sarasota (McIntosh Ready-Mix)", "address": "5505 McIntosh Rd, Sarasota, FL 34233"},
    {"plant_number": "Plant #33", "name": "St. Augustine (World Golf Ready-Mix)", "address": "125 International Golf Pkwy, St. Augustine, FL 32095"},
    {"plant_number": "Plant #34", "name": "St. Augustine (Industry Pl Ready-Mix)", "address": "233 Industry Pl, St. Augustine, FL 32095"},
    {"plant_number": "Plant #35", "name": "St. Petersburg (Ready-Mix)", "address": "601 24th St S, St. Petersburg, FL 33712"},
    {"plant_number": "Plant #36", "name": "Tampa (34th Street Ready-Mix)", "address": "3212 E Clark St, Tampa, FL 33602"},
    {"plant_number": "Plant #37", "name": "Tampa (56th Street Ready-Mix)", "address": "5503 E Diana St, Tampa, FL 33610"},
    {"plant_number": "Plant #38", "name": "Tampa (Waters Avenue Ready-Mix)", "address": "9117 Florida Mining Blvd, Tampa, FL 33634"},
    {"plant_number": "Plant #39", "name": "West Palm Beach (Ready-Mix)", "address": "501 7th St, West Palm Beach, FL 33401"},
    {"plant_number": "Plant #40", "name": "Winter Park (Ready-Mix)", "address": "4010 Forsyth Rd, Winter Park, FL 32792"},
    {"plant_number": "Plant #41", "name": "Zephyrhills (Ready-Mix)", "address": "3946 Copeland Dr, Zephyrhills, FL 33542"},
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
    route_coords: List[Tuple[float, float]] = field(default_factory=list)  # (lat, lon) pairs

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
                # GeoJSON returns [lon, lat]; flip to (lat, lon) for mapping
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