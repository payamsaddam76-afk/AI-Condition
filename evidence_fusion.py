from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from collections import defaultdict


# =============================================================================
# AI CONDITION
# EVIDENCE FUSION
# =============================================================================
#
# This module combines evidence from multiple vibration measurements.
#
# It does NOT:
#   - declare a final fault
#   - treat database documents as independent votes
#   - treat missing measurements as negative evidence
#   - treat one database-pattern mismatch as proof against a fault
#
# =============================================================================


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MeasurementEvidence:

    measurement_id: str

    rpm: float

    features: Any
    matrices: List[Any]

    bearing_id: Optional[str] = None
    point: Optional[str] = None
    direction: Optional[str] = None
    component: Optional[str] = None

    image_path: Optional[str] = None
    sensor_type: Optional[str] = None

    def location_label(self) -> str:

        parts = []

        if self.bearing_id:
            parts.append(str(self.bearing_id))

        if self.point:
            parts.append(str(self.point))

        if not parts:
            return "Unknown Location"

        return " / ".join(parts)

    def display_label(self) -> str:

        location = self.location_label()

        if self.direction:
            return f"{location}-{self.direction}"

        return location


@dataclass
class FusionCandidate:

    mechanism: str

    status: str = "LIMITED EVIDENCE"

    supporting_measurements: List[str] = field(
        default_factory=list
    )

    database_pattern_contradictions: List[str] = field(
        default_factory=list
    )

    directions: List[str] = field(
        default_factory=list
    )

    database_directions: List[str] = field(
        default_factory=list
    )

    locations: List[str] = field(
        default_factory=list
    )

    components: List[str] = field(
        default_factory=list
    )

    supporting_orders: List[float] = field(
        default_factory=list
    )

    missing_pattern_orders: List[float] = field(
        default_factory=list
    )

    context_support: List[str] = field(
        default_factory=list
    )

    database_documents: List[str] = field(
        default_factory=list
    )

    database_pattern_hits: int = 0

    measurement_support_hits: int = 0

    actual_fft_contradictions: int = 0

    reasons: List[str] = field(
        default_factory=list
    )

    @property
    def support_count(self) -> int:

        return len(
            set(
                self.supporting_measurements
            )
        )

    @property
    def pattern_contradiction_count(self) -> int:

        return len(
            set(
                self.database_pattern_contradictions
            )
        )

    def normalize(self) -> None:

        self.supporting_measurements = sorted(
            set(
                str(x)
                for x in self.supporting_measurements
                if x
            )
        )

        self.database_pattern_contradictions = sorted(
            set(
                str(x)
                for x in self.database_pattern_contradictions
                if x
            )
        )

        self.directions = sorted(
            set(
                str(x).strip()
                for x in self.directions
                if x
            )
        )

        self.database_directions = sorted(
            set(
                str(x).strip()
                for x in self.database_directions
                if x
            )
        )

        self.locations = sorted(
            set(
                str(x)
                for x in self.locations
                if x
            )
        )

        self.components = sorted(
            set(
                str(x)
                for x in self.components
                if x
            )
        )

        self.context_support = sorted(
            set(
                str(x)
                for x in self.context_support
                if x
            )
        )

        self.database_documents = sorted(
            set(
                str(x)
                for x in self.database_documents
                if x
            )
        )

        self.supporting_orders = sorted(
            set(
                float(x)
                for x in self.supporting_orders
            )
        )

        self.missing_pattern_orders = sorted(
            set(
                float(x)
                for x in self.missing_pattern_orders
            )
        )


# =============================================================================
# EXPECTED SLOT NORMALIZATION
# =============================================================================

def _normalize_expected_slot(
    slot: Any
) -> Optional[Tuple[str, str]]:

    # -------------------------------------------------------------------------
    # Dictionary format
    #
    # Example:
    #
    # {
    #     "bearing": "B1",
    #     "direction": "Horizontal"
    # }
    #
    # -------------------------------------------------------------------------

    if isinstance(
        slot,
        dict
    ):

        bearing = slot.get(
            "bearing",
            slot.get(
                "bearing_id",
                slot.get(
                    "point",
                    "Unknown"
                )
            )
        )

        direction = slot.get(
            "direction",
            "?"
        )

        if bearing is None:
            bearing = "Unknown"

        if direction is None:
            direction = "?"

        return (
            str(bearing).strip(),
            str(direction).strip(),
        )

    # -------------------------------------------------------------------------
    # Tuple / list format
    #
    # Example:
    #
    # ("B1", "Horizontal")
    #
    # -------------------------------------------------------------------------

    if isinstance(
        slot,
        (
            tuple,
            list
        )
    ):

        if len(slot) < 2:
            return None

        bearing = slot[0]
        direction = slot[1]

        if bearing is None:
            bearing = "Unknown"

        if direction is None:
            direction = "?"

        return (
            str(bearing).strip(),
            str(direction).strip(),
        )

    return None


