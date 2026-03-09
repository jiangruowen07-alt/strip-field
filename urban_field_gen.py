"""
城市线驱动向量场生成器
核心逻辑：基于 Seed Curve 的非中心式扩张
Python 重写版本 - 逻辑完全一致
"""

import tkinter as tk
from tkinter import ttk
import math
import random


def lerp(a, b, t):
    return a + (b - a) * t


def noise(x, y):
    """简易噪声函数 (Lattice Noise)"""
    return (math.sin(x * 0.01) * math.cos(y * 0.01) + math.sin(x * 0.02 + y * 0.015)) * 0.5


class UrbanFieldGenerator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Line-Driven Urban Field Generator")
        self.root.configure(bg="#0a0a0a")
        self.root.geometry("1400x900")

        # State
        self.state = {}
        self.controls = {}

        self._build_ui()
        self._bind_events()
        self.update_state()

    def _build_ui(self):
        main_frame = tk.Frame(self.root, bg="#0a0a0a")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Control Panel
        panel = tk.Frame(main_frame, width=320, bg="#141414", padx=24, pady=24)
        panel.pack(side=tk.LEFT, fill=tk.Y)
        panel.pack_propagate(False)

        # Title
        tk.Label(panel, text="URBAN FIELD GEN", font=("Inter", 20, "bold"),
                 fg="#ffffff", bg="#141414").pack(anchor="w")
        tk.Label(panel, text="V.1.0 LINE-DRIVEN ENGINE", font=("JetBrains Mono", 10),
                 fg="#888888", bg="#141414").pack(anchor="w")

        # RUN MODE & SITE
        self._section_title(panel, "RUN MODE & SITE")
        self._label_group(panel, "Run Mode")
        self.controls["runMode"] = ttk.Combobox(panel, values=["A - Flow Lines", "B - Street Network", "C - Parcel Blocks"],
                                                state="readonly", width=28)
        self.controls["runMode"].set("B - Street Network")
        self.controls["runMode"].pack(fill=tk.X, pady=(0, 16))

        site_frame = tk.Frame(panel, bg="#141414")
        site_frame.pack(fill=tk.X, pady=(0, 16))
        self._label_group(panel, "Site Width")
        self.controls["siteWidth"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                             insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["siteWidth"].insert(0, "1200")
        self.controls["siteWidth"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, "Site Height")
        self.controls["siteHeight"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                               insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["siteHeight"].insert(0, "800")
        self.controls["siteHeight"].pack(fill=tk.X, pady=(0, 16))

        # FIELD LOGIC
        self._section_title(panel, "FIELD LOGIC")
        self._label_group(panel, "Field Type")
        field_opts = ["1. Parallel Offset", "2. Curve Tangent", "3. Curve Normal", "4. Distance Contour",
                     "5. Strip Growth", "6. Hybrid Tangent-Normal", "7. Noise-Modified Line Field"]
        self.controls["fieldType"] = ttk.Combobox(panel, values=field_opts, state="readonly", width=28)
        self.controls["fieldType"].set("1. Parallel Offset")
        self.controls["fieldType"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, "Seed Line Type")
        self.controls["seedType"] = ttk.Combobox(panel, values=["Straight Line", "Sine Wave", "Arc / Curve"],
                                                 state="readonly", width=28)
        self.controls["seedType"].set("Straight Line")
        self.controls["seedType"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, "Seed Rotation", "0°", right_key="rotVal")
        self.controls["seedRotation"] = tk.Scale(panel, from_=0, to=360, orient=tk.HORIZONTAL,
                                                  bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                  highlightthickness=0, showvalue=False)
        self.controls["seedRotation"].set(0)
        self.controls["seedRotation"].pack(fill=tk.X, pady=(0, 24))

        # EXPANSION PARAMETERS
        self._section_title(panel, "EXPANSION PARAMETERS")
        self._label_group(panel, "Line Spacing", "40", right_key="spacingVal")
        self.controls["lineSpacing"] = tk.Scale(panel, from_=10, to=100, orient=tk.HORIZONTAL,
                                                bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                highlightthickness=0, showvalue=False)
        self.controls["lineSpacing"].set(40)
        self.controls["lineSpacing"].pack(fill=tk.X, pady=(0, 16))

        count_frame = tk.Frame(panel, bg="#141414")
        count_frame.pack(fill=tk.X, pady=(0, 16))
        self._label_group(panel, "Pos. Count")
        self.controls["posCount"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                             insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["posCount"].insert(0, "10")
        self.controls["posCount"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, "Neg. Count")
        self.controls["negCount"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                             insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["negCount"].insert(0, "10")
        self.controls["negCount"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, "Spacing Mode")
        self.controls["spacingMode"] = ttk.Combobox(panel, values=["Linear", "Exponential Expansion", "Fibonacci Series"],
                                                    state="readonly", width=28)
        self.controls["spacingMode"].set("Linear")
        self.controls["spacingMode"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, "Spacing Scale", "1.0", right_key="scaleVal")
        self.controls["spacingScale"] = tk.Scale(panel, from_=0.5, to=2.0, resolution=0.1, orient=tk.HORIZONTAL,
                                                 bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                 highlightthickness=0, showvalue=False)
        self.controls["spacingScale"].set(1.0)
        self.controls["spacingScale"].pack(fill=tk.X, pady=(0, 24))

        # NOISE & DISTORTION
        self._section_title(panel, "NOISE & DISTORTION")
        self.controls["noiseEnabled"] = tk.BooleanVar(value=False)
        noise_cb = tk.Checkbutton(panel, text="Enable Noise Distortion", variable=self.controls["noiseEnabled"],
                                  command=self.update_state,
                                  bg="#141414", fg="#e0e0e0", selectcolor="#1a1a1a", activebackground="#141414",
                                  activeforeground="#e0e0e0")
        noise_cb.pack(anchor="w", pady=(0, 16))

        self._label_group(panel, "Noise Scale", "0.005", right_key="noiseScaleVal")
        self.controls["noiseScale"] = tk.Scale(panel, from_=0.001, to=0.02, resolution=0.001, orient=tk.HORIZONTAL,
                                               bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                               highlightthickness=0, showvalue=False)
        self.controls["noiseScale"].set(0.005)
        self.controls["noiseScale"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, "Noise Strength", "20", right_key="noiseStrVal")
        self.controls["noiseStrength"] = tk.Scale(panel, from_=0, to=100, orient=tk.HORIZONTAL,
                                                  bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                  highlightthickness=0, showvalue=False)
        self.controls["noiseStrength"].set(20)
        self.controls["noiseStrength"].pack(fill=tk.X, pady=(0, 24))

        # STREET & PARCEL (B/C)
        self._section_title(panel, "STREET & PARCEL (B/C)")
        self._label_group(panel, "Cross Road Spacing", "80", right_key="crossVal")
        self.controls["crossSpacing"] = tk.Scale(panel, from_=40, to=300, orient=tk.HORIZONTAL,
                                                 bg="#141414", fg="#e0e0e0", troughcolor="#2a2a2a",
                                                 highlightthickness=0, showvalue=False)
        self.controls["crossSpacing"].set(80)
        self.controls["crossSpacing"].pack(fill=tk.X, pady=(0, 16))

        self._label_group(panel, "Parcel Min")
        self.controls["pMin"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                         insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["pMin"].insert(0, "15")
        self.controls["pMin"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, "Parcel Max")
        self.controls["pMax"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                         insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["pMax"].insert(0, "45")
        self.controls["pMax"].pack(fill=tk.X, pady=(0, 4))
        self._label_group(panel, "Parcel Depth Offset")
        self.controls["pDepth"] = tk.Entry(panel, bg="#1a1a1a", fg="#e0e0e0",
                                          insertbackground="#e0e0e0", relief=tk.SOLID, bd=1)
        self.controls["pDepth"].insert(0, "10")
        self.controls["pDepth"].pack(fill=tk.X, pady=(0, 32))

        # Buttons
        btn_frame = tk.Frame(panel, bg="#141414")
        btn_frame.pack(fill=tk.X)
        btn_reset = tk.Button(btn_frame, text="Reset", command=self._reset,
                             bg="#1a1a1a", fg="#e0e0e0", relief=tk.SOLID, bd=1,
                             font=("JetBrains Mono", 10),
                             activebackground="#ffffff", activeforeground="#0a0a0a")
        btn_reset.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        btn_gen = tk.Button(btn_frame, text="Generate", command=self.generate,
                           bg="#ffffff", fg="#0a0a0a", relief=tk.SOLID, bd=1,
                           font=("JetBrains Mono", 10, "bold"),
                           activebackground="#ffffff", activeforeground="#0a0a0a")
        btn_gen.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        tk.Label(panel, text="Non-Radial Field Generator\nUrban Morphology Study Tool",
                 fg="#888888", bg="#141414", font=("Inter", 9)).pack(pady=(32, 0))

        # Canvas Area
        canvas_frame = tk.Frame(main_frame, bg="#050505")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=32, pady=32)

        self.canvas = tk.Canvas(canvas_frame, bg="#050505", highlightthickness=0)
        self.canvas.pack(expand=True)

        self.status_label = tk.Label(canvas_frame, text="COORD_SYSTEM: CARTESIAN\nEXPANSION_VECTOR: LINE_LOCAL_NORMAL\nSTATUS: REALTIME_CALCULATION",
                                    fg="#4d4d4d", bg="#050505", font=("JetBrains Mono", 10),
                                    justify=tk.RIGHT)
        self.status_label.place(relx=1.0, rely=1.0, anchor="se", x=-32, y=-32)

    def _section_title(self, parent, text):
        tk.Label(parent, text=text, font=("Inter", 12, "bold"), fg="#ffffff", bg="#141414").pack(anchor="w", pady=(24, 8))

    def _label_group(self, parent, left, right=None, right_key=None):
        frame = tk.Frame(parent, bg="#141414")
        frame.pack(fill=tk.X)
        tk.Label(frame, text=left, fg="#888888", bg="#141414", font=("Inter", 11)).pack(side=tk.LEFT)
        if right_key:
            lbl = tk.Label(frame, text=right or "", fg="#888888", bg="#141414", font=("Inter", 11))
            lbl.pack(side=tk.RIGHT)
            self.controls[right_key] = lbl
        elif right is not None:
            tk.Label(frame, text=right, fg="#888888", bg="#141414", font=("Inter", 11)).pack(side=tk.RIGHT)

    def _get_run_mode(self):
        val = self.controls["runMode"].get()
        if "A" in val or "Flow" in val:
            return "A"
        if "C" in val or "Parcel" in val:
            return "C"
        return "B"

    def _get_field_type(self):
        val = self.controls["fieldType"].get()
        return val[0] if val else "1"

    def _get_seed_type(self):
        val = self.controls["seedType"].get()
        if "Sine" in val:
            return "sine"
        if "Arc" in val:
            return "arc"
        return "straight"

    def _get_spacing_mode(self):
        val = self.controls["spacingMode"].get()
        if "Exponential" in val:
            return "exponential"
        if "Fibonacci" in val:
            return "fibonacci"
        return "linear"

    def _safe_float(self, val, default):
        try:
            return float(val) if val else default
        except (ValueError, TypeError):
            return default

    def _safe_int(self, val, default):
        try:
            return int(float(val)) if val else default
        except (ValueError, TypeError):
            return default

    def update_state(self):
        self.state["runMode"] = self._get_run_mode()
        self.state["fieldType"] = self._get_field_type()
        self.state["siteWidth"] = self._safe_float(self.controls["siteWidth"].get(), 1200)
        self.state["siteHeight"] = self._safe_float(self.controls["siteHeight"].get(), 800)
        self.state["seedType"] = self._get_seed_type()
        self.state["seedRotation"] = self._safe_float(self.controls["seedRotation"].get(), 0)
        self.state["lineSpacing"] = self._safe_float(self.controls["lineSpacing"].get(), 40)
        self.state["posCount"] = self._safe_int(self.controls["posCount"].get(), 10)
        self.state["negCount"] = self._safe_int(self.controls["negCount"].get(), 10)
        self.state["spacingMode"] = self._get_spacing_mode()
        self.state["spacingScale"] = self._safe_float(self.controls["spacingScale"].get(), 1.0)
        self.state["noiseEnabled"] = self.controls["noiseEnabled"].get()
        self.state["noiseScale"] = self._safe_float(self.controls["noiseScale"].get(), 0.005)
        self.state["noiseStrength"] = self._safe_float(self.controls["noiseStrength"].get(), 20)
        self.state["crossSpacing"] = self._safe_float(self.controls["crossSpacing"].get(), 80)
        self.state["pMin"] = self._safe_float(self.controls["pMin"].get(), 15)
        self.state["pMax"] = self._safe_float(self.controls["pMax"].get(), 45)
        self.state["pDepth"] = self._safe_float(self.controls["pDepth"].get(), 10)

        # 更新显示数值
        self.controls["rotVal"].config(text=f"{self.state['seedRotation']}°")
        self.controls["spacingVal"].config(text=str(self.state["lineSpacing"]))
        self.controls["scaleVal"].config(text=f"{self.state['spacingScale']:.1f}")
        self.controls["noiseScaleVal"].config(text=str(self.state["noiseScale"]))
        self.controls["noiseStrVal"].config(text=str(int(self.state["noiseStrength"])))
        self.controls["crossVal"].config(text=str(int(self.state["crossSpacing"])))

        self.resize_canvas()
        self.generate()

    def resize_canvas(self):
        """原逻辑：canvas 物理尺寸 = siteWidth x siteHeight"""
        w = int(self.state["siteWidth"])
        h = int(self.state["siteHeight"])
        self.canvas.config(width=w, height=h)

    def get_seed_point(self, t):
        """t from 0 to 1"""
        x = (t - 0.5) * self.state["siteWidth"] * 0.8
        y = 0.0

        if self.state["seedType"] == "sine":
            y = math.sin(t * math.pi * 2) * 50
        elif self.state["seedType"] == "arc":
            y = ((t - 0.5) ** 2) * 200

        # 旋转
        rad = self.state["seedRotation"] * math.pi / 180
        rx = x * math.cos(rad) - y * math.sin(rad)
        ry = x * math.sin(rad) + y * math.cos(rad)

        return {"x": rx + self.state["siteWidth"] / 2, "y": ry + self.state["siteHeight"] / 2}

    def get_line_vectors(self, t):
        """获取线上点的切向和法向"""
        p1 = self.get_seed_point(t - 0.01)
        p2 = self.get_seed_point(t + 0.01)
        dx = p2["x"] - p1["x"]
        dy = p2["y"] - p1["y"]
        length = math.sqrt(dx * dx + dy * dy)
        if length == 0:
            length = 1e-10
        tangent = {"x": dx / length, "y": dy / length}
        normal = {"x": -tangent["y"], "y": tangent["x"]}
        return {"tangent": tangent, "normal": normal}

    def generate(self):
        self.canvas.delete("all")
        lines = []
        s = self.state

        # 生成扩张线
        for side in range(2):
            count = s["negCount"] if side == 0 else s["posCount"]
            direction = -1 if side == 0 else 1

            start_i = 1 if side == 0 else 0
            for i in range(start_i, count + 1):
                line_points = []
                actual_index = -i if side == 0 else i

                # 计算偏移距离
                if s["spacingMode"] == "linear":
                    offset_dist = actual_index * s["lineSpacing"] * s["spacingScale"]
                elif s["spacingMode"] == "exponential":
                    offset_dist = (1 if actual_index >= 0 else -1) * (abs(actual_index) ** 1.5) * s["lineSpacing"] * s["spacingScale"] * 0.5
                else:
                    # Fibonacci 模拟
                    offset_dist = actual_index * s["lineSpacing"] * (1 + abs(actual_index) * 0.1) * s["spacingScale"]

                t = 0
                while t <= 1:
                    seed_p = self.get_seed_point(t)
                    vecs = self.get_line_vectors(t)

                    px = seed_p["x"]
                    py = seed_p["y"]

                    # 根据场类型应用逻辑
                    ft = s["fieldType"]
                    if ft == "1":  # Parallel Offset
                        px += vecs["normal"]["x"] * offset_dist
                        py += vecs["normal"]["y"] * offset_dist
                    elif ft == "2":  # Tangent expansion
                        px += vecs["tangent"]["x"] * offset_dist * 0.2
                        py += vecs["normal"]["y"] * offset_dist
                    elif ft == "3":  # Normal focus
                        factor = math.sin(t * math.pi)
                        px += vecs["normal"]["x"] * offset_dist * factor
                        py += vecs["normal"]["y"] * offset_dist * factor
                    elif ft == "4":  # Contour
                        px += vecs["normal"]["x"] * offset_dist
                        py += vecs["normal"]["y"] * offset_dist
                        bulge = math.sin(t * math.pi) * (offset_dist * 0.3)
                        px += vecs["normal"]["x"] * bulge
                        py += vecs["normal"]["y"] * bulge
                    elif ft == "5":  # Strip
                        px += vecs["normal"]["x"] * offset_dist
                        py += vecs["normal"]["y"] * offset_dist
                        if i % 2 == 0:
                            px += vecs["tangent"]["x"] * 20
                    elif ft == "6":  # Hybrid
                        mix = math.cos(t * math.pi * 2)
                        px += (vecs["normal"]["x"] * (1 - mix) + vecs["tangent"]["x"] * mix) * offset_dist
                        py += (vecs["normal"]["y"] * (1 - mix) + vecs["tangent"]["y"] * mix) * offset_dist
                    elif ft == "7":  # Noise
                        px += vecs["normal"]["x"] * offset_dist
                        py += vecs["normal"]["y"] * offset_dist

                    # 应用全局噪声
                    if s["noiseEnabled"]:
                        n = noise(px * s["noiseScale"] * 100, py * s["noiseScale"] * 100)
                        px += n * s["noiseStrength"]
                        py += n * s["noiseStrength"]

                    line_points.append({"x": px, "y": py, "t": t, "offset": offset_dist})
                    t += 0.02

                lines.append(line_points)

        self.draw_result(lines)

    def draw_result(self, lines):
        s = self.state
        if s["runMode"] == "A":
            # FLOW LINES
            for idx, line in enumerate(lines):
                color = "#ff3300" if idx == 0 else "#999999"  # rgba(255,255,255,0.4) 近似
                width = 2 if idx == 0 else 0.5
                pts = [(p["x"], p["y"]) for p in line]
                for i in range(len(pts) - 1):
                    self.canvas.create_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                                           fill=color, width=width)
        elif s["runMode"] in ("B", "C"):
            # STREET NETWORK - 1. Draw Longitudinal lines (Main Streets)
            for line in lines:
                pts = [(p["x"], p["y"]) for p in line]
                for i in range(len(pts) - 1):
                    self.canvas.create_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                                           fill="#b3b3b3", width=1)  # rgba(255,255,255,0.7) 近似

            # 2. Draw Cross Streets (Lateral connection)
            t = 0
            while t <= 1:
                sorted_lines = sorted(lines, key=lambda ln: ln[0]["offset"])
                cross_pts = []
                for line in sorted_lines:
                    p = next((lp for lp in line if lp["t"] >= t), line[-1])
                    cross_pts.append((p["x"], p["y"]))
                for i in range(len(cross_pts) - 1):
                    self.canvas.create_line(cross_pts[i][0], cross_pts[i][1], cross_pts[i + 1][0], cross_pts[i + 1][1],
                                           fill="#4d4d4d", width=0.5)  # rgba(255,255,255,0.3) 近似
                t += 0.05

            # 3. PARCELS (Mode C)
            if s["runMode"] == "C":
                sorted_lines = sorted(lines, key=lambda ln: ln[0]["offset"])
                segments = 15
                for i in range(len(sorted_lines) - 1):
                    line_a = sorted_lines[i]
                    line_b = sorted_lines[i + 1]
                    for seg in range(segments):
                        t_start = seg / segments
                        t_end = (seg + 0.8) / segments

                        p1 = next((p for p in line_a if p["t"] >= t_start), line_a[-1])
                        p2 = next((p for p in line_b if p["t"] >= t_start), line_b[-1])
                        p3 = next((p for p in line_b if p["t"] >= t_end), line_b[-1])
                        p4 = next((p for p in line_a if p["t"] >= t_end), line_a[-1])

                        if random.random() > 0.15:
                            # rgba(255,255,255, 0.05~0.15) 在黑色背景上的近似灰度
                            gray = int(255 * (0.05 + random.random() * 0.1))
                            fill_color = f"#{gray:02x}{gray:02x}{gray:02x}"
                            self.canvas.create_polygon(
                                p1["x"], p1["y"], p2["x"], p2["y"], p3["x"], p3["y"], p4["x"], p4["y"],
                                fill=fill_color, outline="#1a1a1a")  # rgba(255,255,255,0.1) 近似

    def _bind_events(self):
        def on_change(*args):
            self.update_state()

        for key, ctrl in self.controls.items():
            if key in ("rotVal", "spacingVal", "scaleVal", "noiseScaleVal", "noiseStrVal", "crossVal"):
                continue
            if isinstance(ctrl, tk.Scale):
                ctrl.config(command=lambda v, k=key: self.update_state())
            elif isinstance(ctrl, (ttk.Combobox, tk.Entry)):
                ctrl.bind("<<ComboboxSelected>>" if isinstance(ctrl, ttk.Combobox) else "<KeyRelease>", lambda e: self.update_state())
            elif isinstance(ctrl, tk.BooleanVar):
                pass  # 通过 Reset 和按钮处理

        # 绑定所有控件的变更
        for w in self.root.winfo_children():
            self._bind_recursive(w, self.update_state)

    def _bind_recursive(self, widget, callback):
        if isinstance(widget, tk.Scale):
            widget.config(command=lambda v: callback())
        elif isinstance(widget, ttk.Combobox):
            widget.bind("<<ComboboxSelected>>", lambda e: callback())
        elif isinstance(widget, tk.Entry):
            widget.bind("<KeyRelease>", lambda e: callback())
        elif isinstance(widget, tk.Checkbutton):
            pass  # 需在创建时绑定
        for child in widget.winfo_children():
            self._bind_recursive(child, callback)

    def _reset(self):
        self.controls["seedRotation"].set(0)
        self.controls["lineSpacing"].set(40)
        self.controls["posCount"].delete(0, tk.END)
        self.controls["posCount"].insert(0, "10")
        self.controls["negCount"].delete(0, tk.END)
        self.controls["negCount"].insert(0, "10")
        self.controls["noiseEnabled"].set(False)
        self.update_state()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = UrbanFieldGenerator()
    app.run()
