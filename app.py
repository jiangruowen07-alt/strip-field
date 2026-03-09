"""
城市线驱动向量场生成器 - 主应用
基于 Seed Curve 的非中心式扩张
"""

import tkinter as tk
from tkinter import ttk, filedialog
import math
import random

from config import T_COUNT, T_STEP, DRAW_PADDING
from utils import safe_float, safe_int
from curve import sample_curve
from field_generator import (
    precompute_parametric_arrays,
    precompute_custom_curve_arrays,
    generate_lines_from_arrays,
    OffsetFieldEngine,
    BlendedFieldEngine,
    ScalarFieldEngine,
    StreamlineIntegrator,
)
from engines.scalar_field_engine import default_land_price_field
from exporter import export_rhino, export_dxf
from geom import split_segment_inside_outside
from street_network import (
    adaptive_cross_t_positions,
    classify_longitudinal_hierarchy,
    get_line_at_t,
    hierarchy_style,
    ROAD_PRIMARY,
    ROAD_SECONDARY,
    ROAD_LOCAL,
)
from i18n import T, RUN_MODE_OPTS, ENGINE_OPTS, FIELD_TYPE_OPTS, SEED_TYPE_OPTS, SPACING_MODE_OPTS
from i18n import INTEGRATE_METHOD_OPTS, BTN_ADD_CURVE, BTN_DRAW, BTN_DONE_DRAWING, BTN_CLEAR, BTN_RESET, BTN_GENERATE
from i18n import BTN_PARAMS, BTN_EDIT, BTN_DEL, BLEND_PARAMS_TITLE, BLEND_TANGENT, BLEND_NORMAL, BLEND_DECAY
from i18n import BLEND_RADIUS, BLEND_HINT, SCALAR_PARAMS_TITLE, SCALAR_METHOD, SCALAR_STEP, SCALAR_COUNT
from i18n import SCALAR_CENTER_X, SCALAR_CENTER_Y, SCALAR_SIGMA, OFFSET_HINT, MULTI_SEED_HINT, CURVE_PARAMS_HINT
from i18n import CURVE_SELECT_HINT, LINE_SPACING_SHORT, POS_NEG, OFFSET_XY, SPACING_MODE_SHORT
from i18n import SPACING_SCALE_SHORT, CROSS_SPACING_SHORT, NOISE_ENABLED, ROADS_PERP, NO_CURVES_YET
from i18n import ROAD_HIERARCHY, ADAPTIVE_CROSS, CURVATURE_WEIGHT, ATTRACTOR_WEIGHT, VALUE_WEIGHT
from i18n import PARCEL_FRONTAGE_BASED, PARCEL_BLOCK_BY_BLOCK, PARCEL_CORNER_SEPARATE, PARCEL_PERTURBATION
from i18n import PARCEL_PERTURBATION_STR, DRAW_MODE_STATUS, CURVE_SPACING_MODES, SEED_TYPE_OPTS, curve_n_params, curve_n_pts
from parcel_subdivision import subdivide_blocks, rule_based_parcels


