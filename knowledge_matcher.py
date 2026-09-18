# knowledge_matcher.py

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set

from database_engine import (
    DatabaseEngine,
    KnowledgeDocument,
    MachineContext,
)


# ============================================================
# WEIGHTS
# ============================================================

ORDER_STRONG_WEIGHT = 8.0
ORDER_TYPICAL_WEIGHT = 5.0
ORDER_POSSIBLE_WEIGHT = 2.0

MISSING_STRONG_PENALTY = 2.5
MISSING_TYPICAL_PENALTY = 1.25
MISSING_POSSIBLE_PENALTY = 0.0

DOMINANT_MATCH_WEIGHT = 8.0
DOMINANT_MISMATCH_PENALTY = 2.0

AMPLITUDE_WEIGHT = 4.0
CONTEXT_WEIGHT = 5.0
DIRECTION_WEIGHT = 3.0
KEYWORD_WEIGHT = 1.5

MAX_SCORE = 100.0


# ============================================================
# HELPERS
# ============================================================

def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = str(text).lower()

    replacements = {
        "×": "x",
        "✕": "x",
        "＊": "x",
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return re.sub(r"\s+", " ", text).strip()


def clean_order(value: float) -> float:
    return round(float(value), 3)


def order_label(order: float) -> str:
    if abs(order - round(order)) < 1e-9:
        return f"{int(round(order))}X"
    return f"{order:g}X"


# ============================================================
# VIBRATION FEATURES
# ============================================================

@dataclass
class VibrationFeatures:
    rpm: float

    fundamental_amplitude: float = 0.0

    dominant_order: Optional[float] = None
    dominant_amplitude: float = 0.0
    dominant_relative: float = 0.0

    present_orders: List[int] = field(default_factory=list)
    missing_orders: List[int] = field(default_factory=list)

    harmonic_count: int = 0
    highest_order: float = 0.0

    odd_orders: List[int] = field(default_factory=list)
    even_orders: List[int] = field(default_factory=list)

    odd_amplitude: float = 0.0
    even_amplitude: float = 0.0
    odd_even_ratio: float = 0.0

    low_order_amplitude: float = 0.0
    mid_order_amplitude: float = 0.0
    high_order_amplitude: float = 0.0
    high_low_ratio: float = 0.0

    total_amplitude: float = 0.0
    mean_amplitude: float = 0.0
    amplitude_spread: float = 0.0

    average_confidence: float = 0.0
    minimum_confidence: float = 0.0
    maximum_confidence: float = 0.0

    order_ratios: Dict[str, float] = field(default_factory=dict)

    amplitudes: Dict[float, float] = field(default_factory=dict)
    confidences: Dict[float, float] = field(default_factory=dict)

    extra: Dict = field(default_factory=dict)


# ============================================================
# EXPECTATION
# ============================================================

@dataclass
class OrderExpectation:

    order: float

    certainty: str = "typical"

    source_text: str = ""

    reason: str = ""

    @property
    def weight(self) -> float:

        if self.certainty == "strong":
            return ORDER_STRONG_WEIGHT

        if self.certainty == "possible":
            return ORDER_POSSIBLE_WEIGHT

        return ORDER_TYPICAL_WEIGHT


@dataclass
class PatternExpectation:

    orders: Dict[float, OrderExpectation] = field(
        default_factory=dict
    )

    possible_orders: Dict[float, OrderExpectation] = field(
        default_factory=dict
    )

    dominant_orders: Set[float] = field(
        default_factory=set
    )

    ranges: List[Tuple[float, float]] = field(
        default_factory=list
    )

    has_harmonics_statement: bool = False

    machine_context: Set[str] = field(
        default_factory=set
    )

    fault_mechanisms: Set[str] = field(
        default_factory=set
    )

    direction_expectations: Set[str] = field(
        default_factory=set
    )

    raw_text: str = ""

    def add_order(
        self,
        order: float,
        certainty: str = "typical",
        source_text: str = "",
        reason: str = "",
    ):

        order = clean_order(order)

        if certainty == "possible":
            self.add_possible_order(
                order,
                source_text,
                reason,
            )
            return

        existing = self.orders.get(order)

        priority = {
            "typical": 1,
            "strong": 2,
        }

        if existing is None:

            self.orders[order] = OrderExpectation(
                order=order,
                certainty=certainty,
                source_text=source_text,
                reason=reason,
            )

        elif priority.get(
            certainty,
            0,
        ) > priority.get(
            existing.certainty,
            0,
        ):

            existing.certainty = certainty
            existing.source_text = source_text
            existing.reason = reason

    def add_possible_order(
        self,
        order: float,
        source_text: str = "",
        reason: str = "",
    ):

        order = clean_order(order)

        if order in self.orders:
            return

        if order not in self.possible_orders:

            self.possible_orders[order] = OrderExpectation(
                order=order,
                certainty="possible",
                source_text=source_text,
                reason=reason,
            )

    @property
    def expected_orders(self) -> List[float]:
        return sorted(self.orders.keys())

    @property
    def optional_orders(self) -> List[float]:
        return sorted(self.possible_orders.keys())


# ============================================================
# EVIDENCE MATRIX
# ============================================================

@dataclass
class EvidenceMatrix:

    score: float

    document: KnowledgeDocument

    expected_orders: List[float] = field(
        default_factory=list
    )

    optional_orders: List[float] = field(
        default_factory=list
    )

    observed_orders: List[float] = field(
        default_factory=list
    )

    matched_orders: List[float] = field(
        default_factory=list
    )

    missing_orders: List[float] = field(
        default_factory=list
    )

    optional_matches: List[float] = field(
        default_factory=list
    )

    strong_matches: List[float] = field(
        default_factory=list
    )

    typical_matches: List[float] = field(
        default_factory=list
    )

    dominant_expected: List[float] = field(
        default_factory=list
    )

    dominant_observed: Optional[float] = None

    dominant_match: bool = False

    pattern_coverage: float = 0.0

    optional_coverage: float = 0.0

    expected_ranges: List[Tuple[float, float]] = field(
        default_factory=list
    )

    machine_context_matches: List[str] = field(
        default_factory=list
    )

    machine_context_missing: List[str] = field(
        default_factory=list
    )

    fault_mechanisms: List[str] = field(
        default_factory=list
    )

    matched_directions: List[str] = field(
        default_factory=list
    )

    missing_directions: List[str] = field(
        default_factory=list
    )

    matched_ratios: List[str] = field(
        default_factory=list
    )

    keyword_matches: List[str] = field(
        default_factory=list
    )

    reasons: List[str] = field(
        default_factory=list
    )

    support_score: float = 0.0

    missing_penalty: float = 0.0

    dominant_score: float = 0.0

    amplitude_score: float = 0.0

    context_score: float = 0.0

    expectation: Optional[PatternExpectation] = None


# ============================================================
# ORDER EXTRACTION
# ============================================================

def extract_order_mentions(
    text: str,
) -> List[Tuple[float, int, int]]:

    text = normalize_text(text)

    pattern = re.compile(
        r"(?<![\w.])"
        r"(\d+(?:\.\d+)?)"
        r"\s*x"
        r"(?![\w])",
        re.IGNORECASE,
    )

    result = []

    for match in pattern.finditer(text):

        try:

            value = float(
                match.group(1)
            )

            if 0 < value <= 100:

                result.append(
                    (
                        clean_order(value),
                        match.start(),
                        match.end(),
                    )
                )

        except ValueError:
            continue

    return result


def extract_orders_from_text(
    text: str,
) -> List[float]:

    return sorted(
        {
            order
            for order, _, _ in
            extract_order_mentions(text)
        }
    )


# ============================================================
# RANGE EXTRACTION
# ============================================================

def extract_order_ranges(
    text: str,
) -> List[Tuple[float, float]]:

    text = normalize_text(text)

    pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*x"
        r"\s*(?:-|–|—|to|through|تا|الی)"
        r"\s*(\d+(?:\.\d+)?)\s*x",
        re.IGNORECASE,
    )

    ranges = []

    for match in pattern.finditer(text):

        try:

            start = float(
                match.group(1)
            )

            end = float(
                match.group(2)
            )

            if start > end:
                start, end = end, start

            if (
                0 < start <= 100
                and 0 < end <= 100
            ):

                ranges.append(
                    (
                        clean_order(start),
                        clean_order(end),
                    )
                )

        except ValueError:
            continue

    return ranges


