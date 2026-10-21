import re
import json
import base64
from dataclasses import dataclass, asdict

VALID_STYLES = ("cross", "dot", "circle", "t_shape", "cross_dot")
_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _clamp(value, lo, hi, cast):
    """Coerce to cast() then clamp into [lo, hi]; never raises."""
    try:
        value = cast(value)
    except (TypeError, ValueError):
        value = lo
    return max(lo, min(hi, value))


@dataclass
class CrosshairConfig:
    enabled: bool = True
    style: str = "cross_dot"      # "cross", "dot", "circle", "t_shape", "cross_dot"
    size: int = 10                # Length of arms in px
    thickness: int = 2            # Thickness of lines in px
    gap: int = 4                  # Center gap in px
    dot_size: int = 3             # Center dot diameter
    color: str = "#00FF00"        # Hex color
    opacity: float = 1.0          # 0.2 to 1.0
    outline: bool = True          # Dark border
    outline_thickness: int = 1    # Outline border width
    outline_color: str = "#000000"

    def __post_init__(self):
        """Validate and clamp every field so the app can never crash on bad input."""
        self.enabled = self._to_bool(self.enabled, True)
        if self.style not in VALID_STYLES:
            self.style = "cross"
        self.size = _clamp(self.size, 0, 60, int)
        self.thickness = _clamp(self.thickness, 1, 10, int)
        self.gap = _clamp(self.gap, 0, 40, int)
        self.dot_size = _clamp(self.dot_size, 1, 12, int)
        self.opacity = _clamp(self.opacity, 0.2, 1.0, float)
        self.color = self._to_hex(self.color, "#00FF00")
        self.outline = self._to_bool(self.outline, True)
        self.outline_thickness = _clamp(self.outline_thickness, 1, 3, int)
        self.outline_color = self._to_hex(self.outline_color, "#000000")

    @staticmethod
    def _to_bool(value, default):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    @staticmethod
    def _to_hex(value, default):
        value = str(value).strip()
        if not value.startswith("#"):
            value = "#" + value
        return value.upper() if _HEX_RE.match(value) else default

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        if not isinstance(data, dict):
            raise ValueError("Konfiguratsiya obyekti (dict) kutilgan edi.")
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def to_share_code(self) -> str:
        j = json.dumps(self.to_dict())
        b = base64.b64encode(j.encode("utf-8")).decode("ascii")
        return f"CRX-{b}"

    @classmethod
    def from_share_code(cls, code: str):
        code = str(code).strip()
        if code.startswith("CRX-"):
            code = code[4:]
        try:
            j = base64.b64decode(code.encode("ascii"), validate=True).decode("utf-8")
            data = json.loads(j)
        except Exception as e:
            raise ValueError(f"Ulashish kodini o'qib bo'lmadi: {e}") from e
        return cls.from_dict(data)


PRESETS = {
    "AWP Red Sniper Dot": CrosshairConfig(
        style="dot", dot_size=4, size=0, thickness=1, gap=0,
        color="#FF1E1E", outline=True, outline_thickness=1, outline_color="#000000"
    ),
    "CS 1.6 Classic Green": CrosshairConfig(
        style="cross", size=12, thickness=2, gap=5,
        color="#00FF00", outline=False
    ),
    "Valorant Cyan Pro": CrosshairConfig(
        style="cross", size=6, thickness=2, gap=3,
        color="#00FFFF", outline=True, outline_thickness=1
    ),
    "Circle + Dot": CrosshairConfig(
        style="circle", size=10, thickness=2, gap=2, dot_size=2,
        color="#FFE600", outline=True
    ),
    "Cross + Center Dot": CrosshairConfig(
        style="cross_dot", size=8, thickness=2, gap=4, dot_size=3,
        color="#00FF66", outline=True, outline_thickness=1
    ),
    "Minimalist Purple Dot": CrosshairConfig(
        style="dot", dot_size=3, color="#BF00FF",
        outline=True, outline_thickness=1
    ),
}
