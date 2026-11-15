from datetime import datetime
import streamlit as st
from fpdf import FPDF
from calculator_engine import (
    ADMIXTURE_CATALOG,
    AGGREGATE_CATALOG,
    ConcreteSection,
    OrderSummary,
    SLUMP_OPTIONS,
    STRENGTH_PRICES,
    calculate_project_order,
    recommend_slump,
)
from routing_engine import ROUTING_DISCLAIMER, RouteEstimate, find_nearest_plant
from shape_visualizer import render_shape_preview

st.set_page_config(
    page_title="Concrete Order & Dispatch Planner",
    page_icon="🏗️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Mobile-First & Website-Embed CSS
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 2.5rem;
        padding-left: 0.9rem;
        padding-right: 0.9rem;
        max-width: 760px;
    }
    .stButton > button, .stDownloadButton > button {
        min-height: 2.75rem;
        font-weight: 600;
        border-radius: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

SHAPE_OPTIONS = [
    "Rectangular Slab / Footing",
    "Hole, Column & Round Footing",
    "Circular Slab",
    "Tube / Hollow Column",
    "Curb & Gutter Barrier",
    "Stairs",
]

# Session State Initialization
if "sections" not in st.session_state:
    st.session_state.sections = [
        ConcreteSection(
            name="Main Driveway Slab",
            shape="Rectangular Slab / Footing",
            quantity=1,
            length_ft=20.0,
            width_ft=12.0,
            thickness_in=4.0,
        )
    ]

if "preview_zoom" not in st.session_state:
    st.session_state.preview_zoom = 1.0

if "route_estimate" not in st.session_state:
    st.session_state.route_estimate: RouteEstimate | None = None


def _latin1_safe(text: str) -> str:
    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "—": "-",
        "–": "-",
        "×": "x",
        "→": "->",
        "³": "3",
    }
    for src, target in replacements.items():
        text = text.replace(src, target)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_pdf_quote(
    customer_name: str,
    project_name: str,
    mix_strength: str,
    aggregate_type: str,
    target_slump: str,
    sections: list[ConcreteSection],
    summary: OrderSummary,
    admixtures: dict[str, float],
    route: RouteEstimate | None,
) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Concrete Order & Dispatch Summary", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    safe_cust = _latin1_safe(customer_name.strip() or "Walk-In / Online Customer")
    safe_proj = _latin1_safe(project_name.strip() or "Concrete Pour")
    pdf.cell(0, 5, f"Customer: {safe_cust} | Project: {safe_proj}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Generated: {date_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Mix & Batch Specification
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "1. Batch & Mix Specification", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"  - Strength: {_latin1_safe(mix_strength)}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  - Aggregate: {_latin1_safe(aggregate_type)}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  - Target Slump: {_latin1_safe(target_slump)}", new_x="LMARGIN", new_y="NEXT")
    admix_list = _latin1_safe(", ".join(admixtures.keys())) if admixtures else "None"
    pdf.cell(0, 5, f"  - Admixtures: {admix_list}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Dispatch & Plant Routing
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "2. Dispatch Plant & Delivery Routing", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    if route is not None:
        pdf.cell(
            0,
            5,
            f"  - Assigned Plant: {_latin1_safe(route.plant_number)} - {_latin1_safe(route.plant_name)}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.cell(0, 5, f"  - Plant Address: {_latin1_safe(route.plant_address)}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(
            0,
            5,
            f"  - Jobsite Address: {_latin1_safe(route.customer_formatted_address)}",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.cell(
            0,
            5,
            f"  - Est. Distance & Haul Time: {route.distance_miles:.1f} miles (~{route.duration_minutes} mins)",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 4, f"  {_latin1_safe(ROUTING_DISCLAIMER)}")
    else:
        pdf.cell(0, 5, "  - Jobsite address not entered (plant assignment pending).", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Pour Sections
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "3. Pour Sections", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for sec in sections:
        vol_yd = sec.exact_cubic_yards()
        vol_m3 = sec.exact_cubic_meters()
        line = _latin1_safe(
            f"  - {sec.name} [{sec.shape}]: {sec.summary_text()} -> {vol_yd:.2f} yd3 ({vol_m3:.2f} m3)"
        )
        pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Volume & Cost Totals
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "4. Volume & Estimated Cost Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(
        0,
        5,
        f"  - Net Exact Volume: {summary.exact_yards:.2f} yd3 / {summary.exact_meters:.2f} m3",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        f"  - Recommended Order (+{summary.waste_percent:.0f}% waste): {summary.recommended_order_yards:.1f} yd3 / {summary.recommended_order_meters:.2f} m3",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        f"  - Mixer Trucks: {summary.trucks_required} | 80-lb Bag Equiv: ~{summary.equivalent_80lb_bags} bags",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        f"  - Est. 4\" Crushed Stone Sub-Base: {summary.subbase_gravel_tons:.2f} tons | Wire Mesh: {summary.wire_mesh_sqft:.1f} sq ft",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        5,
        f"  - Concrete Subtotal (${summary.effective_yard_rate:,.2f}/yd3): ${summary.concrete_subtotal:,.2f}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(0, 5, f"  - Admixtures Total: ${summary.admixtures_total:,.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"  - Short-Load Delivery Fee: ${summary.short_load_fee_applied:,.2f}", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, f"  Estimated Total: ${summary.estimated_total:,.2f}", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


# Hide header banner when embedded on an existing website via ?embed=true
is_embedded = st.query_params.get("embed", "false").lower() == "true"
if not is_embedded:
    st.title("🏗️ Concrete Order & Dispatch Planner")
    st.caption("Configure your pour, inspect 2D/3D previews, check nearest plant routing, and download a quote.")

# Quick Live Status Strip
live_yards = sum(s.exact_cubic_yards() for s in st.session_state.sections)
st.info(
    f"**Current Pour:** {len(st.session_state.sections)} section(s) · **{live_yards:.2f} yd³** net volume"
    + (f" · **{st.session_state.route_estimate.plant_number}**" if st.session_state.route_estimate else "")
)

# Mobile-First 4-Tab Navigation
tab_shape, tab_list, tab_delivery, tab_quote = st.tabs(
    [
        "📐 1. Shape",
        f"📋 2. List ({len(st.session_state.sections)})",
        "🚚 3. Delivery",
        "💰 4. Quote",
    ]
)

# ==============================================================================
# TAB 1: SHAPE BUILDER & ZOOMABLE 2D/3D PREVIEW
# ==============================================================================
with tab_shape:
    shape_choice = st.selectbox("Select Concrete Shape", options=SHAPE_OPTIONS)
    default_label = shape_choice.partition("/")[0].strip()

    c_name, c_qty = st.columns([2.2, 1])
    sec_name = c_name.text_input("Section Label", value=default_label)
    qty = c_qty.number_input("Qty", min_value=1, value=1, step=1)

    draft_section = ConcreteSection(
        name=sec_name.strip() or default_label,
        shape=shape_choice,
        quantity=int(qty),
    )
    has_validation_error = False

    if shape_choice == "Rectangular Slab / Footing":
        c1, c2 = st.columns(2)
        draft_section.length_ft = c1.number_input("Length (ft)", min_value=0.5, value=10.0, step=1.0)
        draft_section.width_ft = c2.number_input("Width (ft)", min_value=0.5, value=10.0, step=1.0)
        draft_section.thickness_in = st.number_input("Thickness (in)", min_value=1.0, value=4.0, step=0.5)
        if draft_section.thickness_in > 12.0:
            st.warning(
                f"⚠️ Thickness is **{draft_section.thickness_in} in** ({draft_section.thickness_in / 12:.1f} ft). Verify inches vs. feet!"
            )

    elif shape_choice == "Hole, Column & Round Footing":
        c1, c2 = st.columns(2)
        draft_section.diameter_in = c1.number_input("Diameter (in)", min_value=4.0, value=12.0, step=2.0)
        draft_section.depth_ft = c2.number_input("Depth / Height (ft)", min_value=0.5, value=4.0, step=0.5)

    elif shape_choice == "Circular Slab":
        c1, c2 = st.columns(2)
        draft_section.diameter_in = c1.number_input("Diameter (in)", min_value=12.0, value=120.0, step=6.0)
        draft_section.thickness_in = c2.number_input("Thickness (in)", min_value=1.0, value=4.0, step=0.5)

    elif shape_choice == "Tube / Hollow Column":
        c1, c2 = st.columns(2)
        draft_section.outer_diameter_in = c1.number_input("Outer Dia (in)", min_value=6.0, value=24.0, step=2.0)
        draft_section.inner_diameter_in = c2.number_input("Inner Dia (in)", min_value=2.0, value=18.0, step=2.0)
        draft_section.depth_ft = st.number_input("Length / Height (ft)", min_value=0.5, value=8.0, step=0.5)
        if draft_section.inner_diameter_in >= draft_section.outer_diameter_in:
            st.error("Inner diameter must be smaller than outer diameter.")
            has_validation_error = True

    elif shape_choice == "Curb & Gutter Barrier":
        draft_section.length_ft = st.number_input("Total Run Length (ft)", min_value=1.0, value=25.0, step=1.0)
        c1, c2 = st.columns(2)
        draft_section.curb_depth_in = c1.number_input("Curb Depth (in)", min_value=2.0, value=6.0, step=1.0)
        draft_section.curb_height_in = c2.number_input("Curb Reveal Height (in)", min_value=2.0, value=6.0, step=1.0)
        c3, c4 = st.columns(2)
        draft_section.gutter_width_in = c3.number_input("Gutter Width (in)", min_value=2.0, value=12.0, step=1.0)
        draft_section.flag_thickness_in = c4.number_input("Flag Thickness (in)", min_value=2.0, value=6.0, step=1.0)

    elif shape_choice == "Stairs":
        c1, c2 = st.columns(2)
        draft_section.num_steps = int(c1.number_input("Number of Steps", min_value=1, value=4, step=1))
        draft_section.width_ft = c2.number_input("Stair Width (ft)", min_value=1.0, value=4.0, step=0.5)
        c3, c4 = st.columns(2)
        draft_section.run_in = c3.number_input("Tread Run (in)", min_value=6.0, value=11.0, step=0.5)
        draft_section.rise_in = c4.number_input("Step Rise (in)", min_value=4.0, value=7.5, step=0.5)
        draft_section.platform_depth_in = st.number_input("Top Landing Depth (in)", min_value=0.0, value=36.0, step=6.0)

    # Interactive 2D / 3D Preview + Explicit Zoom Controls
    with st.container(border=True):
        view_mode = st.radio(
            "Preview View",
            ["3D Isometric", "2D Blueprint"],
            horizontal=True,
            label_visibility="collapsed",
        )

        # Mobile-friendly Zoom Bar
        z1, z2, z3, z4 = st.columns([1, 1, 1.2, 1.2])
        if z1.button("➖ Out", use_container_width=True, key="zoom_out"):
            st.session_state.preview_zoom = max(0.5, round(st.session_state.preview_zoom - 0.25, 2))
        if z2.button("➕ In", use_container_width=True, key="zoom_in"):
            st.session_state.preview_zoom = min(2.5, round(st.session_state.preview_zoom + 0.25, 2))
        if z3.button("🔄 Reset", use_container_width=True, key="zoom_reset"):
            st.session_state.preview_zoom = 1.0
        z4.markdown(
            f"<div style='text-align:center; padding-top:0.55rem; font-weight:600;'>"
            f"Zoom: {int(st.session_state.preview_zoom * 100)}%</div>",
            unsafe_allow_html=True,
        )

        fig = render_shape_preview(
            draft_section,
            view_mode=view_mode,
            zoom_level=st.session_state.preview_zoom,
        )
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": True, "scrollZoom": True},
        )

    st.caption(
        f"Draft Section Volume: **{draft_section.exact_cubic_yards():.2f} yd³** "
        f"({draft_section.exact_cubic_meters():.2f} m³)"
    )
    if st.button(
        "➕ Add Section to Project",
        use_container_width=True,
        type="primary",
        disabled=has_validation_error,
    ):
        st.session_state.sections.append(draft_section)
        st.toast(f"Added {draft_section.name} ({draft_section.exact_cubic_yards():.2f} yd³)")
        st.rerun()


# ==============================================================================
# TAB 2: ACTIVE PROJECT SECTIONS (MOBILE CARDS WITH QUICK QTY +/-)
# ==============================================================================
with tab_list:
    if not st.session_state.sections:
        st.info("Your project list is empty. Switch to **1. Shape** to add a slab, footing, column, or stairs.")
    else:
        for idx, sec in enumerate(st.session_state.sections):
            with st.container(border=True):
                st.markdown(f"**{sec.name}** · *{sec.shape}*")
                st.caption(sec.summary_text())

                m_col, q_minus, q_plus, del_col = st.columns([2.2, 0.8, 0.8, 0.9])
                m_col.markdown(
                    f"**{sec.exact_cubic_yards():.2f} yd³** ({sec.exact_cubic_meters():.2f} m³)"
                )
                if q_minus.button("−", key=f"dec_{idx}", help="Decrease quantity", use_container_width=True):
                    if sec.quantity > 1:
                        sec.quantity -= 1
                        st.rerun()
                if q_plus.button("+", key=f"inc_{idx}", help="Increase quantity", use_container_width=True):
                    sec.quantity += 1
                    st.rerun()
                if del_col.button("🗑️", key=f"del_{idx}", help="Remove section", use_container_width=True):
                    st.session_state.sections.pop(idx)
                    st.rerun()

        if st.button("Clear All Sections", type="secondary", use_container_width=True):
            st.session_state.sections = []
            st.rerun()


# ==============================================================================
# TAB 3: CUSTOMER INFO & NEAREST BATCH PLANT ROUTING
# ==============================================================================
with tab_delivery:
    st.subheader("Jobsite & Customer Details")
    customer_name = st.text_input("Customer / Contractor Name", placeholder="e.g., Jordan Smith")
    project_name = st.text_input("Project Name", value="Residential Pour")
    jobsite_address = st.text_input(
        "Delivery Street Address",
        placeholder="e.g., 401 E Jackson St, Tampa, FL 33602",
    )

    if st.button("📍 Find Nearest Plant & Estimate Drive Time", type="primary", use_container_width=True):
        try:
            with st.spinner("Calculating distance and travel time from nearest batch plant..."):
                st.session_state.route_estimate = find_nearest_plant(jobsite_address)
        except ValueError as err:
            st.error(str(err))

    route = st.session_state.route_estimate
    if route is not None:
        with st.container(border=True):
            st.markdown(f"### 🏭 {route.plant_number}")
            st.markdown(f"**{route.plant_name}** · {route.plant_address}")
            st.caption(f"Delivering to: {route.customer_formatted_address}")

            r1, r2 = st.columns(2)
            r1.metric("Distance", f"{route.distance_miles:.1f} mi")
            r2.metric("Est. Drive Time", f"~{route.duration_minutes} mins")

            if route.duration_minutes > 45:
                st.warning(
                    "⏱️ **Extended Haul Notice:** Drive time exceeds 45 minutes. Consider adding a "
                    "**Hot-Weather Retarder** in the Quote tab to preserve slump and set time."
                )

            st.caption(ROUTING_DISCLAIMER)


# ==============================================================================
# TAB 4: MIX DESIGN, SUGGESTED SLUMP, QUOTE & PDF DISPATCH
# ==============================================================================
with tab_quote:
    st.subheader("Mix Strength, Aggregate & Slump")

    selected_strength = st.selectbox(
        "Compressive Strength (PSI)",
        options=list(STRENGTH_PRICES.keys()),
        index=2,  # Default 3,500 PSI
    )
    base_price, strength_desc = STRENGTH_PRICES[selected_strength]
    st.caption(f"*{strength_desc}* — Base: **${base_price:,.2f}/yd³**")

    selected_aggregate = st.selectbox(
        "Aggregate / Rock Size",
        options=list(AGGREGATE_CATALOG.keys()),
        index=0,
    )
    agg_upcharge, agg_desc = AGGREGATE_CATALOG[selected_aggregate]
    upcharge_label = f"+${agg_upcharge:,.2f}/yd³" if agg_upcharge > 0 else "Included"
    st.caption(f"*{agg_desc}* ({upcharge_label})")

    # Thin-section + #57 big rock tip
    has_thin_slab = any(
        s.shape in ("Rectangular Slab / Footing", "Circular Slab") and 0 < s.thickness_in < 3.5
        for s in st.session_state.sections
    )
    if has_thin_slab and "#57" in selected_aggregate:
        st.info(
            "💡 **Aggregate Tip:** You have a thin section under 3.5\" thick. **#89 Small Rock (Pea Gravel)** "
            "usually screeds and finishes easier than #57 Big Rock on thin pours."
        )

    # Automatic Suggested Slump
    rec_idx, rec_label, rec_reason = recommend_slump(st.session_state.sections, selected_aggregate)
    st.success(f"🎯 **Suggested Slump: {rec_label}** — {rec_reason}")

    target_slump = st.selectbox(
        "Target Batch Slump",
        options=SLUMP_OPTIONS,
        index=rec_idx,
    )

    with st.expander("➕ Optional Admixtures & Modifiers"):
        admix_selected: dict[str, float] = {}
        for admix_name, (admix_cost, admix_note) in ADMIXTURE_CATALOG.items():
            if st.checkbox(f"{admix_name} (+${admix_cost:,.2f}/yd³)", help=admix_note):
                admix_selected[admix_name] = admix_cost

    if (target_slump.startswith("6\"") or target_slump.startswith("7\"")) and (
        "Water Reducer / Superplasticizer" not in admix_selected
    ):
        st.warning(
            "⚠️ **High-Slump Batch Note:** Pouring at a 6\"+ slump without a **Water Reducer / Superplasticizer** "
            "may reduce final PSI strength if extra water is added at the jobsite."
        )

    waste_rates = {
        "Tightly formed flat slab (+5%)": 5.0,
        "Standard residential pour (+10%)": 10.0,
        "Uneven trench / complex forms (+15%)": 15.0,
    }
    waste_preset = st.selectbox("Jobsite Waste Allowance", options=list(waste_rates.keys()), index=1)
    waste_pct = waste_rates[waste_preset]

    # Supplier Truck & Short-Load Rules (Collapsed on mobile)
    with st.expander("⚙️ Plant Truck & Short-Load Settings"):
        t1, t2 = st.columns(2)
        truck_capacity = t1.number_input("Truck Capacity (yd³)", min_value=5.0, max_value=12.0, value=9.5, step=0.5)
        short_load_threshold = t2.number_input("Short-Load Min (yd³)", min_value=1.0, max_value=8.0, value=4.0, step=0.5)
        short_load_fee = st.number_input("Short-Load Fee ($)", min_value=0.0, max_value=500.0, value=150.0, step=25.0)

    st.divider()

    if not st.session_state.sections:
        st.info("Add at least one section in **1. Shape** to generate your order quote.")
    else:
        summary = calculate_project_order(
            sections=st.session_state.sections,
            waste_percent=waste_pct,
            base_price_per_yard=base_price,
            aggregate_upcharge_per_yard=agg_upcharge,
            admixture_costs_per_yard=admix_selected,
            truck_capacity_yards=truck_capacity,
            short_load_threshold_yards=short_load_threshold,
            short_load_fee=short_load_fee,
        )

        # 2x2 Mobile Metric Grid
        row1_a, row1_b = st.columns(2)
        row1_a.metric(
            "Order Quantity",
            f"{summary.recommended_order_yards:.1f} yd³",
            f"{summary.recommended_order_meters:.2f} m³",
        )
        row1_b.metric("Estimated Total", f"${summary.estimated_total:,.2f}")

        row2_a, row2_b = st.columns(2)
        row2_a.metric("Mixer Trucks", f"{summary.trucks_required}")
        row2_b.metric("Rate / yd³", f"${summary.effective_yard_rate:,.2f}")

        # Full-truck buffer nudge
        remainder_on_truck = summary.recommended_order_yards % truck_capacity
        if 0 < (truck_capacity - remainder_on_truck) <= 0.5 and summary.recommended_order_yards > short_load_threshold:
            st.info(
                f"🚛 **Truck Capacity Tip:** Your order ({summary.recommended_order_yards:.1f} yd³) is right near a "
                f"full {truck_capacity:.1f} yd³ truckload—double-check forms so you don't spill over onto an extra truck!"
            )

        if summary.is_short_load:
            st.warning(
                f"🚚 **Short-Load Fee Applied (+${summary.short_load_fee_applied:,.2f}):** Orders under "
                f"{short_load_threshold:.1f} yd³ incur a short-load delivery fee. "
                f"(Bagged equivalent: ~{summary.equivalent_80lb_bags} × 80-lb bags.)"
            )

        with st.container(border=True):
            st.markdown("**Volume & Cost Breakdown**")
            st.write(f"• **Net Exact Volume:** {summary.exact_yards:.2f} yd³ ({summary.exact_meters:.2f} m³)")
            st.write(f"• **With {waste_pct:.0f}% Waste:** {summary.yards_with_waste:.2f} yd³ ({summary.meters_with_waste:.2f} m³)")
            st.write(f"• **Concrete Subtotal:** ${summary.concrete_subtotal:,.2f}")
            st.write(f"• **Admixtures Total:** ${summary.admixtures_total:,.2f}")
            st.write(f"• **Short-Load Fee:** ${summary.short_load_fee_applied:,.2f}")
            st.divider()
            st.write(f"• **4\" Gravel Sub-Base:** {summary.subbase_gravel_tons:.2f} tons")
            st.write(f"• **Wire Mesh (+10% overlap):** {summary.wire_mesh_sqft:.1f} sq ft")

        pdf_bytes = generate_pdf_quote(
            customer_name=customer_name,
            project_name=project_name,
            mix_strength=selected_strength,
            aggregate_type=selected_aggregate,
            target_slump=target_slump,
            sections=st.session_state.sections,
            summary=summary,
            admixtures=admix_selected,
            route=st.session_state.route_estimate,
        )
        safe_file = f"{project_name.strip().lower().replace(' ', '_') or 'concrete'}_dispatch_quote.pdf"
        st.download_button(
            "📄 Download PDF Quote & Dispatch Summary",
            data=pdf_bytes,
            file_name=safe_file,
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )