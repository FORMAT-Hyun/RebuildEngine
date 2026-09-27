"""Simple 2D Camera."""

class Camera:
    def __init__(self, width: int = 800, height: int = 600):
        self.x = 0.0
        self.y = 0.0
        self.width = width
        self.height = height
        self.target = None  # Instance or None
        self.smooth = 0.15

    def follow(self, target, smooth: float = 0.15):
        self.target = target
        self.smooth = smooth

    def update(self):
        if self.target is not None:
            tx = self.target.x - self.width / 2 + getattr(self.target, "width", 0) / 2
            ty = self.target.y - self.height / 2 + getattr(self.target, "height", 0) / 2
            self.x += (tx - self.x) * self.smooth
            self.y += (ty - self.y) * self.smooth

    def apply(self, world_x: float, world_y: float):
        return world_x - self.x, world_y - self.y

    def set_position(self, x: float, y: float):
        self.x = x
        self.y = y
