"""
UI strings (English only)
"""

T = {
    "title": "Urban Field Gen",
    "subtitle": "V.1.0 LINE-DRIVEN ENGINE",
    "section_run_mode": "RUN MODE & SITE",
    "section_field_logic": "FIELD LOGIC",
    "section_seed_line": "SEED LINE",
    "section_multi_seed": "MULTI SEED LINES",
    "section_curve_params": "CURVE VECTOR PARAMS",
    "section_expansion": "EXPANSION PARAMETERS",
    "section_noise": "NOISE & DISTORTION",
    "section_street": "STREET & PARCEL (B/C)",
    "run_mode": "Run Mode",
    "site_width": "Site Width",
    "site_height": "Site Height",
    "engine": "Engine",
    "field_type": "Field Type",
    "seed_type": "Seed Line Type",
    "seed_rotation": "Seed Rotation",
    "seed_x_offset": "Seed X Offset",
    "seed_y_offset": "Seed Y Offset",
    "seed_length": "Seed Length",
    "sine_amplitude": "Sine Amplitude",
    "arc_curvature": "Arc Curvature",
    "line_spacing": "Line Spacing",
    "pos_count": "Pos. Count",
    "neg_count": "Neg. Count",
    "spacing_mode": "Spacing Mode",
    "spacing_scale": "Spacing Scale",
    "noise_scale": "Noise Scale",
    "noise_strength": "Noise Strength",
    "cross_spacing": "Cross Road Spacing",
    "parcel_min": "Min Frontage",
    "parcel_max": "Max Frontage",
    "parcel_min_area": "Min Area",
    "parcel_max_depth": "Max Depth",
    "parcel_depth": "Parcel Depth Offset",
    "export_rhino": "Export for Rhino",
    "export_py": "Export .py (RhinoScript)",
    "export_dxf": "Export DXF",
    "footer": "Non-Radial Field Generator\nUrban Morphology Study Tool",
    "status_default": "COORD_SYSTEM: CARTESIAN\nEXPANSION_VECTOR: LINE_LOCAL_NORMAL\nSTATUS: REALTIME_CALCULATION",
}

RUN_MODE_OPTS = [
    "A - Flow Lines",
    "B - Street Network",
    "C - Parcel Blocks",
]
ENGINE_OPTS = [
    "A. Offset",
    "B. Blended",
    "C. Scalar+Streamline",
]
FIELD_TYPE_OPTS = [
    "1. Parallel Offset",
    "2. Curve Tangent",
    "3. Curve Normal",
    "4. Distance Contour",
    "5. Strip Growth",
    "6. Hybrid Tangent-Normal",
    "7. Noise-Modified Line Field",
]
SEED_TYPE_OPTS = [
    "Straight Line",
    "Sine Wave",
    "Arc / Curve",
    "Custom (Hand-drawn)",
]
SPACING_MODE_OPTS = [
    "Linear",
    "Exponential Expansion",
    "Fibonacci Series",
]
CURVE_SPACING_MODES = {"Linear": "linear", "Exponential Expansion": "exponential", "Fibonacci Series": "fibonacci"}
INTEGRATE_METHOD_OPTS = ["Euler", "RK4"]

BTN_ADD_CURVE = "+ Add Curve"
BTN_DRAW = "Draw / Edit"
BTN_DONE_DRAWING = "Done Drawing"
BTN_CLEAR = "Clear All"
BTN_RESET = "Reset"
BTN_GENERATE = "Generate"
BTN_PARAMS = "Params"
BTN_EDIT = "Edit"
BTN_DEL = "Del"

BLEND_PARAMS_TITLE = "Blended Params"
BLEND_TANGENT = "Tangent Weight"
BLEND_NORMAL = "Normal Weight"
BLEND_DECAY = "Distance Decay"
BLEND_RADIUS = "Decay Radius"
BLEND_HINT = "Select Custom and add multiple curves"

SCALAR_PARAMS_TITLE = "Scalar Streamline Params"
SCALAR_METHOD = "Integration Method"
SCALAR_STEP = "Step Size"
SCALAR_COUNT = "Streamline Count"
SCALAR_CENTER_X = "Land Price Center X"
SCALAR_CENTER_Y = "Land Price Center Y"
SCALAR_SIGMA = "Land Price Spread σ"

OFFSET_HINT = "Use Field Type below for offset mode"

MULTI_SEED_HINT = "Select Custom to add multiple curves, each can be hand-drawn"
CURVE_PARAMS_HINT = "Select a curve in list to adjust its vector params"
CURVE_SELECT_HINT = "(Click Params in list to select curve)"


def curve_n_params(n):
    return f"Curve {n} Vector Params"


def curve_n_pts(i, n):
    return f"Curve {i} ({n} pts)"


LINE_SPACING_SHORT = "Line Spacing"
POS_NEG = "Pos. / Neg."
OFFSET_XY = "Offset X/Y"
SPACING_MODE_SHORT = "Spacing Mode"
SPACING_SCALE_SHORT = "Spacing Scale"
CROSS_SPACING_SHORT = "Road Density"

NOISE_ENABLED = "Enable Noise Distortion"
ROADS_PERP = "Roads ⊥ Vector Lines"
ROAD_HIERARCHY = "Road Hierarchy (Primary/Secondary/Local)"
ADAPTIVE_CROSS = "Adaptive Cross Streets"
CURVATURE_WEIGHT = "Curvature Weight"
ATTRACTOR_WEIGHT = "Attractor Weight"
VALUE_WEIGHT = "Value Weight"

PARCEL_FRONTAGE_BASED = "Frontage-based Subdivision"
PARCEL_BLOCK_BY_BLOCK = "Block-by-Block"
PARCEL_CORNER_SEPARATE = "Corner Parcels Separate"
PARCEL_PERTURBATION = "Irregular Perturbation"
PARCEL_PERTURBATION_STR = "Perturbation Strength"

NO_CURVES_YET = "(No curves yet. Click + Add Curve)"
DRAW_MODE_STATUS = "DRAW MODE: Curve {} - Click to add points, drag to move"