def _normalize_expected_slots(
    slots: Optional[Sequence[Any]]
) -> List[Tuple[str, str]]:

    if not slots:
        return []

    result = []

    for slot in slots:

        normalized = (
            _normalize_expected_slot(
                slot
            )
        )

        if normalized is None:

            print(
                "WARNING: Invalid expected slot ignored:",
                repr(slot)
            )

            continue

        result.append(
            normalized
        )

    # -------------------------------------------------------------------------
    # Remove duplicates while preserving deterministic order.
    # -------------------------------------------------------------------------

    return sorted(
        set(result)
    )


# =============================================================================
# FUSION REPORT
# =============================================================================

@dataclass
class FusionReport:

    measurements: List[MeasurementEvidence]

    expected_measurements: Optional[int] = None

    expected_slots: List[
        Tuple[str, str]
    ] = field(
        default_factory=list
    )

    candidates: List[FusionCandidate] = field(
        default_factory=list
    )

    def __post_init__(
        self
    ):

        # ---------------------------------------------------------------------
        # IMPORTANT FIX
        #
        # expected_slots can come from the UI as dictionaries:
        #
        # {
        #     "bearing": "B1",
        #     "direction": "Horizontal"
        # }
        #
        # Internally we ALWAYS convert them to:
        #
        # ("B1", "Horizontal")
        #
        # This prevents:
        #
        # TypeError: unhashable type: 'dict'
        # ---------------------------------------------------------------------

        self.expected_slots = (
            _normalize_expected_slots(
                self.expected_slots
            )
        )

    @property
    def measurements_received(
        self
    ) -> int:

        return len(
            self.measurements
        )

    @property
    def machine_measurement_coverage(
        self
    ) -> Optional[float]:

        if (
            self.expected_measurements is None
            or self.expected_measurements <= 0
        ):
            return None

        return (
            self.measurements_received
            /
            self.expected_measurements
        ) * 100.0

    @property
    def available_directions(
        self
    ) -> List[str]:

        return sorted(
            set(
                str(m.direction)
                for m in self.measurements
                if m.direction
            )
        )

    @property
    def available_slots(
        self
    ) -> List[Tuple[str, str]]:

        slots = []

        for measurement in self.measurements:

            bearing = (
                measurement.bearing_id
                or measurement.point
                or "Unknown"
            )

            direction = (
                measurement.direction
                or "?"
            )

            slots.append(
                (
                    str(bearing).strip(),
                    str(direction).strip()
                )
            )

        return sorted(
            set(slots)
        )

    @property
    def missing_expected_slots(
        self
    ) -> List[Tuple[str, str]]:

        if not self.expected_slots:
            return []

        # ---------------------------------------------------------------------
        # available is guaranteed to contain ONLY hashable tuples.
        # ---------------------------------------------------------------------

        available = set(
            self.available_slots
        )

        missing = []

        for slot in self.expected_slots:

            normalized_slot = (
                _normalize_expected_slot(
                    slot
                )
            )

            if normalized_slot is None:
                continue

            if normalized_slot not in available:

                missing.append(
                    normalized_slot
                )

        return missing


# =============================================================================
# GENERIC HELPERS
# =============================================================================

def _get(
    obj: Any,
    *names: str,
    default=None
):

    if obj is None:
        return default

    if isinstance(
        obj,
        dict
    ):

        for name in names:

            if name in obj:
                return obj[name]

        return default

    for name in names:

        if hasattr(
            obj,
            name
        ):

            try:

                return getattr(
                    obj,
                    name
                )

            except Exception:
                pass

    return default


def _as_list(
    value: Any
) -> List[Any]:

    if value is None:
        return []

    if isinstance(
        value,
        (
            list,
            tuple,
            set
        )
    ):
        return list(value)

    return [value]


def _clean_string_list(
    values: Iterable[Any]
) -> List[str]:

    result = []

    for value in values:

        if value is None:
            continue

        text = str(
            value
        ).strip()

        if text:
            result.append(
                text
            )

    return sorted(
        set(result)
    )


# =============================================================================
# ORDER HELPERS
# =============================================================================

def _order_value(
    value: Any
) -> Optional[float]:

    if value is None:
        return None

    if isinstance(
        value,
        (
            int,
            float
        )
    ):
        return float(value)

    text = str(
        value
    ).strip().upper()

    if text.endswith("X"):
        text = text[:-1]

    try:

        return float(
            text
        )

    except Exception:

        return None


def _format_order(
    value: Any
) -> str:

    number = _order_value(
        value
    )

    if number is None:
        return str(value)

    if number.is_integer():
        return f"{int(number)}X"

    return f"{number:g}X"


