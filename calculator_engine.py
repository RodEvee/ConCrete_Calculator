import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

CUBIC_YARDS_TO_METERS = 0.764554858
CUBIC_FEET_PER_YARD = 27.0
BAGS_80LB_PER_YARD = 45.0
GRAVEL_TONS_PER_YARD = 1.4
WIRE_MESH_OVERLAP = 1.10

# --- MIX & AGGREGATE CATALOG (Update base prices when your plant sheet is ready) ---
STRENGTH_PRICES: Dict[str, Tuple[float, str]] = {
    "2,500 PSI": (152.0, "Footings, mass concrete & non-structural fill"),
    "3,000 PSI": (160.0, "Standard sidewalks, patios & shed pads"),
    "3,500 PSI": (168.0, "Residential slabs, garage floors & light driveways"),
    "4,000 PSI": (176.0, "Heavy driveways, RV pads & structural walls"),
    "4,500 PSI": (186.0, "Commercial slabs & heavy equipment pads"),
    "5,000 PSI": (198.0, "High-strength structural & post-tensioned pours"),
}

AGGREGATE_CATALOG: Dict[str, Tuple[float, str]] = {
    "#57 Stone (Big Rock - 3/4\" to 1\")": (
        0.0,
        "Standard coarse aggregate for flatwork, footings & structural pours.",
    ),
    "#89 Stone (Small Rock / Pea Gravel - 3/8\")": (
        10.0,
        "Ideal for line pumps, thin overlays, tight rebar & decorative finishes.",
    ),
    "Grout / Mortar Mix (Fine Sand Only)": (
        14.0,
        "No coarse rock; designed for CMU block fill, post-setting & tight voids.",
    ),
}

ADMIXTURE_CATALOG: Dict[str, Tuple[float, str]] = {
    "Fiber Mesh Reinforcement": (12.0, "Controls plastic shrinkage cracking"),
    "Air Entrainment": (8.0, "Improves freeze-thaw durability & workability"),
    "Water Reducer / Superplasticizer": (11.0, "Increases slump/flow without adding water"),
    "Hot-Weather Retarder": (10.0, "Extends working time on warm days or long hauls"),
    "Non-Chloride Accelerator": (14.0, "Speeds up set time in cool weather"),
}

SLUMP_OPTIONS: List[str] = [
    "3\" (Stiff — Curbs, Stairs & Steep Slopes)",
    "4\" (Standard — Flatwork, Slabs & Driveways)",
    "5\" (Moderate Flow — Reinforced Slabs & Footings)",
    "6\" (High Flow — Columns, Piers & Tight Rebar)",
    "7\"+ (Superplasticized — Line Pump & Complex Forms)",
]


