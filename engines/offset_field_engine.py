"""
OffsetFieldEngine - 基于母线的偏移场引擎
保留原有逻辑作为模式：parallel, tangent_drift, normal_band, contour_bulge, strip_growth, hybrid, noise_modified
"""

import math

from config import T_COUNT, T_STEP
from utils import noise


# 模式常量（与 UI 的 fieldType 1-7 对应）
MODE_PARALLEL = "parallel"           # 1. Parallel Offset
MODE_TANGENT_DRIFT = "tangent_drift" # 2. Curve Tangent
MODE_NORMAL_BAND = "normal_band"     # 3. Curve Normal
MODE_CONTOUR_BULGE = "contour_bulge" # 4. Distance Contour
MODE_STRIP_GROWTH = "strip_growth"   # 5. Strip Growth
MODE_HYBRID = "hybrid"               # 6. Hybrid Tangent-Normal
MODE_NOISE_MODIFIED = "noise_modified"  # 7. Noise-Modified (可叠加到任意模式)


def _mode_from_field_type(ft):
    """将 fieldType 字符串转为模式名"""
    mapping = {
        "1": MODE_PARALLEL,
        "2": MODE_TANGENT_DRIFT,
        "3": MODE_NORMAL_BAND,
        "4": MODE_CONTOUR_BULGE,
        "5": MODE_STRIP_GROWTH,
        "6": MODE_HYBRID,
        "7": MODE_NOISE_MODIFIED,
    }
    return mapping.get(str(ft), MODE_PARALLEL)


class OffsetFieldEngine:
    """
    基于单条母线的偏移场引擎。
    支持多种扩张模式，可叠加噪声。
    """

    def __init__(self, mode=None, noise_enabled=False, noise_scale=0.005, noise_strength=20):
        """
        Args:
            mode: parallel | tangent_drift | normal_band | contour_bulge | strip_growth | hybrid | noise_modified
            noise_enabled: 是否叠加噪声扰动
            noise_scale: 噪声尺度
            noise_strength: 噪声强度
        """
        self.mode = mode or MODE_PARALLEL
        self.noise_enabled = noise_enabled
        self.noise_scale = noise_scale
        self.noise_strength = noise_strength

    @classmethod
    def from_state(cls, state):
        """从 app state 创建"""
        ft = state.get("fieldType", "1")
        mode = _mode_from_field_type(ft)
        # 若选 7 则强制 noise_modified 模式，否则用 noiseEnabled 决定是否叠加噪声
        if mode == MODE_NOISE_MODIFIED:
            return cls(mode=mode, noise_enabled=True,
                       noise_scale=state.get("noiseScale", 0.005),
                       noise_strength=state.get("noiseStrength", 20))
        return cls(mode=mode,
                   noise_enabled=state.get("noiseEnabled", False),
                   noise_scale=state.get("noiseScale", 0.005),
                   noise_strength=state.get("noiseStrength", 20))

    def _apply_offset_mode(self, px, py, t, offset_dist, nx, ny, tx, ty, line_index):
        """根据模式计算偏移后的点"""
        if self.mode == MODE_PARALLEL:
            px += nx * offset_dist
            py += ny * offset_dist
        elif self.mode == MODE_TANGENT_DRIFT:
            px += tx * offset_dist * 0.2
            py += ny * offset_dist
        elif self.mode == MODE_NORMAL_BAND:
            factor = math.sin(t * math.pi)
            px += nx * offset_dist * factor
            py += ny * offset_dist * factor
        elif self.mode == MODE_CONTOUR_BULGE:
            px += nx * offset_dist
            py += ny * offset_dist
            bulge = math.sin(t * math.pi) * (offset_dist * 0.3)
            px += nx * bulge
            py += ny * bulge
        elif self.mode == MODE_STRIP_GROWTH:
            px += nx * offset_dist
            py += ny * offset_dist
            if line_index % 2 == 0:
                px += tx * 20
        elif self.mode == MODE_HYBRID:
            mix = math.cos(t * math.pi * 2)
            px += (nx * (1 - mix) + tx * mix) * offset_dist
            py += (ny * (1 - mix) + ty * mix) * offset_dist
        else:  # noise_modified 或默认：按 parallel 处理
            px += nx * offset_dist
            py += ny * offset_dist
        return px, py

    def _apply_noise(self, px, py):
        """叠加噪声扰动"""
        if not self.noise_enabled:
            return px, py
        ns = self.noise_scale * 100
        n = noise(px * ns, py * ns)
        return px + n * self.noise_strength, py + n * self.noise_strength

    def generate_lines(self, arr, state, params=None):
        """
        从预计算数组生成扩张线。
        arr: (xs, ys, nxs, nys, txs, tys)
        """
        params = params or {}
        xs, ys, nxs, nys, txs, tys = arr
        sp = params.get("lineSpacing", state.get("lineSpacing", 40))
        sc = params.get("spacingScale", state.get("spacingScale", 1.0))
        sm = params.get("spacingMode", state.get("spacingMode", "linear"))
        pos = params.get("posCount", state.get("posCount", 10))
        neg = params.get("negCount", state.get("negCount", 10))
        ox = params.get("offsetX", 0)
        oy = params.get("offsetY", 0)

        lines = []
        line_index = 0
        for side in range(2):
            count = pos if side == 1 else neg
            start_i = 1 if side == 0 else 0
            for i in range(start_i, count + 1):
                actual_index = -i if side == 0 else i
                if sm == "linear":
                    offset_dist = actual_index * sp * sc
                elif sm == "exponential":
                    offset_dist = (1 if actual_index >= 0 else -1) * (abs(actual_index) ** 1.5) * sp * sc * 0.5
                else:
                    offset_dist = actual_index * sp * (1 + abs(actual_index) * 0.1) * sc
                line_points = []
                for ti in range(T_COUNT):
                    t = ti * T_STEP
                    px = xs[ti] + ox
                    py = ys[ti] + oy
                    nx, ny = nxs[ti], nys[ti]
                    tx, ty = txs[ti], tys[ti]
                    px, py = self._apply_offset_mode(px, py, t, offset_dist, nx, ny, tx, ty, line_index)
                    px, py = self._apply_noise(px, py)
                    line_points.append({"x": px, "y": py, "t": t, "offset": offset_dist})
                lines.append(line_points)
                line_index += 1
        return lines