# ============================================================
# CERTAINTY
# ============================================================

STRONG_WORDS = [
    "dominant",
    "strong",
    "strongest",
    "high peak",
    "large peak",
    "major peak",
    "pronounced",
    "significant",
    "پیک بلند",
    "پیک قوی",
    "پیک غالب",
    "غالب",
    "قوی",
    "شدید",
]

TYPICAL_WORDS = [
    "usually",
    "typically",
    "normally",
    "often",
    "generally",
    "common",
    "typical",
    "معمولاً",
    "اغلب",
    "عموماً",
    "معمول",
]

POSSIBLE_WORDS = [
    "may",
    "can",
    "possible",
    "possibly",
    "might",
    "sometimes",
    "could",
    "potentially",
    "ممکن",
    "احتمال",
    "گاهی",
    "می‌تواند",
    "ممکن است",
]


def classify_certainty(
    context: str,
) -> str:

    context = normalize_text(
        context
    )

    for word in STRONG_WORDS:

        if word in context:
            return "strong"

    for word in TYPICAL_WORDS:

        if word in context:
            return "typical"

    for word in POSSIBLE_WORDS:

        if word in context:
            return "possible"

    return "typical"


# ============================================================
# CONTEXT
# ============================================================

MACHINE_CONTEXT_GROUPS = {

    "coupling": [
        "coupling",
        "کوپلینگ",
        "coupler",
    ],

    "bearing": [
        "bearing",
        "bearings",
        "بیرینگ",
        "بلبرینگ",
        "رولبرینگ",
        "journal bearing",
        "rolling element",
    ],

    "gearbox": [
        "gearbox",
        "gear box",
        "گیربکس",
    ],

    "motor": [
        "motor",
        "موتور",
        "electric motor",
    ],

    "pump": [
        "pump",
        "پمپ",
    ],

    "fan": [
        "fan",
        "فن",
    ],

    "compressor": [
        "compressor",
        "کمپرسور",
    ],

    "turbine": [
        "turbine",
        "توربین",
    ],

    "shaft": [
        "shaft",
        "شفت",
        "محور",
    ],
}