def _sorted_orders(
    values: Iterable[Any]
) -> List[float]:

    result = []

    for value in values:

        number = _order_value(
            value
        )

        if number is not None:

            result.append(
                number
            )

    return sorted(
        set(result)
    )


def _format_orders(
    values: Iterable[Any]
) -> str:

    values = _sorted_orders(
        values
    )

    if not values:
        return "None"

    return ", ".join(
        _format_order(value)
        for value in values
    )


# =============================================================================
# MATRIX EXTRACTION
# =============================================================================

def _extract_mechanisms(
    matrix: Any
) -> List[str]:

    values = []

    for name in (
        "fault_mechanisms",
        "fault_mechanism",
        "mechanisms",
        "mechanism",
    ):

        value = _get(
            matrix,
            name
        )

        if value is not None:

            values.extend(
                _as_list(
                    value
                )
            )

    result = []

    for value in values:

        text = str(
            value
        ).strip().lower()

        if text:
            result.append(
                text
            )

    return sorted(
        set(result)
    )


def _extract_document_id(
    matrix: Any
) -> Optional[str]:

    value = _get(
        matrix,
        "document_id",
        "doc_id",
        "source_file",
        "document",
        default=None
    )

    if value is None:
        return None

    if not isinstance(
        value,
        (
            str,
            int,
            float
        )
    ):

        nested = _get(
            value,
            "document_id",
            "source_file",
            "title",
            default=None
        )

        if nested is not None:
            value = nested

    text = str(
        value
    ).strip()

    return (
        text
        if text
        else None
    )


def _extract_expected_orders(
    matrix: Any
) -> List[float]:

    values = []

    for name in (
        "expected_orders",
        "orders",
        "required_orders",
        "typical_orders",
        "strong_orders",
    ):

        value = _get(
            matrix,
            name
        )

        if value is not None:

            values.extend(
                _as_list(
                    value
                )
            )

    return _sorted_orders(
        values
    )


def _extract_matched_orders(
    matrix: Any
) -> List[float]:

    values = []

    for name in (
        "matched_orders",
        "observed_matching_orders",
        "matched",
    ):

        value = _get(
            matrix,
            name
        )

        if value is not None:

            values.extend(
                _as_list(
                    value
                )
            )

    return _sorted_orders(
        values
    )


def _extract_missing_orders(
    matrix: Any
) -> List[float]:

    values = []

    for name in (
        "missing_orders",
        "missing_evidence",
        "missing_pattern_orders",
    ):

        value = _get(
            matrix,
            name
        )

        if value is None:
            continue

        if isinstance(
            value,
            str
        ):

            if value.strip().lower() in {
                "",
                "none",
                "no",
                "null"
            }:

                continue

        values.extend(
            _as_list(
                value
            )
        )

    return _sorted_orders(
        values
    )


def _extract_context(
    matrix: Any
) -> List[str]:

    values = []

    for name in (
        "machine_context",
        "context_matches",
        "context_match",
        "matched_context",
        "context_support",
    ):

        value = _get(
            matrix,
            name
        )

        if value is None:
            continue

        if isinstance(
            value,
            dict
        ):

            for key, val in value.items():

                if val:

                    values.append(
                        str(key)
                    )

        else:

            values.extend(
                _as_list(
                    value
                )
            )

    return _clean_string_list(
        values
    )


def _extract_direction_matches(
    matrix: Any
) -> List[str]:

    values = []

    for name in (
        "direction_matches",
        "direction_match",
        "matched_directions",
    ):

        value = _get(
            matrix,
            name
        )

        if value is not None:

            values.extend(
                _as_list(
                    value
                )
            )

    return _clean_string_list(
        values
    )


def _dominant_match(
    matrix: Any
) -> Optional[bool]:

    value = _get(
        matrix,
        "dominant_match",
        "dominant_matches",
        default=None
    )

    if value is None:
        return None

    if isinstance(
        value,
        bool
    ):
        return value

    text = str(
        value
    ).strip().lower()

    if text in {
        "true",
        "yes",
        "match",
        "matched",
        "1"
    }:

        return True

    if text in {
        "false",
        "no",
        "mismatch",
        "not matched",
        "0"
    }:

        return False

    return None


# =============================================================================
# FEATURE EXTRACTION
# =============================================================================

def _extract_observed_orders(
    features: Any
) -> List[float]:

    values = []

    for name in (
        "present_orders",
        "observed_orders",
        "orders",
    ):

        value = _get(
            features,
            name
        )

        if value is not None:

            values.extend(
                _as_list(
                    value
                )
            )

    return _sorted_orders(
        values
    )


def _extract_dominant_order(
    features: Any
) -> Optional[float]:

    value = _get(
        features,
        "dominant_order",
        "dominant",
        "dominant_order_value",
        default=None
    )

    return _order_value(
        value
    )


