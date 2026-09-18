from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Peak:
    frequency_hz: float
    amplitude: float
    prominence: Optional[float] = None
    source: str = "unknown"

    def to_dict(self):
        return {
            "frequency_hz": round(self.frequency_hz, 4),
            "amplitude": round(self.amplitude, 4),
            "prominence": (
                round(self.prominence, 4)
                if self.prominence is not None
                else None
            ),
            "source": self.source,
        }


@dataclass
class Spectrum:
    frequency_hz: List[float]
    amplitude: List[float]

    rpm: Optional[float] = None

    machine_name: Optional[str] = None
    measurement_point: Optional[str] = None
    direction: Optional[str] = None

    source: str = "unknown"

    peaks: List[Peak] = field(default_factory=list)

    def validate(self):
        if len(self.frequency_hz) != len(self.amplitude):
            raise ValueError(
                "Frequency و Amplitude باید تعداد یکسانی داشته باشند."
            )

        if len(self.frequency_hz) < 3:
            raise ValueError(
                "داده FFT برای تحلیل کافی نیست."
            )

    def to_dict(self):
        return {
            "rpm": self.rpm,
            "machine_name": self.machine_name,
            "measurement_point": self.measurement_point,
            "direction": self.direction,
            "source": self.source,
            "peaks": [p.to_dict() for p in self.peaks],
        }