FAULT_MECHANISM_GROUPS = {

    "looseness": [
        "looseness",
        "loose",
        "لقی",
        "شل",
        "لق بودن",
    ],

    "misalignment": [
        "misalignment",
        "misaligned",
        "عدم هم محوری",
        "ناهم محوری",
    ],

    "unbalance": [
        "unbalance",
        "imbalance",
        "عدم بالانس",
        "نامیزانی",
    ],

    "rub": [
        "rotor rub",
        "rubbing",
        "rub",
        "سایش روتور",
        "روتور راب",
    ],

    "bent_shaft": [
        "bent shaft",
        "شفت خمیده",
        "شفت خم",
    ],

    "bearing_fault": [
        "bearing defect",
        "bearing fault",
        "خرابی بیرینگ",
        "عیب بیرینگ",
    ],
}


DIRECTION_WORDS = {

    "radial": [
        "radial",
        "شعاعی",
        "horizontal",
        "افقی",
        "vertical",
        "عمودی",
    ],

    "axial": [
        "axial",
        "محوری",
    ],
}


def extract_group_matches(
    text: str,
    groups: Dict[str, List[str]],
) -> Set[str]:

    text = normalize_text(text)

    result = set()

    for group, terms in groups.items():

        for term in terms:

            if term in text:

                result.add(group)
                break

    return result


def extract_direction_expectations(
    text: str,
) -> Set[str]:

    text = normalize_text(text)

    result = set()

    for direction, terms in DIRECTION_WORDS.items():

        for term in terms:

            if term in text:

                result.add(direction)
                break

    return result


# ============================================================
# DOMINANT DETECTION
# ============================================================

def is_explicitly_dominant(
    text: str,
    order: float,
    start: int,
    end: int,
) -> bool:

    """
    Detect dominant order only from a LOCAL context.

    Old behavior:
        searched the entire document with:
        dominant.{0,80}3X

    That could accidentally mark several orders as dominant.

    New behavior:
        inspect only a small local window around the order.
    """

    normalized_order = order_label(
        order
    ).lower()

    left = max(
        0,
        start - 55,
    )

    right = min(
        len(text),
        end + 55,
    )

    local = normalize_text(
        text[left:right]
    )

    patterns = [

        # dominant 3x
        rf"\bdominant\b.{{0,35}}"
        rf"\b{re.escape(normalized_order)}\b",

        # 3x dominant
        rf"\b{re.escape(normalized_order)}\b"
        rf".{{0,35}}\bdominant\b",

        # strongest 3x
        rf"\bstrongest\b.{{0,35}}"
        rf"\b{re.escape(normalized_order)}\b",

        # 3x strongest
        rf"\b{re.escape(normalized_order)}\b"
        rf".{{0,35}}\bstrongest\b",

        # strong 3x
        rf"\bstrong\b.{{0,35}}"
        rf"\b{re.escape(normalized_order)}\b",

        # 3x strong
        rf"\b{re.escape(normalized_order)}\b"
        rf".{{0,35}}\bstrong\b",

        # high peak 3x
        rf"\bhigh peak\b.{{0,35}}"
        rf"\b{re.escape(normalized_order)}\b",

        # 3x high peak
        rf"\b{re.escape(normalized_order)}\b"
        rf".{{0,35}}\bhigh peak\b",

        # Persian
        rf"پیک غالب.{{0,35}}"
        rf"{re.escape(normalized_order)}",

        rf"{re.escape(normalized_order)}"
        rf".{{0,35}}پیک غالب",

        rf"پیک قوی.{{0,35}}"
        rf"{re.escape(normalized_order)}",

        rf"{re.escape(normalized_order)}"
        rf".{{0,35}}پیک قوی",

        rf"غالب.{{0,35}}"
        rf"{re.escape(normalized_order)}",

        rf"{re.escape(normalized_order)}"
        rf".{{0,35}}غالب",
    ]

    return any(
        re.search(
            pattern,
            local,
            re.IGNORECASE,
        )
        for pattern in patterns
    )


# ============================================================
# EXPECTATION BUILDER
# ============================================================