# =============================================================================
# MEASUREMENT DEDUPLICATION
# =============================================================================

def deduplicate_measurements(
    measurements: Sequence[
        MeasurementEvidence
    ]
) -> List[MeasurementEvidence]:

    unique = {}

    for measurement in measurements:

        if not isinstance(
            measurement,
            MeasurementEvidence
        ):

            raise TypeError(
                "All measurements must be "
                "MeasurementEvidence objects."
            )

        key = str(
            measurement.measurement_id
        ).strip()

        if not key:

            raise ValueError(
                "measurement_id cannot be empty."
            )

        if key not in unique:

            unique[key] = measurement

    return list(
        unique.values()
    )


# =============================================================================
# EVIDENCE FUSION ENGINE
# =============================================================================

class EvidenceFusionEngine:

    def __init__(
        self,
        expected_measurements:
            Optional[int] = None,

        expected_slots:
            Optional[
                Sequence[Any]
            ] = None,
    ):

        self.expected_measurements = (
            expected_measurements
        )

        # ---------------------------------------------------------------------
        # IMPORTANT FIX
        #
        # Normalize expected slots immediately.
        #
        # This protects the engine even if the caller sends dictionaries.
        # ---------------------------------------------------------------------

        self.expected_slots = (
            _normalize_expected_slots(
                expected_slots
            )
        )

    # -------------------------------------------------------------------------
    # MAIN FUSION
    # -------------------------------------------------------------------------

    def fuse(
        self,
        measurements:
            Sequence[
                MeasurementEvidence
            ],
    ) -> FusionReport:

        measurements = (
            deduplicate_measurements(
                measurements
            )
        )

        report = FusionReport(
            measurements=measurements,
            expected_measurements=(
                self.expected_measurements
            ),
            expected_slots=(
                self.expected_slots
            ),
        )

        candidates: Dict[
            str,
            FusionCandidate
        ] = {}

        # ---------------------------------------------------------------------
        # Process every measurement independently.
        # ---------------------------------------------------------------------

        for measurement in measurements:

            measurement_label = (
                measurement.display_label()
            )

            observed_orders = (
                _extract_observed_orders(
                    measurement.features
                )
            )

            # -----------------------------------------------------------------
            # Fallback if features do not expose orders.
            # -----------------------------------------------------------------

            if not observed_orders:

                all_matrix_orders = []

                for matrix in (
                    measurement.matrices
                ):

                    all_matrix_orders.extend(
                        _extract_matched_orders(
                            matrix
                        )
                    )

                observed_orders = (
                    _sorted_orders(
                        all_matrix_orders
                    )
                )

            # -----------------------------------------------------------------
            # Track mechanisms supported by THIS measurement.
            #
            # Database documents do not create additional measurement votes.
            # -----------------------------------------------------------------

            mechanisms_supported_in_measurement = set()

            # -----------------------------------------------------------------
            # Process database matrices.
            # -----------------------------------------------------------------

            for matrix in (
                measurement.matrices
            ):

                mechanisms = (
                    _extract_mechanisms(
                        matrix
                    )
                )

                if not mechanisms:
                    continue

                matched_orders = (
                    _extract_matched_orders(
                        matrix
                    )
                )

                missing_orders = (
                    _extract_missing_orders(
                        matrix
                    )
                )

                context = (
                    _extract_context(
                        matrix
                    )
                )

                database_directions = (
                    _extract_direction_matches(
                        matrix
                    )
                )

                dominant_match = (
                    _dominant_match(
                        matrix
                    )
                )

                document_id = (
                    _extract_document_id(
                        matrix
                    )
                )

                database_pattern_contradiction = (
                    dominant_match is False
                )

                for mechanism in mechanisms:

                    mechanism = str(
                        mechanism
                    ).strip().lower()

                    if not mechanism:
                        continue

                    if mechanism not in candidates:

                        candidates[
                            mechanism
                        ] = FusionCandidate(
                            mechanism=mechanism
                        )

                    candidate = candidates[
                        mechanism
                    ]

                    # ---------------------------------------------------------
                    # ACTUAL PATTERN SUPPORT
                    # ---------------------------------------------------------

                    if matched_orders:

                        mechanisms_supported_in_measurement.add(
                            mechanism
                        )

                    candidate.supporting_orders.extend(
                        matched_orders
                    )

                    candidate.missing_pattern_orders.extend(
                        missing_orders
                    )

                    # ---------------------------------------------------------
                    # CONTEXT SUPPORT
                    # ---------------------------------------------------------

                    candidate.context_support.extend(
                        context
                    )

                    # ---------------------------------------------------------
                    # ACTUAL MEASUREMENT DIRECTION
                    # ---------------------------------------------------------

                    if measurement.direction:

                        candidate.directions.append(
                            str(
                                measurement.direction
                            )
                        )

                    # ---------------------------------------------------------
                    # DATABASE EXPECTED DIRECTION
                    # ---------------------------------------------------------

                    candidate.database_directions.extend(
                        database_directions
                    )

                    # ---------------------------------------------------------
                    # LOCATION
                    # ---------------------------------------------------------

                    candidate.locations.append(
                        measurement.location_label()
                    )

                    # ---------------------------------------------------------
                    # COMPONENT
                    # ---------------------------------------------------------

                    if measurement.component:

                        candidate.components.append(
                            str(
                                measurement.component
                            )
                        )

                    # ---------------------------------------------------------
                    # DATABASE DOCUMENT
                    # ---------------------------------------------------------

                    if document_id:

                        candidate.database_documents.append(
                            document_id
                        )

                    # ---------------------------------------------------------
                    # DATABASE PATTERN CONTRADICTION
                    # ---------------------------------------------------------

                    if database_pattern_contradiction:

                        contradiction_id = (
                            document_id
                        )

                        if not contradiction_id:

                            contradiction_id = (
                                "database_pattern:"
                                + mechanism
                            )

                        candidate.database_pattern_contradictions.append(
                            contradiction_id
                        )

                    # ---------------------------------------------------------
                    # IMPORTANT:
                    #
                    # Database mismatch is NOT an actual FFT contradiction.
                    # ---------------------------------------------------------

            # -----------------------------------------------------------------
            # Count the measurement only once for each mechanism.
            # -----------------------------------------------------------------

            for mechanism in (
                mechanisms_supported_in_measurement
            ):

                candidates[
                    mechanism
                ].supporting_measurements.append(
                    measurement_label
                )

        # ---------------------------------------------------------------------
        # Finalize candidates.
        # ---------------------------------------------------------------------

        for candidate in candidates.values():

            candidate.normalize()

            candidate.measurement_support_hits = (
                candidate.support_count
            )

            candidate.database_pattern_hits = len(
                candidate.database_documents
            )

            candidate.status = (
                self._classify_status(
                    candidate
                )
            )

            candidate.reasons = (
                self._build_reasons(
                    candidate
                )
            )

        # ---------------------------------------------------------------------
        # Alphabetical order.
        #
        # This is NOT diagnostic ranking.
        # ---------------------------------------------------------------------

        report.candidates = sorted(
            candidates.values(),
            key=lambda item: item.mechanism
        )

        return report

    # -------------------------------------------------------------------------
    # STATUS CLASSIFICATION
    # -------------------------------------------------------------------------

    @staticmethod
    def _classify_status(
        candidate: FusionCandidate
    ) -> str:

        support = (
            candidate.support_count
        )

        if (
            candidate.actual_fft_contradictions > 0
            and support > 0
        ):

            return (
                "CONTRADICTORY EVIDENCE"
            )

        if support >= 2:

            if (
                candidate.pattern_contradiction_count
                > 0
            ):

                return (
                    "PARTIAL EVIDENCE"
                )

            if (
                len(
                    set(
                        candidate.locations
                    )
                ) >= 2
                or
                len(
                    set(
                        candidate.directions
                    )
                ) >= 2
            ):

                return (
                    "STRONG EVIDENCE"
                )

            return (
                "PARTIAL EVIDENCE"
            )

        if support == 1:

            if (
                candidate.supporting_orders
                and (
                    candidate.context_support
                    or
                    candidate.database_directions
                )
            ):

                return "PARTIAL EVIDENCE"

            if candidate.supporting_orders:

                return "COMPATIBLE PATTERN"

            return "LIMITED EVIDENCE"

        return "LIMITED EVIDENCE"

    # -------------------------------------------------------------------------
    # REASONS
    # -------------------------------------------------------------------------

    @staticmethod
    def _build_reasons(
        candidate: FusionCandidate
    ) -> List[str]:

        reasons = []

        if candidate.supporting_orders:

            reasons.append(
                "Supporting order evidence: "
                +
                _format_orders(
                    candidate.supporting_orders
                )
            )

        if candidate.missing_pattern_orders:

            reasons.append(
                "Missing orders inside measured "
                "spectrum: "
                +
                _format_orders(
                    candidate.missing_pattern_orders
                )
            )

        if candidate.context_support:

            reasons.append(
                "Machine context support: "
                +
                ", ".join(
                    candidate.context_support
                )
            )

        if candidate.directions:

            reasons.append(
                "Measurement direction support: "
                +
                ", ".join(
                    candidate.directions
                )
            )

        if candidate.database_directions:

            reasons.append(
                "Database expected direction: "
                +
                ", ".join(
                    candidate.database_directions
                )
            )

        if candidate.database_documents:

            reasons.append(
                "Database knowledge support: "
                +
                str(
                    len(
                        candidate.database_documents
                    )
                )
                +
                " unique document(s)"
            )

        if candidate.database_pattern_contradictions:

            reasons.append(
                "Some database patterns "
                "contradict the observed dominant/pattern."
            )

        return reasons


