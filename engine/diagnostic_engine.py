from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================
# Diagnostic Evidence
# ============================================================

@dataclass
class DiagnosticEvidence:
    """
    Structured evidence for one fault mechanism.

    This object does NOT mean that the fault is confirmed.
    It only stores the evidence collected by the system.
    """

    mechanism: str

    status: str = "LIMITED EVIDENCE"

    evidence_score: float = 0.0

    supporting_measurements: List[str] = field(default_factory=list)

    directions: List[str] = field(default_factory=list)

    locations: List[str] = field(default_factory=list)

    components: List[str] = field(default_factory=list)

    supporting_orders: List[str] = field(default_factory=list)

    missing_pattern_orders: List[str] = field(default_factory=list)

    context_support: List[str] = field(default_factory=list)

    database_documents: List[str] = field(default_factory=list)

    database_pattern_contradictions: List[str] = field(
        default_factory=list
    )

    actual_fft_contradictions: List[str] = field(
        default_factory=list
    )

    reasons: List[str] = field(default_factory=list)

    # --------------------------------------------------------
    # Computed properties
    # --------------------------------------------------------

    @property
    def support_count(self) -> int:
        return len(set(self.supporting_measurements))

    @property
    def direction_count(self) -> int:
        return len(set(self.directions))

    @property
    def location_count(self) -> int:
        return len(set(self.locations))

    @property
    def contradiction_count(self) -> int:
        return len(set(self.actual_fft_contradictions))

    @property
    def database_contradiction_count(self) -> int:
        return len(set(self.database_pattern_contradictions))

    def normalize(self):
        """
        Remove duplicates while preserving deterministic ordering.
        """

        self.supporting_measurements = sorted(
            set(self.supporting_measurements)
        )

        self.directions = sorted(
            set(self.directions)
        )

        self.locations = sorted(
            set(self.locations)
        )

        self.components = sorted(
            set(self.components)
        )

        self.supporting_orders = sorted(
            set(self.supporting_orders),
            key=_order_sort_key
        )

        self.missing_pattern_orders = sorted(
            set(self.missing_pattern_orders),
            key=_order_sort_key
        )

        self.context_support = sorted(
            set(self.context_support)
        )

        self.database_documents = sorted(
            set(self.database_documents)
        )

        self.database_pattern_contradictions = sorted(
            set(self.database_pattern_contradictions)
        )

        self.actual_fft_contradictions = sorted(
            set(self.actual_fft_contradictions)
        )

        self.reasons = list(
            dict.fromkeys(self.reasons)
        )

        return self


# ============================================================
# Diagnostic Report
# ============================================================

@dataclass
class DiagnosticReport:

    measurements_received: int

    expected_measurements: Optional[int]

    coverage_percent: Optional[float]

    available_directions: List[str]

    available_measurements: List[str]

    missing_expected_slots: List[str]

    diagnostics: List[DiagnosticEvidence]

    notes: List[str] = field(default_factory=list)


# ============================================================
# Helper functions
# ============================================================

def _order_sort_key(value: Any):

    text = str(value).strip().upper()

    if text.endswith("X"):
        text = text[:-1]

    try:
        return float(text)
    except Exception:
        return float("inf")


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


def _get(obj: Any, name: str, default=None):

    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def _calculate_coverage(
    received: int,
    expected: Optional[int],
) -> Optional[float]:

    if expected is None:
        return None

    try:
        expected = int(expected)
    except Exception:
        return None

    if expected <= 0:
        return None

    return (received / expected) * 100.0


# ============================================================
# Diagnostic Engine
# ============================================================