def build_pattern_expectation(
    document: KnowledgeDocument,
) -> PatternExpectation:

    text = normalize_text(
        " ".join(
            [
                str(
                    getattr(
                        document,
                        "title",
                        "",
                    )
                    or ""
                ),

                str(
                    getattr(
                        document,
                        "section",
                        "",
                    )
                    or ""
                ),

                str(
                    getattr(
                        document,
                        "section_en",
                        "",
                    )
                    or ""
                ),

                str(
                    getattr(
                        document,
                        "text",
                        "",
                    )
                    or ""
                ),
            ]
        )
    )

    expectation = PatternExpectation(
        raw_text=text
    )

    # ========================================================
    # RANGES
    # ========================================================

    ranges = extract_order_ranges(text)

    for start, end in ranges:

        expectation.ranges.append(
            (
                start,
                end,
            )
        )

        # Expand only reasonable ranges.
        if end - start <= 20:

            for value in range(
                int(start),
                int(end) + 1,
            ):

                expectation.add_order(
                    float(value),
                    certainty="typical",
                    reason=(
                        f"order range "
                        f"{order_label(start)}-"
                        f"{order_label(end)}"
                    ),
                )

    # ========================================================
    # HARMONIC LANGUAGE
    # ========================================================

    harmonic_phrases = [
        "harmonic",
        "harmonics",
        "multiple harmonics",
        "harmonics of 1x",
        "هارمونیک",
        "هارمونیک ها",
        "هارمونیک‌های",
        "هارمونیک های 1x",
    ]

    if any(
        phrase in text
        for phrase in harmonic_phrases
    ):

        expectation.has_harmonics_statement = True

    # ========================================================
    # ORDER MENTIONS
    # ========================================================

    mentions = extract_order_mentions(text)

    for order, start, end in mentions:

        # ----------------------------------------------------
        # Local context only
        # ----------------------------------------------------

        left = max(
            0,
            start - 120,
        )

        right = min(
            len(text),
            end + 120,
        )

        context = text[
            left:right
        ]

        certainty = classify_certainty(
            context
        )

        # ----------------------------------------------------
        # Add order
        # ----------------------------------------------------

        expectation.add_order(
            order,
            certainty=certainty,
            source_text=context,
            reason="explicit order mention",
        )

        # ====================================================
        # DOMINANT DETECTION
        #
        # IMPORTANT:
        # Never search the whole document for:
        #     dominant ... 1X
        #
        # because that can incorrectly mark unrelated
        # orders as dominant.
        #
        # Only the local context around THIS order is used.
        # ====================================================

        normalized_order = (
            order_label(order).lower()
        )

        local_patterns = [

            # English
            rf"\bdominant\b.{{0,45}}"
            rf"{re.escape(normalized_order)}",

            rf"{re.escape(normalized_order)}.{{0,45}}"
            rf"\bdominant\b",

            rf"\bstrongest\b.{{0,45}}"
            rf"{re.escape(normalized_order)}",

            rf"{re.escape(normalized_order)}.{{0,45}}"
            rf"\bstrongest\b",

            rf"\bstrong\b.{{0,35}}"
            rf"{re.escape(normalized_order)}",

            rf"{re.escape(normalized_order)}.{{0,35}}"
            rf"\bstrong\b",

            # English peak expressions
            rf"\bhigh peak\b.{{0,35}}"
            rf"{re.escape(normalized_order)}",

            rf"{re.escape(normalized_order)}.{{0,35}}"
            rf"\bhigh peak\b",

            rf"\bmajor peak\b.{{0,35}}"
            rf"{re.escape(normalized_order)}",

            rf"{re.escape(normalized_order)}.{{0,35}}"
            rf"\bmajor peak\b",

            # Persian
            rf"پیک غالب.{{0,40}}"
            rf"{re.escape(normalized_order)}",

            rf"{re.escape(normalized_order)}.{{0,40}}"
            rf"پیک غالب",

            rf"پیک قوی.{{0,40}}"
            rf"{re.escape(normalized_order)}",

            rf"{re.escape(normalized_order)}.{{0,40}}"
            rf"پیک قوی",

            rf"غالب.{{0,40}}"
            rf"{re.escape(normalized_order)}",

            rf"{re.escape(normalized_order)}.{{0,40}}"
            rf"غالب",
        ]

        local_is_dominant = False

        for pattern in local_patterns:

            if re.search(
                pattern,
                context,
                re.IGNORECASE,
            ):

                local_is_dominant = True
                break

        # ----------------------------------------------------
        # Prevent conditional language from becoming an
        # absolute dominant expectation.
        # ----------------------------------------------------

        conditional_words = [
            "may",
            "can",
            "could",
            "might",
            "possible",
            "possibly",
            "sometimes",
            "potentially",
            "ممکن",
            "ممکن است",
            "احتمال",
            "گاهی",
            "می‌تواند",
        ]

        conditional = any(
            word in context
            for word in conditional_words
        )

        if (
            local_is_dominant
            and not conditional
        ):

            expectation.dominant_orders.add(
                clean_order(order)
            )

    # ========================================================
    # MACHINE CONTEXT
    # ========================================================

    expectation.machine_context = (
        extract_group_matches(
            text,
            MACHINE_CONTEXT_GROUPS,
        )
    )

    # ========================================================
    # FAULT MECHANISM
    # ========================================================

    expectation.fault_mechanisms = (
        extract_group_matches(
            text,
            FAULT_MECHANISM_GROUPS,
        )
    )

    # ========================================================
    # DIRECTION
    # ========================================================

    expectation.direction_expectations = (
        extract_direction_expectations(
            text
        )
    )

    # ========================================================
    # OPTIONAL / POSSIBLE ORDERS
    # ========================================================

    for order, start, end in mentions:

        left = max(
            0,
            start - 120,
        )

        right = min(
            len(text),
            end + 120,
        )

        context = text[
            left:right
        ]

        certainty = classify_certainty(
            context
        )

        if certainty == "possible":

            expectation.orders.pop(
                order,
                None,
            )

            expectation.add_possible_order(
                order,
                source_text=context,
                reason="optional/possible order",
            )

    return expectation
# ============================================================
# MACHINE CONTEXT TO TERMS
# ============================================================

def context_to_terms(
    context: MachineContext,
) -> Set[str]:

    terms = set()

    data = context.to_dict()

    for key, value in data.items():

        if value is None:
            continue

        if isinstance(
            value,
            (list, tuple, set),
        ):

            values = value

        else:

            values = [value]

        for item in values:

            item = normalize_text(
                str(item)
            )

            if not item:
                continue

            terms.add(item)

            for group, keywords in (
                MACHINE_CONTEXT_GROUPS.items()
            ):

                if any(
                    keyword in item
                    for keyword in keywords
                ):

                    terms.add(group)

    return terms


# ============================================================
# MATCHER
# ============================================================

