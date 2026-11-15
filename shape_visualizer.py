import numpy as np
import plotly.graph_objects as go
from calculator_engine import ConcreteSection


def render_shape_preview(
    section: ConcreteSection,
    view_mode: str = "3D Isometric",
    zoom_level: float = 1.0,
) -> go.Figure:
    """
    Generates a scaled, zoomable 2D blueprint or 3D wireframe/mesh preview.
    zoom_level: 0.5 (zoomed out) to 2.5 (zoomed in), default 1.0.
    """
    zoom = max(0.4, min(3.0, zoom_level))
    fig = go.Figure()

    if view_mode == "2D Blueprint":
        max_extent, cx, cy = _add_2d_trace(fig, section)
        half_span = (max_extent * 0.65) / zoom
        fig.update_layout(
            height=290,
            margin=dict(l=16, r=16, t=36, b=16),
            title=dict(
                text=f"2D Blueprint ({int(zoom * 100)}% Zoom)",
                font=dict(size=13),
            ),
            xaxis=dict(
                range=[cx - half_span, cx + half_span],
                scaleanchor="y",
                scaleratio=1,
                showgrid=True,
                zeroline=False,
                title="ft",
            ),
            yaxis=dict(
                range=[cy - half_span, cy + half_span],
                showgrid=True,
                zeroline=False,
                title="ft",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(240,242,246,0.6)",
            dragmode="pan",
        )
    else:
        _add_3d_trace(fig, section)
        cam_dist = 1.65 / zoom
        fig.update_layout(
            height=310,
            margin=dict(l=0, r=0, t=36, b=0),
            title=dict(
                text=f"3D Isometric ({int(zoom * 100)}% Zoom)",
                font=dict(size=13),
            ),
            scene=dict(
                aspectmode="data",
                camera=dict(eye=dict(x=cam_dist, y=cam_dist, z=cam_dist * 0.78)),
                xaxis=dict(title="X (ft)"),
                yaxis=dict(title="Y (ft)"),
                zaxis=dict(title="Z (ft)"),
            ),
            paper_bgcolor="rgba(0,0,0,0)",
        )
    return fig


def _add_2d_trace(fig: go.Figure, s: ConcreteSection) -> tuple[float, float, float]:
    """Draws 2D geometry with dimension callouts and returns (max_span, center_x, center_y)."""
    if s.shape == "Rectangular Slab / Footing":
        l, w = s.length_ft, s.width_ft
        x = [0, l, l, 0, 0]
        y = [0, 0, w, w, 0]
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                fill="toself",
                fillcolor="rgba(100,116,139,0.4)",
                line=dict(color="#334155", width=2),
                showlegend=False,
            )
        )
        fig.add_annotation(x=l / 2, y=-0.06 * max(l, w), text=f"{l}' L", showarrow=False, font=dict(size=11))
        fig.add_annotation(x=l + 0.06 * max(l, w), y=w / 2, text=f"{w}' W", showarrow=False, font=dict(size=11))
        return max(l, w, 1.0), l / 2.0, w / 2.0

    elif s.shape in ("Hole, Column & Round Footing", "Circular Slab"):
        d_ft = s.diameter_in / 12.0
        r = d_ft / 2.0
        theta = np.linspace(0, 2 * np.pi, 60)
        fig.add_trace(
            go.Scatter(
                x=r * np.cos(theta),
                y=r * np.sin(theta),
                fill="toself",
                fillcolor="rgba(100,116,139,0.4)",
                line=dict(color="#334155", width=2),
                showlegend=False,
            )
        )
        fig.add_annotation(x=0, y=0, text=f"{s.diameter_in}\" Dia", showarrow=False, font=dict(size=11))
        return max(d_ft, 1.0), 0.0, 0.0

    elif s.shape == "Tube / Hollow Column":
        d_out_ft = s.outer_diameter_in / 12.0
        r_out = d_out_ft / 2.0
        r_in = (s.inner_diameter_in / 12.0) / 2.0
        theta = np.linspace(0, 2 * np.pi, 60)
        fig.add_trace(
            go.Scatter(
                x=r_out * np.cos(theta),
                y=r_out * np.sin(theta),
                fill="toself",
                fillcolor="rgba(100,116,139,0.4)",
                line=dict(color="#334155", width=2),
                name="Outer",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=r_in * np.cos(theta),
                y=r_in * np.sin(theta),
                fill="toself",
                fillcolor="white",
                line=dict(color="#ef4444", width=2, dash="dash"),
                name="Core",
            )
        )
        return max(d_out_ft, 1.0), 0.0, 0.0

    elif s.shape == "Curb & Gutter Barrier":
        cd = s.curb_depth_in / 12.0
        ch = s.curb_height_in / 12.0
        gw = s.gutter_width_in / 12.0
        ft = s.flag_thickness_in / 12.0
        total_w = cd + gw
        total_h = ft + ch
        x = [0, total_w, total_w, cd, cd, 0, 0]
        y = [0, 0, ft, ft, total_h, total_h, 0]
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                fill="toself",
                fillcolor="rgba(100,116,139,0.4)",
                line=dict(color="#334155", width=2),
                showlegend=False,
            )
        )
        return max(total_w, total_h, 0.5), total_w / 2.0, total_h / 2.0

    elif s.shape == "Stairs":
        steps = max(1, s.num_steps)
        run = s.run_in / 12.0
        rise = s.rise_in / 12.0
        plat = s.platform_depth_in / 12.0
        x = [0.0]
        y = [0.0]
        for i in range(steps):
            x.extend([i * run, (i + 1) * run])
            y.extend([(i + 1) * rise, (i + 1) * rise])
        total_x = steps * run + plat
        total_y = steps * rise
        x.extend([total_x, total_x, 0.0])
        y.extend([total_y, 0.0, 0.0])
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                fill="toself",
                fillcolor="rgba(100,116,139,0.4)",
                line=dict(color="#334155", width=2),
                showlegend=False,
            )
        )
        return max(total_x, total_y, 1.0), total_x / 2.0, total_y / 2.0

    return 10.0, 5.0, 5.0


