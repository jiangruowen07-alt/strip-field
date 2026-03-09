"""
StreamlineIntegrator - 从 seed points 积分出真正流线
支持 Euler 与 RK4 积分方法
"""

import math


METHOD_EULER = "euler"
METHOD_RK4 = "rk4"


class StreamlineIntegrator:
    """
    流线积分器。
    给定向量场 field(x, y) -> (vx, vy)，从种子点出发积分得到流线。
    """

    def __init__(self, field, method=METHOD_RK4, step_size=2.0, max_steps=500):
        """
        Args:
            field: callable (x, y) -> (vx, vy)
            method: "euler" | "rk4"
            step_size: 积分步长
            max_steps: 单条流线最大步数
        """
        self.field = field
        self.method = method
        self.step_size = step_size
        self.max_steps = max_steps

    def _euler_step(self, x, y, dt):
        """Euler 单步"""
        vx, vy = self.field(x, y)
        L = math.sqrt(vx * vx + vy * vy) or 1e-10
        return x + vx / L * dt, y + vy / L * dt

    def _rk4_step(self, x, y, dt):
        """RK4 单步"""
        v1x, v1y = self.field(x, y)
        L1 = math.sqrt(v1x * v1x + v1y * v1y) or 1e-10
        k1x, k1y = v1x / L1 * dt, v1y / L1 * dt

        v2x, v2y = self.field(x + 0.5 * k1x, y + 0.5 * k1y)
        L2 = math.sqrt(v2x * v2x + v2y * v2y) or 1e-10
        k2x, k2y = v2x / L2 * dt, v2y / L2 * dt

        v3x, v3y = self.field(x + 0.5 * k2x, y + 0.5 * k2y)
        L3 = math.sqrt(v3x * v3x + v3y * v3y) or 1e-10
        k3x, k3y = v3x / L3 * dt, v3y / L3 * dt

        v4x, v4y = self.field(x + k3x, y + k3y)
        L4 = math.sqrt(v4x * v4x + v4y * v4y) or 1e-10
        k4x, k4y = v4x / L4 * dt, v4y / L4 * dt

        x_new = x + (k1x + 2 * k2x + 2 * k3x + k4x) / 6
        y_new = y + (k1y + 2 * k2y + 2 * k3y + k4y) / 6
        return x_new, y_new

    def _step(self, x, y, dt):
        if self.method == METHOD_EULER:
            return self._euler_step(x, y, dt)
        return self._rk4_step(x, y, dt)

    def integrate_forward(self, x0, y0, bounds=None):
        """
        从 (x0, y0) 正向积分一条流线。
        bounds: (xmin, ymin, xmax, ymax)，超出则停止
        """
        pts = [{"x": x0, "y": y0, "t": 0}]
        x, y = x0, y0
        dt = self.step_size
        for i in range(self.max_steps - 1):
            x, y = self._step(x, y, dt)
            if bounds:
                xmin, ymin, xmax, ymax = bounds
                if x < xmin or x > xmax or y < ymin or y > ymax:
                    break
            pts.append({"x": x, "y": y, "t": (i + 1) * dt})
        return pts

    def integrate_backward(self, x0, y0, bounds=None):
        """从 (x0, y0) 反向积分（场方向取反）"""
        orig_field = self.field

        def neg_field(x, y):
            vx, vy = orig_field(x, y)
            return (-vx, -vy)

        self.field = neg_field
        try:
            pts = self.integrate_forward(x0, y0, bounds)
        finally:
            self.field = orig_field
        pts.reverse()
        for i, p in enumerate(pts):
            p["t"] = -i * self.step_size
        return pts

    def integrate_bidirectional(self, x0, y0, bounds=None):
        """双向积分，返回一条完整流线"""
        fwd = self.integrate_forward(x0, y0, bounds)
        bwd = self.integrate_backward(x0, y0, bounds)
        # 去掉 bwd 的起点（与 fwd 重复）
        if len(bwd) > 1:
            bwd = bwd[1:]
        return bwd + fwd

    def integrate_from_seeds(self, seed_points, bounds=None, bidirectional=True):
        """
        从多个种子点积分出多条流线。
        seed_points: [(x,y), ...]
        """
        lines = []
        for x0, y0 in seed_points:
            if bidirectional:
                pts = self.integrate_bidirectional(x0, y0, bounds)
            else:
                pts = self.integrate_forward(x0, y0, bounds)
            lines.append(pts)
        return lines
