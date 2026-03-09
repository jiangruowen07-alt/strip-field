"""
ScalarFieldEngine - 从标量场生成梯度场，再生成垂直流线
适合地价等高线等场景：等高线垂直于梯度，流线沿等高线方向
"""

import math


class ScalarFieldEngine:
    """
    标量场引擎。
    - 从标量场 f(x,y) 计算梯度 ∇f = (∂f/∂x, ∂f/∂y)
    - 流线方向 = 梯度旋转90°（垂直于梯度，即沿等高线方向）
    """

    def __init__(self, scalar_field=None, gradient_field=None, h=1e-6):
        """
        Args:
            scalar_field: callable f(x, y) -> float，若提供则自动数值求梯度
            gradient_field: callable (x, y) -> (gx, gy)，若提供则直接使用
            h: 数值微分步长
        """
        self.scalar_field = scalar_field
        self.gradient_field = gradient_field
        self.h = h

    def gradient_at(self, x, y):
        """
        在 (x,y) 处的梯度。
        若提供 gradient_field 则直接调用；否则从 scalar_field 数值求导。
        """
        if self.gradient_field is not None:
            return self.gradient_field(x, y)
        if self.scalar_field is None:
            return (0.0, 0.0)
        h = self.h
        fx_plus = self.scalar_field(x + h, y)
        fx_minus = self.scalar_field(x - h, y)
        fy_plus = self.scalar_field(x, y + h)
        fy_minus = self.scalar_field(x, y - h)
        gx = (fx_plus - fx_minus) / (2 * h)
        gy = (fy_plus - fy_minus) / (2 * h)
        return (gx, gy)

    def perpendicular_direction(self, x, y, clockwise=True):
        """
        垂直于梯度的方向（沿等高线）。
        clockwise=True: (-gy, gx)；False: (gy, -gx)
        """
        gx, gy = self.gradient_at(x, y)
        L = math.sqrt(gx * gx + gy * gy) or 1e-10
        if L < 1e-12:
            return (1.0, 0.0)  # 平坦区域默认向右
        if clockwise:
            return (-gy / L, gx / L)
        return (gy / L, -gx / L)

    def field_at(self, x, y):
        """
        流场向量 at (x,y)。
        返回垂直于梯度的单位向量，适合用于流线积分。
        """
        return self.perpendicular_direction(x, y, clockwise=True)

    def sample_streamline_directions(self, bounds, nx=20, ny=20):
        """
        在矩形域内采样流场方向，用于可视化或调试。
        bounds: (xmin, ymin, xmax, ymax)
        """
        xmin, ymin, xmax, ymax = bounds
        samples = []
        for i in range(nx):
            for j in range(ny):
                x = xmin + (xmax - xmin) * (i + 0.5) / nx
                y = ymin + (ymax - ymin) * (j + 0.5) / ny
                vx, vy = self.field_at(x, y)
                samples.append({"x": x, "y": y, "vx": vx, "vy": vy})
        return samples


def default_land_price_field(x, y, center_x=600, center_y=100, sigma=200):
    """
    示例：简化的地价标量场（高斯型，中心高）
    适合接等高线逻辑：等高线为等值线，流线沿等高线
    """
    dx = x - center_x
    dy = y - center_y
    return math.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma))


def contour_lines_from_scalar(scalar_field, bounds, levels, engine=None):
    """
    从标量场提取等高线（等值线）。
    levels: 等值列表
    等高线需用 marching squares 或类似算法，此处仅提供接口占位。
    """
    _ = engine or ScalarFieldEngine(scalar_field=scalar_field)
    return []  # TODO: marching squares 实现