def _add_3d_trace(fig: go.Figure, s: ConcreteSection):
    if s.shape == "Rectangular Slab / Footing":
        l, w, h = s.length_ft, s.width_ft, s.thickness_in / 12.0
        fig.add_trace(
            go.Mesh3d(
                x=[0, l, l, 0, 0, l, l, 0],
                y=[0, 0, w, w, 0, 0, w, w],
                z=[0, 0, 0, 0, h, h, h, h],
                i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
                j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
                k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
                color="#64748b",
                opacity=0.78,
            )
        )

    elif s.shape in ("Hole, Column & Round Footing", "Circular Slab", "Tube / Hollow Column"):
        r_out = ((s.outer_diameter_in if "Tube" in s.shape else s.diameter_in) / 12.0) / 2.0
        h = s.depth_ft if "Slab" not in s.shape else (s.thickness_in / 12.0)
        theta = np.linspace(0, 2 * np.pi, 36)
        z = np.linspace(0, h, 2)
        theta_grid, z_grid = np.meshgrid(theta, z)

        fig.add_trace(
            go.Surface(
                x=r_out * np.cos(theta_grid),
                y=r_out * np.sin(theta_grid),
                z=z_grid,
                colorscale=[[0, "#64748b"], [1, "#94a3b8"]],
                showscale=False,
                opacity=0.82,
            )
        )
        for z_cap in (0.0, h):
            fig.add_trace(
                go.Scatter3d(
                    x=r_out * np.cos(theta),
                    y=r_out * np.sin(theta),
                    z=[z_cap] * len(theta),
                    mode="lines",
                    line=dict(color="#334155", width=3),
                    showlegend=False,
                )
            )

        if "Tube" in s.shape and s.inner_diameter_in > 0:
            r_in = (s.inner_diameter_in / 12.0) / 2.0
            fig.add_trace(
                go.Surface(
                    x=r_in * np.cos(theta_grid),
                    y=r_in * np.sin(theta_grid),
                    z=z_grid,
                    colorscale=[[0, "#ef4444"], [1, "#f87171"]],
                    showscale=False,
                    opacity=0.65,
                )
            )
            for z_cap in (0.0, h):
                fig.add_trace(
                    go.Scatter3d(
                        x=r_in * np.cos(theta),
                        y=r_in * np.sin(theta),
                        z=[z_cap] * len(theta),
                        mode="lines",
                        line=dict(color="#ef4444", width=3),
                        showlegend=False,
                    )
                )

    elif s.shape == "Curb & Gutter Barrier":
        l = s.length_ft
        cd, ch = s.curb_depth_in / 12.0, s.curb_height_in / 12.0
        gw, ft = s.gutter_width_in / 12.0, s.flag_thickness_in / 12.0
        px = [0.0, cd + gw, cd + gw, cd, cd, 0.0]
        pz = [0.0, 0.0, ft, ft, ft + ch, ft + ch]
        closed_px = px + [px[0]]
        closed_pz = pz + [pz[0]]
        for y_val in [0.0, l]:
            fig.add_trace(
                go.Scatter3d(
                    x=closed_px,
                    y=[y_val] * len(closed_px),
                    z=closed_pz,
                    mode="lines",
                    line=dict(color="#334155", width=5),
                    showlegend=False,
                )
            )
        for x_v, z_v in zip(px, pz):
            fig.add_trace(
                go.Scatter3d(
                    x=[x_v, x_v],
                    y=[0.0, l],
                    z=[z_v, z_v],
                    mode="lines",
                    line=dict(color="#475569", width=4),
                    showlegend=False,
                )
            )

    elif s.shape == "Stairs":
        w = s.width_ft
        steps = max(1, s.num_steps)
        run, rise = s.run_in / 12.0, s.rise_in / 12.0
        plat = s.platform_depth_in / 12.0
        px = [0.0]
        pz = [0.0]
        for i in range(steps):
            px.extend([i * run, (i + 1) * run])
            pz.extend([(i + 1) * rise, (i + 1) * rise])
        px.extend([steps * run + plat, steps * run + plat])
        pz.extend([steps * rise, 0.0])
        closed_px = px + [px[0]]
        closed_pz = pz + [pz[0]]
        for y_val in [0.0, w]:
            fig.add_trace(
                go.Scatter3d(
                    x=closed_px,
                    y=[y_val] * len(closed_px),
                    z=closed_pz,
                    mode="lines",
                    line=dict(color="#334155", width=5),
                    showlegend=False,
                )
            )
        for x_v, z_v in zip(px, pz):
            fig.add_trace(
                go.Scatter3d(
                    x=[x_v, x_v],
                    y=[0.0, w],
                    z=[z_v, z_v],
                    mode="lines",
                    line=dict(color="#475569", width=4),
                    showlegend=False,
                )
            )