# =============================================================================
# EXPECTED MEASUREMENT SLOTS
# =============================================================================

def build_expected_slots(
    bearing_ids: Sequence[str],
    directions: Sequence[str] = (
        "H",
        "V",
        "A",
    ),
) -> List[
    Tuple[str, str]
]:

    result = []

    for bearing in bearing_ids:

        for direction in directions:

            result.append(
                (
                    str(bearing),
                    str(direction)
                )
            )

    return result


# =============================================================================
# REPORT PRINTER
# =============================================================================

def print_fusion_report(
    report: FusionReport
) -> None:

    print()
    print("=" * 90)
    print("EVIDENCE FUSION")
    print("=" * 90)

    print(
        f"Measurements received : "
        f"{report.measurements_received}"
    )

    if report.expected_measurements is not None:

        print(
            f"Expected measurements : "
            f"{report.expected_measurements}"
        )

        coverage = (
            report.machine_measurement_coverage
        )

        if coverage is not None:

            print(
                f"Measurement coverage  : "
                f"{report.measurements_received} / "
                f"{report.expected_measurements} "
                f"({coverage:.1f}%)"
            )

    else:

        print(
            "Expected measurements : Not specified"
        )

        print(
            "Measurement coverage  : Not specified"
        )

    print()

    directions = (
        report.available_directions
    )

    print(
        "Measurement directions : "
        +
        (
            ", ".join(
                directions
            )
            if directions
            else "None"
        )
    )

    print()

    print(
        "Available measurements:"
    )

    if report.measurements:

        for measurement in report.measurements:

            print(
                f"  ✓ "
                f"{measurement.display_label()}"
            )

    else:

        print(
            "  None"
        )

    print()

    if report.expected_slots:

        missing_slots = (
            report.missing_expected_slots
        )

        if missing_slots:

            print(
                "Not provided:"
            )

            grouped = defaultdict(list)

            for bearing, direction in (
                missing_slots
            ):

                grouped[
                    bearing
                ].append(
                    direction
                )

            for bearing in sorted(
                grouped
            ):

                print(
                    f"  {bearing}: "
                    +
                    ", ".join(
                        grouped[bearing]
                    )
                )

        else:

            print(
                "Not provided            : None"
            )

    else:

        print(
            "Not provided            : "
            "Expected slots not specified"
        )

    print()

    all_observed_orders = []
    all_dominant_orders = []

    for measurement in (
        report.measurements
    ):

        all_observed_orders.extend(
            _extract_observed_orders(
                measurement.features
            )
        )

        dominant = (
            _extract_dominant_order(
                measurement.features
            )
        )

        if dominant is not None:

            all_dominant_orders.append(
                dominant
            )

    print(
        "Observed orders        : "
        +
        _format_orders(
            all_observed_orders
        )
    )

    print(
        "Dominant orders        : "
        +
        (
            _format_orders(
                all_dominant_orders
            )
            if all_dominant_orders
            else "None"
        )
    )

    print()

    print(
        "-" * 90
    )

    if report.measurements_received == 1:

        print(
            "NOTE: Only one measurement was available."
        )

        print(
            "The system analyzed it without requiring "
            "additional measurements."
        )

    elif report.measurements_received > 1:

        print(
            "NOTE: All available independent measurements "
            "were fused."
        )

    print(
        "Missing measurements are NOT treated as "
        "negative fault evidence."
    )

    print(
        "Missing orders refer only to orders expected "
        "inside an FFT that was actually measured."
    )

    print(
        "Database-pattern contradictions are kept "
        "separate from actual FFT contradictions."
    )

    for candidate in report.candidates:

        print()

        print(
            "-" * 90
        )

        print(
            f"Mechanism               : "
            f"{candidate.mechanism}"
        )

        print(
            f"Status                  : "
            f"{candidate.status}"
        )

        print(
            f"Supporting measurements : "
            f"{candidate.support_count}"
        )

        print(
            f"Received support        : "
            f"{candidate.support_count} / "
            f"{report.measurements_received}"
        )

        if report.measurements_received > 0:

            rate = (
                candidate.support_count
                /
                report.measurements_received
            ) * 100.0

            print(
                f"Received support rate   : "
                f"{rate:.1f}%"
            )

        if report.expected_measurements:

            print(
                f"Machine coverage        : "
                f"{candidate.support_count} / "
                f"{report.expected_measurements}"
            )

        if candidate.database_pattern_contradictions:

            print(
                "Database contradiction  : "
                +
                ", ".join(
                    candidate.database_pattern_contradictions
                )
            )

        else:

            print(
                "Database contradiction  : None"
            )

        print(
            "Actual FFT contradiction: "
            +
            str(
                candidate.actual_fft_contradictions
            )
        )

        print(
            "Measurement directions  : "
            +
            (
                ", ".join(
                    candidate.directions
                )
                if candidate.directions
                else "None"
            )
        )

        print(
            "Database directions     : "
            +
            (
                ", ".join(
                    candidate.database_directions
                )
                if candidate.database_directions
                else "None"
            )
        )

        if candidate.locations:

            print(
                "Locations               : "
                +
                ", ".join(
                    candidate.locations
                )
            )

        if candidate.components:

            print(
                "Components              : "
                +
                ", ".join(
                    candidate.components
                )
            )

        print(
            "Supporting orders       : "
            +
            (
                _format_orders(
                    candidate.supporting_orders
                )
                if candidate.supporting_orders
                else "None"
            )
        )

        print(
            "Missing in measured FFT : "
            +
            (
                _format_orders(
                    candidate.missing_pattern_orders
                )
                if candidate.missing_pattern_orders
                else "None"
            )
        )

        print(
            "Context support         : "
            +
            (
                ", ".join(
                    candidate.context_support
                )
                if candidate.context_support
                else "None"
            )
        )

        print(
            "Database documents      : "
            +
            str(
                len(
                    candidate.database_documents
                )
            )
        )

        if candidate.reasons:

            print()

            for reason in candidate.reasons:

                print(
                    f"  • {reason}"
                )

    print()

    print(
        "=" * 90
    )