class KnowledgeMatcher:

    def __init__(
        self,
        database_root: str = "database",
    ):

        self.database = DatabaseEngine(
            database_root
        )

        self.database._ensure_loaded()

    @staticmethod
    def _document_text(
        document: KnowledgeDocument,
    ) -> str:

        return normalize_text(
            " ".join(
                [
                    str(
                        getattr(
                            document,
                            "title",
                            "",
                        )
                        or ""
                    ),

                    str(
                        getattr(
                            document,
                            "section",
                            "",
                        )
                        or ""
                    ),

                    str(
                        getattr(
                            document,
                            "section_en",
                            "",
                        )
                        or ""
                    ),

                    str(
                        getattr(
                            document,
                            "text",
                            "",
                        )
                        or ""
                    ),
                ]
            )
        )

    @staticmethod
    def _observed_orders(
        features: VibrationFeatures,
    ) -> Set[float]:

        result = set()

        for order in features.present_orders:

            result.add(
                clean_order(
                    float(order)
                )
            )

        for order in features.amplitudes:

            result.add(
                clean_order(
                    float(order)
                )
            )

        if (
            features.dominant_order
            is not None
        ):

            result.add(
                clean_order(
                    float(
                        features.dominant_order
                    )
                )
            )

        return result

    def _match_orders(
        self,
        expectation: PatternExpectation,
        features: VibrationFeatures,
    ):

        observed = (
            self._observed_orders(
                features
            )
        )

        matched = []
        missing = []

        optional_matches = []

        strong = []
        typical = []

        support = 0.0
        missing_penalty = 0.0

        for order, expected in (
            expectation.orders.items()
        ):

            if order in observed:

                matched.append(order)

                if (
                    expected.certainty
                    == "strong"
                ):

                    strong.append(
                        order
                    )

                else:

                    typical.append(
                        order
                    )

                support += (
                    expected.weight
                )

            else:

                missing.append(order)

                if (
                    expected.certainty
                    == "strong"
                ):

                    missing_penalty += (
                        MISSING_STRONG_PENALTY
                    )

                else:

                    missing_penalty += (
                        MISSING_TYPICAL_PENALTY
                    )

        for order in (
            expectation.possible_orders
        ):

            if order in observed:

                optional_matches.append(
                    order
                )

        return (
            sorted(matched),
            sorted(missing),
            sorted(optional_matches),
            sorted(strong),
            sorted(typical),
            support,
            missing_penalty,
        )

    @staticmethod
    def _match_dominant(
        expectation: PatternExpectation,
        features: VibrationFeatures,
    ) -> Tuple[bool, float]:

        if not expectation.dominant_orders:

            return False, 0.0

        if (
            features.dominant_order
            is None
        ):

            return (
                False,
                -DOMINANT_MISMATCH_PENALTY,
            )

        observed = clean_order(
            float(
                features.dominant_order
            )
        )

        if observed in (
            expectation.dominant_orders
        ):

            return (
                True,
                DOMINANT_MATCH_WEIGHT,
            )

        for expected in (
            expectation.dominant_orders
        ):

            if abs(
                expected - observed
            ) <= 0.1:

                return (
                    True,
                    DOMINANT_MATCH_WEIGHT * 0.8,
                )

        return (
            False,
            -DOMINANT_MISMATCH_PENALTY,
        )

    @staticmethod
    def _amplitude_consistency(
        expectation: PatternExpectation,
        features: VibrationFeatures,
        matched_orders: List[float],
    ) -> float:

        if not matched_orders:
            return 0.0

        if (
            features.dominant_amplitude
            <= 0
        ):

            return 0.0

        score = 0.0

        for order in matched_orders:

            amplitude = (
                features.amplitudes.get(
                    order
                )
            )

            if amplitude is None:
                continue

            relative = (
                amplitude
                / features.dominant_amplitude
            )

            expected = (
                expectation.orders[
                    order
                ]
            )

            if (
                expected.certainty
                == "strong"
            ):

                if relative >= 0.5:

                    score += (
                        AMPLITUDE_WEIGHT
                    )

                elif relative >= 0.2:

                    score += (
                        AMPLITUDE_WEIGHT
                        * 0.5
                    )

            else:

                if relative >= 0.15:

                    score += (
                        AMPLITUDE_WEIGHT
                        * 0.6
                    )

        return min(
            score,
            AMPLITUDE_WEIGHT * 2,
        )

    @staticmethod
    def _context_matches(
        expectation: PatternExpectation,
        machine_context: Optional[MachineContext],
    ):

        if machine_context is None:

            return [], [], 0.0

        machine_terms = (
            context_to_terms(
                machine_context
            )
        )

        matched = []
        missing = []

        for context in sorted(
            expectation.machine_context
        ):

            if context in machine_terms:

                matched.append(context)

            else:

                missing.append(context)

        if not expectation.machine_context:

            return (
                matched,
                missing,
                0.0,
            )

        score = (
            len(matched)
            / len(
                expectation.machine_context
            )
        ) * CONTEXT_WEIGHT

        return (
            matched,
            missing,
            score,
        )

    @staticmethod
    def _direction_matches(
        expectation: PatternExpectation,
        machine_context: Optional[MachineContext],
    ):

        if machine_context is None:

            return [], [], 0.0

        observed = normalize_text(
            str(
                machine_context.direction
                or ""
            )
        )

        if not expectation.direction_expectations:

            return [], [], 0.0

        matched = []
        missing = []

        for expected in (
            expectation.direction_expectations
        ):

            if expected == "radial":

                if any(
                    value in observed
                    for value in [
                        "radial",
                        "horizontal",
                        "vertical",
                        "شعاعی",
                        "افقی",
                        "عمودی",
                    ]
                ):

                    matched.append(
                        expected
                    )

                else:

                    missing.append(
                        expected
                    )

            elif expected == "axial":

                if any(
                    value in observed
                    for value in [
                        "axial",
                        "محوری",
                    ]
                ):

                    matched.append(
                        expected
                    )

                else:

                    missing.append(
                        expected
                    )

        score = (
            len(matched)
            / len(
                expectation.direction_expectations
            )
        ) * DIRECTION_WEIGHT

        return (
            matched,
            missing,
            score,
        )

    @staticmethod
    def _match_ratios(
        document_text: str,
        features: VibrationFeatures,
    ) -> List[str]:

        text = normalize_text(
            document_text
        )

        result = []

        ratio_map = {
            "2x/1x": "2X_to_1X",
            "3x/1x": "3X_to_1X",
            "4x/1x": "4X_to_1X",
            "5x/1x": "5X_to_1X",
        }

        for name, key in ratio_map.items():

            first, second = name.split(
                "/"
            )

            pattern = (
                rf"{re.escape(first)}"
                r"\s*(?:/|to)"
                rf"\s*{re.escape(second)}"
            )

            if re.search(
                pattern,
                text,
                re.IGNORECASE,
            ):

                value = (
                    features.order_ratios.get(
                        key
                    )
                )

                if value is not None:

                    result.append(
                        f"{name.upper()}={value:.3f}"
                    )

        return result

    @staticmethod
    def _keyword_matches(
        document: KnowledgeDocument,
        machine_context: Optional[MachineContext],
    ) -> List[str]:

        if machine_context is None:

            return []

        text = (
            KnowledgeMatcher._document_text(
                document
            )
        )

        terms = context_to_terms(
            machine_context
        )

        result = []

        for term in terms:

            if len(term) < 3:
                continue

            if term in text:

                result.append(term)

        return sorted(
            set(result)
        )

    def score_document(
        self,
        document: KnowledgeDocument,
        features: VibrationFeatures,
        machine_context: Optional[MachineContext] = None,
    ) -> EvidenceMatrix:

        expectation = (
            build_pattern_expectation(
                document
            )
        )

        (
            matched_orders,
            missing_orders,
            optional_matches,
            strong_matches,
            typical_matches,
            support_score,
            missing_penalty,
        ) = self._match_orders(
            expectation,
            features,
        )

        (
            dominant_match,
            dominant_score,
        ) = self._match_dominant(
            expectation,
            features,
        )

        amplitude_score = (
            self._amplitude_consistency(
                expectation,
                features,
                matched_orders,
            )
        )

        (
            machine_context_matches,
            machine_context_missing,
            context_score,
        ) = self._context_matches(
            expectation,
            machine_context,
        )

        (
            matched_directions,
            missing_directions,
            direction_score,
        ) = self._direction_matches(
            expectation,
            machine_context,
        )

        matched_ratios = (
            self._match_ratios(
                self._document_text(
                    document
                ),
                features,
            )
        )

        keyword_matches = (
            self._keyword_matches(
                document,
                machine_context,
            )
        )

        ratio_score = min(
            len(matched_ratios) * 3.0,
            6.0,
        )

        keyword_score = min(
            len(keyword_matches)
            * KEYWORD_WEIGHT,
            6.0,
        )

        expected_count = len(
            expectation.expected_orders
        )

        if expected_count:

            coverage = (
                    len(matched_orders)
                    / expected_count
            )

        else:

            coverage = 0.0

        # A document with only one generic order should not receive
        # the same pattern-strength interpretation as a document
        # containing a multi-order signature.
        pattern_specificity = min(
            expected_count / 3.0,
            1.0,
        )

        optional_count = len(
            expectation.optional_orders
        )

        if optional_count:

            optional_coverage = (
                len(optional_matches)
                / optional_count
            )

        else:

            optional_coverage = 0.0

        raw_score = (
            support_score
            - missing_penalty
            + dominant_score
            + amplitude_score
            + context_score
            + direction_score
            + ratio_score
            + keyword_score
        )

        raw_score += (
                coverage
                * 10.0
                * pattern_specificity
        )

        raw_score += (
            optional_coverage * 2.0
        )

        score = max(
            0.0,
            min(
                MAX_SCORE,
                raw_score,
            ),
        )

        reasons = []

        if matched_orders:

            reasons.append(
                "Observed orders match expected "
                "vibration orders: "
                + ", ".join(
                    order_label(x)
                    for x in matched_orders
                )
            )

        if missing_orders:

            reasons.append(
                "Expected but missing orders: "
                + ", ".join(
                    order_label(x)
                    for x in missing_orders
                )
            )

        if optional_matches:

            reasons.append(
                "Optional orders also observed: "
                + ", ".join(
                    order_label(x)
                    for x in optional_matches
                )
            )

        if dominant_match:

            reasons.append(
                "Observed dominant order "
                f"{order_label(features.dominant_order)} "
                "matches the explicitly expected dominant pattern."
            )

        elif expectation.dominant_orders:

            reasons.append(
                "Observed dominant order does not "
                "match the explicitly expected dominant order."
            )

        if machine_context_matches:

            reasons.append(
                "Machine context matches: "
                + ", ".join(
                    machine_context_matches
                )
            )

        if expectation.fault_mechanisms:

            reasons.append(
                "Fault mechanism described by database: "
                + ", ".join(
                    expectation.fault_mechanisms
                )
            )

        if matched_directions:

            reasons.append(
                "Direction matches: "
                + ", ".join(
                    matched_directions
                )
            )

        if (
            expectation.has_harmonics_statement
        ):

            reasons.append(
                "Database document describes harmonic content."
            )

        return EvidenceMatrix(

            score=score,

            document=document,

            expected_orders=(
                expectation.expected_orders
            ),

            optional_orders=(
                expectation.optional_orders
            ),

            observed_orders=sorted(
                self._observed_orders(
                    features
                )
            ),

            matched_orders=matched_orders,

            missing_orders=missing_orders,

            optional_matches=optional_matches,

            strong_matches=strong_matches,

            typical_matches=typical_matches,

            dominant_expected=sorted(
                expectation.dominant_orders
            ),

            dominant_observed=(
                features.dominant_order
            ),

            dominant_match=dominant_match,

            pattern_coverage=coverage,

            optional_coverage=optional_coverage,

            expected_ranges=(
                expectation.ranges
            ),

            machine_context_matches=(
                machine_context_matches
            ),

            machine_context_missing=(
                machine_context_missing
            ),

            fault_mechanisms=sorted(
                expectation.fault_mechanisms
            ),

            matched_directions=(
                matched_directions
            ),

            missing_directions=(
                missing_directions
            ),

            matched_ratios=(
                matched_ratios
            ),

            keyword_matches=(
                keyword_matches
            ),

            reasons=reasons,

            support_score=support_score,

            missing_penalty=missing_penalty,

            dominant_score=dominant_score,

            amplitude_score=amplitude_score,

            context_score=context_score,

            expectation=expectation,
        )

    def match(
        self,
        features: VibrationFeatures,
        machine_context: Optional[MachineContext] = None,
        top_k: int = 10,
    ) -> List[EvidenceMatrix]:

        self.database._ensure_loaded()

        results = []

        for document in (
            self.database.documents
        ):

            matrix = self.score_document(
                document,
                features,
                machine_context,
            )

            results.append(matrix)

        results.sort(
            key=lambda item: (
                item.score,
                item.pattern_coverage,
                item.dominant_match,
                len(item.matched_orders),
            ),
            reverse=True,
        )

        return results[:top_k]

    @staticmethod
    def build_query(
        features: VibrationFeatures,
        machine_context: Optional[MachineContext] = None,
    ) -> str:

        parts = []

        if features.rpm:

            parts.append(
                f"{features.rpm} RPM"
            )

        if (
            features.dominant_order
            is not None
        ):

            parts.append(
                "dominant "
                + order_label(
                    features.dominant_order
                )
            )

        if features.present_orders:

            parts.append(
                "orders "
                + " ".join(
                    order_label(
                        float(x)
                    )
                    for x in features.present_orders
                )
            )

        if machine_context:

            data = machine_context.to_dict()

            for key in [
                "equipment_type",
                "equipment_category",
                "brand",
                "model",
                "connection_type",
                "transmission_type",
                "bearing_count",
                "measurement_point",
                "direction",
            ]:

                value = data.get(key)

                if value:

                    parts.append(
                        str(value)
                    )

        return " ".join(parts)

    @staticmethod
    def print_matrix(
        matrix: EvidenceMatrix,
        index: Optional[int] = None,
    ):

        document = matrix.document

        print()
        print("=" * 78)

        if index is not None:

            print(
                f"[{index}] "
                f"{document.title or document.document_id}"
            )

        else:

            print(
                document.title
                or document.document_id
            )

        print("=" * 78)

        print(
            f"Score              : "
            f"{matrix.score:.3f}"
        )

        print(
            f"Pattern Coverage   : "
            f"{len(matrix.matched_orders)} / "
            f"{len(matrix.expected_orders)} "
            f"({matrix.pattern_coverage * 100:.1f}%)"
        )

        print(
            f"Optional Coverage  : "
            f"{len(matrix.optional_matches)} / "
            f"{len(matrix.optional_orders)} "
            f"({matrix.optional_coverage * 100:.1f}%)"
        )

        print()

        print(
            "Expected Orders    : "
            + (
                ", ".join(
                    order_label(x)
                    for x in matrix.expected_orders
                )
                if matrix.expected_orders
                else "None"
            )
        )

        if matrix.optional_orders:

            print(
                "Optional Orders    : "
                + ", ".join(
                    order_label(x)
                    for x in matrix.optional_orders
                )
            )

        print(
            "Observed Orders    : "
            + ", ".join(
                order_label(x)
                for x in matrix.observed_orders
            )
        )

        print()

        print(
            "Matched Orders     : "
            + (
                ", ".join(
                    order_label(x)
                    for x in matrix.matched_orders
                )
                if matrix.matched_orders
                else "None"
            )
        )

        print(
            "Missing Evidence   : "
            + (
                ", ".join(
                    order_label(x)
                    for x in matrix.missing_orders
                )
                if matrix.missing_orders
                else "None"
            )
        )

        if matrix.optional_matches:

            print(
                "Optional Matches   : "
                + ", ".join(
                    order_label(x)
                    for x in matrix.optional_matches
                )
            )

        if matrix.dominant_expected:

            print(
                "Expected Dominant  : "
                + ", ".join(
                    order_label(x)
                    for x in matrix.dominant_expected
                )
            )

            observed = (
                order_label(
                    matrix.dominant_observed
                )
                if matrix.dominant_observed
                is not None
                else "None"
            )

            print(
                f"Observed Dominant  : "
                f"{observed}"
            )

            print(
                "Dominant Match     : "
                + (
                    "YES"
                    if matrix.dominant_match
                    else "NO"
                )
            )

        if matrix.machine_context_matches:

            print(
                "Machine Context    : "
                + ", ".join(
                    matrix.machine_context_matches
                )
            )

        if matrix.machine_context_missing:

            print(
                "Context Missing    : "
                + ", ".join(
                    matrix.machine_context_missing
                )
            )

        if matrix.fault_mechanisms:

            print(
                "Fault Mechanism    : "
                + ", ".join(
                    matrix.fault_mechanisms
                )
            )

        if matrix.matched_directions:

            print(
                "Direction Match    : "
                + ", ".join(
                    matrix.matched_directions
                )
            )

        if matrix.missing_directions:

            print(
                "Direction Missing  : "
                + ", ".join(
                    matrix.missing_directions
                )
            )

        if matrix.matched_ratios:

            print(
                "Ratio Evidence     : "
                + ", ".join(
                    matrix.matched_ratios
                )
            )

        print()

        print(
            f"Support Score      : "
            f"{matrix.support_score:.3f}"
        )

        print(
            f"Missing Penalty    : "
            f"{matrix.missing_penalty:.3f}"
        )

        print(
            f"Dominant Score     : "
            f"{matrix.dominant_score:.3f}"
        )

        print(
            f"Amplitude Score    : "
            f"{matrix.amplitude_score:.3f}"
        )

        print(
            f"Context Score      : "
            f"{matrix.context_score:.3f}"
        )

        if matrix.reasons:

            print()
            print("Evidence:")

            for reason in matrix.reasons:

                print(
                    f"  • {reason}"
                )

    def print_results(
        self,
        results: List[EvidenceMatrix],
    ):

        print()
        print("=" * 78)
        print(
            "PATTERN MATCHING / EVIDENCE MATRIX"
        )
        print("=" * 78)

        print(
            f"Documents scanned : "
            f"{len(self.database.documents)}"
        )

        print(
            f"Results returned  : "
            f"{len(results)}"
        )

        for index, result in enumerate(
            results,
            start=1,
        ):

            self.print_matrix(
                result,
                index=index,
            )


