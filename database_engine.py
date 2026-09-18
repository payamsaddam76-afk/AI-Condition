import json
import re
from pathlib import Path
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Optional


# ============================================================
# CONFIG
# ============================================================

DATABASE_PATH = Path(
    r"C:\Users\Lenovo\PycharmProjects\PythonProject4\AI-Condition\database"
)


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class KnowledgeDocument:
    """
    یک واحد دانش استخراج‌شده از Database.

    هر JSON می‌تواند یک یا چند document تولید کند.
    """

    document_id: str

    source_file: str

    source_folder: str

    chapter: Optional[str] = None

    page: Optional[str] = None

    title: Optional[str] = None

    section: Optional[str] = None

    section_en: Optional[str] = None

    text: str = ""

    metadata: dict = field(default_factory=dict)


@dataclass
class SearchResult:
    """
    نتیجه جستجوی Database.
    """

    score: float

    document: KnowledgeDocument

    matched_terms: list[str] = field(
        default_factory=list
    )

    matched_fields: list[str] = field(
        default_factory=list
    )


# ============================================================
# MACHINE CONTEXT
# ============================================================

@dataclass
class MachineContext:
    """
    اطلاعات ساختاری و عملیاتی تجهیز.

    این کلاس فعلاً مستقل از Streamlit است.
    بعداً UI فقط این اطلاعات را پر خواهد کرد.
    """

    equipment_type: Optional[str] = None

    equipment_category: Optional[str] = None

    brand: Optional[str] = None

    model: Optional[str] = None

    serial_number: Optional[str] = None

    rpm: Optional[float] = None

    load: Optional[float] = None

    load_type: Optional[str] = None

    power: Optional[float] = None

    temperature: Optional[float] = None

    connection_type: Optional[str] = None

    transmission_type: Optional[str] = None

    shaft_configuration: Optional[str] = None

    gearbox_type: Optional[str] = None

    bearing_count: Optional[int] = None

    bearings: list[dict] = field(
        default_factory=list
    )

    measurement_point: Optional[str] = None

    direction: Optional[str] = None

    sensor_type: Optional[str] = None

    analysis_mode: Optional[str] = None

    extra: dict = field(
        default_factory=dict
    )

    def to_dict(self):
        """
        تبدیل Context به dictionary.
        """

        return {
            "equipment": {
                "type": self.equipment_type,
                "category": self.equipment_category,
                "brand": self.brand,
                "model": self.model,
                "serial_number": self.serial_number,
            },

            "operating": {
                "rpm": self.rpm,
                "load": self.load,
                "load_type": self.load_type,
                "power": self.power,
                "temperature": self.temperature,
            },

            "mechanical": {
                "connection_type": self.connection_type,
                "transmission_type": self.transmission_type,
                "shaft_configuration":
                    self.shaft_configuration,
                "gearbox_type":
                    self.gearbox_type,
            },

            "bearings": {
                "count": self.bearing_count,
                "items": self.bearings,
            },

            "measurement": {
                "point": self.measurement_point,
                "direction": self.direction,
                "sensor_type": self.sensor_type,
            },

            "analysis": {
                "mode": self.analysis_mode,
            },

            "extra": self.extra,
        }


# ============================================================
# TEXT UTILITIES
# ============================================================

def normalize_text(text: Any) -> str:
    """
    نرمال‌سازی متن برای Search.

    هدف:
    - حذف فاصله‌های اضافی
    - یکسان‌سازی حروف عربی/فارسی
    - lowercase
    """

    if text is None:
        return ""

    text = str(text)

    replacements = {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
        "\u200c": " ",
        "\u200f": " ",
        "\u200e": " ",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new
        )

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def tokenize(text: str) -> list[str]:
    """
    استخراج tokenهای ساده فارسی/انگلیسی/عددی.
    """

    text = normalize_text(text)

    tokens = re.findall(
        r"[a-zA-Z0-9\u0600-\u06ff]+",
        text
    )

    return tokens


def flatten_json(
    value: Any,
    prefix: str = ""
) -> list[tuple[str, str]]:
    """
    JSON تو در تو را به جفت‌های field/value تبدیل می‌کند.

    مثال:

    {
        "title": "Alignment",
        "data": {
            "type": "Angular"
        }
    }

    تبدیل می‌شود به:

    title -> Alignment
    data.type -> Angular
    """

    result = []

    if isinstance(value, dict):

        for key, child in value.items():

            key_name = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            result.extend(
                flatten_json(
                    child,
                    key_name
                )
            )

    elif isinstance(value, list):

        for index, child in enumerate(value):

            key_name = (
                f"{prefix}[{index}]"
            )

            result.extend(
                flatten_json(
                    child,
                    key_name
                )
            )

    else:

        result.append(
            (
                prefix,
                str(value)
            )
        )

    return result