# =============================================================================
# SIMPLE API
# =============================================================================

def fuse_measurements(
    measurements: Sequence[
        MeasurementEvidence
    ],

    expected_measurements:
        Optional[int] = None,

    expected_slots:
        Optional[
            Sequence[Any]
        ] = None,
) -> FusionReport:

    engine = EvidenceFusionEngine(
        expected_measurements=(
            expected_measurements
        ),
        expected_slots=(
            expected_slots
        ),
    )

    return engine.fuse(
        measurements
    )


# =============================================================================
# TEST ADAPTER
# =============================================================================

def _load_current_test_from_knowledge_matcher():

    try:

        import knowledge_matcher as km

    except Exception as exc:

        raise RuntimeError(
            "Could not import knowledge_matcher.py.\n"
            f"Original error: {exc}"
        )

    features = None
    context = None

    feature_builder_names = [
        "build_test_features",
        "create_test_features",
        "get_test_features",
        "make_test_features",
    ]

    context_builder_names = [
        "build_test_context",
        "create_test_context",
        "get_test_context",
        "make_test_context",
    ]

    for name in feature_builder_names:

        fn = getattr(
            km,
            name,
            None
        )

        if callable(fn):

            try:

                features = fn()

                break

            except TypeError:
                pass

    for name in context_builder_names:

        fn = getattr(
            km,
            name,
            None
        )

        if callable(fn):

            try:

                context = fn()

                break

            except TypeError:
                pass

    if features is None:

        for name in dir(km):

            lowered = name.lower()

            if (
                "test" in lowered
                and
                "feature" in lowered
            ):

                value = getattr(
                    km,
                    name,
                    None
                )

                if value is not None:

                    features = value

                    break

    if context is None:

        for name in dir(km):

            lowered = name.lower()

            if (
                "test" in lowered
                and
                "context" in lowered
            ):

                value = getattr(
                    km,
                    name,
                    None
                )

                if value is not None:

                    context = value

                    break

    if features is None:

        raise RuntimeError(
            "Could not automatically find "
            "the test VibrationFeatures object."
        )

    if context is None:

        raise RuntimeError(
            "Could not automatically find "
            "the test MachineContext object."
        )

    matcher_class = getattr(
        km,
        "KnowledgeMatcher",
        None
    )

    if matcher_class is None:

        raise RuntimeError(
            "KnowledgeMatcher class was not found."
        )

    try:

        matcher = matcher_class()

    except TypeError:

        database_engine_class = getattr(
            km,
            "DatabaseEngine",
            None
        )

        if database_engine_class is None:
            raise

        database = (
            database_engine_class()
        )

        try:

            matcher = matcher_class(
                database=database
            )

        except TypeError:

            matcher = matcher_class(
                database
            )

    match_fn = getattr(
        matcher,
        "match",
        None
    )

    if not callable(match_fn):

        raise RuntimeError(
            "KnowledgeMatcher.match() "
            "was not found."
        )

    try:

        matrices = match_fn(
            features,
            context,
            top_k=115
        )

    except TypeError:

        try:

            matrices = match_fn(
                features,
                context,
                top_k=1000
            )

        except TypeError:

            matrices = match_fn(
                features,
                context
            )

    if matrices is None:
        matrices = []

    return (
        features,
        context,
        list(matrices)
    )


