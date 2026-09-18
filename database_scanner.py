import json
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# CONFIG
# ============================================================

DATABASE_PATH = Path(
    r"C:\Users\Lenovo\PycharmProjects\PythonProject4\AI-Condition\database"
)


# ============================================================
# HELPERS
# ============================================================

def get_json_structure(data):
    """
    Return a readable description of the top-level JSON structure.
    """

    if isinstance(data, dict):

        keys = sorted(
            str(key)
            for key in data.keys()
        )

        if len(keys) > 20:
            keys = keys[:20] + ["..."]

        return (
            "OBJECT | Keys: "
            + ", ".join(keys)
        )

    if isinstance(data, list):

        if not data:
            return "ARRAY | Empty"

        first = data[0]

        if isinstance(first, dict):

            keys = sorted(
                str(key)
                for key in first.keys()
            )

            if len(keys) > 20:
                keys = keys[:20] + ["..."]

            return (
                "ARRAY | First item OBJECT | Keys: "
                + ", ".join(keys)
            )

        return (
            "ARRAY | First item type: "
            + type(first).__name__
        )

    return (
        "VALUE | Type: "
        + type(data).__name__
    )


def count_json_values(value, counters):
    """
    Recursively count JSON value types.
    """

    if isinstance(value, dict):

        counters["objects"] += 1

        for child in value.values():
            count_json_values(
                child,
                counters
            )

    elif isinstance(value, list):

        counters["arrays"] += 1

        for child in value:
            count_json_values(
                child,
                counters
            )

    elif isinstance(value, str):

        counters["strings"] += 1

    elif isinstance(value, bool):

        counters["booleans"] += 1

    elif isinstance(
        value,
        (int, float)
    ):

        counters["numbers"] += 1


# ============================================================
# DATABASE SCANNER
# ============================================================

def scan_database(database_path):

    print()
    print("=" * 80)
    print("AI-CONDITION DATABASE SCANNER")
    print("=" * 80)

    print()
    print(
        f"Database:"
    )

    print(
        database_path
    )

    # --------------------------------------------------------
    # Check database
    # --------------------------------------------------------

    if not database_path.exists():

        print()
        print(
            "ERROR: Database folder does not exist."
        )

        return

    if not database_path.is_dir():

        print()
        print(
            "ERROR: Database path is not a folder."
        )

        return

    # --------------------------------------------------------
    # Find ALL JSON files
    # --------------------------------------------------------

    json_files = sorted(
        database_path.rglob("*.json")
    )

    print()
    print(
        f"Total JSON files found: "
        f"{len(json_files)}"
    )

    if not json_files:

        print()
        print(
            "NO JSON FILES FOUND."
        )

        return

    # --------------------------------------------------------
    # Folder statistics
    # --------------------------------------------------------

    folder_counter = Counter()

    for file_path in json_files:

        relative_path = (
            file_path.relative_to(
                database_path
            )
        )

        if len(relative_path.parts) > 1:

            folder = relative_path.parts[0]

        else:

            folder = "ROOT"

        folder_counter[
            folder
        ] += 1

    print()
    print("=" * 80)
    print("FILES BY MAIN FOLDER")
    print("=" * 80)

    for folder, count in sorted(
        folder_counter.items()
    ):

        print(
            f"{folder:<40}"
            f"{count:>6}"
        )

    # --------------------------------------------------------
    # JSON analysis
    # --------------------------------------------------------

    valid_files = 0
    invalid_files = 0

    structure_counter = Counter()

    structure_examples = defaultdict(list)

    value_counters = Counter()

    file_information = []

    # --------------------------------------------------------
    # Read every JSON
    # --------------------------------------------------------

    for index, file_path in enumerate(
        json_files,
        start=1
    ):

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(
                    file
                )

            valid_files += 1

            structure = get_json_structure(
                data
            )

            structure_counter[
                structure
            ] += 1

            if len(
                structure_examples[
                    structure
                ]
            ) < 3:

                structure_examples[
                    structure
                ].append(
                    str(
                        file_path.relative_to(
                            database_path
                        )
                    )
                )

            count_json_values(
                data,
                value_counters
            )

            # --------------------------------------------
            # Basic file information
            # --------------------------------------------

            relative_path = (
                file_path.relative_to(
                    database_path
                )
            )

            file_information.append(
                {
                    "file":
                        str(relative_path),

                    "structure":
                        structure,

                    "size":
                        file_path.stat().st_size,
                }
            )

        except Exception as error:

            invalid_files += 1

            print()
            print(
                "JSON READ ERROR"
            )

            print(
                f"File : {file_path}"
            )

            print(
                f"Error: {error}"
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 80)
    print("DATABASE SUMMARY")
    print("=" * 80)

    print()
    print(
        f"Total files      : "
        f"{len(json_files)}"
    )

    print(
        f"Valid JSON files : "
        f"{valid_files}"
    )

    print(
        f"Invalid files    : "
        f"{invalid_files}"
    )

    # ========================================================
    # VALUE STATISTICS
    # ========================================================

    print()
    print("=" * 80)
    print("JSON VALUE STATISTICS")
    print("=" * 80)

    print()
    print(
        f"Objects   : "
        f"{value_counters['objects']}"
    )

    print(
        f"Arrays    : "
        f"{value_counters['arrays']}"
    )

    print(
        f"Strings   : "
        f"{value_counters['strings']}"
    )

    print(
        f"Numbers   : "
        f"{value_counters['numbers']}"
    )

    print(
        f"Booleans  : "
        f"{value_counters['booleans']}"
    )

    # ========================================================
    # STRUCTURES
    # ========================================================

    print()
    print("=" * 80)
    print("JSON STRUCTURES")
    print("=" * 80)

    structure_number = 1

    for structure, count in (
        structure_counter
        .most_common()
    ):

        print()
        print(
            f"[Structure {structure_number}]"
        )

        print(
            f"Count: {count}"
        )

        print(
            f"{structure}"
        )

        print(
            "Examples:"
        )

        for example in (
            structure_examples[
                structure
            ]
        ):

            print(
                f"  {example}"
            )

        structure_number += 1

    # ========================================================
    # FILE LIST
    # ========================================================

    print()
    print("=" * 80)
    print("ALL JSON FILES")
    print("=" * 80)

    for item in file_information:

        print()
        print(
            f"FILE: {item['file']}"
        )

        print(
            f"SIZE: {item['size']} bytes"
        )

        print(
            f"TYPE: {item['structure']}"
        )

    # ========================================================
    # END
    # ========================================================

    print()
    print("=" * 80)
    print("DATABASE SCAN COMPLETE")
    print("=" * 80)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    scan_database(
        DATABASE_PATH
    )