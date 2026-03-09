"""
城市线驱动向量场生成器 - 主应用
基于 Seed Curve 的非中心式扩张
"""

import tkinter as tk
from tkinter import ttk, filedialog
import math
import random

from config import T_COUNT, T_STEP
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
from i18n import T, RUN_MODE_OPTS, ENGINE_OPTS, FIELD_TYPE_OPTS, SEED_TYPE_OPTS, SPACING_MODE_OPTS
from i18n import INTEGRATE_METHOD_OPTS, BTN_ADD_CURVE, BTN_DRAW, BTN_DONE_DRAWING, BTN_CLEAR, BTN_RESET, BTN_GENERATE
from i18n import BTN_PARAMS, BTN_EDIT, BTN_DEL, BLEND_PARAMS_TITLE, BLEND_TANGENT, BLEND_NORMAL, BLEND_DECAY
from i18n import BLEND_RADIUS, BLEND_HINT, SCALAR_PARAMS_TITLE, SCALAR_METHOD, SCALAR_STEP, SCALAR_COUNT
from i18n import SCALAR_CENTER_X, SCALAR_CENTER_Y, SCALAR_SIGMA, OFFSET_HINT, MULTI_SEED_HINT, CURVE_PARAMS_HINT
from i18n import CURVE_SELECT_HINT, LINE_SPACING_SHORT, POS_NEG, OFFSET_XY, SPACING_MODE_SHORT
from i18n import SPACING_SCALE_SHORT, CROSS_SPACING_SHORT, NOISE_ENABLED, ROADS_PERP, NO_CURVES_YET
from i18n import DRAW_MODE_STATUS, CURVE_SPACING_MODES, SEED_TYPE_OPTS, curve_n_params, curve_n_pts


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
        self.controls["runMode"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, T["site_width"])
        self.controls["siteWidth"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                             insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["siteWidth"].insert(0, "1200")
        self.controls["siteWidth"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, T["site_height"])
        self.controls["siteHeight"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                               insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["siteHeight"].insert(0, "200")
        self.controls["siteHeight"].pack(fill=tk.X, pady=(0, 16))

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
        self.controls["lineSpacing"].pack(fill=tk.X, pady=(0, 16))

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
        self.controls["spacingScale"].pack(fill=tk.X, pady=(0, 24))

        self._section_title(panel, T["section_noise"])
        self.controls["noiseEnabled"] = tk.BooleanVar(value=False)
        noise_cb = tk.Checkbutton(panel, text=NOISE_ENABLED, variable=self.controls["noiseEnabled"],
                                  command=self.update_state,
                                  bg="#141414", fg="#e0e0e0", selectcolor="#1a1a1a", activebackground="#141414",
                                  activeforeground="#e0e0e0", wraplength=350, justify=tk.LEFT)
        noise_cb.pack(anchor="w", pady=(0, 16))

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
        self.controls["noiseStrength"].pack(fill=tk.X, pady=(0, 24))

        self._section_title(panel, T["section_street"])
        self.controls["roadsPerpendicular"] = tk.BooleanVar(value=True)
        perp_cb = tk.Checkbutton(panel, text=ROADS_PERP,
                                 variable=self.controls["roadsPerpendicular"],
                                 command=self.update_state,
                                 bg="#141414", fg="#e0e0e0", selectcolor="#1a1a1a", activebackground="#141414",
                                 activeforeground="#e0e0e0", wraplength=350, justify=tk.LEFT)
        perp_cb.pack(anchor="w", pady=(0, 16))
        self._label_group(panel, T["cross_spacing"], "80", right_key="crossVal")
        self.controls["crossSpacing"] = tk.Scale(panel, from_=40, to=300, orient=tk.HORIZONTAL,
                                                 bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                 highlightthickness=0, showvalue=False)
        self.controls["crossSpacing"].set(80)
        self.controls["crossSpacing"].pack(fill=tk.X, pady=(0, 16))

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
        self._label_group(panel, T["parcel_depth"])
        self.controls["pDepth"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                          insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["pDepth"].insert(0, "10")
        self.controls["pDepth"].pack(fill=tk.X, pady=(0, 32))

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
        tk.Label(parent, text=text, font=("Inter", 12, "bold"), fg="#ffffff", bg="#141414",
                 wraplength=wraplength, justify=tk.LEFT).pack(anchor="w", pady=(24, 8))

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

    def _find_point_at(self, x, y, radius=10):
        best_ci, best_pi, best_d = -1, -1, radius * radius
        for ci, curve in enumerate(self.custom_seed_curves):
            pts = self._get_curve_points(curve)
            for pi, (px, py) in enumerate(pts):
                d = (x - px) ** 2 + (y - py) ** 2
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
            self._get_curve_points(self.custom_seed_curves[self.editing_curve_index]).append((event.x, event.y))
            self._refresh_curve_list()
            self.update_state()

    def _on_canvas_drag(self, event):
        if self.drag_curve_idx is not None and self.drag_point_idx is not None:
            pts = self._get_curve_points(self.custom_seed_curves[self.drag_curve_idx])
            if 0 <= self.drag_point_idx < len(pts):
                pts[self.drag_point_idx] = (event.x, event.y)
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
        self.state["pMin"] = safe_float(self.controls["pMin"].get(), 15)
        self.state["pMax"] = safe_float(self.controls["pMax"].get(), 45)
        self.state["pDepth"] = safe_float(self.controls["pDepth"].get(), 10)

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

        self.controls["rotVal"].config(text=f"{self.state['seedRotation']}°")
        self.controls["seedXVal"].config(text=str(int(self.state["seedXOffset"])))
        self.controls["seedYVal"].config(text=str(int(self.state["seedYOffset"])))
        self.controls["seedLenVal"].config(text=f"{self.state['seedLength']:.2f}")
        self.controls["spacingVal"].config(text=str(self.state["lineSpacing"]))
        self.controls["scaleVal"].config(text=f"{self.state['spacingScale']:.1f}")
        self.controls["noiseScaleVal"].config(text=str(self.state["noiseScale"]))
        self.controls["noiseStrVal"].config(text=str(int(self.state["noiseStrength"])))
        self.controls["crossVal"].config(text=str(int(self.state["crossSpacing"])))

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
        self.generate()

    def resize_canvas(self):
        w = int(self.state["siteWidth"])
        h = int(self.state["siteHeight"])
        self.canvas.config(width=w, height=h)

    def generate(self):
        self.canvas.delete("all")
        s = self.state
        lines_by_curve = []
        cross_spacings = []
        eng = s.get("engine", "offset")

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
        else:
            if s["seedType"] == "custom":
                if self.custom_seed_curves:
                    for curve in self.custom_seed_curves:
                        if len(self._get_curve_points(curve)) >= 2:
                            lines_by_curve.append(self._generate_lines_for_curve(curve))
                            p = curve.get("params", self._get_curve_params_defaults()) if isinstance(curve, dict) else {}
                            cross_spacings.append(p.get("crossSpacing", s["crossSpacing"]))
            else:
                arr = precompute_parametric_arrays(s)
                lines = generate_lines_from_arrays(arr, s, {})
                lines_by_curve = [lines] if lines else []
                cross_spacings = [s["crossSpacing"]] if lines else []

        if not cross_spacings:
            cross_spacings = [s["crossSpacing"]]

        self.draw_result(lines_by_curve, cross_spacings)

    def draw_result(self, lines_by_curve, cross_spacings=None):
        s = self.state
        cross_spacings = cross_spacings or [s["crossSpacing"]]
        self._export_geometry = {"polylines": [], "parcels": []}

        self.canvas.create_rectangle(0, 0, s["siteWidth"], s["siteHeight"],
                                     outline="#555555", width=2, dash=(4, 4))
        curve_colors = ["#ff6600", "#66ff00", "#0066ff", "#ff00ff", "#00ffff"]
        perp = s.get("roadsPerpendicular", True)
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
                        self.canvas.create_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                                               fill=color, width=width)
            elif s["runMode"] in ("B", "C"):
                for line in lines:
                    pts = [(p["x"], p["y"]) for p in line]
                    self._export_geometry["polylines"].append(pts)
                    fill, w = (cross_color, cross_w) if perp else (main_color, main_w)
                    for i in range(len(pts) - 1):
                        self.canvas.create_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                                               fill=fill, width=w)

                sorted_lines = sorted(lines, key=lambda ln: ln[0]["offset"])
                cs = cross_spacings[curve_idx] if curve_idx < len(cross_spacings) else s["crossSpacing"]
                num_sections = max(3, min(51, int(1600 / max(cs, 10))))
                for j in range(num_sections):
                    t = j / max(num_sections - 1, 1) if num_sections > 1 else 0
                    idx = 0 if t <= 0 else min(int(t / T_STEP) + 1, T_COUNT - 1)
                    cross_pts = []
                    for line in sorted_lines:
                        p = line[idx]
                        cross_pts.append((p["x"], p["y"]))
                    self._export_geometry["polylines"].append(cross_pts)
                    fill, w = (main_color, main_w) if perp else (cross_color, cross_w)
                    for i in range(len(cross_pts) - 1):
                        self.canvas.create_line(cross_pts[i][0], cross_pts[i][1], cross_pts[i + 1][0], cross_pts[i + 1][1],
                                               fill=fill, width=w)

                if s["runMode"] == "C":
                    segments = 15
                    for i in range(len(sorted_lines) - 1):
                        line_a = sorted_lines[i]
                        line_b = sorted_lines[i + 1]
                        for seg in range(segments):
                            t_start = seg / segments
                            t_end = (seg + 0.8) / segments
                            idx_s = 0 if t_start <= 0 else min(int(t_start / T_STEP) + 1, T_COUNT - 1)
                            idx_e = 0 if t_end <= 0 else min(int(t_end / T_STEP) + 1, T_COUNT - 1)
                            p1, p2 = line_a[idx_s], line_b[idx_s]
                            p3, p4 = line_b[idx_e], line_a[idx_e]
                            parcel_pts = [(p1["x"], p1["y"]), (p2["x"], p2["y"]), (p3["x"], p3["y"]), (p4["x"], p4["y"])]
                            self._export_geometry["parcels"].append(parcel_pts)
                            if random.random() > 0.15:
                                gray = int(255 * (0.05 + random.random() * 0.1))
                                fill_color = f"#{gray:02x}{gray:02x}{gray:02x}"
                                self.canvas.create_polygon(
                                    p1["x"], p1["y"], p2["x"], p2["y"], p3["x"], p3["y"], p4["x"], p4["y"],
                                    fill=fill_color, outline="#1a1a1a")

        if s["seedType"] == "custom" and self.custom_seed_curves:
            colors = ["#ff6600", "#66ff00", "#0066ff", "#ff00ff", "#00ffff"]
            for ci, curve in enumerate(self.custom_seed_curves):
                pts = self._get_curve_points(curve)
                if len(pts) < 2:
                    for x, y in pts:
                        self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#ff3300", outline="#ffffff")
                    continue
                color = colors[ci % len(colors)]
                curve_pts = sample_curve(pts)
                for i in range(len(curve_pts) - 1):
                    x1, y1 = curve_pts[i]
                    x2, y2 = curve_pts[i + 1]
                    self.canvas.create_line(x1, y1, x2, y2, fill=color, width=2)
                for x, y in pts:
                    self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=color, outline="#ffffff")

    def _bind_events(self):
        for key, ctrl in self.controls.items():
            if key in ("rotVal", "spacingVal", "scaleVal", "noiseScaleVal", "noiseStrVal", "crossVal",
                       "seedXVal", "seedYVal", "seedLenVal"):
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
        self.update_state()

    def run(self):
        self.root.mainloop()
