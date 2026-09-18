
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class MeasurementRecommendation:
    bearing_id: Optional[str] = None
    point: Optional[str] = None
    direction: Optional[str] = None
    measurement_id: Optional[str] = None
    priority: int = 1
    reason: str = ""
    target_mechanisms: List[str] = field(default_factory=list)
    information_type: str = "ADDITIONAL EVIDENCE"


@dataclass
class RecommendationReport:
    recommendations: List[MeasurementRecommendation] = field(
        default_factory=list
    )
    available_measurements: List[str] = field(
        default_factory=list
    )
    missing_slots: List[str] = field(
        default_factory=list
    )
    notes: List[str] = field(
        default_factory=list
    )


def _get(obj: Any, name: str, default=None):
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def _clean_list(value: Any) -> List[str]:
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]

    result = []

    for item in values:
        if item is None:
            continue

        text = str(item).strip()

        if text:
            result.append(text)

    return result


class MeasurementRecommendationEngine:

    DIRECTIONS = (
        "Horizontal",
        "Vertical",
        "Axial",
    )

    def __init__(self, directions=None):
        if directions is None:
            self.directions = list(self.DIRECTIONS)
        else:
            self.directions = list(directions)

    def recommend(
        self,
        fusion_report: Any,
        diagnostic_report: Any = None,
    ) -> RecommendationReport:

        available_measurements = self._get_available_measurements(
            fusion_report
        )

        missing_slots = self._get_missing_slots(
            fusion_report
        )

        recommendations = []

        # --------------------------------------------------
        # First use explicit missing slots
        # --------------------------------------------------

        for slot in missing_slots:
            recommendation = self._recommend_from_slot(
                slot,
                diagnostic_report,
            )

            if recommendation is not None:
                recommendations.append(
                    recommendation
                )

        # --------------------------------------------------
        # If no explicit slots exist,
        # infer useful missing directions.
        # --------------------------------------------------

        if not recommendations:
            recommendations.extend(
                self._infer_missing_directions(
                    available_measurements,
                    diagnostic_report,
                )
            )

        recommendations = self._deduplicate(
            recommendations
        )

        recommendations.sort(
            key=lambda item: (
                item.priority,
                str(item.bearing_id),
                str(item.direction),
            )
        )

        notes = [
            "Recommendations are based only on "
            "measurements actually received.",
            "Missing measurements are not treated "
            "as negative fault evidence.",
            "Recommendations indicate additional "
            "information that may reduce uncertainty.",
        ]

        return RecommendationReport(
            recommendations=recommendations,
            available_measurements=available_measurements,
            missing_slots=missing_slots,
            notes=notes,
        )

    def _get_available_measurements(
        self,
        fusion_report: Any,
    ) -> List[str]:

        values = _clean_list(
            _get(
                fusion_report,
                "available_measurements",
                [],
            )
        )

        return sorted(set(values))

    def _get_missing_slots(
        self,
        fusion_report: Any,
    ) -> List[str]:

        values = _clean_list(
            _get(
                fusion_report,
                "missing_expected_slots",
                [],
            )
        )

        return sorted(set(values))

    def _recommend_from_slot(
        self,
        slot: str,
        diagnostic_report: Any,
    ) -> Optional[MeasurementRecommendation]:

        text = str(slot).strip()

        if not text:
            return None

        bearing_id = None
        direction = None

        if "-" in text:
            parts = [
                part.strip()
                for part in text.split("-")
                if part.strip()
            ]

            if len(parts) >= 2:
                bearing_id = parts[0]
                direction = self._normalize_direction(
                    parts[-1]
                )

        targets = self._get_target_mechanisms(
            diagnostic_report
        )

        reason = (
            "This expected measurement slot is missing "
            "and can provide additional evidence."
        )

        if targets:
            reason += (
                " It can help compare the currently "
                "compatible fault mechanisms."
            )

        return MeasurementRecommendation(
            bearing_id=bearing_id,
            point=bearing_id,
            direction=direction,
            measurement_id=text,
            priority=1,
            reason=reason,
            target_mechanisms=targets,
            information_type="MISSING EXPECTED MEASUREMENT",
        )

    def _infer_missing_directions(
        self,
        available_measurements: List[str],
        diagnostic_report: Any,
    ) -> List[MeasurementRecommendation]:

        recommendations = []

        bearings = set()

        for measurement in available_measurements:

            text = str(measurement)

            if "-" not in text:
                continue

            parts = text.split("-")

            if not parts:
                continue

            bearing = parts[0].strip()

            if bearing:
                bearings.add(bearing)

        targets = self._get_target_mechanisms(
            diagnostic_report
        )

        # --------------------------------------------------
        # No bearing information
        # --------------------------------------------------

        if not bearings:

            recommendations.append(
                MeasurementRecommendation(
                    bearing_id=None,
                    point=None,
                    direction="Axial",
                    measurement_id=None,
                    priority=2,
                    reason=(
                        "An Axial measurement is not "
                        "currently represented in the "
                        "available measurement set."
                    ),
                    target_mechanisms=targets,
                    information_type="DIRECTIONAL EVIDENCE",
                )
            )

            return recommendations

        # --------------------------------------------------
        # Existing directions per bearing
        # --------------------------------------------------

        existing = {}

        for bearing in bearings:
            existing[bearing] = set()

        for measurement in available_measurements:

            text = str(measurement)

            if "-" not in text:
                continue

            parts = text.split("-")

            if len(parts) < 2:
                continue

            bearing = parts[0].strip()

            direction = self._normalize_direction(
                parts[-1]
            )

            if bearing in existing and direction:
                existing[bearing].add(direction)

        # --------------------------------------------------
        # Recommend Axial if H and V exist
        # --------------------------------------------------

        for bearing in sorted(bearings):

            current = existing.get(
                bearing,
                set(),
            )

            if (
                "Horizontal" in current
                and "Vertical" in current
                and "Axial" not in current
            ):

                recommendations.append(
                    MeasurementRecommendation(
                        bearing_id=bearing,
                        point=bearing,
                        direction="Axial",
                        measurement_id=None,
                        priority=2,
                        reason=(
                            "Horizontal and Vertical "
                            "measurements are available, "
                            "while Axial is absent. "
                            "An Axial measurement can "
                            "provide additional directional "
                            "evidence."
                        ),
                        target_mechanisms=targets,
                        information_type="DIRECTIONAL EVIDENCE",
                    )
                )

        return recommendations

    def _get_target_mechanisms(
        self,
        diagnostic_report: Any,
    ) -> List[str]:

        if diagnostic_report is None:
            return []

        diagnostics = _get(
            diagnostic_report,
            "diagnostics",
            [],
        )

        targets = []

        for item in diagnostics:

            mechanism = _get(
                item,
                "mechanism",
                None,
            )

            if mechanism:
                targets.append(
                    str(mechanism)
                )

        return sorted(set(targets))

    def _normalize_direction(
        self,
        value: Any,
    ) -> Optional[str]:

        if value is None:
            return None

        text = str(value).strip().upper()

        mapping = {
            "H": "Horizontal",
            "HOR": "Horizontal",
            "HORIZONTAL": "Horizontal",

            "V": "Vertical",
            "VER": "Vertical",
            "VERTICAL": "Vertical",

            "A": "Axial",
            "AX": "Axial",
            "AXIAL": "Axial",
        }

        return mapping.get(
            text,
            str(value).strip(),
        )

    def _deduplicate(
        self,
        recommendations: List[
            MeasurementRecommendation
        ],
    ) -> List[MeasurementRecommendation]:

        result = []
        seen = set()

        for item in recommendations:

            key = (
                item.bearing_id,
                item.direction,
                item.measurement_id,
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(item)

        return result


def print_recommendation_report(
    report: RecommendationReport,
):

    print()
    print("=" * 75)
    print("ADDITIONAL MEASUREMENT RECOMMENDATIONS")
    print("=" * 75)

    if not report.recommendations:

        print(
            "No additional measurement recommendation "
            "was generated."
        )

    else:

        for index, recommendation in enumerate(
            report.recommendations,
            start=1,
        ):

            print()
            print(
                f"{index}. "
                f"{recommendation.information_type}"
            )

            print(
                f"   Priority          : "
                f"{recommendation.priority}"
            )

            if recommendation.bearing_id:
                print(
                    f"   Bearing           : "
                    f"{recommendation.bearing_id}"
                )

            if recommendation.point:
                print(
                    f"   Point             : "
                    f"{recommendation.point}"
                )

            if recommendation.direction:
                print(
                    f"   Direction         : "
                    f"{recommendation.direction}"
                )

            if recommendation.measurement_id:
                print(
                    f"   Measurement ID    : "
                    f"{recommendation.measurement_id}"
                )

            if recommendation.target_mechanisms:
                print(
                    "   Target mechanisms : "
                    + ", ".join(
                        recommendation.target_mechanisms
                    )
                )

            print(
                f"   Reason            : "
                f"{recommendation.reason}"
            )

    print()

    for note in report.notes:
        print(
            f"NOTE: {note}"
        )

    print("=" * 75)