@dataclass
class ConcreteSection:
    """Represents a concrete pour section across 6 distinct geometry types."""
    name: str
    shape: str
    quantity: int = 1
    # Shared & Rectangular / Circular dimensions
    length_ft: float = 0.0
    width_ft: float = 0.0
    thickness_in: float = 0.0
    diameter_in: float = 0.0
    depth_ft: float = 0.0
    # Tube / Hollow Cylinder dimensions
    outer_diameter_in: float = 0.0
    inner_diameter_in: float = 0.0
    # Curb & Gutter dimensions
    curb_depth_in: float = 0.0
    curb_height_in: float = 0.0
    gutter_width_in: float = 0.0
    flag_thickness_in: float = 0.0
    # Stairs dimensions
    num_steps: int = 1
    run_in: float = 0.0
    rise_in: float = 0.0
    platform_depth_in: float = 0.0

    def exact_cubic_yards(self) -> float:
        """Calculates raw net volume in cubic yards."""
        if self.shape == "Rectangular Slab / Footing":
            cubic_feet = self.length_ft * self.width_ft * (self.thickness_in / 12.0)

        elif self.shape == "Hole, Column & Round Footing":
            radius_ft = (self.diameter_in / 12.0) / 2.0
            cubic_feet = math.pi * (radius_ft ** 2) * self.depth_ft

        elif self.shape == "Circular Slab":
            radius_ft = (self.diameter_in / 12.0) / 2.0
            cubic_feet = math.pi * (radius_ft ** 2) * (self.thickness_in / 12.0)

        elif self.shape == "Tube / Hollow Column":
            r_outer_ft = (self.outer_diameter_in / 12.0) / 2.0
            r_inner_ft = (self.inner_diameter_in / 12.0) / 2.0
            if r_inner_ft >= r_outer_ft:
                return 0.0
            cubic_feet = math.pi * ((r_outer_ft ** 2) - (r_inner_ft ** 2)) * self.depth_ft

        elif self.shape == "Curb & Gutter Barrier":
            flag_area_sqft = (self.gutter_width_in / 12.0) * (self.flag_thickness_in / 12.0)
            curb_area_sqft = (self.curb_depth_in / 12.0) * (self.curb_height_in / 12.0)
            cubic_feet = (flag_area_sqft + curb_area_sqft) * self.length_ft

        elif self.shape == "Stairs":
            w_ft = self.width_ft
            run_ft = self.run_in / 12.0
            rise_ft = self.rise_in / 12.0
            plat_ft = self.platform_depth_in / 12.0

            steps_vol = sum((i * rise_ft) * run_ft * w_ft for i in range(1, self.num_steps + 1))
            total_height_ft = self.num_steps * rise_ft
            platform_vol = plat_ft * total_height_ft * w_ft
            cubic_feet = steps_vol + platform_vol

        else:
            raise ValueError(f"Unsupported shape: {self.shape}")

        return (cubic_feet * self.quantity) / CUBIC_FEET_PER_YARD

    def exact_cubic_meters(self) -> float:
        return self.exact_cubic_yards() * CUBIC_YARDS_TO_METERS

    def surface_area_sqft(self) -> float:
        if self.shape == "Rectangular Slab / Footing":
            return self.length_ft * self.width_ft * self.quantity
        elif self.shape == "Circular Slab":
            radius_ft = (self.diameter_in / 12.0) / 2.0
            return math.pi * (radius_ft ** 2) * self.quantity
        return 0.0

    def summary_text(self) -> str:
        if self.shape == "Rectangular Slab / Footing":
            return f"{self.length_ft}' L × {self.width_ft}' W × {self.thickness_in}\" T (Qty: {self.quantity})"
        elif self.shape == "Hole, Column & Round Footing":
            return f"{self.diameter_in}\" Dia × {self.depth_ft}' Depth (Qty: {self.quantity})"
        elif self.shape == "Circular Slab":
            return f"{self.diameter_in}\" Dia × {self.thickness_in}\" Thick (Qty: {self.quantity})"
        elif self.shape == "Tube / Hollow Column":
            return f"{self.outer_diameter_in}\" OD / {self.inner_diameter_in}\" ID × {self.depth_ft}' L (Qty: {self.quantity})"
        elif self.shape == "Curb & Gutter Barrier":
            return (
                f"{self.length_ft}' L | Curb {self.curb_depth_in}\"×{self.curb_height_in}\" "
                f"+ Gutter {self.gutter_width_in}\"×{self.flag_thickness_in}\" (Qty: {self.quantity})"
            )
        elif self.shape == "Stairs":
            plat_txt = f" + {self.platform_depth_in}\" Landing" if self.platform_depth_in > 0 else ""
            return f"{self.num_steps} Steps ({self.rise_in}\"R × {self.run_in}\"T) × {self.width_ft}' W{plat_txt} (Qty: {self.quantity})"
        return ""


@dataclass
class OrderSummary:
    exact_yards: float
    exact_meters: float
    waste_percent: float
    yards_with_waste: float
    meters_with_waste: float
    recommended_order_yards: float
    recommended_order_meters: float
    is_short_load: bool
    trucks_required: int
    equivalent_80lb_bags: int
    subbase_gravel_tons: float
    wire_mesh_sqft: float
    effective_yard_rate: float
    concrete_subtotal: float
    admixtures_total: float
    short_load_fee_applied: float
    estimated_total: float