# ============================================================
# DATABASE ENGINE
# ============================================================

class DatabaseEngine:

    def __init__(
        self,
        database_path: Path = DATABASE_PATH
    ):

        self.database_path = Path(
            database_path
        )

        self.documents: list[
            KnowledgeDocument
        ] = []

        self.index: dict[
            str,
            set[str]
        ] = {}

        self.term_frequency = Counter()

        self.folder_counter = Counter()

        self.file_counter = Counter()

        self.loaded = False

    # ========================================================
    # LOAD DATABASE
    # ========================================================

    def load(self):
        """
        تمام JSONهای Database را می‌خواند
        و به KnowledgeDocument تبدیل می‌کند.
        """

        self.documents.clear()

        self.index.clear()

        self.term_frequency.clear()

        self.folder_counter.clear()

        self.file_counter.clear()

        if not self.database_path.exists():

            raise FileNotFoundError(
                f"Database not found:\n"
                f"{self.database_path}"
            )

        json_files = sorted(
            self.database_path.rglob(
                "*.json"
            )
        )

        for file_path in json_files:

            try:

                with open(
                    file_path,
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = json.load(
                        file
                    )

                self._process_json_file(
                    file_path,
                    data
                )

            except Exception as error:

                print(
                    f"[WARNING] Could not read:"
                    f" {file_path}"
                )

                print(
                    f"          {error}"
                )

        self._build_index()

        self.loaded = True

        return self

    # ========================================================
    # PROCESS JSON FILE
    # ========================================================

    def _process_json_file(
        self,
        file_path: Path,
        data: Any
    ):

        relative_path = (
            file_path.relative_to(
                self.database_path
            )
        )

        relative_str = str(
            relative_path
        )

        folder = (
            relative_path.parts[0]
            if len(relative_path.parts) > 1
            else "ROOT"
        )

        self.folder_counter[
            folder
        ] += 1

        self.file_counter[
            relative_str
        ] += 1

        # ----------------------------------------------------
        # Standard page/document JSON
        # ----------------------------------------------------

        if self._looks_like_document(data):

            document = (
                self._create_document(
                    file_path,
                    data
                )
            )

            self.documents.append(
                document
            )

            return

        # ----------------------------------------------------
        # Nested JSON
        # ----------------------------------------------------

        if isinstance(data, dict):

            created = False

            for key, value in data.items():

                if not isinstance(
                    value,
                    (dict, list)
                ):

                    continue

                nested_documents = (
                    self._extract_nested_documents(
                        file_path=file_path,
                        parent_key=str(key),
                        value=value
                    )
                )

                if nested_documents:

                    self.documents.extend(
                        nested_documents
                    )

                    created = True

            if created:
                return

        # ----------------------------------------------------
        # Generic fallback
        # ----------------------------------------------------

        text = self._json_to_text(
            data
        )

        document = KnowledgeDocument(
            document_id=self._make_document_id(
                relative_str,
                "root"
            ),

            source_file=relative_str,

            source_folder=folder,

            text=text,

            metadata={
                "json_type":
                    type(data).__name__
            }
        )

        self.documents.append(
            document
        )

    # ========================================================
    # DOCUMENT DETECTION
    # ========================================================

    @staticmethod
    def _looks_like_document(
        data: Any
    ) -> bool:

        if not isinstance(
            data,
            dict
        ):
            return False

        keys = {
            str(key).lower()
            for key in data.keys()
        }

        document_keys = {
            "content",
            "title",
            "page",
            "chapter",
            "section",
            "section_en"
        }

        return bool(
            keys.intersection(
                document_keys
            )
        )

    # ========================================================
    # CREATE STANDARD DOCUMENT
    # ========================================================

    def _create_document(
        self,
        file_path: Path,
        data: dict
    ) -> KnowledgeDocument:

        relative_path = (
            file_path.relative_to(
                self.database_path
            )
        )

        relative_str = str(
            relative_path
        )

        folder = (
            relative_path.parts[0]
            if len(relative_path.parts) > 1
            else "ROOT"
        )

        chapter = data.get(
            "chapter"
        )

        page = data.get(
            "page"
        )

        title = data.get(
            "title"
        )

        section = data.get(
            "section"
        )

        section_en = data.get(
            "section_en"
        )

        content = data.get(
            "content"
        )

        text_parts = []

        for value in [
            chapter,
            page,
            title,
            section,
            section_en,
            content,
        ]:

            if value is not None:

                text_parts.append(
                    self._json_to_text(
                        value
                    )
                )

        # Include any additional fields.
        known_keys = {
            "chapter",
            "page",
            "title",
            "section",
            "section_en",
            "content",
        }

        for key, value in data.items():

            if key in known_keys:
                continue

            text_parts.append(
                self._json_to_text(
                    value
                )
            )

        text = " ".join(
            part
            for part in text_parts
            if part
        )

        return KnowledgeDocument(
            document_id=self._make_document_id(
                relative_str,
                "root"
            ),

            source_file=relative_str,

            source_folder=folder,

            chapter=(
                str(chapter)
                if chapter is not None
                else None
            ),

            page=(
                str(page)
                if page is not None
                else None
            ),

            title=(
                str(title)
                if title is not None
                else None
            ),

            section=(
                str(section)
                if section is not None
                else None
            ),

            section_en=(
                str(section_en)
                if section_en is not None
                else None
            ),

            text=text,

            metadata={
                "source_type":
                    "document_json"
            }
        )

    # ========================================================
    # NESTED DOCUMENT EXTRACTION
    # ========================================================

    def _extract_nested_documents(
        self,
        file_path: Path,
        parent_key: str,
        value: Any
    ) -> list[KnowledgeDocument]:

        documents = []

        relative_path = (
            file_path.relative_to(
                self.database_path
            )
        )

        relative_str = str(
            relative_path
        )

        folder = (
            relative_path.parts[0]
            if len(relative_path.parts) > 1
            else "ROOT"
        )

        if isinstance(
            value,
            dict
        ):

            # --------------------------------------------
            # Nested page object
            # --------------------------------------------

            text = self._json_to_text(
                value
            )

            title = value.get(
                "title"
            )

            page = value.get(
                "page"
            )

            section = value.get(
                "section"
            )

            section_en = value.get(
                "section_en"
            )

            chapter = value.get(
                "chapter"
            )

            document = KnowledgeDocument(
                document_id=self._make_document_id(
                    relative_str,
                    parent_key
                ),

                source_file=relative_str,

                source_folder=folder,

                chapter=(
                    str(chapter)
                    if chapter is not None
                    else None
                ),

                page=(
                    str(page)
                    if page is not None
                    else parent_key
                ),

                title=(
                    str(title)
                    if title is not None
                    else parent_key
                ),

                section=(
                    str(section)
                    if section is not None
                    else None
                ),

                section_en=(
                    str(section_en)
                    if section_en is not None
                    else None
                ),

                text=text,

                metadata={
                    "source_type":
                        "nested_document",

                    "parent_key":
                        parent_key
                }
            )

            documents.append(
                document
            )

        elif isinstance(
            value,
            list
        ):

            for index, item in enumerate(
                value
            ):

                nested_key = (
                    f"{parent_key}[{index}]"
                )

                documents.extend(
                    self._extract_nested_documents(
                        file_path=file_path,
                        parent_key=nested_key,
                        value=item
                    )
                )

        return documents

    # ========================================================
    # JSON TO TEXT
    # ========================================================

    def _json_to_text(
        self,
        value: Any
    ) -> str:

        if value is None:

            return ""

        if isinstance(
            value,
            str
        ):

            return value

        if isinstance(
            value,
            (int, float, bool)
        ):

            return str(value)

        if isinstance(
            value,
            list
        ):

            parts = []

            for item in value:

                text = self._json_to_text(
                    item
                )

                if text:
                    parts.append(
                        text
                    )

            return " ".join(parts)

        if isinstance(
            value,
            dict
        ):

            parts = []

            for key, child in value.items():

                child_text = (
                    self._json_to_text(
                        child
                    )
                )

                if child_text:

                    parts.append(
                        f"{key}: {child_text}"
                    )

            return " ".join(parts)

        return str(value)

    # ========================================================
    # DOCUMENT ID
    # ========================================================

    @staticmethod
    def _make_document_id(
        source_file: str,
        suffix: str
    ) -> str:

        safe_file = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            source_file
        )

        safe_suffix = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            suffix
        )

        return (
            f"{safe_file}__{safe_suffix}"
        )

    # ========================================================
    # BUILD SEARCH INDEX
    # ========================================================

    def _build_index(self):

        index = {}

        for document in self.documents:

            searchable_text = " ".join(
                [
                    document.chapter or "",
                    document.page or "",
                    document.title or "",
                    document.section or "",
                    document.section_en or "",
                    document.text or "",
                ]
            )

            tokens = set(
                tokenize(
                    searchable_text
                )
            )

            for token in tokens:

                if token not in index:

                    index[token] = set()

                index[token].add(
                    document.document_id
                )

            for token in tokenize(
                searchable_text
            ):

                self.term_frequency[
                    token
                ] += 1

        self.index = index

    # ========================================================
    # ENSURE LOADED
    # ========================================================

    def _ensure_loaded(self):

        if not self.loaded:

            self.load()

    # ========================================================
    # SIMPLE SEARCH
    # ========================================================

    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> list[SearchResult]:
        """
        جستجوی متنی در کل Database.

        فعلاً keyword based است.
        در مرحله بعد semantic/AI search
        روی همین معماری اضافه خواهد شد.
        """

        self._ensure_loaded()

        query_tokens = tokenize(
            query
        )

        if not query_tokens:

            return []

        results = []

        for document in self.documents:

            score = 0.0

            matched_terms = []

            matched_fields = []

            # --------------------------------------------
            # Searchable fields
            # --------------------------------------------

            fields = {
                "chapter":
                    document.chapter or "",

                "page":
                    document.page or "",

                "title":
                    document.title or "",

                "section":
                    document.section or "",

                "section_en":
                    document.section_en or "",

                "text":
                    document.text or "",
            }

            normalized_fields = {
                key: normalize_text(
                    value
                )
                for key, value in fields.items()
            }

            # --------------------------------------------
            # Score each query term
            # --------------------------------------------

            for term in query_tokens:

                term_found = False

                for field_name, field_text in (
                    normalized_fields.items()
                ):

                    if term in field_text:

                        term_found = True

                        if term not in matched_terms:

                            matched_terms.append(
                                term
                            )

                        if field_name not in matched_fields:

                            matched_fields.append(
                                field_name
                            )

                        # --------------------------------
                        # Field importance
                        # --------------------------------

                        if field_name == "title":

                            score += 5.0

                        elif field_name == "section":

                            score += 4.0

                        elif field_name == "section_en":

                            score += 4.0

                        elif field_name == "chapter":

                            score += 2.0

                        elif field_name == "page":

                            score += 1.0

                        else:

                            score += 2.0

                if not term_found:
                    continue

            # --------------------------------------------
            # Multi-term bonus
            # --------------------------------------------

            if matched_terms:

                coverage = (
                    len(matched_terms)
                    / len(query_tokens)
                )

                score += (
                    coverage * 5.0
                )

            # --------------------------------------------
            # Exact phrase bonus
            # --------------------------------------------

            normalized_query = normalize_text(
                query
            )

            normalized_full_text = normalize_text(
                " ".join(
                    fields.values()
                )
            )

            if (
                normalized_query
                and normalized_query
                in normalized_full_text
            ):

                score += 10.0

            if score > 0:

                results.append(
                    SearchResult(
                        score=score,

                        document=document,

                        matched_terms=matched_terms,

                        matched_fields=matched_fields
                    )
                )

        results.sort(
            key=lambda result:
                result.score,
            reverse=True
        )

        return results[:top_k]

    # ========================================================
    # CONTEXT SEARCH
    # ========================================================

    def search_with_context(
        self,
        query: str,
        machine_context: MachineContext,
        top_k: int = 10
    ) -> list[SearchResult]:
        """
        جستجو بر اساس Query + Machine Context.

        فعلاً Context به Query تبدیل می‌شود.
        در مرحله بعد وزن‌دهی تخصصی‌تر اضافه خواهد شد.
        """

        context_terms = []

        # Equipment
        for value in [
            machine_context.equipment_type,
            machine_context.equipment_category,
            machine_context.brand,
            machine_context.model,
            machine_context.connection_type,
            machine_context.transmission_type,
            machine_context.shaft_configuration,
            machine_context.gearbox_type,
            machine_context.measurement_point,
            machine_context.direction,
            machine_context.sensor_type,
            machine_context.analysis_mode,
        ]:

            if value:

                context_terms.append(
                    str(value)
                )

        # Bearings
        for bearing in (
            machine_context.bearings
        ):

            if not isinstance(
                bearing,
                dict
            ):
                continue

            for value in bearing.values():

                if value:

                    context_terms.append(
                        str(value)
                    )

        combined_query = " ".join(
            [query]
            + context_terms
        )

        return self.search(
            combined_query,
            top_k=top_k
        )

    # ========================================================
    # DATABASE STATS
    # ========================================================

    def stats(self) -> dict:

        self._ensure_loaded()

        return {
            "database_path":
                str(self.database_path),

            "json_files":
                len(self.file_counter),

            "documents":
                len(self.documents),

            "indexed_terms":
                len(self.index),

            "folders":
                dict(
                    self.folder_counter
                ),
        }

    # ========================================================
    # PRINT SUMMARY
    # ========================================================

    def print_summary(self):

        self._ensure_loaded()

        stats = self.stats()

        print()
        print("=" * 80)
        print("DATABASE ENGINE SUMMARY")
        print("=" * 80)

        print()
        print(
            f"Database path : "
            f"{stats['database_path']}"
        )

        print(
            f"JSON files    : "
            f"{stats['json_files']}"
        )

        print(
            f"Documents     : "
            f"{stats['documents']}"
        )

        print(
            f"Indexed terms : "
            f"{stats['indexed_terms']}"
        )

        print()
        print(
            "Documents by folder:"
        )

        for folder, count in sorted(
            self.folder_counter.items()
        ):

            print(
                f"  {folder:<40}"
                f"{count:>5}"
            )

        print()
        print("=" * 80)

    # ========================================================
    # PRINT SEARCH RESULTS
    # ========================================================

    @staticmethod
    def print_results(
        results: list[SearchResult]
    ):

        print()
        print("=" * 80)
        print("DATABASE SEARCH RESULTS")
        print("=" * 80)

        if not results:

            print()
            print(
                "No relevant documents found."
            )

            return

        for index, result in enumerate(
            results,
            start=1
        ):

            document = result.document

            print()
            print(
                f"[{index}] "
                f"Score: "
                f"{result.score:.3f}"
            )

            print(
                f"Source: "
                f"{document.source_file}"
            )

            if document.title:

                print(
                    f"Title : "
                    f"{document.title}"
                )

            if document.section:

                print(
                    f"Section: "
                    f"{document.section}"
                )

            if document.section_en:

                print(
                    f"Section EN: "
                    f"{document.section_en}"
                )

            if document.page:

                print(
                    f"Page: "
                    f"{document.page}"
                )

            print(
                f"Matched terms: "
                f"{', '.join(result.matched_terms)}"
            )

            print(
                f"Matched fields: "
                f"{', '.join(result.matched_fields)}"
            )

            text = normalize_text(
                document.text
            )

            if len(text) > 500:

                text = (
                    text[:500]
                    + " ..."
                )

            print(
                f"Text: {text}"
            )