class UrbanFieldGenerator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(T["title"])
        self.root.configure(bg="#0a0a0a")
        self.root.geometry("1400x900")

        self.state = {}
        self.controls = {}
        self.custom_seed_curves = []
        self.selected_curve_for_params = -1
        self.editing_curve_index = -1
        self.draw_mode = False
        self.drag_curve_idx = None
        self.drag_point_idx = None
        self._canvas_custom_bound = False
        self._curve_list_frame = None
        self._export_geometry = {"polylines": [], "parcels": []}
        self._generate_after_id = None
        self._debounce_ms = 120

        self._build_ui()
        self._bind_events()
        self._on_engine_change()
        self.update_state()

    def _build_ui(self):
        main_frame = tk.Frame(self.root, bg="#0a0a0a")
        main_frame.pack(fill=tk.BOTH, expand=True)

        panel_outer = tk.Frame(main_frame, width=400, bg="#141414")
        panel_outer.pack(side=tk.LEFT, fill=tk.Y)
        panel_outer.pack_propagate(False)

        panel_canvas = tk.Canvas(panel_outer, bg="#141414", highlightthickness=0)
        panel_scrollbar = ttk.Scrollbar(panel_outer, orient=tk.VERTICAL, command=panel_canvas.yview)
        panel = tk.Frame(panel_canvas, bg="#141414", padx=24, pady=24)
        panel_window = panel_canvas.create_window((0, 0), window=panel, anchor="nw")
        panel_canvas.configure(yscrollcommand=panel_scrollbar.set)
        panel_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        panel_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_panel_configure(event):
            panel_canvas.configure(scrollregion=panel_canvas.bbox("all"))

        def _on_canvas_configure(event):
            panel_canvas.itemconfig(panel_window, width=event.width)

        def _on_mousewheel(event):
            panel_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        panel.bind("<Configure>", _on_panel_configure)
        panel_canvas.bind("<Configure>", _on_canvas_configure)

        def _bind_mousewheel(event):
            panel_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            panel_canvas.unbind_all("<MouseWheel>")

        panel_canvas.bind("<Enter>", _bind_mousewheel)
        panel_canvas.bind("<Leave>", _unbind_mousewheel)

        tk.Label(panel, text=T["title"], font=("Inter", 18, "bold"),
                 fg="#ffffff", bg="#141414", wraplength=350, justify=tk.LEFT).pack(anchor="w")
        tk.Label(panel, text=T["subtitle"], font=("JetBrains Mono", 9),
                 fg="#888888", bg="#141414", wraplength=350, justify=tk.LEFT).pack(anchor="w")

        self._section_title(panel, T["section_run_mode"], wraplength=350)
        self._label_group(panel, T["run_mode"])
        self.controls["runMode"] = ttk.Combobox(panel, values=RUN_MODE_OPTS, state="readonly", width=36)
        self.controls["runMode"].set(RUN_MODE_OPTS[1])
        self.controls["runMode"].pack(fill=tk.X, pady=(0, 10))

        self._label_group(panel, T["site_width"])
        self.controls["siteWidth"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                             insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["siteWidth"].insert(0, "1200")
        self.controls["siteWidth"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, T["site_height"])
        self.controls["siteHeight"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                               insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["siteHeight"].insert(0, "200")
        self.controls["siteHeight"].pack(fill=tk.X, pady=(0, 10))

        self._section_title(panel, T["section_field_logic"])
        self._label_group(panel, T["engine"])
        self.controls["engine"] = ttk.Combobox(panel, values=ENGINE_OPTS, state="readonly", width=36)
        self.controls["engine"].set(ENGINE_OPTS[0])
        self.controls["engine"].pack(fill=tk.X, pady=(0, 8))
        self.controls["engine"].bind("<<ComboboxSelected>>", lambda e: self._on_engine_change())

        self._engine_params_frame = tk.Frame(panel, bg="#141414")
        self._engine_params_frame.pack(fill=tk.X, pady=(0, 8))

        self._label_group(panel, T["field_type"])
        self.controls["fieldType"] = ttk.Combobox(panel, values=FIELD_TYPE_OPTS, state="readonly", width=36)
        self.controls["fieldType"].set(FIELD_TYPE_OPTS[0])
        self.controls["fieldType"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, T["seed_type"])
        self.controls["seedType"] = ttk.Combobox(panel, values=SEED_TYPE_OPTS, state="readonly", width=36)
        self.controls["seedType"].set(SEED_TYPE_OPTS[0])
        self.controls["seedType"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, T["seed_rotation"], "0°", right_key="rotVal")
        self.controls["seedRotation"] = tk.Scale(panel, from_=0, to=360, orient=tk.HORIZONTAL,
                                                  bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                  highlightthickness=0, showvalue=False)
        self.controls["seedRotation"].set(0)
        self.controls["seedRotation"].pack(fill=tk.X, pady=(0, 16))

        self._section_title(panel, T["section_seed_line"])
        self._label_group(panel, T["seed_x_offset"], "0", right_key="seedXVal")
        self.controls["seedXOffset"] = tk.Scale(panel, from_=-500, to=500, orient=tk.HORIZONTAL,
                                                bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                highlightthickness=0, showvalue=False)
        self.controls["seedXOffset"].set(0)
        self.controls["seedXOffset"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, T["seed_y_offset"], "0", right_key="seedYVal")
        self.controls["seedYOffset"] = tk.Scale(panel, from_=-200, to=200, orient=tk.HORIZONTAL,
                                                bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                highlightthickness=0, showvalue=False)
        self.controls["seedYOffset"].set(0)
        self.controls["seedYOffset"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, T["seed_length"], "0.8", right_key="seedLenVal")
        self.controls["seedLength"] = tk.Scale(panel, from_=0.2, to=1.0, resolution=0.05, orient=tk.HORIZONTAL,
                                               bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                               highlightthickness=0, showvalue=False)
        self.controls["seedLength"].set(0.8)
        self.controls["seedLength"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, T["sine_amplitude"])
        self.controls["seedSineAmp"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                                insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["seedSineAmp"].insert(0, "50")
        self.controls["seedSineAmp"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, T["arc_curvature"])
        self.controls["seedArcCurv"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                                insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["seedArcCurv"].insert(0, "200")
        self.controls["seedArcCurv"].pack(fill=tk.X, pady=(0, 8))

        self._section_title(panel, T["section_multi_seed"])
        tk.Label(panel, text=MULTI_SEED_HINT, fg="#666666", bg="#141414",
                 font=("Inter", 9), wraplength=350, justify=tk.LEFT).pack(anchor="w", pady=(0, 8))
        self._curve_list_frame = tk.Frame(panel, bg="#141414")
        self._curve_list_frame.pack(fill=tk.X, pady=(0, 8))
        draw_btn_frame = tk.Frame(panel, bg="#141414")
        draw_btn_frame.pack(fill=tk.X, pady=(0, 8))
        self.controls["btnAddCurve"] = tk.Button(draw_btn_frame, text=BTN_ADD_CURVE, command=self._add_new_curve,
                                                 bg="#2a4a2a", fg="#e0e0e0", relief=tk.SOLID, bd=1,
                                                 font=("JetBrains Mono", 10))
        self.controls["btnAddCurve"].pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.controls["btnDraw"] = tk.Button(draw_btn_frame, text=BTN_DRAW, command=self._toggle_draw_mode,
                                             bg="#2a2a2a", fg="#e0e0e0", relief=tk.SOLID, bd=1,
                                             font=("JetBrains Mono", 10))
        self.controls["btnDraw"].pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))
        self.controls["btnClear"] = tk.Button(draw_btn_frame, text=BTN_CLEAR, command=self._clear_all_curves,
                                              bg="#1a1a1a", fg="#e0e0e0", relief=tk.SOLID, bd=1,
                                              font=("JetBrains Mono", 10))
        self.controls["btnClear"].pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        self._section_title(panel, T["section_curve_params"])
        self._curve_params_frame = tk.Frame(panel, bg="#141414")
        self._curve_params_frame.pack(fill=tk.X, pady=(0, 8))
        tk.Label(self._curve_params_frame, text=CURVE_PARAMS_HINT, fg="#666666", bg="#141414",
                 font=("Inter", 9), wraplength=350, justify=tk.LEFT).pack(anchor="w", pady=(0, 8))
        self._curve_params_inner = tk.Frame(self._curve_params_frame, bg="#141414")
        self._curve_params_inner.pack(fill=tk.X)

        self._section_title(panel, T["section_expansion"])
        self._label_group(panel, T["line_spacing"], "40", right_key="spacingVal")
        self.controls["lineSpacing"] = tk.Scale(panel, from_=10, to=100, orient=tk.HORIZONTAL,
                                                bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                highlightthickness=0, showvalue=False)
        self.controls["lineSpacing"].set(40)
        self.controls["lineSpacing"].pack(fill=tk.X, pady=(0, 10))

        self._label_group(panel, T["pos_count"])
        self.controls["posCount"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                             insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["posCount"].insert(0, "10")
        self.controls["posCount"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, T["neg_count"])
        self.controls["negCount"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                             insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["negCount"].insert(0, "10")
        self.controls["negCount"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, T["spacing_mode"])
        self.controls["spacingMode"] = ttk.Combobox(panel, values=SPACING_MODE_OPTS, state="readonly", width=36)
        self.controls["spacingMode"].set(SPACING_MODE_OPTS[0])
        self.controls["spacingMode"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, T["spacing_scale"], "1.0", right_key="scaleVal")
        self.controls["spacingScale"] = tk.Scale(panel, from_=0.5, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
                                                 bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                 highlightthickness=0, showvalue=False)
        self.controls["spacingScale"].set(1.0)
        self.controls["spacingScale"].pack(fill=tk.X, pady=(0, 14))

        self._section_title(panel, T["section_noise"])
        self.controls["noiseEnabled"] = tk.BooleanVar(value=False)
        noise_cb = tk.Checkbutton(panel, text=NOISE_ENABLED, variable=self.controls["noiseEnabled"],
                                  command=self.update_state,
                                  bg="#141414", fg="#e0e0e0", selectcolor="#1a1a1a", activebackground="#141414",
                                  activeforeground="#e0e0e0", wraplength=350, justify=tk.LEFT)
        noise_cb.pack(anchor="w", pady=(0, 8))

        self._label_group(panel, T["noise_scale"], "0.005", right_key="noiseScaleVal")
        self.controls["noiseScale"] = tk.Scale(panel, from_=0.001, to=0.02, resolution=0.001, orient=tk.HORIZONTAL,
                                               bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                               highlightthickness=0, showvalue=False)
        self.controls["noiseScale"].set(0.005)
        self.controls["noiseScale"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, T["noise_strength"], "20", right_key="noiseStrVal")
        self.controls["noiseStrength"] = tk.Scale(panel, from_=0, to=100, orient=tk.HORIZONTAL,
                                                  bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                  highlightthickness=0, showvalue=False)
        self.controls["noiseStrength"].set(20)
        self.controls["noiseStrength"].pack(fill=tk.X, pady=(0, 12))

        self._section_title(panel, T["section_street"])
        cb_row = tk.Frame(panel, bg="#141414")
        cb_row.pack(fill=tk.X, pady=(0, 4))
        self.controls["roadsPerpendicular"] = tk.BooleanVar(value=True)
        tk.Checkbutton(cb_row, text="⊥", variable=self.controls["roadsPerpendicular"], command=self.update_state,
                      bg="#141414", fg="#e0e0e0", selectcolor="#1a1a1a", activebackground="#141414",
                      activeforeground="#e0e0e0", font=("Inter", 9)).pack(side=tk.LEFT, padx=(0, 8))
        self.controls["roadHierarchy"] = tk.BooleanVar(value=True)
        tk.Checkbutton(cb_row, text="Hierarchy", variable=self.controls["roadHierarchy"], command=self.update_state,
                      bg="#141414", fg="#e0e0e0", selectcolor="#1a1a1a", activebackground="#141414",
                      activeforeground="#e0e0e0", font=("Inter", 9)).pack(side=tk.LEFT, padx=(0, 8))
        self.controls["adaptiveCross"] = tk.BooleanVar(value=True)
        tk.Checkbutton(cb_row, text="Adaptive", variable=self.controls["adaptiveCross"], command=self.update_state,
                      bg="#141414", fg="#e0e0e0", selectcolor="#1a1a1a", activebackground="#141414",
                      activeforeground="#e0e0e0", font=("Inter", 9)).pack(side=tk.LEFT)
        self._label_group(panel, T["cross_spacing"], "80", right_key="crossVal")
        self.controls["crossSpacing"] = tk.Scale(panel, from_=40, to=300, orient=tk.HORIZONTAL,
                                                 bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                 highlightthickness=0, showvalue=False)
        self.controls["crossSpacing"].set(80)
        self.controls["crossSpacing"].pack(fill=tk.X, pady=(0, 4))
        adapt_row = tk.Frame(panel, bg="#141414")
        adapt_row.pack(fill=tk.X, pady=(0, 8))
        adapt_row.columnconfigure((0, 1, 2), weight=1)
        for col, (key, lbl, default) in enumerate([
            ("curvatureWeight", "Curv", 0.4), ("attractorWeight", "Attr", 0.3), ("valueWeight", "Value", 0.2)
        ]):
            f = tk.Frame(adapt_row, bg="#141414")
            f.grid(row=0, column=col, sticky="ew", padx=2)
            tk.Label(f, text=lbl, fg="#666", bg="#141414", font=("Inter", 8)).pack(anchor="w")
            s = tk.Scale(f, from_=0, to=1, resolution=0.1, orient=tk.HORIZONTAL,
                        bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a", highlightthickness=0, showvalue=False,
                        command=lambda v, k=key: self._update_adaptive_labels())
            s.set(default)
            s.pack(fill=tk.X)
            self.controls[key] = s
            val_key = {"curvatureWeight": "curvWeightVal", "attractorWeight": "attrWeightVal", "valueWeight": "valWeightVal"}[key]
            vl = tk.Label(f, text=str(default), fg="#888", bg="#141414", font=("Inter", 8))
            vl.pack(anchor="e")
            self.controls[val_key] = vl

        self._label_group(panel, T["parcel_min"])
        self.controls["pMin"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                         insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["pMin"].insert(0, "15")
        self.controls["pMin"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, T["parcel_max"])
        self.controls["pMax"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                         insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["pMax"].insert(0, "45")
        self.controls["pMax"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, T["parcel_min_area"])
        self.controls["pMinArea"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                             insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["pMinArea"].insert(0, "50")
        self.controls["pMinArea"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, T["parcel_max_depth"])
        self.controls["pMaxDepth"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                              insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["pMaxDepth"].insert(0, "200")
        self.controls["pMaxDepth"].pack(fill=tk.X, pady=(0, 8))

        parcel_cb_frame = tk.Frame(panel, bg="#141414")
        parcel_cb_frame.pack(fill=tk.X, pady=(0, 4))
        parcel_cb_frame.columnconfigure((0, 1), weight=1)
        for row, col, (key, lbl) in [
            (0, 0, ("parcelFrontageBased", "Frontage")), (0, 1, ("parcelBlockByBlock", "Block")),
            (1, 0, ("parcelCornerSeparate", "Corner")), (1, 1, ("parcelPerturbation", "Perturb"))
        ]:
            self.controls[key] = tk.BooleanVar(value=(key != "parcelPerturbation"))
            tk.Checkbutton(parcel_cb_frame, text=lbl, variable=self.controls[key], command=self.update_state,
                          bg="#141414", fg="#e0e0e0", selectcolor="#1a1a1a", activebackground="#141414",
                          activeforeground="#e0e0e0", font=("Inter", 9)).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=2)
        self._label_group(panel, PARCEL_PERTURBATION_STR, "0.02", right_key="pertStrVal")
        self.controls["parcelPerturbationStr"] = tk.Scale(panel, from_=0, to=0.1, resolution=0.005,
                                                        orient=tk.HORIZONTAL, bg="#141414", fg="#e0e0e0",
                                                        troughcolor="#2a2a2a", highlightthickness=0, showvalue=False,
                                                        command=lambda v: self.update_state())
        self.controls["parcelPerturbationStr"].set(0.02)
        self.controls["parcelPerturbationStr"].pack(fill=tk.X, pady=(0, 16))

        btn_frame = tk.Frame(panel, bg="#141414")
        btn_frame.pack(fill=tk.X)
        btn_reset = tk.Button(btn_frame, text=BTN_RESET, command=self._reset,
                             bg="#1a1a1a", fg="#e0e0e0", relief=tk.SOLID, bd=1,
                             font=("JetBrains Mono", 10),
                             activebackground="#ffffff", activeforeground="#0a0a0a")
        btn_reset.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        btn_gen = tk.Button(btn_frame, text=BTN_GENERATE, command=self.generate,
                           bg="#ffffff", fg="#0a0a0a", relief=tk.SOLID, bd=1,
                           font=("JetBrains Mono", 10, "bold"),
                           activebackground="#ffffff", activeforeground="#0a0a0a")
        btn_gen.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        export_frame = tk.Frame(panel, bg="#141414")
        export_frame.pack(fill=tk.X, pady=(16, 0))
        tk.Label(export_frame, text=T["export_rhino"], fg="#888888", bg="#141414",
                 font=("Inter", 10), wraplength=350, justify=tk.LEFT).pack(anchor="w")
        exp_btn_frame = tk.Frame(export_frame, bg="#141414")
        exp_btn_frame.pack(fill=tk.X, pady=(4, 0))
        btn_export_rhino = tk.Button(exp_btn_frame, text=T["export_py"], command=self._export_rhino,
                                    bg="#2a4a6a", fg="#e0e0e0", relief=tk.SOLID, bd=1,
                                    font=("JetBrains Mono", 10))
        btn_export_rhino.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        btn_export_dxf = tk.Button(exp_btn_frame, text=T["export_dxf"], command=self._export_dxf,
                                  bg="#2a4a6a", fg="#e0e0e0", relief=tk.SOLID, bd=1,
                                  font=("JetBrains Mono", 10))
        btn_export_dxf.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        tk.Label(panel, text=T["footer"],
                 fg="#888888", bg="#141414", font=("Inter", 9), wraplength=350, justify=tk.LEFT).pack(pady=(32, 0))

        canvas_frame = tk.Frame(main_frame, bg="#050505")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=32, pady=32)
        self.canvas = tk.Canvas(canvas_frame, bg="#050505", highlightthickness=0)
        self.canvas.pack(expand=True)
        self.status_label = tk.Label(canvas_frame, text=T["status_default"],
                                    fg="#4d4d4d", bg="#050505", font=("JetBrains Mono", 9),
                                    justify=tk.RIGHT, wraplength=280)
        self.status_label.place(relx=1.0, rely=1.0, anchor="se", x=-32, y=-32)

    def _section_title(self, parent, text, wraplength=350):
        tk.Label(parent, text=text, font=("Inter", 11, "bold"), fg="#ffffff", bg="#141414",
                 wraplength=wraplength, justify=tk.LEFT).pack(anchor="w", pady=(14, 4))

    def _label_group(self, parent, left, right=None, right_key=None):
        frame = tk.Frame(parent, bg="#141414")
        frame.pack(fill=tk.X)
        left_lbl = tk.Label(frame, text=left, fg="#888888", bg="#141414", font=("Inter", 10), wraplength=320, justify=tk.LEFT)
        left_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        if right_key:
            lbl = tk.Label(frame, text=right or "", fg="#888888", bg="#141414", font=("Inter", 10))
            lbl.pack(side=tk.RIGHT)
            self.controls[right_key] = lbl
        elif right is not None:
            tk.Label(frame, text=right, fg="#888888", bg="#141414", font=("Inter", 10)).pack(side=tk.RIGHT)

    def _get_run_mode(self):
        val = self.controls["runMode"].get()
        if "A" in val or "Flow" in val:
            return "A"
        if "C" in val or "Parcel" in val:
            return "C"
        return "B"

    def _get_engine(self):
        val = self.controls["engine"].get()
        if "B" in val or "Blended" in val:
            return "blended"
        if "C" in val or "Scalar" in val:
            return "scalar"
        return "offset"

    def _on_engine_change(self):
        """切换引擎时重建引擎专属参数区"""
        for w in self._engine_params_frame.winfo_children():
            w.destroy()
        eng = self._get_engine()
        if eng == "blended":
            tk.Label(self._engine_params_frame, text=BLEND_PARAMS_TITLE, fg="#e0e0e0", bg="#141414",
                     font=("Inter", 10, "bold")).pack(anchor="w", pady=(0, 4))
            self._label_group(self._engine_params_frame, BLEND_TANGENT, "0", right_key="blendTwVal")
            self.controls["blendTangentW"] = tk.Scale(self._engine_params_frame, from_=0, to=1, resolution=0.1,
                                                     orient=tk.HORIZONTAL, bg="#141414", fg="#e0e0e0",
                                                     troughcolor="#2a2a2a", highlightthickness=0, showvalue=False,
                                                     command=lambda v: self._update_blend_labels())
            self.controls["blendTangentW"].set(0)
            self.controls["blendTangentW"].pack(fill=tk.X, pady=(0, 4))
            self._label_group(self._engine_params_frame, BLEND_NORMAL, "1", right_key="blendNwVal")
            self.controls["blendNormalW"] = tk.Scale(self._engine_params_frame, from_=0, to=1, resolution=0.1,
                                                    orient=tk.HORIZONTAL, bg="#141414", fg="#e0e0e0",
                                                    troughcolor="#2a2a2a", highlightthickness=0, showvalue=False,
                                                    command=lambda v: self._update_blend_labels())
            self.controls["blendNormalW"].set(1)
            self.controls["blendNormalW"].pack(fill=tk.X, pady=(0, 4))
            self._label_group(self._engine_params_frame, BLEND_DECAY, "0", right_key="blendDecayVal")
            self.controls["blendDecay"] = tk.Scale(self._engine_params_frame, from_=0, to=3, resolution=0.1,
                                                  orient=tk.HORIZONTAL, bg="#141414", fg="#e0e0e0",
                                                  troughcolor="#2a2a2a", highlightthickness=0, showvalue=False,
                                                  command=lambda v: self._update_blend_labels())
            self.controls["blendDecay"].set(0)
            self.controls["blendDecay"].pack(fill=tk.X, pady=(0, 4))
            self._label_group(self._engine_params_frame, BLEND_RADIUS, "200", right_key="blendRadiusVal")
            self.controls["blendRadius"] = tk.Scale(self._engine_params_frame, from_=50, to=500, orient=tk.HORIZONTAL,
                                                  bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                  highlightthickness=0, showvalue=False,
                                                  command=lambda v: self._update_blend_labels())
            self.controls["blendRadius"].set(200)
            self.controls["blendRadius"].pack(fill=tk.X, pady=(0, 8))
            tk.Label(self._engine_params_frame, text=BLEND_HINT, fg="#666666", bg="#141414",
                     font=("Inter", 9), wraplength=350, justify=tk.LEFT).pack(anchor="w")
        elif eng == "scalar":
            tk.Label(self._engine_params_frame, text=SCALAR_PARAMS_TITLE, fg="#e0e0e0", bg="#141414",
                     font=("Inter", 10, "bold")).pack(anchor="w", pady=(0, 4))
            self._label_group(self._engine_params_frame, SCALAR_METHOD)
            self.controls["integrateMethod"] = ttk.Combobox(self._engine_params_frame,
                                                            values=INTEGRATE_METHOD_OPTS, state="readonly", width=12)
            self.controls["integrateMethod"].set(INTEGRATE_METHOD_OPTS[1])
            self.controls["integrateMethod"].pack(fill=tk.X, pady=(0, 4))
            self._label_group(self._engine_params_frame, SCALAR_STEP, "5", right_key="integrateStepVal")
            self.controls["integrateStep"] = tk.Scale(self._engine_params_frame, from_=1, to=20, orient=tk.HORIZONTAL,
                                                      bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                      highlightthickness=0, showvalue=False,
                                                      command=lambda v: self.update_state())
            self.controls["integrateStep"].set(5)
            self.controls["integrateStep"].pack(fill=tk.X, pady=(0, 4))
            self._label_group(self._engine_params_frame, SCALAR_COUNT, "12", right_key="scalarStreamCountVal")
            self.controls["scalarStreamCount"] = tk.Scale(self._engine_params_frame, from_=3, to=30, orient=tk.HORIZONTAL,
                                                          bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                          highlightthickness=0, showvalue=False,
                                                          command=lambda v: self.update_state())
            self.controls["scalarStreamCount"].set(12)
            self.controls["scalarStreamCount"].pack(fill=tk.X, pady=(0, 4))
            w_max = max(400, safe_float(self.controls["siteWidth"].get(), 1200))
            h_max = max(200, safe_float(self.controls["siteHeight"].get(), 200))
            self._label_group(self._engine_params_frame, SCALAR_CENTER_X, "600", right_key="scalarCxVal")
            self.controls["scalarCenterX"] = tk.Scale(self._engine_params_frame, from_=0, to=w_max, orient=tk.HORIZONTAL,
                                                      bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                      highlightthickness=0, showvalue=False,
                                                      command=lambda v: self.update_state())
            self.controls["scalarCenterX"].set(min(600, int(w_max * 0.5)))
            self.controls["scalarCenterX"].pack(fill=tk.X, pady=(0, 4))
            self._label_group(self._engine_params_frame, SCALAR_CENTER_Y, "100", right_key="scalarCyVal")
            self.controls["scalarCenterY"] = tk.Scale(self._engine_params_frame, from_=0, to=h_max, orient=tk.HORIZONTAL,
                                                      bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                      highlightthickness=0, showvalue=False,
                                                      command=lambda v: self.update_state())
            self.controls["scalarCenterY"].set(100)
            self.controls["scalarCenterY"].pack(fill=tk.X, pady=(0, 4))
            self._label_group(self._engine_params_frame, SCALAR_SIGMA, "200", right_key="scalarSigmaVal")
            self.controls["scalarSigma"] = tk.Scale(self._engine_params_frame, from_=50, to=400, orient=tk.HORIZONTAL,
                                                   bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                   highlightthickness=0, showvalue=False,
                                                   command=lambda v: self.update_state())
            self.controls["scalarSigma"].set(200)
            self.controls["scalarSigma"].pack(fill=tk.X, pady=(0, 8))
        else:
            tk.Label(self._engine_params_frame, text=OFFSET_HINT, fg="#666666", bg="#141414",
                     font=("Inter", 9), wraplength=350, justify=tk.LEFT).pack(anchor="w")
        self._bind_recursive(self._engine_params_frame, self.update_state)
        self.update_state()

    def _update_adaptive_labels(self):
        for k, ctrl in [("curvWeightVal", "curvatureWeight"), ("attrWeightVal", "attractorWeight"), ("valWeightVal", "valueWeight")]:
            if k in self.controls and ctrl in self.controls and self.controls[ctrl].winfo_exists():
                self.controls[k].config(text=f"{self.controls[ctrl].get():.1f}")
        self.update_state()

    def _update_blend_labels(self):
        if self._get_engine() != "blended":
            return
        if "blendTwVal" in self.controls and "blendTangentW" in self.controls:
            self.controls["blendTwVal"].config(text=f"{self.controls['blendTangentW'].get():.1f}")
        if "blendNwVal" in self.controls and "blendNormalW" in self.controls:
            self.controls["blendNwVal"].config(text=f"{self.controls['blendNormalW'].get():.1f}")
        if "blendDecayVal" in self.controls and "blendDecay" in self.controls:
            self.controls["blendDecayVal"].config(text=f"{self.controls['blendDecay'].get():.1f}")
        if "blendRadiusVal" in self.controls and "blendRadius" in self.controls:
            self.controls["blendRadiusVal"].config(text=str(int(self.controls["blendRadius"].get())))
        self.update_state()

    def _get_field_type(self):
        val = self.controls["fieldType"].get()
        return val[0] if val else "1"

    def _get_seed_type(self):
        val = self.controls["seedType"].get()
        if "Sine" in val:
            return "sine"
        if "Arc" in val:
            return "arc"
        if "Custom" in val or "Hand" in val:
            return "custom"
        return "straight"

    def _get_spacing_mode(self):
        val = self.controls["spacingMode"].get()
        if "Exponential" in val:
            return "exponential"
        if "Fibonacci" in val:
            return "fibonacci"
        return "linear"

    def _get_curve_params_defaults(self):
        return {
            "fieldType": self._get_field_type(),
            "lineSpacing": safe_float(self.controls["lineSpacing"].get(), 40),
            "posCount": safe_int(self.controls["posCount"].get(), 10),
            "negCount": safe_int(self.controls["negCount"].get(), 10),
            "spacingMode": self._get_spacing_mode(),
            "spacingScale": safe_float(self.controls["spacingScale"].get(), 1.0),
            "offsetX": 0,
            "offsetY": 0,
            "crossSpacing": safe_float(self.controls["crossSpacing"].get(), 80),
        }

    def _get_curve_points(self, curve):
        if isinstance(curve, dict):
            return curve["points"]
        return curve

    def _ensure_curve_dict(self, curve):
        if isinstance(curve, list):
            return {"points": curve, "params": self._get_curve_params_defaults()}
        return curve

    def _add_new_curve(self):
        self.controls["seedType"].set(SEED_TYPE_OPTS[3])
        self.custom_seed_curves.append({"points": [], "params": self._get_curve_params_defaults()})
        self.editing_curve_index = len(self.custom_seed_curves) - 1
        self.draw_mode = True
        self.controls["btnDraw"].config(text=BTN_DONE_DRAWING, bg="#3a5a3a")
        self.status_label.config(text=DRAW_MODE_STATUS.format(self.editing_curve_index + 1))
        self._refresh_curve_list()
        self.update_state()

    def _edit_curve(self, idx):
        if 0 <= idx < len(self.custom_seed_curves):
            self.controls["seedType"].set(SEED_TYPE_OPTS[3])
            self.editing_curve_index = idx
            self.draw_mode = True
            self.controls["btnDraw"].config(text=BTN_DONE_DRAWING, bg="#3a5a3a")
            self.status_label.config(text=DRAW_MODE_STATUS.format(idx + 1))
            self._refresh_curve_list()
            self.update_state()

    def _select_curve_params(self, idx):
        if 0 <= idx < len(self.custom_seed_curves):
            self.selected_curve_for_params = idx
            self._build_curve_params_ui()
            self.update_state()

    def _build_curve_params_ui(self):
        if not hasattr(self, "_curve_params_inner") or self._curve_params_inner is None:
            return
        for w in self._curve_params_inner.winfo_children():
            w.destroy()
        if self.selected_curve_for_params < 0 or self.selected_curve_for_params >= len(self.custom_seed_curves):
            tk.Label(self._curve_params_inner, text=CURVE_SELECT_HINT, fg="#555555", bg="#141414",
                     font=("Inter", 9), wraplength=350, justify=tk.LEFT).pack(anchor="w")
            return
        curve = self.custom_seed_curves[self.selected_curve_for_params]
        if isinstance(curve, list):
            return
        p = curve.setdefault("params", self._get_curve_params_defaults())
        idx = self.selected_curve_for_params

        def _on_change(key, val):
            p[key] = val
            self.update_state()

        tk.Label(self._curve_params_inner, text=curve_n_params(idx + 1), fg="#e0e0e0", bg="#141414",
                 font=("Inter", 10, "bold")).pack(anchor="w", pady=(0, 8))
        row_ft = tk.Frame(self._curve_params_inner, bg="#141414")
        row_ft.pack(fill=tk.X, pady=2)
        row_ft.columnconfigure(1, weight=1)
        tk.Label(row_ft, text=T["field_type"], fg="#888888", bg="#141414", font=("Inter", 9), wraplength=140, justify=tk.LEFT).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ft_combo = ttk.Combobox(row_ft, values=FIELD_TYPE_OPTS, state="readonly", width=28)
        ft_key = p.get("fieldType", self._get_field_type())
        ft_idx = max(0, min(int(ft_key) - 1 if ft_key.isdigit() else 0, len(FIELD_TYPE_OPTS) - 1))
        ft_combo.set(FIELD_TYPE_OPTS[ft_idx])
        ft_combo.grid(row=0, column=1, sticky="ew")
        def _on_ft_change(e=None):
            sel = ft_combo.get()
            idx = FIELD_TYPE_OPTS.index(sel) if sel in FIELD_TYPE_OPTS else 0
            _on_change("fieldType", str(idx + 1))
        ft_combo.bind("<<ComboboxSelected>>", _on_ft_change)
        row = tk.Frame(self._curve_params_inner, bg="#141414")
        row.pack(fill=tk.X, pady=2)
        row.columnconfigure(1, weight=1)
        tk.Label(row, text=LINE_SPACING_SHORT, fg="#888888", bg="#141414", font=("Inter", 9), wraplength=140, justify=tk.LEFT).grid(row=0, column=0, sticky="w", padx=(0, 8))
        sp = tk.Scale(row, from_=10, to=100, orient=tk.HORIZONTAL, bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                      highlightthickness=0, showvalue=False, command=lambda v: _on_change("lineSpacing", float(v)))
        sp.set(p.get("lineSpacing", 40))
        sp.grid(row=0, column=1, sticky="ew")
        tk.Label(row, text=str(int(p.get("lineSpacing", 40))), fg="#888888", bg="#141414", font=("Inter", 9)).grid(row=0, column=2, padx=(4, 0))
        row2 = tk.Frame(self._curve_params_inner, bg="#141414")
        row2.pack(fill=tk.X, pady=2)
        row2.columnconfigure(1, weight=1)
        tk.Label(row2, text=POS_NEG, fg="#888888", bg="#141414", font=("Inter", 9), wraplength=140, justify=tk.LEFT).grid(row=0, column=0, sticky="w", padx=(0, 8))
        pe = tk.Entry(row2, bg="#1a1a1a", fg="#e0e0e0", width=6)
        pe.insert(0, str(p.get("posCount", 10)))
        pe.grid(row=0, column=1, sticky="w", padx=(0, 4))
        ne = tk.Entry(row2, bg="#1a1a1a", fg="#e0e0e0", width=6)
        ne.insert(0, str(p.get("negCount", 10)))
        ne.grid(row=0, column=2, sticky="w")

        def _apply_counts():
            try:
                p["posCount"] = int(float(pe.get()))
                p["negCount"] = int(float(ne.get()))
                self.update_state()
            except Exception:
                pass

        pe.bind("<KeyRelease>", lambda e: _apply_counts())
        ne.bind("<KeyRelease>", lambda e: _apply_counts())
        row3 = tk.Frame(self._curve_params_inner, bg="#141414")
        row3.pack(fill=tk.X, pady=2)
        row3.columnconfigure(1, weight=1)
        tk.Label(row3, text=OFFSET_XY, fg="#888888", bg="#141414", font=("Inter", 9), wraplength=140, justify=tk.LEFT).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ox = tk.Scale(row3, from_=-100, to=100, orient=tk.HORIZONTAL, bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                      highlightthickness=0, showvalue=False, command=lambda v: _on_change("offsetX", float(v)))
        ox.set(p.get("offsetX", 0))
        ox.grid(row=0, column=1, sticky="ew", padx=(0, 4))
        oy = tk.Scale(row3, from_=-100, to=100, orient=tk.HORIZONTAL, bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                      highlightthickness=0, showvalue=False, command=lambda v: _on_change("offsetY", float(v)))
        oy.set(p.get("offsetY", 0))
        oy.grid(row=0, column=2, sticky="ew")
        row4a = tk.Frame(self._curve_params_inner, bg="#141414")
        row4a.pack(fill=tk.X, pady=2)
        row4a.columnconfigure(1, weight=1)
        tk.Label(row4a, text=SPACING_MODE_SHORT, fg="#888888", bg="#141414", font=("Inter", 9), wraplength=140, justify=tk.LEFT).grid(row=0, column=0, sticky="w", padx=(0, 8))
        _sm_map = CURVE_SPACING_MODES
        _sm_rev = {v: k for k, v in _sm_map.items()}
        sm_combo = ttk.Combobox(row4a, values=list(_sm_map.keys()), state="readonly", width=18)
        sm_combo.set(_sm_rev.get(p.get("spacingMode", "linear"), list(_sm_map.keys())[0]))
        sm_combo.grid(row=0, column=1, sticky="ew")
        sm_combo.bind("<<ComboboxSelected>>", lambda e: _on_change("spacingMode", _sm_map.get(sm_combo.get(), "linear")))
        row4 = tk.Frame(self._curve_params_inner, bg="#141414")
        row4.pack(fill=tk.X, pady=2)
        row4.columnconfigure(1, weight=1)
        tk.Label(row4, text=SPACING_SCALE_SHORT, fg="#888888", bg="#141414", font=("Inter", 9), wraplength=140, justify=tk.LEFT).grid(row=0, column=0, sticky="w", padx=(0, 8))
        sc = tk.Scale(row4, from_=0.5, to=2.0, resolution=0.1, orient=tk.HORIZONTAL, bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                      highlightthickness=0, showvalue=False, command=lambda v: _on_change("spacingScale", float(v)))
        sc.set(p.get("spacingScale", 1.0))
        sc.grid(row=0, column=1, sticky="ew", padx=(0, 4))
        tk.Label(row4, text=f"{p.get('spacingScale', 1.0):.1f}", fg="#888888", bg="#141414", font=("Inter", 9)).grid(row=0, column=2, padx=(4, 0))
        row5 = tk.Frame(self._curve_params_inner, bg="#141414")
        row5.pack(fill=tk.X, pady=2)
        row5.columnconfigure(1, weight=1)
        tk.Label(row5, text=CROSS_SPACING_SHORT, fg="#888888", bg="#141414", font=("Inter", 9), wraplength=140, justify=tk.LEFT).grid(row=0, column=0, sticky="w", padx=(0, 8))
        lbl_cross = tk.Label(row5, text=str(int(p.get("crossSpacing", 80))), fg="#888888", bg="#141414", font=("Inter", 9), width=4)

        def _on_cross(v):
            _on_change("crossSpacing", float(v))
            lbl_cross.config(text=str(int(float(v))))

        cross_sp = tk.Scale(row5, from_=20, to=300, orient=tk.HORIZONTAL, bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                           highlightthickness=0, showvalue=False, command=_on_cross)
        cross_sp.set(p.get("crossSpacing", 80))
        cross_sp.grid(row=0, column=1, sticky="ew", padx=(0, 4))
        lbl_cross.grid(row=0, column=2, padx=(4, 0))

    def _delete_curve(self, idx):
        if 0 <= idx < len(self.custom_seed_curves):
            del self.custom_seed_curves[idx]
            if self.selected_curve_for_params == idx:
                self.selected_curve_for_params = -1
                self._build_curve_params_ui()
            elif self.selected_curve_for_params > idx:
                self.selected_curve_for_params -= 1
            if self.editing_curve_index == idx:
                self.editing_curve_index = -1
                self.draw_mode = False
                self._exit_draw_mode()
            elif self.editing_curve_index > idx:
                self.editing_curve_index -= 1
            self._refresh_curve_list()
            self.update_state()

    def _refresh_curve_list(self):
        for i, curve in enumerate(self.custom_seed_curves):
            if isinstance(curve, list):
                self.custom_seed_curves[i] = {"points": curve, "params": self._get_curve_params_defaults()}
        for w in self._curve_list_frame.winfo_children():
            w.destroy()
        for i, curve in enumerate(self.custom_seed_curves):
            pts = self._get_curve_points(curve)
            n = len(pts)
            row = tk.Frame(self._curve_list_frame, bg="#141414")
            row.pack(fill=tk.X, pady=2)
            lbl = tk.Label(row, text=curve_n_pts(i + 1, n), fg="#888888", bg="#141414", font=("Inter", 10))
            lbl.pack(side=tk.LEFT)
            btn_params = tk.Button(row, text=BTN_PARAMS, command=lambda idx=i: self._select_curve_params(idx),
                                   bg="#2a3a4a", fg="#e0e0e0", relief=tk.SOLID, bd=1, font=("JetBrains Mono", 9))
            btn_params.pack(side=tk.RIGHT, padx=2)
            btn_edit = tk.Button(row, text=BTN_EDIT, command=lambda idx=i: self._edit_curve(idx),
                                 bg="#2a2a2a", fg="#e0e0e0", relief=tk.SOLID, bd=1, font=("JetBrains Mono", 9))
            btn_edit.pack(side=tk.RIGHT, padx=2)
            btn_del = tk.Button(row, text=BTN_DEL, command=lambda idx=i: self._delete_curve(idx),
                                bg="#4a2a2a", fg="#e0e0e0", relief=tk.SOLID, bd=1, font=("JetBrains Mono", 9))
            btn_del.pack(side=tk.RIGHT)
        if not self.custom_seed_curves:
            tk.Label(self._curve_list_frame, text=NO_CURVES_YET, fg="#555555", bg="#141414",
                     font=("Inter", 9), wraplength=350, justify=tk.LEFT).pack(anchor="w")

    def _toggle_draw_mode(self):
        if self.draw_mode:
            self._exit_draw_mode()
        else:
            if not self.custom_seed_curves:
                self._add_new_curve()
                return
            if self.editing_curve_index < 0:
                self.editing_curve_index = 0
            self.controls["seedType"].set(SEED_TYPE_OPTS[3])
            self.draw_mode = True
            self.controls["btnDraw"].config(text=BTN_DONE_DRAWING, bg="#3a5a3a")
            self.status_label.config(text=DRAW_MODE_STATUS.format(self.editing_curve_index + 1))
        self.update_state()

    def _exit_draw_mode(self):
        self.draw_mode = False
        self.editing_curve_index = -1
        self.controls["btnDraw"].config(text=BTN_DRAW, bg="#2a2a2a")
        self.status_label.config(text=T["status_default"])
        self._refresh_curve_list()

    def _find_point_at(self, canvas_x, canvas_y, radius=10):
        lx, ly = self._unpad(canvas_x, canvas_y)
        best_ci, best_pi, best_d = -1, -1, radius * radius
        for ci, curve in enumerate(self.custom_seed_curves):
            pts = self._get_curve_points(curve)
            for pi, (px, py) in enumerate(pts):
                d = (lx - px) ** 2 + (ly - py) ** 2
                if d < best_d:
                    best_d, best_ci, best_pi = d, ci, pi
        return (best_ci, best_pi)

    def _on_canvas_click(self, event):
        if self.state.get("seedType") != "custom":
            return
        ci, pi = self._find_point_at(event.x, event.y)
        if ci >= 0 and pi >= 0:
            self.drag_curve_idx = ci
            self.drag_point_idx = pi
        elif self.draw_mode and self.editing_curve_index >= 0 and self.editing_curve_index < len(self.custom_seed_curves):
            lx, ly = self._unpad(event.x, event.y)
            self._get_curve_points(self.custom_seed_curves[self.editing_curve_index]).append((lx, ly))
            self._refresh_curve_list()
            self.update_state()

    def _on_canvas_drag(self, event):
        if self.drag_curve_idx is not None and self.drag_point_idx is not None:
            pts = self._get_curve_points(self.custom_seed_curves[self.drag_curve_idx])
            if 0 <= self.drag_point_idx < len(pts):
                lx, ly = self._unpad(event.x, event.y)
                pts[self.drag_point_idx] = (lx, ly)
                self._refresh_curve_list()
                self.update_state()

    def _on_canvas_release(self, event):
        self.drag_curve_idx = None
        self.drag_point_idx = None

    def _clear_all_curves(self):
        self.custom_seed_curves.clear()
        self.editing_curve_index = -1
        if self.draw_mode:
            self._toggle_draw_mode()
        self._refresh_curve_list()
        self.update_state()

    def _generate_lines_for_curve(self, curve):
        points = self._get_curve_points(curve)
        arr = precompute_custom_curve_arrays(points)
        if arr is None:
            return []
        p = curve.get("params", self._get_curve_params_defaults()) if isinstance(curve, dict) else {}
        return generate_lines_from_arrays(arr, self.state, p)

    def update_state(self):
        self.state["runMode"] = self._get_run_mode()
        self.state["engine"] = self._get_engine()
        self.state["fieldType"] = self._get_field_type()
        self.state["siteWidth"] = safe_float(self.controls["siteWidth"].get(), 1200)
        self.state["siteHeight"] = safe_float(self.controls["siteHeight"].get(), 200)
        self.state["seedType"] = self._get_seed_type()
        self.state["seedRotation"] = safe_float(self.controls["seedRotation"].get(), 0)
        self.state["seedXOffset"] = safe_float(self.controls["seedXOffset"].get(), 0)
        self.state["seedYOffset"] = safe_float(self.controls["seedYOffset"].get(), 0)
        self.state["seedLength"] = safe_float(self.controls["seedLength"].get(), 0.8)
        self.state["seedSineAmp"] = safe_float(self.controls["seedSineAmp"].get(), 50)
        self.state["seedArcCurv"] = safe_float(self.controls["seedArcCurv"].get(), 200)
        self.state["lineSpacing"] = safe_float(self.controls["lineSpacing"].get(), 40)
        self.state["posCount"] = safe_int(self.controls["posCount"].get(), 10)
        self.state["negCount"] = safe_int(self.controls["negCount"].get(), 10)
        self.state["spacingMode"] = self._get_spacing_mode()
        self.state["spacingScale"] = safe_float(self.controls["spacingScale"].get(), 1.0)
        self.state["noiseEnabled"] = self.controls["noiseEnabled"].get()
        self.state["noiseScale"] = safe_float(self.controls["noiseScale"].get(), 0.005)
        self.state["noiseStrength"] = safe_float(self.controls["noiseStrength"].get(), 20)
        self.state["crossSpacing"] = safe_float(self.controls["crossSpacing"].get(), 80)
        self.state["roadsPerpendicular"] = self.controls["roadsPerpendicular"].get()
        self.state["roadHierarchy"] = self.controls["roadHierarchy"].get() if "roadHierarchy" in self.controls else True
        self.state["adaptiveCross"] = self.controls["adaptiveCross"].get() if "adaptiveCross" in self.controls else True
        self.state["curvatureWeight"] = safe_float(self.controls["curvatureWeight"].get(), 0.4) if "curvatureWeight" in self.controls else 0.4
        self.state["attractorWeight"] = safe_float(self.controls["attractorWeight"].get(), 0.3) if "attractorWeight" in self.controls else 0.3
        self.state["valueWeight"] = safe_float(self.controls["valueWeight"].get(), 0.2) if "valueWeight" in self.controls else 0.2
        self.state["pMin"] = safe_float(self.controls["pMin"].get(), 15)
        self.state["pMax"] = safe_float(self.controls["pMax"].get(), 45)
        self.state["pMinArea"] = safe_float(self.controls["pMinArea"].get(), 50) if "pMinArea" in self.controls else 50
        self.state["pMaxDepth"] = safe_float(self.controls["pMaxDepth"].get(), 200) if "pMaxDepth" in self.controls else 200
        self.state["pDepth"] = safe_float(self.controls["pDepth"].get(), 10) if "pDepth" in self.controls else 10
        self.state["parcelFrontageBased"] = self.controls["parcelFrontageBased"].get() if "parcelFrontageBased" in self.controls else True
        self.state["parcelBlockByBlock"] = self.controls["parcelBlockByBlock"].get() if "parcelBlockByBlock" in self.controls else True
        self.state["parcelCornerSeparate"] = self.controls["parcelCornerSeparate"].get() if "parcelCornerSeparate" in self.controls else True
        self.state["parcelPerturbation"] = self.controls["parcelPerturbation"].get() if "parcelPerturbation" in self.controls else False
        self.state["parcelPerturbationStr"] = safe_float(self.controls["parcelPerturbationStr"].get(), 0.02) if "parcelPerturbationStr" in self.controls else 0.02

        if self.state["engine"] == "blended":
            for key, default in [("blendTangentW", 0), ("blendNormalW", 1), ("blendDecay", 0), ("blendRadius", 200)]:
                if key in self.controls and self.controls[key].winfo_exists():
                    self.state[key] = safe_float(self.controls[key].get(), default)
        elif self.state["engine"] == "scalar":
            if "integrateMethod" in self.controls and self.controls["integrateMethod"].winfo_exists():
                self.state["integrateMethod"] = "euler" if self.controls["integrateMethod"].get() == "Euler" else "rk4"
            for key, default in [("integrateStep", 5), ("scalarStreamCount", 12), ("scalarCenterX", 600),
                                  ("scalarCenterY", 100), ("scalarSigma", 200)]:
                if key in self.controls and self.controls[key].winfo_exists():
                    self.state[key] = safe_float(self.controls[key].get(), default) if key != "scalarStreamCount" else safe_int(self.controls[key].get(), default)
            for k, v in [("integrateStepVal", "integrateStep"), ("scalarStreamCountVal", "scalarStreamCount"),
                         ("scalarCxVal", "scalarCenterX"), ("scalarCyVal", "scalarCenterY"), ("scalarSigmaVal", "scalarSigma")]:
                if k in self.controls and v in self.state:
                    self.controls[k].config(text=str(int(self.state[v])))

        if "pertStrVal" in self.controls and "parcelPerturbationStr" in self.state:
            self.controls["pertStrVal"].config(text=f"{self.state['parcelPerturbationStr']:.3f}")
        self.controls["rotVal"].config(text=f"{self.state['seedRotation']}°")
        self.controls["seedXVal"].config(text=str(int(self.state["seedXOffset"])))
        self.controls["seedYVal"].config(text=str(int(self.state["seedYOffset"])))
        self.controls["seedLenVal"].config(text=f"{self.state['seedLength']:.2f}")
        self.controls["spacingVal"].config(text=str(self.state["lineSpacing"]))
        self.controls["scaleVal"].config(text=f"{self.state['spacingScale']:.1f}")
        self.controls["noiseScaleVal"].config(text=str(self.state["noiseScale"]))
        self.controls["noiseStrVal"].config(text=str(int(self.state["noiseStrength"])))
        self.controls["crossVal"].config(text=str(int(self.state["crossSpacing"])))
        for k, v in [("curvWeightVal", "curvatureWeight"), ("attrWeightVal", "attractorWeight"), ("valWeightVal", "valueWeight")]:
            if k in self.controls and v in self.state:
                self.controls[k].config(text=f"{self.state[v]:.1f}")

        if self.draw_mode and self.state["seedType"] != "custom":
            self._exit_draw_mode()
        if self.state["seedType"] == "custom" and self._curve_list_frame:
            self._refresh_curve_list()
        if self.state["seedType"] == "custom":
            if not self._canvas_custom_bound:
                self.canvas.bind("<Button-1>", self._on_canvas_click)
                self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
                self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
                self._canvas_custom_bound = True
        else:
            if self._canvas_custom_bound:
                self.canvas.unbind("<Button-1>")
                self.canvas.unbind("<B1-Motion>")
                self.canvas.unbind("<ButtonRelease-1>")
                self._canvas_custom_bound = False
        self.resize_canvas()
        self._schedule_generate()

    def _schedule_generate(self):
        """Debounce: 仅在实际生成前等待最后一次变更"""
        if self._generate_after_id:
            self.root.after_cancel(self._generate_after_id)
        self._generate_after_id = self.root.after(self._debounce_ms, self._do_scheduled_generate)

    def _do_scheduled_generate(self):
        self._generate_after_id = None
        self.generate()

    def resize_canvas(self):
        w = int(self.state["siteWidth"])
        h = int(self.state["siteHeight"])
        self.canvas.config(width=w + 2 * DRAW_PADDING, height=h + 2 * DRAW_PADDING)

    def _pad(self, x, y):
        """逻辑坐标转画布坐标"""
        return x + DRAW_PADDING, y + DRAW_PADDING

    def _unpad(self, cx, cy):
        """画布坐标转逻辑坐标"""
        return cx - DRAW_PADDING, cy - DRAW_PADDING

    def _draw_line_segment(self, p0, p1, fill, width, dashed_outside=True):
        """绘制线段，矩形内实线、矩形外虚线。全在内则直接绘制以加速"""
        w, h = self.state["siteWidth"], self.state["siteHeight"]
        x0, y0, x1, y1 = p0[0], p0[1], p1[0], p1[1]
        in0 = 0 <= x0 <= w and 0 <= y0 <= h
        in1 = 0 <= x1 <= w and 0 <= y1 <= h
        if in0 and in1:
            ax, ay = self._pad(x0, y0)
            bx, by = self._pad(x1, y1)
            self.canvas.create_line(ax, ay, bx, by, fill=fill, width=width)
            return
        parts = split_segment_inside_outside(p0, p1, 0, 0, w, h)
        for kind, seg in parts:
            a, b = seg[0], seg[1]
            ax, ay = self._pad(a[0], a[1])
            bx, by = self._pad(b[0], b[1])
            dash = (4, 4) if (kind == "outside" and dashed_outside) else ()
            self.canvas.create_line(ax, ay, bx, by, fill=fill, width=width, dash=dash)

    def generate(self):
        if self._generate_after_id:
            self.root.after_cancel(self._generate_after_id)
            self._generate_after_id = None
        self.canvas.delete("all")
        s = self.state
        lines_by_curve = []
        cross_spacings = []
        eng = s.get("engine", "offset")

        curve_arrays_by_curve = []
        if eng == "blended":
            curves_with_pts = [c for c in self.custom_seed_curves if len(self._get_curve_points(c)) >= 2]
            if len(curves_with_pts) >= 1:
                blended = BlendedFieldEngine(
                    tangent_weight=s.get("blendTangentW", 0),
                    normal_weight=s.get("blendNormalW", 1),
                    distance_decay=s.get("blendDecay", 0),
                    decay_radius=s.get("blendRadius", 200),
                )
                curves_data = []
                for curve in curves_with_pts:
                    pts = self._get_curve_points(curve)
                    p = curve.get("params", self._get_curve_params_defaults()) if isinstance(curve, dict) else {}
                    curves_data.append({"points": pts, "weight": 1.0})
                lines = blended.generate_lines(curves_data, s,
                    line_spacing=s.get("lineSpacing", 40),
                    pos_count=s.get("posCount", 10),
                    neg_count=s.get("negCount", 10))
                lines_by_curve = [lines] if lines else []
                cross_spacings = [s.get("crossSpacing", 80)] * len(lines_by_curve) if lines_by_curve else []
                pts0 = self._get_curve_points(curves_with_pts[0])
                arr = precompute_custom_curve_arrays(pts0)
                curve_arrays_by_curve = [(arr[0], arr[1])] if arr else []
        elif eng == "scalar":
            cx = s.get("scalarCenterX", 600)
            cy = s.get("scalarCenterY", 100)
            sigma = s.get("scalarSigma", 200)
            scalar_fn = lambda x, y: default_land_price_field(x, y, center_x=cx, center_y=cy, sigma=sigma)
            scalar_eng = ScalarFieldEngine(scalar_field=scalar_fn)
            method = "euler" if s.get("integrateMethod") == "euler" else "rk4"
            step = s.get("integrateStep", 5)
            integrator = StreamlineIntegrator(scalar_eng.field_at, method=method, step_size=step, max_steps=300)
            w, h = s["siteWidth"], s["siteHeight"]
            n = max(3, int(s.get("scalarStreamCount", 12)))
            seeds = [(w * 0.1 + (w * 0.8) * i / max(n - 1, 1), h * 0.5) for i in range(n)]
            bounds = (0, 0, w, h)
            streams = integrator.integrate_from_seeds(seeds, bounds=bounds, bidirectional=True)
            lines_by_curve = [streams] if streams else []
            cross_spacings = [s.get("crossSpacing", 80)]
            curve_arrays_by_curve = []
        else:
            if s["seedType"] == "custom":
                if self.custom_seed_curves:
                    for curve in self.custom_seed_curves:
                        if len(self._get_curve_points(curve)) >= 2:
                            pts = self._get_curve_points(curve)
                            arr = precompute_custom_curve_arrays(pts)
                            curve_arrays_by_curve.append((arr[0], arr[1]) if arr else ([], []))
                            lines_by_curve.append(self._generate_lines_for_curve(curve))
                            p = curve.get("params", self._get_curve_params_defaults()) if isinstance(curve, dict) else {}
                            cross_spacings.append(p.get("crossSpacing", s["crossSpacing"]))
            else:
                arr = precompute_parametric_arrays(s)
                curve_arrays_by_curve = [(arr[0], arr[1])]
                lines = generate_lines_from_arrays(arr, s, {})
                lines_by_curve = [lines] if lines else []
                cross_spacings = [s["crossSpacing"]] if lines else []

        if not cross_spacings:
            cross_spacings = [s["crossSpacing"]]
        while len(curve_arrays_by_curve) < len(lines_by_curve):
            curve_arrays_by_curve.append(([], []))

        self.draw_result(lines_by_curve, cross_spacings, curve_arrays_by_curve)

    def draw_result(self, lines_by_curve, cross_spacings=None, curve_arrays_by_curve=None):
        s = self.state
        cross_spacings = cross_spacings or [s["crossSpacing"]]
        curve_arrays_by_curve = curve_arrays_by_curve or []
        self._export_geometry = {"polylines": [], "parcels": []}

        pw, ph = s["siteWidth"], s["siteHeight"]
        self.canvas.create_rectangle(DRAW_PADDING, DRAW_PADDING, DRAW_PADDING + pw, DRAW_PADDING + ph,
                                     outline="#555555", width=2, dash=(4, 4))
        curve_colors = ["#ff6600", "#66ff00", "#0066ff", "#ff00ff", "#00ffff"]
        perp = s.get("roadsPerpendicular", True)
        use_hierarchy = s.get("roadHierarchy", True)
        use_adaptive = s.get("adaptiveCross", True)
        main_color, main_w = "#b3b3b3", 1
        cross_color, cross_w = "#4d4d4d", 0.5

        for curve_idx, lines in enumerate(lines_by_curve):
            if not lines:
                continue
            curve_color = curve_colors[curve_idx % len(curve_colors)] if len(lines_by_curve) > 1 else "#ff3300"
            is_streamline = s.get("engine") == "scalar" or (lines and "offset" not in lines[0][0])

            if s["runMode"] == "A" or is_streamline:
                for idx, line in enumerate(lines):
                    color = curve_color if (idx == 0 and not is_streamline) else "#888888"
                    width = 1.5 if is_streamline else (2 if idx == 0 else 0.5)
                    pts = [(p["x"], p["y"]) for p in line]
                    self._export_geometry["polylines"].append(pts)
                    for i in range(len(pts) - 1):
                        self._draw_line_segment(pts[i], pts[i + 1], color, width)
            elif s["runMode"] in ("B", "C"):
                sorted_lines = sorted(lines, key=lambda ln: abs(ln[0].get("offset", 0)))
                hierarchy = classify_longitudinal_hierarchy(lines) if use_hierarchy else []
                line_level = {idx: level for idx, level in hierarchy}

                for line_idx, line in enumerate(lines):
                    pts = [(p["x"], p["y"]) for p in line]
                    self._export_geometry["polylines"].append(pts)
                    if use_hierarchy and line_idx in line_level:
                        w, fill = hierarchy_style(line_level[line_idx])
                    else:
                        fill, w = (cross_color, cross_w) if perp else (main_color, main_w)
                    for i in range(len(pts) - 1):
                        self._draw_line_segment(pts[i], pts[i + 1], fill, w)

                cs = cross_spacings[curve_idx] if curve_idx < len(cross_spacings) else s["crossSpacing"]
                xs, ys = ([], [])
                if curve_idx < len(curve_arrays_by_curve):
                    xs, ys = curve_arrays_by_curve[curve_idx]
                value_field = None
                cx = s.get("scalarCenterX", s["siteWidth"] / 2)
                cy = s.get("scalarCenterY", s["siteHeight"] / 2)
                sigma = s.get("scalarSigma", 200)
                value_field = lambda x, y, cx=cx, cy=cy, sigma=sigma: default_land_price_field(x, y, center_x=cx, center_y=cy, sigma=sigma)
                if use_adaptive and xs and ys:
                    t_positions = adaptive_cross_t_positions(
                        xs, ys, sorted_lines,
                        base_spacing=cs,
                        curvature_weight=s.get("curvatureWeight", 0.4),
                        attractor_weight=s.get("attractorWeight", 0.3),
                        value_weight=s.get("valueWeight", 0.2),
                        attractor_x=s["siteWidth"] / 2,
                        attractor_y=s["siteHeight"] / 2,
                        attractor_sigma=sigma,
                        value_field=value_field,
                        site_width=s["siteWidth"],
                        site_height=s["siteHeight"],
                    )
                else:
                    num_sections = max(3, min(51, int(1600 / max(cs, 10))))
                    t_positions = [j / max(num_sections - 1, 1) for j in range(num_sections)]

                for t in t_positions:
                    idx = 0 if t <= 0 else min(int(t / T_STEP), T_COUNT - 1)
                    cross_pts = get_line_at_t(sorted_lines, t, perp=True)
                    if len(cross_pts) < 2:
                        continue
                    self._export_geometry["polylines"].append(cross_pts)
                    fill, w = (main_color, main_w) if perp else (cross_color, cross_w)
                    for i in range(len(cross_pts) - 1):
                        self._draw_line_segment(cross_pts[i], cross_pts[i + 1], fill, w)

                if s["runMode"] == "C":
                    use_frontage = s.get("parcelFrontageBased", True)
                    use_block = s.get("parcelBlockByBlock", True)
                    use_corner = s.get("parcelCornerSeparate", True)
                    use_pert = s.get("parcelPerturbation", False)
                    pert_str = s.get("parcelPerturbationStr", 0.02) if use_pert else 0
                    min_f = s.get("pMin", 15)
                    max_f = s.get("pMax", 45)
                    min_a = s.get("pMinArea", 50)
                    max_d = s.get("pMaxDepth", 200)

                    if use_frontage and use_block:
                        parcel_list = subdivide_blocks(
                            sorted_lines, t_positions,
                            min_frontage=min_f, max_frontage=max_f,
                            min_area=min_a, max_depth=max_d,
                            use_frontage_based=True,
                            use_block_by_block=True,
                            corner_parcels_separate=use_corner,
                            perturbation_strength=pert_str,
                            seed=hash(str(s.get("seedRotation", 0))),
                        )
                    else:
                        parcel_list = rule_based_parcels(sorted_lines, segments=15)

                    for parcel_pts in parcel_list:
                        self._export_geometry["parcels"].append(parcel_pts)
                        if random.random() > 0.15:
                            gray = int(255 * (0.05 + random.random() * 0.1))
                            fill_color = f"#{gray:02x}{gray:02x}{gray:02x}"
                            pad_pts = [self._pad(x, y) for x, y in parcel_pts]
                            flat = [c for p in pad_pts for c in p]
                            self.canvas.create_polygon(
                                *flat, fill=fill_color, outline="#1a1a1a")

        if s["seedType"] == "custom" and self.custom_seed_curves:
            colors = ["#ff6600", "#66ff00", "#0066ff", "#ff00ff", "#00ffff"]
            for ci, curve in enumerate(self.custom_seed_curves):
                pts = self._get_curve_points(curve)
                if len(pts) < 2:
                    for x, y in pts:
                        cx, cy = self._pad(x, y)
                        self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="#ff3300", outline="#ffffff")
                    continue
                color = colors[ci % len(colors)]
                curve_pts = sample_curve(pts)
                for i in range(len(curve_pts) - 1):
                    self._draw_line_segment(curve_pts[i], curve_pts[i + 1], color, 2)
                for x, y in pts:
                    cx, cy = self._pad(x, y)
                    self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=color, outline="#ffffff")

    def _bind_events(self):
        for key, ctrl in self.controls.items():
            if key in ("rotVal", "spacingVal", "scaleVal", "noiseScaleVal", "noiseStrVal", "crossVal",
                       "seedXVal", "seedYVal", "seedLenVal", "curvWeightVal", "attrWeightVal", "valWeightVal"):
                continue
            if isinstance(ctrl, tk.Scale):
                ctrl.config(command=lambda v, k=key: self.update_state())
            elif isinstance(ctrl, (ttk.Combobox, tk.Entry)):
                ctrl.bind("<<ComboboxSelected>>" if isinstance(ctrl, ttk.Combobox) else "<KeyRelease>", lambda e: self.update_state())
        for w in self.root.winfo_children():
            self._bind_recursive(w, self.update_state)

    def _bind_recursive(self, widget, callback):
        if isinstance(widget, tk.Scale):
            widget.config(command=lambda v: callback())
        elif isinstance(widget, ttk.Combobox):
            widget.bind("<<ComboboxSelected>>", lambda e: callback())
        elif isinstance(widget, tk.Entry):
            widget.bind("<KeyRelease>", lambda e: callback())
        for child in widget.winfo_children():
            self._bind_recursive(child, callback)

    def _export_rhino(self):
        def status_cb(msg):
            self.status_label.config(text=msg)
        export_rhino(self._export_geometry, self.state["siteWidth"], self.state["siteHeight"], status_cb)

    def _export_dxf(self):
        def status_cb(msg):
            self.status_label.config(text=msg)
        export_dxf(self._export_geometry, self.state["siteWidth"], self.state["siteHeight"], status_cb)

    def _reset(self):
        self.controls["seedRotation"].set(0)
        self.controls["seedXOffset"].set(0)
        self.controls["seedYOffset"].set(0)
        self.controls["seedLength"].set(0.8)
        self.controls["seedSineAmp"].delete(0, tk.END)
        self.controls["seedSineAmp"].insert(0, "50")
        self.controls["seedArcCurv"].delete(0, tk.END)
        self.controls["seedArcCurv"].insert(0, "200")
        self.controls["lineSpacing"].set(40)
        self.controls["posCount"].delete(0, tk.END)
        self.controls["posCount"].insert(0, "10")
        self.controls["negCount"].delete(0, tk.END)
        self.controls["negCount"].insert(0, "10")
        self.controls["noiseEnabled"].set(False)
        if "pMinArea" in self.controls:
            self.controls["pMinArea"].delete(0, tk.END)
            self.controls["pMinArea"].insert(0, "50")
        if "pMaxDepth" in self.controls:
            self.controls["pMaxDepth"].delete(0, tk.END)
            self.controls["pMaxDepth"].insert(0, "200")
        if "parcelFrontageBased" in self.controls:
            self.controls["parcelFrontageBased"].set(True)
        if "parcelBlockByBlock" in self.controls:
            self.controls["parcelBlockByBlock"].set(True)
        if "parcelCornerSeparate" in self.controls:
            self.controls["parcelCornerSeparate"].set(True)
        if "parcelPerturbation" in self.controls:
            self.controls["parcelPerturbation"].set(False)
        if "parcelPerturbationStr" in self.controls:
            self.controls["parcelPerturbationStr"].set(0.02)
        self.update_state()

    def run(self):
        self.root.mainloop()