# =============================================================================
# SINGLE MEASUREMENT TEST
# =============================================================================

def run_single_measurement_test():

    print()

    print(
        "=" * 90
    )

    print(
        "TEST — SINGLE MEASUREMENT"
    )

    print(
        "=" * 90
    )

    try:

        (
            features,
            context,
            matrices
        ) = (
            _load_current_test_from_knowledge_matcher()
        )

    except Exception as exc:

        print()

        print(
            "TEST ADAPTER ERROR"
        )

        print(
            "-" * 90
        )

        print(
            str(exc)
        )

        print()

        print(
            "The EvidenceFusionEngine itself "
            "is available for direct integration."
        )

        print(
            "=" * 90
        )

        return

    expected_slots = (
        build_expected_slots(
            bearing_ids=[
                "Bearing 1",
                "Bearing 2",
                "Bearing 3",
                "Bearing 4",
            ],
            directions=[
                "H",
                "V",
                "A",
            ],
        )
    )

    measurement = (
        MeasurementEvidence(
            measurement_id="B1-H",
            bearing_id="Bearing 1",
            point="Motor DE",
            direction="H",
            component="Motor",
            rpm=1500,
            features=features,
            matrices=matrices,
        )
    )

    engine = (
        EvidenceFusionEngine(
            expected_measurements=len(
                expected_slots
            ),
            expected_slots=(
                expected_slots
            ),
        )
    )

    report = engine.fuse(
        [
            measurement
        ]
    )

    print_fusion_report(
        report
    )