# ============================================================
# TEST
# ============================================================

def test_database_engine():

    print()
    print("=" * 80)
    print("AI-CONDITION DATABASE ENGINE TEST")
    print("=" * 80)

    engine = DatabaseEngine()

    engine.load()

    engine.print_summary()

    # --------------------------------------------------------
    # Test queries
    # --------------------------------------------------------

    queries = [
        "alignment",
        "balancing",
        "bearing",
        "vibration",
        "misalignment",
        "looseness",
        "gear",
        "harmonic",
    ]

    for query in queries:

        print()
        print()
        print(
            "#" * 80
        )

        print(
            f"QUERY: {query}"
        )

        print(
            "#" * 80
        )

        results = engine.search(
            query,
            top_k=5
        )

        engine.print_results(
            results
        )

    # --------------------------------------------------------
    # Context test
    # --------------------------------------------------------

    print()
    print()
    print(
        "#" * 80
    )

    print(
        "CONTEXT SEARCH TEST"
    )

    print(
        "#" * 80
    )

    context = MachineContext(
        equipment_type="Electric Motor",

        rpm=1500,

        connection_type="Coupling",

        bearing_count=2,

        bearings=[
            {
                "id": "B1",
                "type":
                    "Rolling Element Bearing",
                "location":
                    "Motor DE",
            },
            {
                "id": "B2",
                "type":
                    "Rolling Element Bearing",
                "location":
                    "Motor NDE",
            },
        ],

        measurement_point="Motor DE",

        direction="Horizontal",
    )

    context_results = (
        engine.search_with_context(
            query=(
                "1X 2X 3X "
                "multiple harmonics"
            ),

            machine_context=context,

            top_k=10
        )
    )

    engine.print_results(
        context_results
    )

    print()
    print("=" * 80)
    print("DATABASE ENGINE TEST COMPLETE")
    print("=" * 80)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    test_database_engine()