class AIDiagnosticEngine:
    """
    Converts fused evidence into structured diagnostic evidence.

    IMPORTANT:
    This engine does NOT automatically declare a fault as confirmed.

    Missing measurements are NOT negative evidence.
    """

    def __init__(
        self,
        minimum_strong_support: int = 2,
    ):

        self.minimum_strong_support = max(
            1,
            int(minimum_strong_support)
        )

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def diagnose(
        self,
        fusion_report: Any,
    ) -> DiagnosticReport:

        measurements_received = int(
            _get(
                fusion_report,
                "measurements_received",
                0
            ) or 0
        )

        expected_measurements = _get(
            fusion_report,
            "expected_measurements",
            None
        )

        coverage_percent = _calculate_coverage(
            measurements_received,
            expected_measurements
        )

        available_directions = sorted(
            _clean_list(
                _get(
                    fusion_report,
                    "available_directions",
                    []
                )
            )
        )

        available_measurements = sorted(
            _clean_list(
                _get(
                    fusion_report,
                    "available_measurements",
                    []
                )
            )
        )

        missing_expected_slots = sorted(
            _clean_list(
                _get(
                    fusion_report,
                    "missing_expected_slots",
                    []
                )
            )
        )

        diagnostics = []

        candidates = _get(
            fusion_report,
            "candidates",
            []
        )

        for candidate in candidates:

            diagnostic = self._build_diagnostic(
                candidate
            )

            diagnostics.append(
                diagnostic
            )

        diagnostics = sorted(
            diagnostics,
            key=lambda item: (
                -item.evidence_score,
                item.mechanism.lower()
            )
        )

        notes = self._build_report_notes(
            measurements_received=measurements_received,
            expected_measurements=expected_measurements,
            missing_expected_slots=missing_expected_slots,
        )

        return DiagnosticReport(
            measurements_received=measurements_received,
            expected_measurements=expected_measurements,
            coverage_percent=coverage_percent,
            available_directions=available_directions,
            available_measurements=available_measurements,
            missing_expected_slots=missing_expected_slots,
            diagnostics=diagnostics,
            notes=notes,
        )

    # --------------------------------------------------------
    # Build one diagnostic item
    # --------------------------------------------------------

    def _build_diagnostic(
        self,
        candidate: Any,
    ) -> DiagnosticEvidence:

        mechanism = str(
            _get(
                candidate,
                "mechanism",
                "unknown"
            )
        )

        evidence = DiagnosticEvidence(
            mechanism=mechanism,

            status=str(
                _get(
                    candidate,
                    "status",
                    "LIMITED EVIDENCE"
                )
            ),

            supporting_measurements=_clean_list(
                _get(
                    candidate,
                    "supporting_measurements",
                    []
                )
            ),

            directions=_clean_list(
                _get(
                    candidate,
                    "directions",
                    []
                )
            ),

            locations=_clean_list(
                _get(
                    candidate,
                    "locations",
                    []
                )
            ),

            components=_clean_list(
                _get(
                    candidate,
                    "components",
                    []
                )
            ),

            supporting_orders=_clean_list(
                _get(
                    candidate,
                    "supporting_orders",
                    []
                )
            ),

            missing_pattern_orders=_clean_list(
                _get(
                    candidate,
                    "missing_pattern_orders",
                    []
                )
            ),

            context_support=_clean_list(
                _get(
                    candidate,
                    "context_support",
                    []
                )
            ),

            database_documents=_clean_list(
                _get(
                    candidate,
                    "database_documents",
                    []
                )
            ),

            database_pattern_contradictions=_clean_list(
                _get(
                    candidate,
                    "database_pattern_contradictions",
                    []
                )
            ),

            actual_fft_contradictions=_clean_list(
                _get(
                    candidate,
                    "actual_fft_contradictions",
                    []
                )
            ),

            reasons=_clean_list(
                _get(
                    candidate,
                    "reasons",
                    []
                )
            ),
        )

        evidence.normalize()

        evidence.evidence_score = (
            self._calculate_evidence_score(
                evidence
            )
        )

        return evidence

    # --------------------------------------------------------
    # Evidence score
    # --------------------------------------------------------

    def _calculate_evidence_score(
        self,
        evidence: DiagnosticEvidence,
    ) -> float:

        score = 0.0

        # ----------------------------------------------------
        # Measurement support
        # ----------------------------------------------------

        score += min(
            evidence.support_count * 15.0,
            45.0
        )

        # ----------------------------------------------------
        # Direction diversity
        # ----------------------------------------------------

        if evidence.direction_count >= 2:
            score += 15.0

        elif evidence.direction_count == 1:
            score += 7.0

        # ----------------------------------------------------
        # Location diversity
        # ----------------------------------------------------

        if evidence.location_count >= 2:
            score += 15.0

        elif evidence.location_count == 1:
            score += 7.0

        # ----------------------------------------------------
        # Supporting orders
        # ----------------------------------------------------

        order_count = len(
            evidence.supporting_orders
        )

        score += min(
            order_count * 2.0,
            10.0
        )

        # ----------------------------------------------------
        # Context
        # ----------------------------------------------------

        if evidence.context_support:
            score += min(
                len(evidence.context_support) * 2.0,
                6.0
            )

        # ----------------------------------------------------
        # Database evidence
        # ----------------------------------------------------

        if evidence.database_documents:
            score += min(
                len(evidence.database_documents) * 1.0,
                5.0
            )

        # ----------------------------------------------------
        # Database contradictions
        #
        # These are NOT actual FFT contradictions.
        # They only reduce confidence slightly.
        # ----------------------------------------------------

        score -= min(
            evidence.database_contradiction_count * 2.0,
            8.0
        )

        # ----------------------------------------------------
        # Actual FFT contradictions
        #
        # These are much more important.
        # ----------------------------------------------------

        score -= min(
            evidence.contradiction_count * 15.0,
            45.0
        )

        score = max(
            0.0,
            min(score, 100.0)
        )

        return round(
            score,
            2
        )

    # --------------------------------------------------------
    # Report notes
    # --------------------------------------------------------

    def _build_report_notes(
        self,
        measurements_received: int,
        expected_measurements: Optional[int],
        missing_expected_slots: List[str],
    ) -> List[str]:

        notes = []

        if expected_measurements is not None:

            coverage = _calculate_coverage(
                measurements_received,
                expected_measurements
            )

            if coverage is not None:

                notes.append(
                    f"Measurement coverage: "
                    f"{measurements_received}/"
                    f"{expected_measurements} "
                    f"({coverage:.1f}%)."
                )

        if missing_expected_slots:

            notes.append(
                "Missing measurement slots are "
                "not treated as negative fault evidence."
            )

        if not missing_expected_slots and expected_measurements is not None:

            if measurements_received < expected_measurements:

                notes.append(
                    "Some measurements are not present, "
                    "but no explicit expected slots were supplied."
                )

        notes.append(
            "Diagnostic evidence is based only on "
            "measurements actually received."
        )

        notes.append(
            "Database pattern contradictions are kept "
            "separate from actual FFT contradictions."
        )

        return notes