# ============================================================
# TEST FEATURES
# ============================================================

def create_test_features() -> VibrationFeatures:

    return VibrationFeatures(

        rpm=1500,

        fundamental_amplitude=53.0,

        dominant_order=3.0,

        dominant_amplitude=243.0,

        dominant_relative=1.0,

        present_orders=[
            1,
            2,
            3,
            4,
            5,
            7,
            8,
        ],

        missing_orders=[
            6,
            9,
            10,
        ],

        harmonic_count=7,

        highest_order=8,

        odd_orders=[
            1,
            3,
            5,
            7,
        ],

        even_orders=[
            2,
            4,
            8,
        ],

        odd_amplitude=372,

        even_amplitude=203,

        odd_even_ratio=1.8325,

        low_order_amplitude=437,

        mid_order_amplitude=93,

        high_order_amplitude=45,

        high_low_ratio=0.1030,

        total_amplitude=575,

        mean_amplitude=82.143,

        amplitude_spread=2.958,

        average_confidence=0.780,

        minimum_confidence=0.141,

        maximum_confidence=0.991,

        order_ratios={
            "2X_to_1X": 2.6604,
            "3X_to_1X": 4.5849,
            "4X_to_1X": 0.7925,
            "5X_to_1X": 0.9623,
            "7X_to_1X": 0.4717,
            "8X_to_1X": 0.3774,
            "3X_to_2X": 1.7234,
        },

        amplitudes={
            1.0: 53.0,
            2.0: 141.0,
            3.0: 243.0,
            4.0: 42.0,
            5.0: 51.0,
            7.0: 25.0,
            8.0: 20.0,
        },

        confidences={
            1.0: 0.141,
            2.0: 0.924,
            3.0: 0.882,
            4.0: 0.860,
            5.0: 0.991,
            7.0: 0.833,
            8.0: 0.829,
        },
    )