# =============================================================================
# CREATE MEASUREMENT
# =============================================================================

def create_measurement(
    measurement_id: str,
    features: Any,
    matrices: Sequence[Any],
    rpm: float,
    bearing_id: Optional[str],
    point: Optional[str],
    direction: Optional[str],
    component: Optional[str] = None,
) -> MeasurementEvidence:

    return MeasurementEvidence(
        measurement_id=measurement_id,
        bearing_id=bearing_id,
        point=point,
        direction=direction,
        component=component,
        rpm=rpm,
        features=features,
        matrices=list(matrices),
    )


# =============================================================================
# MULTI-MEASUREMENT TEST
# =============================================================================

def run_multi_measurement_test():

    print()

    print(
        "=" * 90
    )

    print(
        "TEST — MULTI MEASUREMENT"
    )

    print(
        "=" * 90
    )

    try:

        (
            features,
            context,
            matrices
        ) = (
            _load_current_test_from_knowledge_matcher()
        )

    except Exception as exc:

        print()

        print(
            "TEST ADAPTER ERROR"
        )

        print(
            "-" * 90
        )

        print(
            str(exc)
        )

        print(
            "=" * 90
        )

        return

    # -------------------------------------------------------------------------
    # TEST MACHINE
    #
    # 4 bearings × 3 directions = 12 possible measurements
    #
    # Only 4 measurements are supplied here.
    # -------------------------------------------------------------------------

    expected_slots = build_expected_slots(
        bearing_ids=[
            "Bearing 1",
            "Bearing 2",
            "Bearing 3",
            "Bearing 4",
        ],
        directions=[
            "H",
            "V",
            "A",
        ],
    )

    measurements = [

        MeasurementEvidence(
            measurement_id="B1-H",
            bearing_id="Bearing 1",
            point="Motor DE",
            direction="H",
            component="Motor",
            rpm=1500,
            features=features,
            matrices=matrices,
        ),

        MeasurementEvidence(
            measurement_id="B1-V",
            bearing_id="Bearing 1",
            point="Motor DE",
            direction="V",
            component="Motor",
            rpm=1500,
            features=features,
            matrices=matrices,
        ),

        MeasurementEvidence(
            measurement_id="B2-H",
            bearing_id="Bearing 2",
            point="Motor NDE",
            direction="H",
            component="Motor",
            rpm=1500,
            features=features,
            matrices=matrices,
        ),

        MeasurementEvidence(
            measurement_id="B2-V",
            bearing_id="Bearing 2",
            point="Motor NDE",
            direction="V",
            component="Motor",
            rpm=1500,
            features=features,
            matrices=matrices,
        ),
    ]

    engine = EvidenceFusionEngine(
        expected_measurements=len(
            expected_slots
        ),
        expected_slots=expected_slots,
    )

    report = engine.fuse(
        measurements
    )

    print_fusion_report(
        report
    )

    print()

    print(
        "=" * 90
    )

    print(
        "MULTI-MEASUREMENT TEST COMPLETE"
    )

    print(
        "=" * 90
    )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":

    run_single_measurement_test()

    print()
    print()
    print()

    run_multi_measurement_test()