# ============================================================
# Human-readable report
# ============================================================

def print_diagnostic_report(
    report: DiagnosticReport,
):

    print()
    print("=" * 75)
    print("AI DIAGNOSTIC REPORT")
    print("=" * 75)

    print(
        f"Measurements received : "
        f"{report.measurements_received}"
    )

    if report.expected_measurements is not None:

        if report.coverage_percent is not None:

            print(
                f"Coverage              : "
                f"{report.measurements_received}/"
                f"{report.expected_measurements} "
                f"({report.coverage_percent:.1f}%)"
            )

    if report.available_directions:

        print(
            "Directions             : "
            + ", ".join(
                report.available_directions
            )
        )

    print()

    for diagnostic in report.diagnostics:

        print("-" * 75)

        print(
            f"Mechanism              : "
            f"{diagnostic.mechanism}"
        )

        print(
            f"Status                 : "
            f"{diagnostic.status}"
        )

        print(
            f"Evidence Score         : "
            f"{diagnostic.evidence_score:.2f}/100"
        )

        print(
            f"Supporting Measurements: "
            f"{diagnostic.support_count}"
        )

        if diagnostic.supporting_measurements:

            print(
                "Measurements           : "
                + ", ".join(
                    diagnostic.supporting_measurements
                )
            )

        if diagnostic.directions:

            print(
                "Directions             : "
                + ", ".join(
                    diagnostic.directions
                )
            )

        if diagnostic.locations:

            print(
                "Locations              : "
                + ", ".join(
                    diagnostic.locations
                )
            )

        if diagnostic.supporting_orders:

            print(
                "Supporting Orders      : "
                + ", ".join(
                    diagnostic.supporting_orders
                )
            )

        if diagnostic.missing_pattern_orders:

            print(
                "Missing Pattern Orders : "
                + ", ".join(
                    diagnostic.missing_pattern_orders
                )
            )

        if diagnostic.context_support:

            print(
                "Context Support        : "
                + ", ".join(
                    diagnostic.context_support
                )
            )

        if diagnostic.database_documents:

            print(
                "Database Documents     : "
                + ", ".join(
                    diagnostic.database_documents
                )
            )

        if diagnostic.database_pattern_contradictions:

            print(
                "Database Contradiction : "
                + ", ".join(
                    diagnostic.database_pattern_contradictions
                )
            )

        if diagnostic.actual_fft_contradictions:
            print(
                "Actual FFT Contradict. : "
                + ", ".join(
                    diagnostic.actual_fft_contradictions
                )
            )
        for reason in diagnostic.reasons:

            print(
                f"Reason                 : {reason}"
            )

    print()

    for note in report.notes:

        print(
            f"NOTE: {note}"
        )

    print("=" * 75)


# ============================================================
# Convenience function
# ============================================================

def run_diagnostic(
    fusion_report: DiagnosticReport,
) -> DiagnosticReport:

    engine = AIDiagnosticEngine()

    return engine.diagnose(
        fusion_report
    )