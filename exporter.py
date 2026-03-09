"""
导出逻辑：RhinoScript (.py)、DXF
"""

from tkinter import filedialog

from geom import clip_polyline_to_rect, clip_polygon_to_rect


def get_clipped_geometry(export_geometry, site_width, site_height):
    """以场地矩形为边界裁剪几何体"""
    xmin, ymin = 0, 0
    xmax, ymax = site_width, site_height
    polylines = []
    for pts in export_geometry["polylines"]:
        polylines.extend(clip_polyline_to_rect(pts, xmin, ymin, xmax, ymax))
    parcels = []
    for pts in export_geometry["parcels"]:
        parcels.extend(clip_polygon_to_rect(pts, xmin, ymin, xmax, ymax))
    return {"polylines": polylines, "parcels": parcels}


def export_rhino(export_geometry, site_width, site_height, status_callback=None):
    """导出 RhinoScript (.py)"""
    if not export_geometry["polylines"] and not export_geometry["parcels"]:
        if status_callback:
            status_callback("No geometry to export. Generate first.")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".py",
        filetypes=[("Python script", "*.py"), ("All files", "*.*")],
        title="Export for Rhino"
    )
    if not path:
        return
    geo = get_clipped_geometry(export_geometry, site_width, site_height)
    if not geo["polylines"] and not geo["parcels"]:
        if status_callback:
            status_callback("No geometry inside boundary after clip.")
        return
    lines = []
    lines.append('"""Strip Field Export - Run in Rhino Python Editor (EditPythonScript)"""')
    lines.append("import rhinoscriptsyntax as rs")
    lines.append("")
    lines.append("# Clipped to site boundary rectangle")
    lines.append("")
    for pts in geo["polylines"]:
        if len(pts) < 2:
            continue
        pts_str = ", ".join(f"({p[0]:.4f}, {p[1]:.4f}, 0)" for p in pts)
        lines.append(f"rs.AddCurve([{pts_str}])")
    for pts in geo["parcels"]:
        if len(pts) < 3:
            continue
        closed_pts = pts + [pts[0]]
        pts_str = ", ".join(f"({p[0]:.4f}, {p[1]:.4f}, 0)" for p in closed_pts)
        lines.append(f"rs.AddCurve([{pts_str}], 1)  # parcel (closed)")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        if status_callback:
            status_callback(f"Exported to {path}")
    except Exception as e:
        if status_callback:
            status_callback(f"Export failed: {e}")


def export_dxf(export_geometry, site_width, site_height, status_callback=None):
    """导出 DXF"""
    if not export_geometry["polylines"] and not export_geometry["parcels"]:
        if status_callback:
            status_callback("No geometry to export. Generate first.")
        return
    try:
        import ezdxf
    except ImportError:
        if status_callback:
            status_callback("DXF export requires: pip install ezdxf")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".dxf",
        filetypes=[("DXF file", "*.dxf"), ("All files", "*.*")],
        title="Export DXF"
    )
    if not path:
        return
    geo = get_clipped_geometry(export_geometry, site_width, site_height)
    if not geo["polylines"] and not geo["parcels"]:
        if status_callback:
            status_callback("No geometry inside boundary after clip.")
        return
    try:
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        for pts in geo["polylines"]:
            if len(pts) < 2:
                continue
            msp.add_lwpolyline([(p[0], p[1]) for p in pts])
        for pts in geo["parcels"]:
            if len(pts) < 3:
                continue
            msp.add_lwpolyline([(p[0], p[1]) for p in pts], close=True)
        doc.saveas(path)
        if status_callback:
            status_callback(f"Exported to {path}")
    except Exception as e:
        if status_callback:
            status_callback(f"Export failed: {e}")