def recommend_slump(sections: List[ConcreteSection], aggregate_choice: str) -> Tuple[int, str, str]:
    """
    Determines the suggested slump index in SLUMP_OPTIONS, target label, and explanation
    based on project shapes and aggregate selection.
    """
    shapes = {s.shape for s in sections}

    if "Stairs" in shapes or "Curb & Gutter Barrier" in shapes:
        return (
            0,
            '3" – 4" Slump',
            "Stairs or curbs are in your project—a stiffer 3\"–4\" mix prevents vertical risers and curb faces from slumping.",
        )

    if "Grout" in aggregate_choice:
        return (
            4,
            '7"+ Slump',
            "Grout/mortar mixes require high flow (7\"+) to fill block cells and tight voids completely.",
        )

    if "#89" in aggregate_choice:
        return (
            3,
            '5" – 6" Slump',
            "#89 Small Rock (pea gravel) is commonly placed at a 5\"–6\" slump for line pumping and smooth finishes.",
        )

    if "Hole, Column & Round Footing" in shapes or "Tube / Hollow Column" in shapes:
        return (
            3,
            '5" – 6" Slump',
            "Vertical columns, piers, and hollow tubes consolidate best around 5\"–6\" slump to avoid honeycombing.",
        )

    return (
        1,
        '4" – 5" Slump',
        "Standard flatwork (slabs, patios, driveways) finishes cleanest at a 4\"–5\" slump without excess bleed water.",
    )


def round_up_half_yard(yards: float) -> float:
    if yards <= 0:
        return 0.0
    return math.ceil((yards * 2.0) - 1e-9) / 2.0


def calculate_project_order(
    sections: List[ConcreteSection],
    waste_percent: float = 10.0,
    base_price_per_yard: float = 168.0,
    aggregate_upcharge_per_yard: float = 0.0,
    admixture_costs_per_yard: Optional[Dict[str, float]] = None,
    truck_capacity_yards: float = 9.5,
    short_load_threshold_yards: float = 4.0,
    short_load_fee: float = 150.0,
    subbase_depth_in: float = 4.0,
) -> OrderSummary:
    admixture_costs_per_yard = admixture_costs_per_yard or {}

    exact_yards = sum(sec.exact_cubic_yards() for sec in sections)
    total_slab_sqft = sum(sec.surface_area_sqft() for sec in sections)

    yards_with_waste = exact_yards * (1.0 + (waste_percent / 100.0))
    order_yards = round_up_half_yard(yards_with_waste)

    exact_meters = exact_yards * CUBIC_YARDS_TO_METERS
    meters_with_waste = yards_with_waste * CUBIC_YARDS_TO_METERS
    order_meters = order_yards * CUBIC_YARDS_TO_METERS

    is_short_load = 0 < order_yards < short_load_threshold_yards
    trucks_required = math.ceil(order_yards / truck_capacity_yards) if order_yards > 0 else 0
    equivalent_bags = math.ceil(yards_with_waste * BAGS_80LB_PER_YARD)

    subbase_yards = (total_slab_sqft * (subbase_depth_in / 12.0)) / CUBIC_FEET_PER_YARD
    subbase_tons = subbase_yards * GRAVEL_TONS_PER_YARD
    wire_mesh_sqft = total_slab_sqft * WIRE_MESH_OVERLAP

    effective_yard_rate = base_price_per_yard + aggregate_upcharge_per_yard
    concrete_subtotal = order_yards * effective_yard_rate
    admixture_rate = sum(admixture_costs_per_yard.values())
    admixtures_total = order_yards * admixture_rate
    applied_short_load = short_load_fee if is_short_load else 0.0
    estimated_total = concrete_subtotal + admixtures_total + applied_short_load

    return OrderSummary(
        exact_yards=round(exact_yards, 2),
        exact_meters=round(exact_meters, 2),
        waste_percent=waste_percent,
        yards_with_waste=round(yards_with_waste, 2),
        meters_with_waste=round(meters_with_waste, 2),
        recommended_order_yards=order_yards,
        recommended_order_meters=round(order_meters, 2),
        is_short_load=is_short_load,
        trucks_required=trucks_required,
        equivalent_80lb_bags=equivalent_bags,
        subbase_gravel_tons=round(subbase_tons, 2),
        wire_mesh_sqft=round(wire_mesh_sqft, 1),
        effective_yard_rate=round(effective_yard_rate, 2),
        concrete_subtotal=round(concrete_subtotal, 2),
        admixtures_total=round(admixtures_total, 2),
        short_load_fee_applied=round(applied_short_load, 2),
        estimated_total=round(estimated_total, 2),
    )