# ============================================================
# TEST CONTEXT
# ============================================================

def create_test_context() -> MachineContext:

    return MachineContext(

        equipment_type="Electric Motor",

        equipment_category="Rotating Machinery",

        brand="Test",

        model="Test Model",

        rpm=1500,

        connection_type="Coupling",

        transmission_type="Direct Coupled",

        bearing_count=2,

        bearings=[
            "Rolling Element Bearing",
            "Rolling Element Bearing",
        ],

        measurement_point="Motor DE",

        direction="Horizontal",

        sensor_type="Accelerometer",

        analysis_mode="FFT",
    )


# ============================================================
# MAIN
# ============================================================

def test_knowledge_matcher():

    print()
    print("=" * 78)
    print(
        "AI CONDITION — PATTERN MATCHING"
    )
    print("=" * 78)

    features = create_test_features()

    context = create_test_context()

    matcher = KnowledgeMatcher(
        database_root="database"
    )

    print()

    print(
        f"RPM              : "
        f"{features.rpm}"
    )

    print(
        "Observed Orders  : "
        + ", ".join(
            order_label(
                float(x)
            )
            for x in features.present_orders
        )
    )

    print(
        f"Dominant Order   : "
        f"{order_label(features.dominant_order)}"
    )

    print(
        f"Context          : "
        f"{context.equipment_type} / "
        f"{context.connection_type} / "
        f"{context.direction}"
    )

    results = matcher.match(
        features=features,
        machine_context=context,
        top_k=10,
    )

    matcher.print_results(
        results
    )

    print()
    print("=" * 78)
    print(
        "PATTERN MATCHING COMPLETE"
    )
    print("=" * 78)


if __name__ == "__main__":
    test_knowledge_matcher()