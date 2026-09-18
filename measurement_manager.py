
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from database_engine import MachineContext

from engine.multi_measurement_analyzer import MultiMeasurementAnalyzer
from engine.diagnostic_engine import AIDiagnosticEngine
from engine.measurement_recommender import MeasurementRecommendationEngine


# ============================================================
# CONFIG
# ============================================================

DEFAULT_RPM = 1500.0

FREQUENCY_CALIBRATION = {
    "slope_hz_per_pixel": 0.60604178,
    "intercept_hz": -242.22631,
}


# ============================================================
# COLORS
# ============================================================

BG = "#11161c"
PANEL = "#19212a"
PANEL_2 = "#202a34"
BORDER = "#303c48"

TEXT = "#e8edf2"
TEXT_DIM = "#91a0ae"

GREEN = "#39d98a"
GREEN_DARK = "#183d2c"

BLUE = "#4da3ff"
BLUE_DARK = "#18304a"

ORANGE = "#ffb454"
ORANGE_DARK = "#49361c"

RED = "#ff6262"
RED_DARK = "#482323"

PURPLE = "#a98cff"
WHITE = "#ffffff"


# ============================================================
# APPLICATION
# ============================================================

class MeasurementManager(tk.Tk):

    def __init__(self):

        super().__init__()

        self.title("AI Condition Monitoring")
        self.geometry("1500x920")
        self.minsize(1250, 780)
        self.configure(bg=BG)

        # ----------------------------------------------------
        # DATA
        # ----------------------------------------------------

        self.measurements = {}

        self.analysis_results = {}

        self.selected_measurement_id = None

        self.preview_image = None

        # ----------------------------------------------------
        # VARIABLES
        # ----------------------------------------------------

        self.rpm_var = tk.StringVar(
            value=str(DEFAULT_RPM)
        )

        self.machine_var = tk.StringVar(
            value="Test Machine"
        )

        self.component_var = tk.StringVar(
            value="Fan"
        )

        self.bearing_count_var = tk.IntVar(
            value=4
        )

        self.status_var = tk.StringVar(
            value="SYSTEM READY — Add vibration measurements to begin."
        )

        self.coverage_var = tk.StringVar(
            value="0 / 12 measurements"
        )

        self.coverage_percent_var = tk.StringVar(
            value="0.0%"
        )

        # Analysis state
        self.analysis_running = False
        self.analysis_total = 0
        self.analysis_completed = 0

        # ----------------------------------------------------
        # STYLE
        # ----------------------------------------------------

        self._configure_styles()

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self._build_ui()

        self._refresh_bearing_map()

        self._update_coverage()

        self._install_messagebox_debugger()
    # ========================================================
    # STYLE
    # ========================================================

    def _configure_styles(self):

        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "TCombobox",
            fieldbackground=PANEL_2,
            background=PANEL_2,
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
        )

        style.configure(
            "TEntry",
            fieldbackground=PANEL_2,
            foreground=TEXT,
            bordercolor=BORDER,
            insertcolor=TEXT,
        )

        style.configure(
            "Horizontal.TProgressbar",
            troughcolor="#0c1015",
            background=GREEN,
            bordercolor=BORDER,
            lightcolor=GREEN,
            darkcolor=GREEN,
        )

    # ========================================================
    # MAIN UI
    # ========================================================

    def _build_ui(self):

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = tk.Frame(
            self,
            bg="#0c1116",
            height=82,
        )

        header.pack(fill="x")
        header.pack_propagate(False)

        left_header = tk.Frame(
            header,
            bg="#0c1116",
        )

        left_header.pack(
            side="left",
            padx=28,
            pady=13,
        )

        tk.Label(
            left_header,
            text="AI CONDITION",
            bg="#0c1116",
            fg=WHITE,
            font=("Segoe UI", 21, "bold"),
        ).pack(anchor="w")

        tk.Label(
            left_header,
            text="Intelligent Vibration & Condition Monitoring",
            bg="#0c1116",
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        self.system_status_label = tk.Label(
            header,
            text="● SYSTEM READY",
            bg="#0c1116",
            fg=GREEN,
            font=("Segoe UI", 10, "bold"),
        )

        self.system_status_label.pack(
            side="right",
            padx=28,
        )

        # ----------------------------------------------------
        # MAIN SCROLL AREA
        # ----------------------------------------------------

        outer = tk.Frame(
            self,
            bg=BG,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        canvas = tk.Canvas(
            outer,
            bg=BG,
            highlightthickness=0,
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=canvas.yview,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        self.main_frame = tk.Frame(
            canvas,
            bg=BG,
        )

        window_id = canvas.create_window(
            (0, 0),
            window=self.main_frame,
            anchor="nw",
        )

        self.main_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfig(
                window_id,
                width=event.width,
            )
        )

        # ----------------------------------------------------
        # TOP CARDS
        # ----------------------------------------------------

        top = tk.Frame(
            self.main_frame,
            bg=BG,
        )

        top.pack(
            fill="x",
            padx=22,
            pady=(20, 10),
        )

        self._build_machine_card(top)
        self._build_coverage_card(top)

        # ----------------------------------------------------
        # BEARING MAP
        # ----------------------------------------------------

        self._build_section_title(
            self.main_frame,
            "BEARING MAP",
            "H / V / A measurements can be uploaded independently.",
        )

        self.bearing_map_container = tk.Frame(
            self.main_frame,
            bg=BG,
        )

        self.bearing_map_container.pack(
            fill="x",
            padx=22,
            pady=(5, 15),
        )

        # ----------------------------------------------------
        # LOWER AREA
        # ----------------------------------------------------

        lower = tk.Frame(
            self.main_frame,
            bg=BG,
        )

        lower.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=5,
        )

        self._build_preview_panel(lower)

        self._build_analysis_panel(lower)

        # ----------------------------------------------------
        # ANALYSIS PROGRESS
        # ----------------------------------------------------

        self._build_progress_panel(
            self.main_frame
        )

        # ----------------------------------------------------
        # ANALYZE BUTTON
        # ----------------------------------------------------

        analyze_frame = tk.Frame(
            self.main_frame,
            bg=BG,
        )

        analyze_frame.pack(
            fill="x",
            padx=22,
            pady=(15, 10),
        )

        self.analyze_button = tk.Button(
            analyze_frame,
            text="▶  ANALYZE MACHINE",
            command=self._start_analysis,
            bg=GREEN,
            fg="#07130d",
            activebackground="#63e9a7",
            activeforeground="#07130d",
            font=("Segoe UI", 13, "bold"),
            relief="flat",
            cursor="hand2",
            height=2,
        )

        self.analyze_button.pack(
            fill="x",
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        status_frame = tk.Frame(
            self,
            bg="#0c1116",
            height=38,
        )

        status_frame.pack(fill="x")
        status_frame.pack_propagate(False)

        tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg="#0c1116",
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(
            fill="both",
            padx=22,
        )

    # ========================================================
    # MACHINE CARD
    # ========================================================

    def _build_machine_card(self, parent):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8),
        )

        tk.Label(
            card,
            text="MACHINE CONFIGURATION",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(15, 8),
        )

        grid = tk.Frame(
            card,
            bg=PANEL,
        )

        grid.pack(
            fill="x",
            padx=18,
            pady=(0, 18),
        )

        self._input_row(
            grid,
            0,
            "RPM",
            self.rpm_var,
        )

        self._input_row(
            grid,
            1,
            "Machine",
            self.machine_var,
        )

        self._input_row(
            grid,
            2,
            "Component",
            self.component_var,
        )

        tk.Label(
            grid,
            text="Bearings",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=5,
        )

        tk.Spinbox(
            grid,
            from_=1,
            to=20,
            textvariable=self.bearing_count_var,
            bg=PANEL_2,
            fg=TEXT,
            insertbackground=TEXT,
            buttonbackground=PANEL_2,
            relief="flat",
            width=10,
            font=("Segoe UI", 9),
        ).grid(
            row=3,
            column=1,
            sticky="w",
            padx=10,
            pady=5,
        )

        tk.Button(
            grid,
            text="UPDATE MAP",
            command=self._refresh_bearing_map,
            bg=BLUE_DARK,
            fg=BLUE,
            activebackground=BLUE,
            activeforeground=BG,
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        ).grid(
            row=3,
            column=2,
            padx=10,
        )

    def _input_row(
        self,
        parent,
        row,
        label,
        variable,
    ):

        tk.Label(
            parent,
            text=label,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=5,
        )

        tk.Entry(
            parent,
            textvariable=variable,
            bg=PANEL_2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 9),
            width=24,
        ).grid(
            row=row,
            column=1,
            columnspan=2,
            sticky="w",
            padx=10,
            pady=5,
        )

    # ========================================================
    # COVERAGE CARD
    # ========================================================

    def _build_coverage_card(self, parent):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            side="right",
            fill="both",
            padx=(8, 0),
        )

        tk.Label(
            card,
            text="MEASUREMENT COVERAGE",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(15, 2),
        )

        tk.Label(
            card,
            textvariable=self.coverage_percent_var,
            bg=PANEL,
            fg=GREEN,
            font=("Segoe UI", 24, "bold"),
        ).pack(
            anchor="w",
            padx=18,
        )

        self.coverage_progress = ttk.Progressbar(
            card,
            style="Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )

        self.coverage_progress.pack(
            fill="x",
            padx=18,
            pady=7,
        )

        tk.Label(
            card,
            textvariable=self.coverage_var,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).pack(
            anchor="w",
            padx=18,
        )

        self.direction_label = tk.Label(
            card,
            text="H 0/0     V 0/0     A 0/0",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        )

        self.direction_label.pack(
            anchor="w",
            padx=18,
            pady=(8, 15),
        )

    # ========================================================
    # SECTION TITLE
    # ========================================================

    def _build_section_title(
        self,
        parent,
        title,
        subtitle,
    ):

        frame = tk.Frame(
            parent,
            bg=BG,
        )

        frame.pack(
            fill="x",
            padx=22,
            pady=(8, 2),
        )

        tk.Label(
            frame,
            text=title,
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")

        tk.Label(
            frame,
            text=subtitle,
            bg=BG,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

    # ========================================================
    # BEARING MAP
    # ========================================================

    def _refresh_bearing_map(self):

        try:
            count = int(
                self.bearing_count_var.get()
            )
        except Exception:
            count = 1

        count = max(
            1,
            min(count, 20),
        )

        for widget in self.bearing_map_container.winfo_children():
            widget.destroy()

        for index in range(count):

            bearing_id = f"B{index + 1}"

            card = self._create_bearing_card(
                self.bearing_map_container,
                bearing_id,
                index,
            )

            row = index // 4
            column = index % 4

            card.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=6,
                pady=6,
            )

        for column in range(4):

            self.bearing_map_container.grid_columnconfigure(
                column,
                weight=1,
            )

        self._update_coverage()

    def _create_bearing_card(
        self,
        parent,
        bearing_id,
        index,
    ):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        header = tk.Frame(
            card,
            bg=PANEL,
        )

        header.pack(
            fill="x",
            padx=12,
            pady=(10, 4),
        )

        tk.Label(
            header,
            text=bearing_id,
            bg=PANEL,
            fg=WHITE,
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")

        tk.Label(
            header,
            text=f"Bearing {index + 1}",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
        ).pack(side="right")

        tk.Frame(
            card,
            bg=BORDER,
            height=1,
        ).pack(
            fill="x",
            padx=12,
        )

        body = tk.Frame(
            card,
            bg=PANEL,
        )

        body.pack(
            fill="x",
            padx=12,
            pady=10,
        )

        directions = [
            ("H", "Horizontal"),
            ("V", "Vertical"),
            ("A", "Axial"),
        ]

        for short, direction in directions:

            measurement_id = self._measurement_id(
                bearing_id,
                short,
            )

            measurement = self.measurements.get(
                measurement_id
            )

            row = tk.Frame(
                body,
                bg=PANEL,
            )

            row.pack(
                fill="x",
                pady=3,
            )

            tk.Label(
                row,
                text=short,
                bg=PANEL,
                fg=TEXT,
                font=("Segoe UI", 10, "bold"),
                width=2,
            ).pack(side="left")

            status = "○ NOT MEASURED"
            bg = PANEL_2
            fg = TEXT_DIM

            if measurement:

                state = measurement.get(
                    "status",
                    "READY",
                )

                if state == "READY":
                    status = "● READY"
                    bg = BLUE_DARK
                    fg = BLUE

                elif state == "ANALYZING":
                    status = "● ANALYZING"
                    bg = ORANGE_DARK
                    fg = ORANGE

                elif state == "ANALYZED":
                    status = "✓ ANALYZED"
                    bg = GREEN_DARK
                    fg = GREEN

                elif state == "ERROR":
                    status = "✕ ERROR"
                    bg = RED_DARK
                    fg = RED

            button = tk.Button(
                row,
                text=status,
                command=lambda b=bearing_id, d=direction:
                    self._upload_for_slot(b, d),
                bg=bg,
                fg=fg,
                activebackground=bg,
                activeforeground=fg,
                relief="flat",
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
                anchor="w",
            )

            button.pack(
                side="left",
                fill="x",
                expand=True,
            )

        return card

    # ========================================================
    # SLOT
    # ========================================================

    def _measurement_id(
        self,
        bearing,
        short_direction,
    ):

        return f"{bearing}-{short_direction}"

    # ========================================================
    # UPLOAD
    # ========================================================

    def _upload_for_slot(
        self,
        bearing,
        direction,
    ):

        short = {
            "Horizontal": "H",
            "Vertical": "V",
            "Axial": "A",
        }[direction]

        measurement_id = self._measurement_id(
            bearing,
            short,
        )

        if measurement_id in self.measurements:

            answer = messagebox.askyesnocancel(
                "Measurement Exists",
                (
                    f"{bearing} / {direction} already exists.\n\n"
                    "YES = Replace\n"
                    "NO = Delete\n"
                    "CANCEL = Keep"
                ),
            )

            if answer is None:
                return

            if answer is False:

                del self.measurements[
                    measurement_id
                ]

                self.analysis_results.pop(
                    measurement_id,
                    None,
                )

                self.selected_measurement_id = None

                self._refresh_bearing_map()
                self._update_preview()

                self.status_var.set(
                    f"Measurement removed: {measurement_id}"
                )

                return

        path = filedialog.askopenfilename(
            title=(
                f"Select FFT Image — "
                f"{bearing} / {direction}"
            ),
            filetypes=[
                (
                    "FFT Images",
                    "*.png *.jpg *.jpeg",
                ),
                (
                    "PNG",
                    "*.png",
                ),
                (
                    "JPEG",
                    "*.jpg *.jpeg",
                ),
            ],
        )

        if not path:
            return

        if not os.path.isfile(path):
            messagebox.showerror(
                "Invalid File",
                "The selected image could not be found.",
            )
            return

        point = f"Bearing {bearing[1:]}"

        self.measurements[measurement_id] = {
            "id": measurement_id,
            "image": path,
            "bearing": bearing,
            "point": point,
            "direction": direction,
            "component": (
                self.component_var.get().strip()
                or "Unknown"
            ),
            "status": "READY",
        }

        self.analysis_results.pop(
            measurement_id,
            None,
        )

        self.selected_measurement_id = (
            measurement_id
        )

        self._refresh_bearing_map()
        self._update_preview()
        self._update_coverage()

        self.status_var.set(
            f"READY — {measurement_id} — "
            f"{os.path.basename(path)}"
        )

    # ========================================================
    # PREVIEW PANEL
    # ========================================================

    def _build_preview_panel(self, parent):

        panel = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        panel.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8),
        )

        tk.Label(
            panel,
            text="FFT PREVIEW",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(15, 3),
        )

        tk.Label(
            panel,
            text="Selected vibration measurement",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=18,
        )

        self.preview_label = tk.Label(
            panel,
            text="No measurement selected",
            bg="#0c1116",
            fg=TEXT_DIM,
            font=("Segoe UI", 10),
        )

        self.preview_label.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=15,
        )

    # ========================================================
    # ANALYSIS DETAIL PANEL
    # ========================================================

    def _build_analysis_panel(self, parent):

        panel = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
            width=480,
        )

        panel.pack(
            side="right",
            fill="both",
            padx=(8, 0),
        )

        panel.pack_propagate(False)

        tk.Label(
            panel,
            text="MEASUREMENT ANALYSIS",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(15, 3),
        )

        self.analysis_subtitle = tk.Label(
            panel,
            text="Select a measurement",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
        )

        self.analysis_subtitle.pack(
            anchor="w",
            padx=18,
        )

        self.analysis_content = tk.Frame(
            panel,
            bg=PANEL,
        )

        self.analysis_content.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=12,
        )

    # ========================================================
    # PROGRESS PANEL
    # ========================================================

    def _build_progress_panel(self, parent):

        panel = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        panel.pack(
            fill="x",
            padx=22,
            pady=(10, 5),
        )

        top = tk.Frame(
            panel,
            bg=PANEL,
        )

        top.pack(
            fill="x",
            padx=18,
            pady=(12, 4),
        )

        self.progress_title = tk.Label(
            top,
            text="ANALYSIS STATUS",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        )

        self.progress_title.pack(
            side="left"
        )

        self.progress_text = tk.Label(
            top,
            text="Waiting",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        )

        self.progress_text.pack(
            side="right"
        )

        self.analysis_progress = ttk.Progressbar(
            panel,
            style="Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )

        self.analysis_progress.pack(
            fill="x",
            padx=18,
            pady=(2, 12),
        )

    # ========================================================
    # UPDATE PREVIEW
    # ========================================================

    def _update_preview(self):

        measurement = self.measurements.get(
            self.selected_measurement_id
        )

        if not measurement:

            self.preview_label.configure(
                image="",
                text="No measurement selected",
            )

            self.preview_image = None

            self._clear_analysis_panel()

            return

        path = measurement["image"]

        try:

            from PIL import Image, ImageTk

            image = Image.open(path)

            image.thumbnail(
                (700, 400)
            )

            self.preview_image = ImageTk.PhotoImage(
                image
            )

            self.preview_label.configure(
                image=self.preview_image,
                text="",
            )

        except Exception:

            self.preview_label.configure(
                image="",
                text=(
                    "FFT image selected\n\n"
                    f"{os.path.basename(path)}\n\n"
                    "Install Pillow for image preview."
                ),
            )

        self._show_measurement_details(
            measurement
        )

    # ========================================================
    # MEASUREMENT DETAILS
    # ========================================================

    def _show_measurement_details(
        self,
        measurement,
    ):

        self._clear_analysis_panel()

        self.analysis_subtitle.configure(
            text=(
                f"{measurement['id']}  •  "
                f"{measurement['direction']}"
            )
        )

        self._add_detail(
            "Status",
            measurement.get(
                "status",
                "READY",
            ),
        )

        self._add_detail(
            "Bearing",
            measurement["bearing"],
        )

        self._add_detail(
            "Point",
            measurement["point"],
        )

        self._add_detail(
            "Direction",
            measurement["direction"],
        )

        self._add_detail(
            "Component",
            measurement["component"],
        )

        self._add_detail(
            "File",
            os.path.basename(
                measurement["image"]
            ),
        )

        result = self.analysis_results.get(
            measurement["id"]
        )

        if not result:

            tk.Label(
                self.analysis_content,
                text="Analysis not available yet.",
                bg=PANEL,
                fg=TEXT_DIM,
                font=("Segoe UI", 9, "italic"),
            ).pack(
                anchor="w",
                pady=15,
            )

            return

        separator = tk.Frame(
            self.analysis_content,
            bg=BORDER,
            height=1,
        )

        separator.pack(
            fill="x",
            pady=10,
        )

        tk.Label(
            self.analysis_content,
            text="EXTRACTED SPECTRUM",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 7),
        )

        self._add_detail(
            "RPM",
            self._result_value(
                result,
                "rpm",
                "—",
            ),
        )

        self._add_detail(
            "Peaks",
            self._result_value(
                result,
                "peak_count",
                "—",
            ),
        )

        self._add_detail(
            "Matched Orders",
            self._result_value(
                result,
                "matched_orders",
                "—",
            ),
        )

        self._add_detail(
            "Dominant Order",
            self._result_value(
                result,
                "dominant_order",
                "—",
            ),
        )

        self._add_detail(
            "Dominant Amplitude",
            self._result_value(
                result,
                "dominant_amplitude",
                "—",
            ),
        )

        orders = result.get(
            "orders",
            [],
        )

        if orders:

            separator = tk.Frame(
                self.analysis_content,
                bg=BORDER,
                height=1,
            )

            separator.pack(
                fill="x",
                pady=10,
            )

            tk.Label(
                self.analysis_content,
                text="MATCHED ORDERS",
                bg=PANEL,
                fg=TEXT,
                font=("Segoe UI", 9, "bold"),
            ).pack(
                anchor="w",
                pady=(0, 5),
            )

            for order in orders[:12]:

                self._add_order_row(
                    order
                )

    def _clear_analysis_panel(self):

        for widget in self.analysis_content.winfo_children():
            widget.destroy()

        self.analysis_subtitle.configure(
            text="Select a measurement"
        )

    def _add_detail(
        self,
        label,
        value,
    ):

        row = tk.Frame(
            self.analysis_content,
            bg=PANEL,
        )

        row.pack(
            fill="x",
            pady=3,
        )

        tk.Label(
            row,
            text=label,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
            width=20,
            anchor="w",
        ).pack(side="left")

        value_text = str(value)

        if value_text == "ANALYZED":
            value_fg = GREEN
        elif value_text == "READY":
            value_fg = BLUE
        elif value_text == "ERROR":
            value_fg = RED
        else:
            value_fg = TEXT

        tk.Label(
            row,
            text=value_text,
            bg=PANEL,
            fg=value_fg,
            font=("Segoe UI", 8, "bold"),
            anchor="w",
            justify="left",
            wraplength=250,
        ).pack(
            side="left",
            fill="x",
            expand=True,
        )

    def _add_order_row(
        self,
        order,
    ):

        if isinstance(order, dict):

            order_name = (
                order.get("order")
                or order.get("order_label")
                or order.get("name")
                or "—"
            )

            frequency = (
                order.get("frequency")
                or order.get("freq")
                or "—"
            )

            amplitude = (
                order.get("amplitude")
                or order.get("amp")
                or "—"
            )

            confidence = (
                order.get("confidence")
                or "—"
            )

        else:

            order_name = str(order)
            frequency = "—"
            amplitude = "—"
            confidence = "—"

        row = tk.Frame(
            self.analysis_content,
            bg=PANEL_2,
        )

        row.pack(
            fill="x",
            pady=2,
        )

        tk.Label(
            row,
            text=str(order_name),
            bg=PANEL_2,
            fg=BLUE,
            font=("Segoe UI", 8, "bold"),
            width=7,
        ).pack(side="left")

        tk.Label(
            row,
            text=self._format_number(
                frequency
            ),
            bg=PANEL_2,
            fg=TEXT,
            font=("Segoe UI", 8),
            width=12,
        ).pack(side="left")

        tk.Label(
            row,
            text=self._format_number(
                amplitude
            ),
            bg=PANEL_2,
            fg=TEXT,
            font=("Segoe UI", 8),
            width=12,
        ).pack(side="left")

        tk.Label(
            row,
            text=self._format_number(
                confidence
            ),
            bg=PANEL_2,
            fg=GREEN,
            font=("Segoe UI", 8),
        ).pack(side="left")

    # ========================================================
    # ANALYSIS
    # ========================================================

    def _start_analysis(self):

        if self.analysis_running:
            return

        if not self.measurements:

            messagebox.showwarning(
                "No Measurements",
                "Please upload at least one FFT measurement.",
            )

            return

        try:

            rpm = float(
                self.rpm_var.get().strip()
            )

            if rpm <= 0:
                raise ValueError

        except Exception:

            messagebox.showerror(
                "Invalid RPM",
                "Please enter a valid positive RPM.",
            )

            return

        self.analysis_running = True

        self.analysis_total = len(
            self.measurements
        )

        self.analysis_completed = 0

        self.analysis_progress["value"] = 0

        self.progress_text.configure(
            text=(
                f"0 / {self.analysis_total}"
            )
        )

        self.progress_title.configure(
            text="AI ANALYSIS RUNNING"
        )

        self.system_status_label.configure(
            text="● ANALYSIS RUNNING",
            fg=ORANGE,
        )

        self.analyze_button.configure(
            state="disabled",
            text="⏳  ANALYZING MACHINE...",
            bg=ORANGE,
            fg="#171006",
        )

        self.status_var.set(
            "ANALYSIS RUNNING — Please wait..."
        )

        # Reset old analyzed states
        for measurement in self.measurements.values():

            measurement["status"] = "READY"

        self._refresh_bearing_map()

        thread = threading.Thread(
            target=self._analysis_worker,
            args=(rpm,),
            daemon=True,
        )

        thread.start()

    # ========================================================
    # ANALYSIS WORKER
    # ========================================================

    def _analysis_worker(
        self,
        rpm,
    ):

        try:

            bearing_count = int(
                self.bearing_count_var.get()
            )

            bearing_count = max(
                1,
                min(
                    bearing_count,
                    20,
                ),
            )

            bearing_ids = [
                f"B{i}"
                for i in range(
                    1,
                    bearing_count + 1,
                )
            ]

            context = MachineContext(
                equipment_type="Electric Motor",
                equipment_category="Rotating Machinery",
                brand="Test",
                model="Condition Monitoring",
                rpm=rpm,
                connection_type="Coupling",
                transmission_type="Direct Coupled",
                bearing_count=bearing_count,
                bearings=[
                    "Rolling Element Bearing"
                    for _ in bearing_ids
                ],
                measurement_point="Motor DE",
                direction="Horizontal",
                sensor_type="Accelerometer",
                analysis_mode="FFT",
            )

            analyzer = MultiMeasurementAnalyzer(
                rpm=rpm,
                machine_context=context,
                max_order=10,
                rpm_tolerance=10,
                percent_tolerance=3.0,
                frequency_calibration=FREQUENCY_CALIBRATION,
            )

            # ------------------------------------------------
            # INDIVIDUAL ANALYSIS
            # ------------------------------------------------

            measurement_items = list(
                self.measurements.values()
            )

            for index, measurement in enumerate(
                measurement_items,
                start=1,
            ):

                measurement_id = measurement["id"]

                self.after(
                    0,
                    self._set_measurement_status,
                    measurement_id,
                    "ANALYZING",
                    index,
                )

                try:

                    analyzer.add_measurement(
                        image_path=measurement["image"],
                        measurement_id=measurement_id,
                        bearing_id=measurement["bearing"],
                        point=measurement["point"],
                        direction=measurement["direction"],
                        component=measurement["component"],
                        machine_name=(
                            self.machine_var.get().strip()
                            or "Unknown Machine"
                        ),
                        sensor_type="Accelerometer",
                    )

                    # Get the MeasurementEvidence just created
                    evidence = None

                    if analyzer.measurements:

                        for item in reversed(
                            analyzer.measurements
                        ):

                            if getattr(
                                item,
                                "measurement_id",
                                None,
                            ) == measurement_id:

                                evidence = item
                                break

                    result = self._extract_analysis_result(
                        evidence
                    )

                    self.analysis_results[
                        measurement_id
                    ] = result

                    self.after(
                        0,
                        self._set_measurement_status,
                        measurement_id,
                        "ANALYZED",
                        index,
                    )

                except Exception as exc:

                    measurement["analysis_error"] = str(
                        exc
                    )

                    self.after(
                        0,
                        self._set_measurement_status,
                        measurement_id,
                        "ERROR",
                        index,
                    )

            # ------------------------------------------------
            # EXPECTED SLOTS
            # ------------------------------------------------

            expected_slots = []

            for bearing_id in bearing_ids:

                for direction in [
                    "Horizontal",
                    "Vertical",
                    "Axial",
                ]:

                    expected_slots.append(
                        {
                            "bearing": bearing_id,
                            "direction": direction,
                        }
                    )

            # ------------------------------------------------
            # FUSION
            # ------------------------------------------------

            fusion_report = analyzer.fuse(
                expected_measurements=len(
                    expected_slots
                ),
                expected_slots=expected_slots,
            )

            diagnostic_engine = (
                AIDiagnosticEngine()
            )

            diagnostic_report = (
                diagnostic_engine.diagnose(
                    fusion_report
                )
            )

            recommendation_engine = (
                MeasurementRecommendationEngine()
            )

            recommendation_report = (
                recommendation_engine.recommend(
                    fusion_report
                )
            )

            self.after(
                0,
                self._analysis_complete,
                fusion_report,
                diagnostic_report,
                recommendation_report,
            )

        except Exception as exc:

            import traceback

            print()
            print()
            print("=" * 120)
            print("!!! ORIGINAL ERROR INSIDE _analysis_worker !!!")
            print("=" * 120)

            print(
                "TYPE:",
                type(exc).__name__,
            )

            print(
                "ERROR:",
                repr(exc),
            )

            print()

            traceback.print_exc()

            print()

            print(
                "TRACEBACK FRAMES:"
            )

            for frame in traceback.extract_tb(
                    exc.__traceback__
            ):
                print(
                    "-" * 120
                )

                print(
                    "FILE     :",
                    frame.filename,
                )

                print(
                    "FUNCTION :",
                    frame.name,
                )

                print(
                    "LINE     :",
                    frame.lineno,
                )

                print(
                    "CODE     :",
                    frame.line,
                )

            print(
                "=" * 120
            )
            print()

            self.after(
                0,
                self._analysis_failed,
                exc,
            )
    # ========================================================
    # STATUS UPDATE
    # ========================================================
    def _terminal_log(
            self,
            title,
            data=None,
            separator=True,
    ):

        print()

        if separator:
            print(
                "=" * 100
            )

        print(
            f"[AI CONDITION] {title}"
        )

        if separator:
            print(
                "-" * 100
            )

        if data is not None:

            if isinstance(
                    data,
                    dict,
            ):

                for key, value in data.items():
                    print(
                        f"{key}: {value}"
                    )

            elif isinstance(
                    data,
                    (
                            list,
                            tuple,
                            set,
                    ),
            ):

                for index, item in enumerate(
                        data,
                        start=1,
                ):
                    print(
                        f"{index}. {item}"
                    )

            else:

                print(
                    data
                )

        if separator:
            print(
                "=" * 100
            )

        try:
            import sys

            sys.stdout.flush()

        except Exception:
            pass

    def _terminal_print_ui_state(
            self,
            title="CURRENT UI STATE",
    ):
        """
        چاپ کامل وضعیت فعلی UI و Measurements در Terminal
        برای Debug و بررسی وضعیت برنامه.
        """

        print()
        print("=" * 90)
        print(f" {title}")
        print("=" * 90)

        # ---------------------------------------------------------
        # MACHINE
        # ---------------------------------------------------------
        try:
            machine_var = getattr(
                self,
                "machine_var",
                None,
            )

            if hasattr(machine_var, "get"):
                machine_value = machine_var.get()
            else:
                machine_value = "—"

            print(
                f"Machine            : {machine_value}"
            )

        except Exception as e:
            print(
                f"Machine            : — "
                f"(ERROR: {e})"
            )

        # ---------------------------------------------------------
        # RPM
        # ---------------------------------------------------------
        try:
            rpm_var = getattr(
                self,
                "rpm_var",
                None,
            )

            if hasattr(rpm_var, "get"):
                rpm_value = rpm_var.get()
            else:
                rpm_value = "—"

            print(
                f"RPM                : {rpm_value}"
            )

        except Exception as e:
            print(
                f"RPM                : — "
                f"(ERROR: {e})"
            )

        # ---------------------------------------------------------
        # COMPONENT
        # ---------------------------------------------------------
        try:
            component_var = getattr(
                self,
                "component_var",
                None,
            )

            if hasattr(component_var, "get"):
                component_value = component_var.get()
            else:
                component_value = "—"

            print(
                f"Component          : {component_value}"
            )

        except Exception as e:
            print(
                f"Component          : — "
                f"(ERROR: {e})"
            )

        # ---------------------------------------------------------
        # BEARING COUNT
        # ---------------------------------------------------------
        try:
            bearing_count_var = getattr(
                self,
                "bearing_count_var",
                None,
            )

            if hasattr(bearing_count_var, "get"):
                bearing_count_value = (
                    bearing_count_var.get()
                )
            else:
                bearing_count_value = "—"

            print(
                f"Bearing Count      : "
                f"{bearing_count_value}"
            )

        except Exception as e:
            print(
                f"Bearing Count      : — "
                f"(ERROR: {e})"
            )

        # ---------------------------------------------------------
        # ANALYSIS STATUS
        # ---------------------------------------------------------
        try:
            analysis_total = getattr(
                self,
                "analysis_total",
                0,
            )

            analysis_completed = getattr(
                self,
                "analysis_completed",
                0,
            )

            print(
                f"Analysis Completed : "
                f"{analysis_completed} / "
                f"{analysis_total}"
            )

        except Exception as e:
            print(
                f"Analysis Completed : — "
                f"(ERROR: {e})"
            )

        # ---------------------------------------------------------
        # SELECTED MEASUREMENT
        # ---------------------------------------------------------
        try:
            selected_id = getattr(
                self,
                "selected_measurement_id",
                None,
            )

            print(
                f"Selected Measurement: "
                f"{selected_id if selected_id else '—'}"
            )

        except Exception as e:
            print(
                f"Selected Measurement: — "
                f"(ERROR: {e})"
            )

        # ---------------------------------------------------------
        # MEASUREMENTS
        # ---------------------------------------------------------
        try:
            measurements = getattr(
                self,
                "measurements",
                {},
            )

            print()
            print("-" * 90)
            print(
                f"MEASUREMENTS "
                f"({len(measurements)})"
            )
            print("-" * 90)

            if not measurements:
                print(
                    "No measurements found."
                )

            else:

                for measurement_id, data in (
                        measurements.items()
                ):

                    print()
                    print(
                        f"[{measurement_id}]"
                    )

                    if not isinstance(
                            data,
                            dict,
                    ):
                        print(
                            f"  Data              : "
                            f"{data}"
                        )
                        continue

                    # ---------------------------------------------
                    # STATUS
                    # ---------------------------------------------
                    print(
                        f"  Status            : "
                        f"{data.get('status', '—')}"
                    )

                    # ---------------------------------------------
                    # IMAGE
                    # ---------------------------------------------
                    print(
                        f"  Image             : "
                        f"{data.get('image_path', '—')}"
                    )

                    # ---------------------------------------------
                    # BEARING
                    # ---------------------------------------------
                    print(
                        f"  Bearing           : "
                        f"{data.get('bearing_id', '—')}"
                    )

                    # ---------------------------------------------
                    # POINT
                    # ---------------------------------------------
                    print(
                        f"  Point             : "
                        f"{data.get('point', '—')}"
                    )

                    # ---------------------------------------------
                    # DIRECTION
                    # ---------------------------------------------
                    print(
                        f"  Direction         : "
                        f"{data.get('direction', '—')}"
                    )

                    # ---------------------------------------------
                    # COMPONENT
                    # ---------------------------------------------
                    print(
                        f"  Component         : "
                        f"{data.get('component', '—')}"
                    )

                    # ---------------------------------------------
                    # ERROR
                    # ---------------------------------------------
                    if data.get("error"):
                        print(
                            f"  Error             : "
                            f"{data.get('error')}"
                        )

                    # ---------------------------------------------
                    # ANALYSIS RESULT
                    # ---------------------------------------------
                    result = data.get(
                        "analysis_result"
                    )

                    if result is not None:
                        print(
                            f"  Analysis Result   : "
                            f"{result}"
                        )

        except Exception as e:

            print()
            print(
                "ERROR READING MEASUREMENTS:"
            )

            print(
                f"  {e}"
            )

        # ---------------------------------------------------------
        # STATUS VARIABLE
        # ---------------------------------------------------------
        try:
            status_var = getattr(
                self,
                "status_var",
                None,
            )

            if hasattr(status_var, "get"):
                print()
                print(
                    f"UI Status          : "
                    f"{status_var.get()}"
                )

        except Exception as e:

            print(
                f"UI Status          : — "
                f"(ERROR: {e})"
            )

        # ---------------------------------------------------------
        # PROGRESS
        # ---------------------------------------------------------
        try:
            progress_var = getattr(
                self,
                "analysis_progress",
                None,
            )

            if progress_var is not None:

                try:
                    progress_value = (
                        progress_var["value"]
                    )
                except Exception:
                    progress_value = "—"

                print(
                    f"Progress           : "
                    f"{progress_value}"
                )

        except Exception as e:

            print(
                f"Progress           : — "
                f"(ERROR: {e})"
            )

        # ---------------------------------------------------------
        # FINAL
        # ---------------------------------------------------------
        print()
        print("=" * 90)
        print(
            "END UI STATE"
        )
        print("=" * 90)
        print()
    def _set_measurement_status(
            self,
            measurement_id,
            status,
            index,
    ):

        if measurement_id in self.measurements:
            self.measurements[
                measurement_id
            ]["status"] = status

        self.analysis_completed = index

        percentage = (
                             index /
                             max(
                                 self.analysis_total,
                                 1,
                             )
                     ) * 100

        self.analysis_progress[
            "value"
        ] = percentage

        self.progress_text.configure(
            text=(
                f"{index} / "
                f"{self.analysis_total}"
            )
        )

        self.status_var.set(
            f"{status} — {measurement_id}"
        )

        # =====================================================================
        # TERMINAL MIRROR
        # =====================================================================

        measurement = (
            self.measurements.get(
                measurement_id,
                {}
            )
        )

        print()
        print(
            "=" * 100
        )

        print(
            "[AI CONDITION] MEASUREMENT STATUS UPDATE"
        )

        print(
            "-" * 100
        )

        print(
            f"Measurement ID : {measurement_id}"
        )

        print(
            f"Status         : {status}"
        )

        print(
            f"Progress       : "
            f"{index} / {self.analysis_total}"
        )

        print(
            f"Percentage     : {percentage:.1f}%"
        )

        if isinstance(
                measurement,
                dict,
        ):

            print()

            print(
                "Measurement Data:"
            )

            for key, value in (
                    measurement.items()
            ):
                print(
                    f"  {key}: {value}"
                )

        print(
            "=" * 100
        )

        try:

            import sys

            sys.stdout.flush()

        except Exception:
            pass

        self._refresh_bearing_map()

        if (
                self.selected_measurement_id
                == measurement_id
        ):
            self._update_preview()
    # ========================================================
    # ANALYSIS RESULT EXTRACTION
    # ========================================================

    def _extract_analysis_result(
        self,
        evidence,
    ):

        result = {
            "rpm": "—",
            "peak_count": "—",
            "matched_orders": "—",
            "dominant_order": "—",
            "dominant_amplitude": "—",
            "orders": [],
        }

        if evidence is None:
            return result

        # ----------------------------------------------------
        # VibrationFeatures
        # ----------------------------------------------------

        features = getattr(
            evidence,
            "features",
            None,
        )

        if features is not None:

            result["rpm"] = getattr(
                features,
                "rpm",
                "—",
            )

            dominant_order = getattr(
                features,
                "dominant_order",
                "—",
            )

            result["dominant_order"] = (
                self._format_order(
                    dominant_order
                )
            )

            result["dominant_amplitude"] = (
                getattr(
                    features,
                    "dominant_amplitude",
                    "—",
                )
            )

            present_orders = getattr(
                features,
                "present_orders",
                [],
            )

            result["matched_orders"] = len(
                present_orders
            )

        # ----------------------------------------------------
        # Raw Evidence / Extra
        # ----------------------------------------------------

        raw_features = getattr(
            features,
            "extra",
            None,
        )

        if isinstance(
            raw_features,
            dict,
        ):

            fundamental = raw_features.get(
                "fundamental",
                {},
            )

            if isinstance(
                fundamental,
                dict,
            ):

                if result["dominant_order"] == "—":

                    result["dominant_order"] = (
                        self._format_order(
                            fundamental.get(
                                "dominant_order"
                            )
                        )
                    )

                if result[
                    "dominant_amplitude"
                ] == "—":

                    result[
                        "dominant_amplitude"
                    ] = fundamental.get(
                        "dominant_amplitude",
                        "—",
                    )

        # ----------------------------------------------------
        # Matcher / Evidence
        # ----------------------------------------------------

        order_results = getattr(
            evidence,
            "order_results",
            None,
        )

        if order_results is None:

            order_results = getattr(
                evidence,
                "orders",
                None,
            )

        if order_results:

            result["orders"] = (
                self._normalize_orders(
                    order_results
                )
            )

            result["peak_count"] = len(
                order_results
            )

        else:

            order_map = getattr(
                evidence,
                "order_map",
                None,
            )

            if isinstance(
                order_map,
                dict,
            ):

                result["orders"] = (
                    self._normalize_orders(
                        order_map.values()
                    )
                )

                result["peak_count"] = len(
                    order_map
                )

        if (
            result["matched_orders"] == "—"
            and result["orders"]
        ):

            result["matched_orders"] = len(
                result["orders"]
            )

        return result

    # ========================================================
    # NORMALIZE ORDERS
    # ========================================================
    def _install_messagebox_debugger(
            self,
    ):

        import tkinter.messagebox as messagebox
        import traceback

        original_showerror = messagebox.showerror

        def debug_showerror(
                title,
                message,
                *args,
                **kwargs,
        ):
            print()
            print()
            print("=" * 120)
            print("!!! MESSAGEBOX.SHOWERROR CALLED !!!")
            print("=" * 120)

            print(
                "TITLE:",
                repr(title),
            )

            print()

            print(
                "MESSAGE TYPE:",
                type(message).__name__,
            )

            print(
                "MESSAGE:",
                repr(message),
            )

            print()

            print(
                "CURRENT STACK:"
            )

            traceback.print_stack()

            print(
                "=" * 120
            )
            print()

            return original_showerror(
                title,
                message,
                *args,
                **kwargs,
            )

        messagebox.showerror = (
            debug_showerror
        )

        print(
            "MESSAGEBOX DEBUGGER INSTALLED"
        )
    def _normalize_orders(
        self,
        orders,
    ):

        normalized = []

        if isinstance(
            orders,
            dict,
        ):

            iterable = orders.values()

        else:

            iterable = orders

        for item in iterable:

            if isinstance(
                item,
                dict,
            ):

                normalized.append(
                    {
                        "order": (
                            item.get("order")
                            or item.get(
                                "order_label"
                            )
                            or item.get("name")
                        ),
                        "frequency": (
                            item.get("frequency")
                            or item.get("freq")
                        ),
                        "amplitude": (
                            item.get("amplitude")
                            or item.get("amp")
                        ),
                        "confidence": item.get(
                            "confidence"
                        ),
                    }
                )

            else:

                normalized.append(
                    {
                        "order": str(item),
                        "frequency": None,
                        "amplitude": None,
                        "confidence": None,
                    }
                )

        return normalized

    # ========================================================
    # ANALYSIS COMPLETE
    # ========================================================

    def _analysis_complete(
        self,
        fusion_report,
        diagnostic_report,
        recommendation_report,
    ):

        self.analysis_running = False

        self.analysis_progress[
            "value"
        ] = 100

        self.progress_text.configure(
            text=(
                f"{self.analysis_total} / "
                f"{self.analysis_total} — COMPLETE"
            )
        )

        self.progress_title.configure(
            text="ANALYSIS COMPLETE"
        )

        self.system_status_label.configure(
            text="● ANALYSIS COMPLETE",
            fg=GREEN,
        )

        self.analyze_button.configure(
            state="normal",
            text="✓  ANALYSIS COMPLETE — VIEW REPORT",
            bg=GREEN,
            fg="#07130d",
        )

        self.status_var.set(
            "ANALYSIS COMPLETE — Diagnostic evidence generated."
        )

        self._refresh_bearing_map()

        self._update_preview()

        self._show_results(
            fusion_report,
            diagnostic_report,
            recommendation_report,
        )

        # Restore button after opening report
        self.after(
            1000,
            self._restore_analyze_button,
        )

    def _restore_analyze_button(self):

        if not self.analysis_running:

            self.analyze_button.configure(
                state="normal",
                text="▶  ANALYZE MACHINE",
                bg=GREEN,
                fg="#07130d",
            )

    # ========================================================
    # ANALYSIS FAILED
    # ========================================================

    def _analysis_failed(
            self,
            exc,
    ):

        import traceback

        self.analysis_running = False

        # ----------------------------------------------------
        # PRINT EXACT ORIGINAL EXCEPTION
        # ----------------------------------------------------

        print()
        print()
        print("=" * 120)
        print("!!! ANALYSIS FAILED — ORIGINAL EXCEPTION !!!")
        print("=" * 120)

        print(
            "Exception Type :",
            type(exc).__name__,
        )

        print(
            "Exception      :",
            repr(exc),
        )

        print()

        print(
            "EXCEPTION ATTRIBUTES:"
        )

        try:

            print(
                vars(exc)
            )

        except Exception:

            print(
                "No __dict__ available"
            )

        print()

        print(
            "TRACEBACK STORED IN EXCEPTION:"
        )

        if exc.__traceback__:

            traceback.print_exception(
                type(exc),
                exc,
                exc.__traceback__,
            )

            print()

            print(
                "EXACT FRAMES:"
            )

            frames = traceback.extract_tb(
                exc.__traceback__
            )

            for frame in frames:
                print(
                    "-" * 120
                )

                print(
                    "FILE     :",
                    frame.filename,
                )

                print(
                    "FUNCTION :",
                    frame.name,
                )

                print(
                    "LINE     :",
                    frame.lineno,
                )

                print(
                    "CODE     :",
                    frame.line,
                )

        else:

            print(
                "!!! NO TRACEBACK STORED !!!"
            )

            print(
                "The exception was probably converted "
                "to a string before reaching this function."
            )

        print(
            "=" * 120
        )
        print()

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self.progress_title.configure(
            text="ANALYSIS FAILED"
        )

        self.progress_text.configure(
            text="ERROR"
        )

        self.system_status_label.configure(
            text="● ANALYSIS ERROR",
            fg=RED,
        )

        self.analyze_button.configure(
            state="normal",
            text="▶  ANALYZE MACHINE",
            bg=GREEN,
            fg="#07130d",
        )

        self.status_var.set(
            "ANALYSIS FAILED — See error message."
        )

        # ----------------------------------------------------
        # ERROR MESSAGE
        # ----------------------------------------------------

        error_text = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        if exc.__traceback__:

            error_text += (
                "\n\n"
                "EXACT LOCATION:\n"
            )

            frames = traceback.extract_tb(
                exc.__traceback__
            )

            if frames:
                last_frame = frames[-1]

                error_text += (
                    f"\nFile: "
                    f"{last_frame.filename}"
                    f"\nFunction: "
                    f"{last_frame.name}"
                    f"\nLine: "
                    f"{last_frame.lineno}"
                    f"\nCode: "
                    f"{last_frame.line}"
                )

        messagebox.showerror(
            "Analysis Error",
            error_text,
        )
    # ========================================================
    # RESULTS WINDOW
    # ========================================================

    def _show_results(
        self,
        fusion_report,
        diagnostic_report,
        recommendation_report,
    ):

        window = tk.Toplevel(
            self
        )

        window.title(
            "AI Condition — Diagnostic Results"
        )

        window.geometry(
            "1250x850"
        )

        window.minsize(
            1000,
            700,
        )

        window.configure(
            bg=BG
        )

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = tk.Frame(
            window,
            bg="#0c1116",
            height=85,
        )

        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="AI DIAGNOSTIC REPORT",
            bg="#0c1116",
            fg=WHITE,
            font=("Segoe UI", 19, "bold"),
        ).pack(
            anchor="w",
            padx=25,
            pady=(14, 0),
        )

        tk.Label(
            header,
            text=(
                "Evidence-based condition assessment — "
                "not a confirmed fault declaration"
            ),
            bg="#0c1116",
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).pack(
            anchor="w",
            padx=25,
        )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        summary = tk.Frame(
            window,
            bg=BG,
        )

        summary.pack(
            fill="x",
            padx=22,
            pady=18,
        )

        received = getattr(
            diagnostic_report,
            "measurements_received",
            len(self.measurements),
        )

        expected = getattr(
            diagnostic_report,
            "expected_measurements",
            len(self.measurements),
        )

        coverage = getattr(
            diagnostic_report,
            "coverage_percent",
            0,
        )

        directions = getattr(
            diagnostic_report,
            "available_directions",
            [],
        )

        diagnostics = getattr(
            diagnostic_report,
            "diagnostics",
            [],
        )

        self._result_card(
            summary,
            "MEASUREMENTS",
            str(received),
            "received",
            GREEN,
        )

        self._result_card(
            summary,
            "COVERAGE",
            f"{coverage:.1f}%",
            f"{received}/{expected}",
            BLUE,
        )

        self._result_card(
            summary,
            "DIRECTIONS",
            str(len(directions)),
            ", ".join(
                directions
            ) if directions else "None",
            PURPLE,
        )

        self._result_card(
            summary,
            "EVIDENCE CANDIDATES",
            str(len(diagnostics)),
            "mechanisms",
            ORANGE,
        )

        # ----------------------------------------------------
        # SCROLL CONTENT
        # ----------------------------------------------------

        outer = tk.Frame(
            window,
            bg=BG,
        )

        outer.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=(0, 15),
        )

        canvas = tk.Canvas(
            outer,
            bg=BG,
            highlightthickness=0,
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=canvas.yview,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        body = tk.Frame(
            canvas,
            bg=BG,
        )

        canvas_window = canvas.create_window(
            (0, 0),
            window=body,
            anchor="nw",
        )

        body.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            ),
        )

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(
                canvas_window,
                width=e.width,
            ),
        )

        # ----------------------------------------------------
        # DIAGNOSTICS
        # ----------------------------------------------------

        tk.Label(
            body,
            text="DIAGNOSTIC EVIDENCE",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 13, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        for diagnostic in diagnostics:

            self._build_diagnostic_card(
                body,
                diagnostic,
            )

        # ----------------------------------------------------
        # RECOMMENDATIONS
        # ----------------------------------------------------

        tk.Label(
            body,
            text="RECOMMENDED NEXT MEASUREMENTS",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 13, "bold"),
        ).pack(
            anchor="w",
            pady=(20, 8),
        )

        self._build_recommendation_card(
            body,
            recommendation_report,
        )

        # ----------------------------------------------------
        # NOTES
        # ----------------------------------------------------

        notes = getattr(
            diagnostic_report,
            "notes",
            [],
        )

        if notes:

            tk.Label(
                body,
                text="ANALYSIS NOTES",
                bg=BG,
                fg=TEXT,
                font=("Segoe UI", 13, "bold"),
            ).pack(
                anchor="w",
                pady=(20, 8),
            )

            card = tk.Frame(
                body,
                bg=PANEL,
                highlightbackground=BORDER,
                highlightthickness=1,
            )

            card.pack(
                fill="x",
            )

            for note in notes:

                tk.Label(
                    card,
                    text=f"• {note}",
                    bg=PANEL,
                    fg=TEXT_DIM,
                    font=("Segoe UI", 9),
                    anchor="w",
                    justify="left",
                    wraplength=1050,
                ).pack(
                    fill="x",
                    padx=18,
                    pady=6,
                )

    # ========================================================
    # RESULT CARD
    # ========================================================

    def _result_card(
        self,
        parent,
        title,
        value,
        subtitle,
        accent,
    ):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5,
        )

        tk.Label(
            card,
            text=title,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8, "bold"),
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 0),
        )

        tk.Label(
            card,
            text=value,
            bg=PANEL,
            fg=accent,
            font=("Segoe UI", 20, "bold"),
        ).pack(
            anchor="w",
            padx=15,
            pady=(2, 0),
        )

        tk.Label(
            card,
            text=subtitle,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=15,
            pady=(0, 12),
        )

    # ========================================================
    # DIAGNOSTIC CARD
    # ========================================================

    def _build_diagnostic_card(
        self,
        parent,
        diagnostic,
    ):

        mechanism = getattr(
            diagnostic,
            "mechanism",
            "Unknown",
        )

        status = getattr(
            diagnostic,
            "status",
            "UNKNOWN",
        )

        score = getattr(
            diagnostic,
            "evidence_score",
            0,
        )

        support = getattr(
            diagnostic,
            "supporting_measurements",
            [],
        )

        directions = getattr(
            diagnostic,
            "directions",
            [],
        )

        locations = getattr(
            diagnostic,
            "locations",
            [],
        )

        orders = getattr(
            diagnostic,
            "supporting_orders",
            [],
        )

        missing = getattr(
            diagnostic,
            "missing_pattern_orders",
            [],
        )

        database_docs = getattr(
            diagnostic,
            "database_documents",
            [],
        )

        database_contradictions = getattr(
            diagnostic,
            "database_pattern_contradictions",
            [],
        )

        fft_contradictions = getattr(
            diagnostic,
            "actual_fft_contradictions",
            [],
        )

        reasons = getattr(
            diagnostic,
            "reasons",
            [],
        )

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            fill="x",
            pady=6,
        )

        top = tk.Frame(
            card,
            bg=PANEL,
        )

        top.pack(
            fill="x",
            padx=18,
            pady=(14, 8),
        )

        tk.Label(
            top,
            text=mechanism.replace(
                "_",
                " ",
            ).upper(),
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        status_color = GREEN

        if "PARTIAL" in str(
            status
        ).upper():

            status_color = ORANGE

        if "CONTRAD" in str(
            status
        ).upper():

            status_color = RED

        tk.Label(
            top,
            text=str(status),
            bg=PANEL,
            fg=status_color,
            font=("Segoe UI", 9, "bold"),
        ).pack(
            side="right"
        )

        tk.Label(
            top,
            text=f"Evidence {score:.1f}/100",
            bg=PANEL,
            fg=BLUE,
            font=("Segoe UI", 9, "bold"),
        ).pack(
            side="right",
            padx=25,
        )

        tk.Frame(
            card,
            bg=BORDER,
            height=1,
        ).pack(
            fill="x",
            padx=18,
        )

        grid = tk.Frame(
            card,
            bg=PANEL,
        )

        grid.pack(
            fill="x",
            padx=18,
            pady=10,
        )

        self._result_field(
            grid,
            0,
            "Measurements",
            self._format_list(
                support
            ),
        )

        self._result_field(
            grid,
            1,
            "Directions",
            self._format_list(
                directions
            ),
        )

        self._result_field(
            grid,
            2,
            "Locations",
            self._format_list(
                locations
            ),
        )

        self._result_field(
            grid,
            3,
            "Supporting Orders",
            self._format_orders(
                orders
            ),
        )

        self._result_field(
            grid,
            4,
            "Missing Pattern",
            self._format_orders(
                missing
            ),
        )

        self._result_field(
            grid,
            5,
            "Database Documents",
            str(
                len(
                    database_docs
                )
            ),
        )

        self._result_field(
            grid,
            6,
            "Database Contradictions",
            str(
                len(
                    database_contradictions
                )
            ),
        )

        self._result_field(
            grid,
            7,
            "Actual FFT Contradictions",
            str(
                len(
                    fft_contradictions
                )
            ),
        )

        if reasons:

            tk.Label(
                card,
                text="Evidence Reasoning",
                bg=PANEL,
                fg=TEXT,
                font=("Segoe UI", 9, "bold"),
            ).pack(
                anchor="w",
                padx=18,
                pady=(4, 2),
            )

            for reason in reasons:

                tk.Label(
                    card,
                    text=f"• {reason}",
                    bg=PANEL,
                    fg=TEXT_DIM,
                    font=("Segoe UI", 8),
                    justify="left",
                    anchor="w",
                    wraplength=1050,
                ).pack(
                    fill="x",
                    padx=28,
                    pady=2,
                )

        tk.Label(
            card,
            text=(
                "Evidence candidate only — "
                "additional evidence may be required."
            ),
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8, "italic"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(10, 14),
        )

    # ========================================================
    # RESULT FIELD
    # ========================================================

    def _result_field(
        self,
        parent,
        row,
        label,
        value,
    ):

        tk.Label(
            parent,
            text=label,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
            width=24,
            anchor="w",
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=3,
        )

        tk.Label(
            parent,
            text=value,
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 8, "bold"),
            anchor="w",
            justify="left",
            wraplength=800,
        ).grid(
            row=row,
            column=1,
            sticky="w",
            pady=3,
        )

    # ========================================================
    # RECOMMENDATION
    # ========================================================

    def _build_recommendation_card(
        self,
        parent,
        recommendation_report,
    ):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            fill="x",
        )

        recommendations = getattr(
            recommendation_report,
            "recommendations",
            [],
        )

        if not recommendations:

            tk.Label(
                card,
                text=(
                    "No additional measurement "
                    "is currently required."
                ),
                bg=PANEL,
                fg=GREEN,
                font=("Segoe UI", 9, "bold"),
            ).pack(
                anchor="w",
                padx=18,
                pady=16,
            )

            return

        for recommendation in recommendations:

            priority = getattr(
                recommendation,
                "priority",
                "",
            )

            direction = getattr(
                recommendation,
                "direction",
                "",
            )

            targets = getattr(
                recommendation,
                "target_mechanisms",
                [],
            )

            reason = getattr(
                recommendation,
                "reason",
                "",
            )

            row = tk.Frame(
                card,
                bg=PANEL,
            )

            row.pack(
                fill="x",
                padx=18,
                pady=8,
            )

            tk.Label(
                row,
                text=f"PRIORITY {priority}",
                bg=ORANGE_DARK,
                fg=ORANGE,
                font=("Segoe UI", 8, "bold"),
                padx=8,
                pady=4,
            ).pack(
                side="left"
            )

            tk.Label(
                row,
                text=direction,
                bg=PANEL,
                fg=WHITE,
                font=("Segoe UI", 10, "bold"),
            ).pack(
                side="left",
                padx=15,
            )

            tk.Label(
                row,
                text=", ".join(
                    str(x).replace(
                        "_",
                        " ",
                    )
                    for x in targets
                ),
                bg=PANEL,
                fg=TEXT_DIM,
                font=("Segoe UI", 8),
            ).pack(
                side="left",
                padx=10,
            )

            tk.Label(
                card,
                text=reason,
                bg=PANEL,
                fg=TEXT_DIM,
                font=("Segoe UI", 8),
                justify="left",
                anchor="w",
                wraplength=1050,
            ).pack(
                fill="x",
                padx=25,
                pady=(0, 8),
            )

    # ========================================================
    # UTILITIES
    # ========================================================

    def _update_coverage(self):

        try:
            bearing_count = int(
                self.bearing_count_var.get()
            )
        except Exception:
            bearing_count = 1

        bearing_count = max(
            1,
            min(
                bearing_count,
                20,
            ),
        )

        expected = (
            bearing_count * 3
        )

        received = len(
            self.measurements
        )

        percentage = (
            received /
            expected *
            100
            if expected
            else 0
        )

        self.coverage_var.set(
            f"{received} / {expected} measurements"
        )

        self.coverage_percent_var.set(
            f"{percentage:.1f}%"
        )

        self.coverage_progress[
            "value"
        ] = percentage

        h = sum(
            1
            for item in self.measurements.values()
            if item["direction"] == "Horizontal"
        )

        v = sum(
            1
            for item in self.measurements.values()
            if item["direction"] == "Vertical"
        )

        a = sum(
            1
            for item in self.measurements.values()
            if item["direction"] == "Axial"
        )

        self.direction_label.configure(
            text=(
                f"H {h}/{bearing_count}     "
                f"V {v}/{bearing_count}     "
                f"A {a}/{bearing_count}"
            )
        )

    @staticmethod
    def _result_value(
        result,
        key,
        default="—",
    ):

        value = result.get(
            key,
            default,
        )

        if value is None:
            return default

        return str(value)

    @staticmethod
    def _format_number(value):

        if value is None:
            return "—"

        try:

            number = float(value)

            if number.is_integer():
                return str(
                    int(number)
                )

            return f"{number:.3f}"

        except Exception:

            return str(value)

    @staticmethod
    def _format_order(value):

        if value is None:
            return "—"

        if isinstance(
            value,
            str,
        ):

            return value

        try:

            number = float(value)

            if number.is_integer():

                return f"{int(number)}X"

            return f"{number:g}X"

        except Exception:

            return str(value)

    @staticmethod
    def _format_list(value):

        if not value:
            return "—"

        if isinstance(
            value,
            (list, tuple, set),
        ):

            return ", ".join(
                str(item)
                for item in value
            )

        return str(value)

    @staticmethod
    def _format_orders(value):

        if not value:
            return "—"

        result = []

        for item in value:

            if isinstance(
                item,
                dict,
            ):

                item = (
                    item.get("order")
                    or item.get(
                        "order_label"
                    )
                    or item.get("name")
                    or item
                )

            try:

                number = float(item)

                if number.is_integer():

                    result.append(
                        f"{int(number)}X"
                    )

                else:

                    result.append(
                        f"{number:g}X"
                    )

            except Exception:

                text = str(item)

                if not text.endswith("X"):
                    text += "X"

                result.append(
                    text
                )

        return ", ".join(result)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    app = MeasurementManager()

    app.mainloop()
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from database_engine import MachineContext

from engine.multi_measurement_analyzer import MultiMeasurementAnalyzer
from engine.diagnostic_engine import AIDiagnosticEngine
from engine.measurement_recommender import MeasurementRecommendationEngine


# ============================================================
# CONFIG
# ============================================================

DEFAULT_RPM = 1500.0

FREQUENCY_CALIBRATION = {
    "slope_hz_per_pixel": 0.60604178,
    "intercept_hz": -242.22631,
}


# ============================================================
# COLORS
# ============================================================

BG = "#11161c"
PANEL = "#19212a"
PANEL_2 = "#202a34"
BORDER = "#303c48"

TEXT = "#e8edf2"
TEXT_DIM = "#91a0ae"

GREEN = "#39d98a"
GREEN_DARK = "#183d2c"

BLUE = "#4da3ff"
BLUE_DARK = "#18304a"

ORANGE = "#ffb454"
ORANGE_DARK = "#49361c"

RED = "#ff6262"
RED_DARK = "#482323"

PURPLE = "#a98cff"
WHITE = "#ffffff"


# ============================================================
# APPLICATION
# ============================================================

class MeasurementManager(tk.Tk):

    def __init__(self):

        super().__init__()

        self.title("AI Condition Monitoring")
        self.geometry("1500x920")
        self.minsize(1250, 780)
        self.configure(bg=BG)

        # ----------------------------------------------------
        # DATA
        # ----------------------------------------------------

        self.measurements = {}

        self.analysis_results = {}

        self.selected_measurement_id = None

        self.preview_image = None

        # ----------------------------------------------------
        # VARIABLES
        # ----------------------------------------------------

        self.rpm_var = tk.StringVar(
            value=str(DEFAULT_RPM)
        )

        self.machine_var = tk.StringVar(
            value="Test Machine"
        )

        self.component_var = tk.StringVar(
            value="Fan"
        )

        self.bearing_count_var = tk.IntVar(
            value=4
        )

        self.status_var = tk.StringVar(
            value="SYSTEM READY — Add vibration measurements to begin."
        )

        self.coverage_var = tk.StringVar(
            value="0 / 12 measurements"
        )

        self.coverage_percent_var = tk.StringVar(
            value="0.0%"
        )

        # Analysis state
        self.analysis_running = False
        self.analysis_total = 0
        self.analysis_completed = 0

        # ----------------------------------------------------
        # STYLE
        # ----------------------------------------------------

        self._configure_styles()

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self._build_ui()

        self._refresh_bearing_map()

        self._update_coverage()

    # ========================================================
    # STYLE
    # ========================================================

    def _configure_styles(self):

        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "TCombobox",
            fieldbackground=PANEL_2,
            background=PANEL_2,
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
        )

        style.configure(
            "TEntry",
            fieldbackground=PANEL_2,
            foreground=TEXT,
            bordercolor=BORDER,
            insertcolor=TEXT,
        )

        style.configure(
            "Horizontal.TProgressbar",
            troughcolor="#0c1015",
            background=GREEN,
            bordercolor=BORDER,
            lightcolor=GREEN,
            darkcolor=GREEN,
        )

    # ========================================================
    # MAIN UI
    # ========================================================

    def _build_ui(self):

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = tk.Frame(
            self,
            bg="#0c1116",
            height=82,
        )

        header.pack(fill="x")
        header.pack_propagate(False)

        left_header = tk.Frame(
            header,
            bg="#0c1116",
        )

        left_header.pack(
            side="left",
            padx=28,
            pady=13,
        )

        tk.Label(
            left_header,
            text="AI CONDITION",
            bg="#0c1116",
            fg=WHITE,
            font=("Segoe UI", 21, "bold"),
        ).pack(anchor="w")

        tk.Label(
            left_header,
            text="Intelligent Vibration & Condition Monitoring",
            bg="#0c1116",
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        self.system_status_label = tk.Label(
            header,
            text="● SYSTEM READY",
            bg="#0c1116",
            fg=GREEN,
            font=("Segoe UI", 10, "bold"),
        )

        self.system_status_label.pack(
            side="right",
            padx=28,
        )

        # ----------------------------------------------------
        # MAIN SCROLL AREA
        # ----------------------------------------------------

        outer = tk.Frame(
            self,
            bg=BG,
        )

        outer.pack(
            fill="both",
            expand=True,
        )

        canvas = tk.Canvas(
            outer,
            bg=BG,
            highlightthickness=0,
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=canvas.yview,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        self.main_frame = tk.Frame(
            canvas,
            bg=BG,
        )

        window_id = canvas.create_window(
            (0, 0),
            window=self.main_frame,
            anchor="nw",
        )

        self.main_frame.bind(
            "<Configure>",
            lambda event: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfig(
                window_id,
                width=event.width,
            )
        )

        # ----------------------------------------------------
        # TOP CARDS
        # ----------------------------------------------------

        top = tk.Frame(
            self.main_frame,
            bg=BG,
        )

        top.pack(
            fill="x",
            padx=22,
            pady=(20, 10),
        )

        self._build_machine_card(top)
        self._build_coverage_card(top)

        # ----------------------------------------------------
        # BEARING MAP
        # ----------------------------------------------------

        self._build_section_title(
            self.main_frame,
            "BEARING MAP",
            "H / V / A measurements can be uploaded independently.",
        )

        self.bearing_map_container = tk.Frame(
            self.main_frame,
            bg=BG,
        )

        self.bearing_map_container.pack(
            fill="x",
            padx=22,
            pady=(5, 15),
        )

        # ----------------------------------------------------
        # LOWER AREA
        # ----------------------------------------------------

        lower = tk.Frame(
            self.main_frame,
            bg=BG,
        )

        lower.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=5,
        )

        self._build_preview_panel(lower)

        self._build_analysis_panel(lower)

        # ----------------------------------------------------
        # ANALYSIS PROGRESS
        # ----------------------------------------------------

        self._build_progress_panel(
            self.main_frame
        )

        # ----------------------------------------------------
        # ANALYZE BUTTON
        # ----------------------------------------------------

        analyze_frame = tk.Frame(
            self.main_frame,
            bg=BG,
        )

        analyze_frame.pack(
            fill="x",
            padx=22,
            pady=(15, 10),
        )

        self.analyze_button = tk.Button(
            analyze_frame,
            text="▶  ANALYZE MACHINE",
            command=self._start_analysis,
            bg=GREEN,
            fg="#07130d",
            activebackground="#63e9a7",
            activeforeground="#07130d",
            font=("Segoe UI", 13, "bold"),
            relief="flat",
            cursor="hand2",
            height=2,
        )

        self.analyze_button.pack(
            fill="x",
        )

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        status_frame = tk.Frame(
            self,
            bg="#0c1116",
            height=38,
        )

        status_frame.pack(fill="x")
        status_frame.pack_propagate(False)

        tk.Label(
            status_frame,
            textvariable=self.status_var,
            bg="#0c1116",
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(
            fill="both",
            padx=22,
        )

    # ========================================================
    # MACHINE CARD
    # ========================================================

    def _build_machine_card(self, parent):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8),
        )

        tk.Label(
            card,
            text="MACHINE CONFIGURATION",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(15, 8),
        )

        grid = tk.Frame(
            card,
            bg=PANEL,
        )

        grid.pack(
            fill="x",
            padx=18,
            pady=(0, 18),
        )

        self._input_row(
            grid,
            0,
            "RPM",
            self.rpm_var,
        )

        self._input_row(
            grid,
            1,
            "Machine",
            self.machine_var,
        )

        self._input_row(
            grid,
            2,
            "Component",
            self.component_var,
        )

        tk.Label(
            grid,
            text="Bearings",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=5,
        )

        tk.Spinbox(
            grid,
            from_=1,
            to=20,
            textvariable=self.bearing_count_var,
            bg=PANEL_2,
            fg=TEXT,
            insertbackground=TEXT,
            buttonbackground=PANEL_2,
            relief="flat",
            width=10,
            font=("Segoe UI", 9),
        ).grid(
            row=3,
            column=1,
            sticky="w",
            padx=10,
            pady=5,
        )

        tk.Button(
            grid,
            text="UPDATE MAP",
            command=self._refresh_bearing_map,
            bg=BLUE_DARK,
            fg=BLUE,
            activebackground=BLUE,
            activeforeground=BG,
            relief="flat",
            font=("Segoe UI", 8, "bold"),
            cursor="hand2",
        ).grid(
            row=3,
            column=2,
            padx=10,
        )

    def _input_row(
        self,
        parent,
        row,
        label,
        variable,
    ):

        tk.Label(
            parent,
            text=label,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=5,
        )

        tk.Entry(
            parent,
            textvariable=variable,
            bg=PANEL_2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 9),
            width=24,
        ).grid(
            row=row,
            column=1,
            columnspan=2,
            sticky="w",
            padx=10,
            pady=5,
        )

    # ========================================================
    # COVERAGE CARD
    # ========================================================

    def _build_coverage_card(self, parent):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            side="right",
            fill="both",
            padx=(8, 0),
        )

        tk.Label(
            card,
            text="MEASUREMENT COVERAGE",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(15, 2),
        )

        tk.Label(
            card,
            textvariable=self.coverage_percent_var,
            bg=PANEL,
            fg=GREEN,
            font=("Segoe UI", 24, "bold"),
        ).pack(
            anchor="w",
            padx=18,
        )

        self.coverage_progress = ttk.Progressbar(
            card,
            style="Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )

        self.coverage_progress.pack(
            fill="x",
            padx=18,
            pady=7,
        )

        tk.Label(
            card,
            textvariable=self.coverage_var,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).pack(
            anchor="w",
            padx=18,
        )

        self.direction_label = tk.Label(
            card,
            text="H 0/0     V 0/0     A 0/0",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        )

        self.direction_label.pack(
            anchor="w",
            padx=18,
            pady=(8, 15),
        )

    # ========================================================
    # SECTION TITLE
    # ========================================================

    def _build_section_title(
        self,
        parent,
        title,
        subtitle,
    ):

        frame = tk.Frame(
            parent,
            bg=BG,
        )

        frame.pack(
            fill="x",
            padx=22,
            pady=(8, 2),
        )

        tk.Label(
            frame,
            text=title,
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 13, "bold"),
        ).pack(anchor="w")

        tk.Label(
            frame,
            text=subtitle,
            bg=BG,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

    # ========================================================
    # BEARING MAP
    # ========================================================

    def _refresh_bearing_map(self):

        try:
            count = int(
                self.bearing_count_var.get()
            )
        except Exception:
            count = 1

        count = max(
            1,
            min(count, 20),
        )

        for widget in self.bearing_map_container.winfo_children():
            widget.destroy()

        for index in range(count):

            bearing_id = f"B{index + 1}"

            card = self._create_bearing_card(
                self.bearing_map_container,
                bearing_id,
                index,
            )

            row = index // 4
            column = index % 4

            card.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=6,
                pady=6,
            )

        for column in range(4):

            self.bearing_map_container.grid_columnconfigure(
                column,
                weight=1,
            )

        self._update_coverage()

    def _create_bearing_card(
        self,
        parent,
        bearing_id,
        index,
    ):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        header = tk.Frame(
            card,
            bg=PANEL,
        )

        header.pack(
            fill="x",
            padx=12,
            pady=(10, 4),
        )

        tk.Label(
            header,
            text=bearing_id,
            bg=PANEL,
            fg=WHITE,
            font=("Segoe UI", 13, "bold"),
        ).pack(side="left")

        tk.Label(
            header,
            text=f"Bearing {index + 1}",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
        ).pack(side="right")

        tk.Frame(
            card,
            bg=BORDER,
            height=1,
        ).pack(
            fill="x",
            padx=12,
        )

        body = tk.Frame(
            card,
            bg=PANEL,
        )

        body.pack(
            fill="x",
            padx=12,
            pady=10,
        )

        directions = [
            ("H", "Horizontal"),
            ("V", "Vertical"),
            ("A", "Axial"),
        ]

        for short, direction in directions:

            measurement_id = self._measurement_id(
                bearing_id,
                short,
            )

            measurement = self.measurements.get(
                measurement_id
            )

            row = tk.Frame(
                body,
                bg=PANEL,
            )

            row.pack(
                fill="x",
                pady=3,
            )

            tk.Label(
                row,
                text=short,
                bg=PANEL,
                fg=TEXT,
                font=("Segoe UI", 10, "bold"),
                width=2,
            ).pack(side="left")

            status = "○ NOT MEASURED"
            bg = PANEL_2
            fg = TEXT_DIM

            if measurement:

                state = measurement.get(
                    "status",
                    "READY",
                )

                if state == "READY":
                    status = "● READY"
                    bg = BLUE_DARK
                    fg = BLUE

                elif state == "ANALYZING":
                    status = "● ANALYZING"
                    bg = ORANGE_DARK
                    fg = ORANGE

                elif state == "ANALYZED":
                    status = "✓ ANALYZED"
                    bg = GREEN_DARK
                    fg = GREEN

                elif state == "ERROR":
                    status = "✕ ERROR"
                    bg = RED_DARK
                    fg = RED

            button = tk.Button(
                row,
                text=status,
                command=lambda b=bearing_id, d=direction:
                    self._upload_for_slot(b, d),
                bg=bg,
                fg=fg,
                activebackground=bg,
                activeforeground=fg,
                relief="flat",
                font=("Segoe UI", 8, "bold"),
                cursor="hand2",
                anchor="w",
            )

            button.pack(
                side="left",
                fill="x",
                expand=True,
            )

        return card

    # ========================================================
    # SLOT
    # ========================================================

    def _measurement_id(
        self,
        bearing,
        short_direction,
    ):

        return f"{bearing}-{short_direction}"

    # ========================================================
    # UPLOAD
    # ========================================================

    def _upload_for_slot(
        self,
        bearing,
        direction,
    ):

        short = {
            "Horizontal": "H",
            "Vertical": "V",
            "Axial": "A",
        }[direction]

        measurement_id = self._measurement_id(
            bearing,
            short,
        )

        if measurement_id in self.measurements:

            answer = messagebox.askyesnocancel(
                "Measurement Exists",
                (
                    f"{bearing} / {direction} already exists.\n\n"
                    "YES = Replace\n"
                    "NO = Delete\n"
                    "CANCEL = Keep"
                ),
            )

            if answer is None:
                return

            if answer is False:

                del self.measurements[
                    measurement_id
                ]

                self.analysis_results.pop(
                    measurement_id,
                    None,
                )

                self.selected_measurement_id = None

                self._refresh_bearing_map()
                self._update_preview()

                self.status_var.set(
                    f"Measurement removed: {measurement_id}"
                )

                return

        path = filedialog.askopenfilename(
            title=(
                f"Select FFT Image — "
                f"{bearing} / {direction}"
            ),
            filetypes=[
                (
                    "FFT Images",
                    "*.png *.jpg *.jpeg",
                ),
                (
                    "PNG",
                    "*.png",
                ),
                (
                    "JPEG",
                    "*.jpg *.jpeg",
                ),
            ],
        )

        if not path:
            return

        if not os.path.isfile(path):
            messagebox.showerror(
                "Invalid File",
                "The selected image could not be found.",
            )
            return

        point = f"Bearing {bearing[1:]}"

        self.measurements[measurement_id] = {
            "id": measurement_id,
            "image": path,
            "bearing": bearing,
            "point": point,
            "direction": direction,
            "component": (
                self.component_var.get().strip()
                or "Unknown"
            ),
            "status": "READY",
        }

        self.analysis_results.pop(
            measurement_id,
            None,
        )

        self.selected_measurement_id = (
            measurement_id
        )

        self._refresh_bearing_map()
        self._update_preview()
        self._update_coverage()

        self.status_var.set(
            f"READY — {measurement_id} — "
            f"{os.path.basename(path)}"
        )

    # ========================================================
    # PREVIEW PANEL
    # ========================================================

    def _build_preview_panel(self, parent):

        panel = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        panel.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8),
        )

        tk.Label(
            panel,
            text="FFT PREVIEW",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(15, 3),
        )

        tk.Label(
            panel,
            text="Selected vibration measurement",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=18,
        )

        self.preview_label = tk.Label(
            panel,
            text="No measurement selected",
            bg="#0c1116",
            fg=TEXT_DIM,
            font=("Segoe UI", 10),
        )

        self.preview_label.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=15,
        )

    # ========================================================
    # ANALYSIS DETAIL PANEL
    # ========================================================

    def _build_analysis_panel(self, parent):

        panel = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
            width=480,
        )

        panel.pack(
            side="right",
            fill="both",
            padx=(8, 0),
        )

        panel.pack_propagate(False)

        tk.Label(
            panel,
            text="MEASUREMENT ANALYSIS",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(15, 3),
        )

        self.analysis_subtitle = tk.Label(
            panel,
            text="Select a measurement",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
        )

        self.analysis_subtitle.pack(
            anchor="w",
            padx=18,
        )

        self.analysis_content = tk.Frame(
            panel,
            bg=PANEL,
        )

        self.analysis_content.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=12,
        )

    # ========================================================
    # PROGRESS PANEL
    # ========================================================

    def _build_progress_panel(self, parent):

        panel = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        panel.pack(
            fill="x",
            padx=22,
            pady=(10, 5),
        )

        top = tk.Frame(
            panel,
            bg=PANEL,
        )

        top.pack(
            fill="x",
            padx=18,
            pady=(12, 4),
        )

        self.progress_title = tk.Label(
            top,
            text="ANALYSIS STATUS",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        )

        self.progress_title.pack(
            side="left"
        )

        self.progress_text = tk.Label(
            top,
            text="Waiting",
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 9),
        )

        self.progress_text.pack(
            side="right"
        )

        self.analysis_progress = ttk.Progressbar(
            panel,
            style="Horizontal.TProgressbar",
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )

        self.analysis_progress.pack(
            fill="x",
            padx=18,
            pady=(2, 12),
        )

    # ========================================================
    # UPDATE PREVIEW
    # ========================================================

    def _update_preview(self):

        measurement = self.measurements.get(
            self.selected_measurement_id
        )

        if not measurement:

            self.preview_label.configure(
                image="",
                text="No measurement selected",
            )

            self.preview_image = None

            self._clear_analysis_panel()

            return

        path = measurement["image"]

        try:

            from PIL import Image, ImageTk

            image = Image.open(path)

            image.thumbnail(
                (700, 400)
            )

            self.preview_image = ImageTk.PhotoImage(
                image
            )

            self.preview_label.configure(
                image=self.preview_image,
                text="",
            )

        except Exception:

            self.preview_label.configure(
                image="",
                text=(
                    "FFT image selected\n\n"
                    f"{os.path.basename(path)}\n\n"
                    "Install Pillow for image preview."
                ),
            )

        self._show_measurement_details(
            measurement
        )

    # ========================================================
    # MEASUREMENT DETAILS
    # ========================================================

    def _show_measurement_details(
        self,
        measurement,
    ):

        self._clear_analysis_panel()

        self.analysis_subtitle.configure(
            text=(
                f"{measurement['id']}  •  "
                f"{measurement['direction']}"
            )
        )

        self._add_detail(
            "Status",
            measurement.get(
                "status",
                "READY",
            ),
        )

        self._add_detail(
            "Bearing",
            measurement["bearing"],
        )

        self._add_detail(
            "Point",
            measurement["point"],
        )

        self._add_detail(
            "Direction",
            measurement["direction"],
        )

        self._add_detail(
            "Component",
            measurement["component"],
        )

        self._add_detail(
            "File",
            os.path.basename(
                measurement["image"]
            ),
        )

        result = self.analysis_results.get(
            measurement["id"]
        )

        if not result:

            tk.Label(
                self.analysis_content,
                text="Analysis not available yet.",
                bg=PANEL,
                fg=TEXT_DIM,
                font=("Segoe UI", 9, "italic"),
            ).pack(
                anchor="w",
                pady=15,
            )

            return

        separator = tk.Frame(
            self.analysis_content,
            bg=BORDER,
            height=1,
        )

        separator.pack(
            fill="x",
            pady=10,
        )

        tk.Label(
            self.analysis_content,
            text="EXTRACTED SPECTRUM",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 7),
        )

        self._add_detail(
            "RPM",
            self._result_value(
                result,
                "rpm",
                "—",
            ),
        )

        self._add_detail(
            "Peaks",
            self._result_value(
                result,
                "peak_count",
                "—",
            ),
        )

        self._add_detail(
            "Matched Orders",
            self._result_value(
                result,
                "matched_orders",
                "—",
            ),
        )

        self._add_detail(
            "Dominant Order",
            self._result_value(
                result,
                "dominant_order",
                "—",
            ),
        )

        self._add_detail(
            "Dominant Amplitude",
            self._result_value(
                result,
                "dominant_amplitude",
                "—",
            ),
        )

        orders = result.get(
            "orders",
            [],
        )

        if orders:

            separator = tk.Frame(
                self.analysis_content,
                bg=BORDER,
                height=1,
            )

            separator.pack(
                fill="x",
                pady=10,
            )

            tk.Label(
                self.analysis_content,
                text="MATCHED ORDERS",
                bg=PANEL,
                fg=TEXT,
                font=("Segoe UI", 9, "bold"),
            ).pack(
                anchor="w",
                pady=(0, 5),
            )

            for order in orders[:12]:

                self._add_order_row(
                    order
                )

    def _clear_analysis_panel(self):

        for widget in self.analysis_content.winfo_children():
            widget.destroy()

        self.analysis_subtitle.configure(
            text="Select a measurement"
        )

    def _add_detail(
        self,
        label,
        value,
    ):

        row = tk.Frame(
            self.analysis_content,
            bg=PANEL,
        )

        row.pack(
            fill="x",
            pady=3,
        )

        tk.Label(
            row,
            text=label,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
            width=20,
            anchor="w",
        ).pack(side="left")

        value_text = str(value)

        if value_text == "ANALYZED":
            value_fg = GREEN
        elif value_text == "READY":
            value_fg = BLUE
        elif value_text == "ERROR":
            value_fg = RED
        else:
            value_fg = TEXT

        tk.Label(
            row,
            text=value_text,
            bg=PANEL,
            fg=value_fg,
            font=("Segoe UI", 8, "bold"),
            anchor="w",
            justify="left",
            wraplength=250,
        ).pack(
            side="left",
            fill="x",
            expand=True,
        )

    def _add_order_row(
        self,
        order,
    ):

        if isinstance(order, dict):

            order_name = (
                order.get("order")
                or order.get("order_label")
                or order.get("name")
                or "—"
            )

            frequency = (
                order.get("frequency")
                or order.get("freq")
                or "—"
            )

            amplitude = (
                order.get("amplitude")
                or order.get("amp")
                or "—"
            )

            confidence = (
                order.get("confidence")
                or "—"
            )

        else:

            order_name = str(order)
            frequency = "—"
            amplitude = "—"
            confidence = "—"

        row = tk.Frame(
            self.analysis_content,
            bg=PANEL_2,
        )

        row.pack(
            fill="x",
            pady=2,
        )

        tk.Label(
            row,
            text=str(order_name),
            bg=PANEL_2,
            fg=BLUE,
            font=("Segoe UI", 8, "bold"),
            width=7,
        ).pack(side="left")

        tk.Label(
            row,
            text=self._format_number(
                frequency
            ),
            bg=PANEL_2,
            fg=TEXT,
            font=("Segoe UI", 8),
            width=12,
        ).pack(side="left")

        tk.Label(
            row,
            text=self._format_number(
                amplitude
            ),
            bg=PANEL_2,
            fg=TEXT,
            font=("Segoe UI", 8),
            width=12,
        ).pack(side="left")

        tk.Label(
            row,
            text=self._format_number(
                confidence
            ),
            bg=PANEL_2,
            fg=GREEN,
            font=("Segoe UI", 8),
        ).pack(side="left")

    # ========================================================
    # ANALYSIS
    # ========================================================

    def _start_analysis(self):

        if self.analysis_running:
            return

        if not self.measurements:

            messagebox.showwarning(
                "No Measurements",
                "Please upload at least one FFT measurement.",
            )

            return

        try:

            rpm = float(
                self.rpm_var.get().strip()
            )

            if rpm <= 0:
                raise ValueError

        except Exception:

            messagebox.showerror(
                "Invalid RPM",
                "Please enter a valid positive RPM.",
            )

            return

        self.analysis_running = True

        self.analysis_total = len(
            self.measurements
        )

        self.analysis_completed = 0

        self.analysis_progress["value"] = 0

        self.progress_text.configure(
            text=(
                f"0 / {self.analysis_total}"
            )
        )

        self.progress_title.configure(
            text="AI ANALYSIS RUNNING"
        )

        self.system_status_label.configure(
            text="● ANALYSIS RUNNING",
            fg=ORANGE,
        )

        self.analyze_button.configure(
            state="disabled",
            text="⏳  ANALYZING MACHINE...",
            bg=ORANGE,
            fg="#171006",
        )

        self.status_var.set(
            "ANALYSIS RUNNING — Please wait..."
        )

        # Reset old analyzed states
        for measurement in self.measurements.values():

            measurement["status"] = "READY"

        self._refresh_bearing_map()

        thread = threading.Thread(
            target=self._analysis_worker,
            args=(rpm,),
            daemon=True,
        )

        thread.start()

    # ========================================================
    # ANALYSIS WORKER
    # ========================================================

    def _analysis_worker(
            self,
    ):

        try:

            print()
            print()
            print(
                "#" * 100
            )
            print(
                "# AI CONDITION — ANALYSIS START"
            )
            print(
                "#" * 100
            )

            try:

                print(
                    f"Machine              : "
                    f"{self.machine_var.get()}"
                )

            except Exception:

                print(
                    "Machine              : —"
                )

            try:

                print(
                    f"RPM                  : "
                    f"{self.rpm_var.get()}"
                )

            except Exception:

                print(
                    "RPM                  : —"
                )

            try:

                print(
                    f"Measurements loaded  : "
                    f"{len(self.measurements)}"
                )

            except Exception:

                print(
                    "Measurements loaded  : —"
                )

            print()

            print(
                "MEASUREMENTS TO ANALYZE"
            )

            print(
                "-" * 100
            )

            for measurement_id, measurement in (
                    self.measurements.items()
            ):

                print()

                print(
                    f"ID: {measurement_id}"
                )

                if isinstance(
                        measurement,
                        dict,
                ):

                    for key, value in (
                            measurement.items()
                    ):
                        print(
                            f"  {key}: {value}"
                        )

            print(
                "#" * 100
            )

            import sys

            sys.stdout.flush()

            # =================================================================
            # MACHINE CONTEXT
            # =================================================================

            machine_context = MachineContext(
                equipment_type=(
                    self.machine_var.get()
                    if hasattr(
                        self,
                        "machine_var"
                    )
                    else None
                ),
                rpm=float(
                    self.rpm_var.get()
                ),
            )

            # =================================================================
            # ANALYZER
            # =================================================================

            analyzer = MultiMeasurementAnalyzer(
                machine_context=machine_context
            )

            # =================================================================
            # ANALYZE EVERY MEASUREMENT
            # =================================================================

            total = len(
                self.measurements
            )

            self.analysis_total = total
            self.analysis_completed = 0

            for index, (
                    measurement_id,
                    measurement
            ) in enumerate(
                self.measurements.items(),
                start=1,
            ):

                self._set_measurement_status(
                    measurement_id,
                    "ANALYZING",
                    index - 1,
                )

                print()
                print(
                    "=" * 100
                )

                print(
                    f"ANALYZING MEASUREMENT: "
                    f"{measurement_id}"
                )

                print(
                    "-" * 100
                )

                if not isinstance(
                        measurement,
                        dict,
                ):
                    raise TypeError(
                        f"Measurement '{measurement_id}' "
                        f"must be a dictionary."
                    )

                image_path = measurement.get(
                    "image_path"
                )

                bearing_id = measurement.get(
                    "bearing_id",
                    measurement.get(
                        "bearing"
                    )
                )

                point = measurement.get(
                    "point",
                    bearing_id
                )

                direction = measurement.get(
                    "direction"
                )

                component = measurement.get(
                    "component"
                )

                print(
                    f"Image     : {image_path}"
                )

                print(
                    f"Bearing   : {bearing_id}"
                )

                print(
                    f"Point     : {point}"
                )

                print(
                    f"Direction : {direction}"
                )

                print(
                    f"Component : {component}"
                )

                print(
                    f"RPM       : "
                    f"{machine_context.rpm}"
                )

                print(
                    "=" * 100
                )

                import sys

                sys.stdout.flush()

                # =============================================================
                # ADD MEASUREMENT
                # =============================================================

                analyzer.add_measurement(
                    measurement_id=measurement_id,
                    image_path=image_path,
                    bearing_id=bearing_id,
                    point=point,
                    direction=direction,
                    component=component,
                )

                # =============================================================
                # FIND CREATED MEASUREMENT EVIDENCE
                # =============================================================

                evidence = None

                for item in analyzer.measurements:

                    if (
                            getattr(
                                item,
                                "measurement_id",
                                None
                            )
                            ==
                            measurement_id
                    ):
                        evidence = item
                        break

                if evidence is None:
                    raise RuntimeError(
                        "Measurement evidence was not "
                        f"created for '{measurement_id}'."
                    )

                # =============================================================
                # EXTRACT ANALYSIS RESULT
                # =============================================================

                analysis_result = (
                    self._extract_analysis_result(
                        evidence
                    )
                )

                measurement[
                    "analysis"
                ] = analysis_result

                # =============================================================
                # PRINT ANALYSIS RESULT
                # =============================================================

                print()
                print(
                    "=" * 100
                )

                print(
                    f"ANALYSIS RESULT — "
                    f"{measurement_id}"
                )

                print(
                    "-" * 100
                )

                print(
                    f"RPM              : "
                    f"{analysis_result.get('rpm', '—')}"
                )

                print(
                    f"Peak count       : "
                    f"{analysis_result.get('peak_count', '—')}"
                )

                print(
                    f"Matched orders   : "
                    f"{analysis_result.get('matched_orders', '—')}"
                )

                print(
                    f"Dominant order   : "
                    f"{analysis_result.get('dominant_order', '—')}"
                )

                print(
                    f"Dominant amp     : "
                    f"{analysis_result.get('dominant_amplitude', '—')}"
                )

                print(
                    f"Orders           : "
                    f"{analysis_result.get('orders', [])}"
                )

                print(
                    "=" * 100
                )

                import sys

                sys.stdout.flush()

                # =============================================================
                # UPDATE STATUS
                # =============================================================

                self._set_measurement_status(
                    measurement_id,
                    "ANALYZED",
                    index,
                )

            # =================================================================
            # EXPECTED SLOTS
            # =================================================================

            bearing_ids = []

            for measurement in (
                    self.measurements.values()
            ):

                if not isinstance(
                        measurement,
                        dict,
                ):
                    continue

                bearing_id = measurement.get(
                    "bearing_id",
                    measurement.get(
                        "bearing"
                    )
                )

                if bearing_id is not None:

                    bearing_id = str(
                        bearing_id
                    ).strip()

                    if (
                            bearing_id
                            and
                            bearing_id not in bearing_ids
                    ):
                        bearing_ids.append(
                            bearing_id
                        )

            # -----------------------------------------------------------------
            # If the UI has a bearing-count variable, include all bearings.
            # -----------------------------------------------------------------

            try:

                bearing_count = int(
                    self.bearing_count_var.get()
                )

                for number in range(
                        1,
                        bearing_count + 1
                ):

                    bearing_id = f"B{number}"

                    if (
                            bearing_id
                            not in bearing_ids
                    ):
                        bearing_ids.append(
                            bearing_id
                        )

            except Exception:

                pass

            bearing_ids = sorted(
                bearing_ids
            )

            # =================================================================
            # BUILD EXPECTED SLOTS
            # =================================================================

            expected_slots = []

            for bearing_id in bearing_ids:

                for direction in [
                    "Horizontal",
                    "Vertical",
                    "Axial",
                ]:
                    expected_slots.append(
                        {
                            "bearing": bearing_id,
                            "direction": direction,
                        }
                    )

            # =================================================================
            # PRINT FUSION INPUT
            # =================================================================

            print()
            print(
                "=" * 100
            )

            print(
                "AI CONDITION — FUSION INPUT"
            )

            print(
                "=" * 100
            )

            print(
                f"Measurements received : "
                f"{len(analyzer.measurements)}"
            )

            print(
                f"Expected measurements : "
                f"{len(expected_slots)}"
            )

            print()

            print(
                "EXPECTED SLOTS"
            )

            print(
                "-" * 100
            )

            for slot_index, slot in enumerate(
                    expected_slots,
                    start=1,
            ):
                print(
                    f"{slot_index}. {slot}"
                )

            print()

            print(
                "MEASUREMENTS"
            )

            print(
                "-" * 100
            )

            for item_index, measurement in enumerate(
                    analyzer.measurements,
                    start=1,
            ):
                print()

                print(
                    f"[{item_index}]"
                )

                print(
                    f"ID        : "
                    f"{getattr(measurement, 'measurement_id', '—')}"
                )

                print(
                    f"Bearing   : "
                    f"{getattr(measurement, 'bearing_id', '—')}"
                )

                print(
                    f"Point     : "
                    f"{getattr(measurement, 'point', '—')}"
                )

                print(
                    f"Direction : "
                    f"{getattr(measurement, 'direction', '—')}"
                )

                print(
                    f"Component : "
                    f"{getattr(measurement, 'component', '—')}"
                )

                print(
                    f"RPM       : "
                    f"{getattr(measurement, 'rpm', '—')}"
                )

            print(
                "=" * 100
            )

            import sys

            sys.stdout.flush()

            # =================================================================
            # FUSION
            # =================================================================

            fusion_report = analyzer.fuse(
                expected_measurements=len(
                    expected_slots
                ),
                expected_slots=expected_slots,
            )

            # =================================================================
            # PRINT FUSION RESULT
            # =================================================================

            print()
            print(
                "=" * 100
            )

            print(
                "AI CONDITION — FUSION RESULT"
            )

            print(
                "=" * 100
            )

            print(
                f"Measurements received : "
                f"{getattr(fusion_report, 'measurements_received', '—')}"
            )

            print(
                f"Expected measurements : "
                f"{getattr(fusion_report, 'expected_measurements', '—')}"
            )

            print(
                f"Coverage              : "
                f"{getattr(fusion_report, 'machine_measurement_coverage', '—')}"
            )

            print(
                f"Available directions  : "
                f"{getattr(fusion_report, 'available_directions', [])}"
            )

            print(
                f"Available slots       : "
                f"{getattr(fusion_report, 'available_slots', [])}"
            )

            print(
                f"Missing expected slots: "
                f"{getattr(fusion_report, 'missing_expected_slots', [])}"
            )

            print()

            print(
                "FUSION CANDIDATES"
            )

            print(
                "-" * 100
            )

            for candidate_index, candidate in enumerate(
                    getattr(
                        fusion_report,
                        "candidates",
                        []
                    ),
                    start=1,
            ):
                print()

                print(
                    f"[CANDIDATE {candidate_index}]"
                )

                print(
                    f"Mechanism                     : "
                    f"{getattr(candidate, 'mechanism', '—')}"
                )

                print(
                    f"Status                        : "
                    f"{getattr(candidate, 'status', '—')}"
                )

                print(
                    f"Supporting measurements       : "
                    f"{getattr(candidate, 'supporting_measurements', [])}"
                )

                print(
                    f"Directions                    : "
                    f"{getattr(candidate, 'directions', [])}"
                )

                print(
                    f"Database directions           : "
                    f"{getattr(candidate, 'database_directions', [])}"
                )

                print(
                    f"Locations                     : "
                    f"{getattr(candidate, 'locations', [])}"
                )

                print(
                    f"Components                    : "
                    f"{getattr(candidate, 'components', [])}"
                )

                print(
                    f"Supporting orders             : "
                    f"{getattr(candidate, 'supporting_orders', [])}"
                )

                print(
                    f"Missing pattern orders        : "
                    f"{getattr(candidate, 'missing_pattern_orders', [])}"
                )

                print(
                    f"Context support               : "
                    f"{getattr(candidate, 'context_support', [])}"
                )

                print(
                    f"Database documents            : "
                    f"{getattr(candidate, 'database_documents', [])}"
                )

                print(
                    f"Database pattern contradictions: "
                    f"{getattr(candidate, 'database_pattern_contradictions', [])}"
                )

                print(
                    f"Actual FFT contradictions    : "
                    f"{getattr(candidate, 'actual_fft_contradictions', 0)}"
                )

                print(
                    f"Reasons                       : "
                    f"{getattr(candidate, 'reasons', [])}"
                )

            print(
                "=" * 100
            )

            import sys

            sys.stdout.flush()

            # =================================================================
            # DIAGNOSTIC ENGINE
            # =================================================================

            diagnostic_engine = AIDiagnosticEngine()

            diagnostic_report = (
                diagnostic_engine.diagnose(
                    fusion_report
                )
            )

            # =================================================================
            # PRINT DIAGNOSTIC REPORT
            # =================================================================

            print()
            print(
                "=" * 100
            )

            print(
                "AI CONDITION — DIAGNOSTIC REPORT"
            )

            print(
                "=" * 100
            )

            print(
                f"Measurements received : "
                f"{getattr(diagnostic_report, 'measurements_received', '—')}"
            )

            print(
                f"Expected measurements : "
                f"{getattr(diagnostic_report, 'expected_measurements', '—')}"
            )

            print(
                f"Coverage              : "
                f"{getattr(diagnostic_report, 'coverage_percent', '—')}"
            )

            print(
                f"Available directions  : "
                f"{getattr(diagnostic_report, 'available_directions', [])}"
            )

            print(
                f"Available measurements: "
                f"{getattr(diagnostic_report, 'available_measurements', [])}"
            )

            print(
                f"Missing slots         : "
                f"{getattr(diagnostic_report, 'missing_expected_slots', [])}"
            )

            print()

            print(
                "DIAGNOSTICS"
            )

            print(
                "-" * 100
            )

            for diagnostic_index, diagnostic in enumerate(
                    getattr(
                        diagnostic_report,
                        "diagnostics",
                        []
                    ),
                    start=1,
            ):

                print()

                print(
                    f"[DIAGNOSTIC {diagnostic_index}]"
                )

                if hasattr(
                        diagnostic,
                        "__dict__"
                ):

                    for key, value in (
                            diagnostic.__dict__.items()
                    ):
                        print(
                            f"{key}: {value}"
                        )

                elif isinstance(
                        diagnostic,
                        dict,
                ):

                    for key, value in (
                            diagnostic.items()
                    ):
                        print(
                            f"{key}: {value}"
                        )

                else:

                    print(
                        diagnostic
                    )

            print()

            print(
                "NOTES"
            )

            print(
                "-" * 100
            )

            for note in getattr(
                    diagnostic_report,
                    "notes",
                    []
            ):
                print(
                    f"• {note}"
                )

            print(
                "=" * 100
            )

            import sys

            sys.stdout.flush()

            # =================================================================
            # RECOMMENDATION ENGINE
            # =================================================================

            recommendation_engine = (
                MeasurementRecommendationEngine()
            )

            recommendation_report = (
                recommendation_engine.recommend(
                    fusion_report
                )
            )

            # =================================================================
            # PRINT RECOMMENDATIONS
            # =================================================================

            print()
            print(
                "=" * 100
            )

            print(
                "AI CONDITION — MEASUREMENT RECOMMENDATIONS"
            )

            print(
                "=" * 100
            )

            if hasattr(
                    recommendation_report,
                    "__dict__"
            ):

                for key, value in (
                        recommendation_report.__dict__.items()
                ):

                    print()

                    print(
                        f"{key}:"
                    )

                    if isinstance(
                            value,
                            (
                                    list,
                                    tuple,
                            )
                    ):

                        for recommendation_index, item in enumerate(
                                value,
                                start=1,
                        ):
                            print(
                                f"  {recommendation_index}. "
                                f"{item}"
                            )

                    else:

                        print(
                            f"  {value}"
                        )

            else:

                print(
                    recommendation_report
                )

            print(
                "=" * 100
            )

            import sys

            sys.stdout.flush()

            # =================================================================
            # COMPLETE
            # =================================================================

            self.after(
                0,
                self._analysis_complete,
                fusion_report,
                diagnostic_report,
                recommendation_report,
            )

        except Exception as exc:

            # =================================================================
            # PRINT COMPLETE ERROR TO TERMINAL
            # =================================================================

            import traceback
            import sys

            print()
            print()
            print(
                "#" * 100
            )

            print(
                "# AI CONDITION — ANALYSIS ERROR"
            )

            print(
                "#" * 100
            )

            print(
                f"Exception type : "
                f"{type(exc).__name__}"
            )

            print(
                f"Exception      : "
                f"{exc}"
            )

            print()

            print(
                "FULL TRACEBACK"
            )

            print(
                "-" * 100
            )

            traceback.print_exc()

            print(
                "#" * 100
            )

            sys.stdout.flush()

            self.after(
                0,
                self._analysis_failed,
                exc,
            )
    # ========================================================
    # STATUS UPDATE
    # ========================================================

    def _set_measurement_status(
        self,
        measurement_id,
        status,
        index,
    ):

        if measurement_id in self.measurements:

            self.measurements[
                measurement_id
            ]["status"] = status

        self.analysis_completed = index

        percentage = (
            index /
            max(
                self.analysis_total,
                1,
            )
        ) * 100

        self.analysis_progress[
            "value"
        ] = percentage

        self.progress_text.configure(
            text=(
                f"{index} / "
                f"{self.analysis_total}"
            )
        )

        self.status_var.set(
            f"{status} — {measurement_id}"
        )

        self._refresh_bearing_map()

        if (
            self.selected_measurement_id
            == measurement_id
        ):
            self._update_preview()

    # ========================================================
    # ANALYSIS RESULT EXTRACTION
    # ========================================================

    def _extract_analysis_result(
        self,
        evidence,
    ):

        result = {
            "rpm": "—",
            "peak_count": "—",
            "matched_orders": "—",
            "dominant_order": "—",
            "dominant_amplitude": "—",
            "orders": [],
        }

        if evidence is None:
            return result

        # ----------------------------------------------------
        # VibrationFeatures
        # ----------------------------------------------------

        features = getattr(
            evidence,
            "features",
            None,
        )

        if features is not None:

            result["rpm"] = getattr(
                features,
                "rpm",
                "—",
            )

            dominant_order = getattr(
                features,
                "dominant_order",
                "—",
            )

            result["dominant_order"] = (
                self._format_order(
                    dominant_order
                )
            )

            result["dominant_amplitude"] = (
                getattr(
                    features,
                    "dominant_amplitude",
                    "—",
                )
            )

            present_orders = getattr(
                features,
                "present_orders",
                [],
            )

            result["matched_orders"] = len(
                present_orders
            )

        # ----------------------------------------------------
        # Raw Evidence / Extra
        # ----------------------------------------------------

        raw_features = getattr(
            features,
            "extra",
            None,
        )

        if isinstance(
            raw_features,
            dict,
        ):

            fundamental = raw_features.get(
                "fundamental",
                {},
            )

            if isinstance(
                fundamental,
                dict,
            ):

                if result["dominant_order"] == "—":

                    result["dominant_order"] = (
                        self._format_order(
                            fundamental.get(
                                "dominant_order"
                            )
                        )
                    )

                if result[
                    "dominant_amplitude"
                ] == "—":

                    result[
                        "dominant_amplitude"
                    ] = fundamental.get(
                        "dominant_amplitude",
                        "—",
                    )

        # ----------------------------------------------------
        # Matcher / Evidence
        # ----------------------------------------------------

        order_results = getattr(
            evidence,
            "order_results",
            None,
        )

        if order_results is None:

            order_results = getattr(
                evidence,
                "orders",
                None,
            )

        if order_results:

            result["orders"] = (
                self._normalize_orders(
                    order_results
                )
            )

            result["peak_count"] = len(
                order_results
            )

        else:

            order_map = getattr(
                evidence,
                "order_map",
                None,
            )

            if isinstance(
                order_map,
                dict,
            ):

                result["orders"] = (
                    self._normalize_orders(
                        order_map.values()
                    )
                )

                result["peak_count"] = len(
                    order_map
                )

        if (
            result["matched_orders"] == "—"
            and result["orders"]
        ):

            result["matched_orders"] = len(
                result["orders"]
            )

        return result

    # ========================================================
    # NORMALIZE ORDERS
    # ========================================================

    def _normalize_orders(
        self,
        orders,
    ):

        normalized = []

        if isinstance(
            orders,
            dict,
        ):

            iterable = orders.values()

        else:

            iterable = orders

        for item in iterable:

            if isinstance(
                item,
                dict,
            ):

                normalized.append(
                    {
                        "order": (
                            item.get("order")
                            or item.get(
                                "order_label"
                            )
                            or item.get("name")
                        ),
                        "frequency": (
                            item.get("frequency")
                            or item.get("freq")
                        ),
                        "amplitude": (
                            item.get("amplitude")
                            or item.get("amp")
                        ),
                        "confidence": item.get(
                            "confidence"
                        ),
                    }
                )

            else:

                normalized.append(
                    {
                        "order": str(item),
                        "frequency": None,
                        "amplitude": None,
                        "confidence": None,
                    }
                )

        return normalized

    # ========================================================
    # ANALYSIS COMPLETE
    # ========================================================

    def _analysis_complete(
        self,
        fusion_report,
        diagnostic_report,
        recommendation_report,
    ):

        self.analysis_running = False

        self.analysis_progress[
            "value"
        ] = 100

        self.progress_text.configure(
            text=(
                f"{self.analysis_total} / "
                f"{self.analysis_total} — COMPLETE"
            )
        )

        self.progress_title.configure(
            text="ANALYSIS COMPLETE"
        )

        self.system_status_label.configure(
            text="● ANALYSIS COMPLETE",
            fg=GREEN,
        )

        self.analyze_button.configure(
            state="normal",
            text="✓  ANALYSIS COMPLETE — VIEW REPORT",
            bg=GREEN,
            fg="#07130d",
        )

        self.status_var.set(
            "ANALYSIS COMPLETE — Diagnostic evidence generated."
        )

        self._refresh_bearing_map()

        self._update_preview()

        self._show_results(
            fusion_report,
            diagnostic_report,
            recommendation_report,
        )

        # Restore button after opening report
        self.after(
            1000,
            self._restore_analyze_button,
        )

    def _restore_analyze_button(self):

        if not self.analysis_running:

            self.analyze_button.configure(
                state="normal",
                text="▶  ANALYZE MACHINE",
                bg=GREEN,
                fg="#07130d",
            )

    # ========================================================
    # ANALYSIS FAILED
    # ========================================================

    def _analysis_failed(
        self,
        exc,
    ):

        self.analysis_running = False

        self.progress_title.configure(
            text="ANALYSIS FAILED"
        )

        self.progress_text.configure(
            text="ERROR"
        )

        self.system_status_label.configure(
            text="● ANALYSIS ERROR",
            fg=RED,
        )

        self.analyze_button.configure(
            state="normal",
            text="▶  ANALYZE MACHINE",
            bg=GREEN,
            fg="#07130d",
        )

        self.status_var.set(
            "ANALYSIS FAILED — See error message."
        )

        messagebox.showerror(
            "Analysis Error",
            (
                "An error occurred during analysis:\n\n"
                f"{type(exc).__name__}: {exc}"
            ),
        )

    # ========================================================
    # RESULTS WINDOW
    # ========================================================

    def _show_results(
            self,
            fusion_report,
            diagnostic_report,
            recommendation_report,
    ):

        # =====================================================================
        # PRINT EXACT RESULT WINDOW DATA
        # =====================================================================

        print()
        print(
            "#" * 100
        )

        print(
            "# AI CONDITION — RESULT WINDOW"
        )

        print(
            "#" * 100
        )

        received = getattr(
            diagnostic_report,
            "measurements_received",
            len(
                self.measurements
            ),
        )

        expected = getattr(
            diagnostic_report,
            "expected_measurements",
            len(
                self.measurements
            ),
        )

        coverage = getattr(
            diagnostic_report,
            "coverage_percent",
            0,
        )

        directions = getattr(
            diagnostic_report,
            "available_directions",
            [],
        )

        diagnostics = getattr(
            diagnostic_report,
            "diagnostics",
            [],
        )

        missing_slots = getattr(
            diagnostic_report,
            "missing_expected_slots",
            [],
        )

        notes = getattr(
            diagnostic_report,
            "notes",
            [],
        )

        print()

        print(
            "SUMMARY"
        )

        print(
            "-" * 100
        )

        print(
            f"MEASUREMENTS       : "
            f"{received}"
        )

        print(
            f"COVERAGE           : "
            f"{coverage:.1f}%"
        )

        print(
            f"EXPECTED           : "
            f"{expected}"
        )

        print(
            f"DIRECTIONS         : "
            f"{directions}"
        )

        print(
            f"EVIDENCE CANDIDATES: "
            f"{len(diagnostics)}"
        )

        print()

        print(
            "MISSING EXPECTED SLOTS"
        )

        print(
            "-" * 100
        )

        if missing_slots:

            for slot in missing_slots:
                print(
                    f"  {slot}"
                )

        else:

            print(
                "  None"
            )

        print()

        print(
            "DIAGNOSTIC EVIDENCE"
        )

        print(
            "-" * 100
        )

        for index, diagnostic in enumerate(
                diagnostics,
                start=1,
        ):

            print()

            print(
                f"[DIAGNOSTIC {index}]"
            )

            if hasattr(
                    diagnostic,
                    "__dict__"
            ):

                for key, value in (
                        diagnostic.__dict__.items()
                ):
                    print(
                        f"  {key}: {value}"
                    )

            elif isinstance(
                    diagnostic,
                    dict,
            ):

                for key, value in (
                        diagnostic.items()
                ):
                    print(
                        f"  {key}: {value}"
                    )

            else:

                print(
                    f"  {diagnostic}"
                )

        print()

        print(
            "RECOMMENDED NEXT MEASUREMENTS"
        )

        print(
            "-" * 100
        )

        if hasattr(
                recommendation_report,
                "__dict__"
        ):

            for key, value in (
                    recommendation_report.__dict__.items()
            ):
                print(
                    f"{key}: {value}"
                )

        else:

            print(
                recommendation_report
            )

        print()

        print(
            "ANALYSIS NOTES"
        )

        print(
            "-" * 100
        )

        if notes:

            for note in notes:
                print(
                    f"• {note}"
                )

        else:

            print(
                "None"
            )

        print(
            "#" * 100
        )

        try:

            import sys

            sys.stdout.flush()

        except Exception:

            pass

        # =====================================================================
        # CREATE RESULT WINDOW
        # =====================================================================

        window = tk.Toplevel(
            self
        )

        window.title(
            "AI Condition — Diagnostic Results"
        )

        window.geometry(
            "1250x850"
        )

        window.minsize(
            1000,
            700,
        )

        window.configure(
            bg=BG
        )

        # =====================================================================
        # HEADER
        # =====================================================================

        header = tk.Frame(
            window,
            bg="#0c1116",
            height=85,
        )

        header.pack(
            fill="x"
        )

        header.pack_propagate(
            False
        )

        tk.Label(
            header,
            text="AI DIAGNOSTIC REPORT",
            bg="#0c1116",
            fg=WHITE,
            font=(
                "Segoe UI",
                19,
                "bold",
            ),
        ).pack(
            anchor="w",
            padx=25,
            pady=(14, 0),
        )

        tk.Label(
            header,
            text=(
                "Evidence-based condition assessment — "
                "not a confirmed fault declaration"
            ),
            bg="#0c1116",
            fg=TEXT_DIM,
            font=(
                "Segoe UI",
                9,
            ),
        ).pack(
            anchor="w",
            padx=25,
        )

        # =====================================================================
        # SUMMARY
        # =====================================================================

        summary = tk.Frame(
            window,
            bg=BG,
        )

        summary.pack(
            fill="x",
            padx=22,
            pady=18,
        )

        self._result_card(
            summary,
            "MEASUREMENTS",
            str(received),
            "received",
            GREEN,
        )

        self._result_card(
            summary,
            "COVERAGE",
            f"{coverage:.1f}%",
            f"{received}/{expected}",
            BLUE,
        )

        self._result_card(
            summary,
            "DIRECTIONS",
            str(
                len(
                    directions
                )
            ),
            ", ".join(
                directions
            )
            if directions
            else "None",
            PURPLE,
        )

        self._result_card(
            summary,
            "EVIDENCE CANDIDATES",
            str(
                len(
                    diagnostics
                )
            ),
            "mechanisms",
            ORANGE,
        )

        # =====================================================================
        # SCROLL CONTENT
        # =====================================================================

        outer = tk.Frame(
            window,
            bg=BG,
        )

        outer.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=(0, 15),
        )

        canvas = tk.Canvas(
            outer,
            bg=BG,
            highlightthickness=0,
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=canvas.yview,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        body = tk.Frame(
            canvas,
            bg=BG,
        )

        canvas_window = canvas.create_window(
            (0, 0),
            window=body,
            anchor="nw",
        )

        body.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox(
                    "all"
                )
            ),
        )

        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(
                canvas_window,
                width=e.width,
            ),
        )

        # =====================================================================
        # DIAGNOSTICS
        # =====================================================================

        tk.Label(
            body,
            text="DIAGNOSTIC EVIDENCE",
            bg=BG,
            fg=TEXT,
            font=(
                "Segoe UI",
                13,
                "bold",
            ),
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        if diagnostics:

            for diagnostic in diagnostics:
                self._build_diagnostic_card(
                    body,
                    diagnostic,
                )

        else:

            empty_card = tk.Frame(
                body,
                bg=PANEL,
                highlightbackground=BORDER,
                highlightthickness=1,
            )

            empty_card.pack(
                fill="x",
            )

            tk.Label(
                empty_card,
                text=(
                    "No diagnostic candidates were "
                    "generated from the available evidence."
                ),
                bg=PANEL,
                fg=TEXT_DIM,
                font=(
                    "Segoe UI",
                    10,
                ),
                anchor="w",
                justify="left",
            ).pack(
                fill="x",
                padx=18,
                pady=15,
            )

        # =====================================================================
        # RECOMMENDATIONS
        # =====================================================================

        tk.Label(
            body,
            text="RECOMMENDED NEXT MEASUREMENTS",
            bg=BG,
            fg=TEXT,
            font=(
                "Segoe UI",
                13,
                "bold",
            ),
        ).pack(
            anchor="w",
            pady=(20, 8),
        )

        self._build_recommendation_card(
            body,
            recommendation_report,
        )

        # =====================================================================
        # NOTES
        # =====================================================================

        if notes:

            tk.Label(
                body,
                text="ANALYSIS NOTES",
                bg=BG,
                fg=TEXT,
                font=(
                    "Segoe UI",
                    13,
                    "bold",
                ),
            ).pack(
                anchor="w",
                pady=(20, 8),
            )

            card = tk.Frame(
                body,
                bg=PANEL,
                highlightbackground=BORDER,
                highlightthickness=1,
            )

            card.pack(
                fill="x",
            )

            for note in notes:
                tk.Label(
                    card,
                    text=f"• {note}",
                    bg=PANEL,
                    fg=TEXT_DIM,
                    font=(
                        "Segoe UI",
                        9,
                    ),
                    anchor="w",
                    justify="left",
                    wraplength=1050,
                ).pack(
                    fill="x",
                    padx=18,
                    pady=6,
                )

        # =====================================================================
        # FINAL UI STATE TO TERMINAL
        # =====================================================================

        print()
        print(
            "=" * 100
        )

        print(
            "AI CONDITION — RESULT WINDOW DISPLAYED"
        )

        print(
            "=" * 100
        )

        print(
            "The diagnostic result window is now visible to the user."
        )

        print(
            f"Measurements : {received}"
        )

        print(
            f"Coverage     : {coverage:.1f}%"
        )

        print(
            f"Directions   : {directions}"
        )

        print(
            f"Diagnostics  : {len(diagnostics)}"
        )

        print(
            f"Missing slots: {missing_slots}"
        )

        print(
            "=" * 100
        )

        try:

            import sys

            sys.stdout.flush()

        except Exception:

            pass
    # ========================================================
    # RESULT CARD
    # ========================================================

    def _result_card(
        self,
        parent,
        title,
        value,
        subtitle,
        accent,
    ):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5,
        )

        tk.Label(
            card,
            text=title,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8, "bold"),
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 0),
        )

        tk.Label(
            card,
            text=value,
            bg=PANEL,
            fg=accent,
            font=("Segoe UI", 20, "bold"),
        ).pack(
            anchor="w",
            padx=15,
            pady=(2, 0),
        )

        tk.Label(
            card,
            text=subtitle,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
        ).pack(
            anchor="w",
            padx=15,
            pady=(0, 12),
        )

    # ========================================================
    # DIAGNOSTIC CARD
    # ========================================================

    def _build_diagnostic_card(
        self,
        parent,
        diagnostic,
    ):

        mechanism = getattr(
            diagnostic,
            "mechanism",
            "Unknown",
        )

        status = getattr(
            diagnostic,
            "status",
            "UNKNOWN",
        )

        score = getattr(
            diagnostic,
            "evidence_score",
            0,
        )

        support = getattr(
            diagnostic,
            "supporting_measurements",
            [],
        )

        directions = getattr(
            diagnostic,
            "directions",
            [],
        )

        locations = getattr(
            diagnostic,
            "locations",
            [],
        )

        orders = getattr(
            diagnostic,
            "supporting_orders",
            [],
        )

        missing = getattr(
            diagnostic,
            "missing_pattern_orders",
            [],
        )

        database_docs = getattr(
            diagnostic,
            "database_documents",
            [],
        )

        database_contradictions = getattr(
            diagnostic,
            "database_pattern_contradictions",
            [],
        )

        fft_contradictions = getattr(
            diagnostic,
            "actual_fft_contradictions",
            [],
        )

        reasons = getattr(
            diagnostic,
            "reasons",
            [],
        )

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            fill="x",
            pady=6,
        )

        top = tk.Frame(
            card,
            bg=PANEL,
        )

        top.pack(
            fill="x",
            padx=18,
            pady=(14, 8),
        )

        tk.Label(
            top,
            text=mechanism.replace(
                "_",
                " ",
            ).upper(),
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        status_color = GREEN

        if "PARTIAL" in str(
            status
        ).upper():

            status_color = ORANGE

        if "CONTRAD" in str(
            status
        ).upper():

            status_color = RED

        tk.Label(
            top,
            text=str(status),
            bg=PANEL,
            fg=status_color,
            font=("Segoe UI", 9, "bold"),
        ).pack(
            side="right"
        )

        tk.Label(
            top,
            text=f"Evidence {score:.1f}/100",
            bg=PANEL,
            fg=BLUE,
            font=("Segoe UI", 9, "bold"),
        ).pack(
            side="right",
            padx=25,
        )

        tk.Frame(
            card,
            bg=BORDER,
            height=1,
        ).pack(
            fill="x",
            padx=18,
        )

        grid = tk.Frame(
            card,
            bg=PANEL,
        )

        grid.pack(
            fill="x",
            padx=18,
            pady=10,
        )

        self._result_field(
            grid,
            0,
            "Measurements",
            self._format_list(
                support
            ),
        )

        self._result_field(
            grid,
            1,
            "Directions",
            self._format_list(
                directions
            ),
        )

        self._result_field(
            grid,
            2,
            "Locations",
            self._format_list(
                locations
            ),
        )

        self._result_field(
            grid,
            3,
            "Supporting Orders",
            self._format_orders(
                orders
            ),
        )

        self._result_field(
            grid,
            4,
            "Missing Pattern",
            self._format_orders(
                missing
            ),
        )

        self._result_field(
            grid,
            5,
            "Database Documents",
            str(
                len(
                    database_docs
                )
            ),
        )

        self._result_field(
            grid,
            6,
            "Database Contradictions",
            str(
                len(
                    database_contradictions
                )
            ),
        )

        self._result_field(
            grid,
            7,
            "Actual FFT Contradictions",
            str(
                len(
                    fft_contradictions
                )
            ),
        )

        if reasons:

            tk.Label(
                card,
                text="Evidence Reasoning",
                bg=PANEL,
                fg=TEXT,
                font=("Segoe UI", 9, "bold"),
            ).pack(
                anchor="w",
                padx=18,
                pady=(4, 2),
            )

            for reason in reasons:

                tk.Label(
                    card,
                    text=f"• {reason}",
                    bg=PANEL,
                    fg=TEXT_DIM,
                    font=("Segoe UI", 8),
                    justify="left",
                    anchor="w",
                    wraplength=1050,
                ).pack(
                    fill="x",
                    padx=28,
                    pady=2,
                )

        tk.Label(
            card,
            text=(
                "Evidence candidate only — "
                "additional evidence may be required."
            ),
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8, "italic"),
        ).pack(
            anchor="w",
            padx=18,
            pady=(10, 14),
        )

    # ========================================================
    # RESULT FIELD
    # ========================================================

    def _result_field(
        self,
        parent,
        row,
        label,
        value,
    ):

        tk.Label(
            parent,
            text=label,
            bg=PANEL,
            fg=TEXT_DIM,
            font=("Segoe UI", 8),
            width=24,
            anchor="w",
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=3,
        )

        tk.Label(
            parent,
            text=value,
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 8, "bold"),
            anchor="w",
            justify="left",
            wraplength=800,
        ).grid(
            row=row,
            column=1,
            sticky="w",
            pady=3,
        )

    # ========================================================
    # RECOMMENDATION
    # ========================================================

    def _build_recommendation_card(
        self,
        parent,
        recommendation_report,
    ):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1,
        )

        card.pack(
            fill="x",
        )

        recommendations = getattr(
            recommendation_report,
            "recommendations",
            [],
        )

        if not recommendations:

            tk.Label(
                card,
                text=(
                    "No additional measurement "
                    "is currently required."
                ),
                bg=PANEL,
                fg=GREEN,
                font=("Segoe UI", 9, "bold"),
            ).pack(
                anchor="w",
                padx=18,
                pady=16,
            )

            return

        for recommendation in recommendations:

            priority = getattr(
                recommendation,
                "priority",
                "",
            )

            direction = getattr(
                recommendation,
                "direction",
                "",
            )

            targets = getattr(
                recommendation,
                "target_mechanisms",
                [],
            )

            reason = getattr(
                recommendation,
                "reason",
                "",
            )

            row = tk.Frame(
                card,
                bg=PANEL,
            )

            row.pack(
                fill="x",
                padx=18,
                pady=8,
            )

            tk.Label(
                row,
                text=f"PRIORITY {priority}",
                bg=ORANGE_DARK,
                fg=ORANGE,
                font=("Segoe UI", 8, "bold"),
                padx=8,
                pady=4,
            ).pack(
                side="left"
            )

            tk.Label(
                row,
                text=direction,
                bg=PANEL,
                fg=WHITE,
                font=("Segoe UI", 10, "bold"),
            ).pack(
                side="left",
                padx=15,
            )

            tk.Label(
                row,
                text=", ".join(
                    str(x).replace(
                        "_",
                        " ",
                    )
                    for x in targets
                ),
                bg=PANEL,
                fg=TEXT_DIM,
                font=("Segoe UI", 8),
            ).pack(
                side="left",
                padx=10,
            )

            tk.Label(
                card,
                text=reason,
                bg=PANEL,
                fg=TEXT_DIM,
                font=("Segoe UI", 8),
                justify="left",
                anchor="w",
                wraplength=1050,
            ).pack(
                fill="x",
                padx=25,
                pady=(0, 8),
            )

    # ========================================================
    # UTILITIES
    # ========================================================

    def _update_coverage(self):

        try:
            bearing_count = int(
                self.bearing_count_var.get()
            )
        except Exception:
            bearing_count = 1

        bearing_count = max(
            1,
            min(
                bearing_count,
                20,
            ),
        )

        expected = (
            bearing_count * 3
        )

        received = len(
            self.measurements
        )

        percentage = (
            received /
            expected *
            100
            if expected
            else 0
        )

        self.coverage_var.set(
            f"{received} / {expected} measurements"
        )

        self.coverage_percent_var.set(
            f"{percentage:.1f}%"
        )

        self.coverage_progress[
            "value"
        ] = percentage

        h = sum(
            1
            for item in self.measurements.values()
            if item["direction"] == "Horizontal"
        )

        v = sum(
            1
            for item in self.measurements.values()
            if item["direction"] == "Vertical"
        )

        a = sum(
            1
            for item in self.measurements.values()
            if item["direction"] == "Axial"
        )

        self.direction_label.configure(
            text=(
                f"H {h}/{bearing_count}     "
                f"V {v}/{bearing_count}     "
                f"A {a}/{bearing_count}"
            )
        )

    @staticmethod
    def _result_value(
        result,
        key,
        default="—",
    ):

        value = result.get(
            key,
            default,
        )

        if value is None:
            return default

        return str(value)

    @staticmethod
    def _format_number(value):

        if value is None:
            return "—"

        try:

            number = float(value)

            if number.is_integer():
                return str(
                    int(number)
                )

            return f"{number:.3f}"

        except Exception:

            return str(value)

    @staticmethod
    def _format_order(value):

        if value is None:
            return "—"

        if isinstance(
            value,
            str,
        ):

            return value

        try:

            number = float(value)

            if number.is_integer():

                return f"{int(number)}X"

            return f"{number:g}X"

        except Exception:

            return str(value)

    @staticmethod
    def _format_list(value):

        if not value:
            return "—"

        if isinstance(
            value,
            (list, tuple, set),
        ):

            return ", ".join(
                str(item)
                for item in value
            )

        return str(value)

    @staticmethod
    def _format_orders(value):

        if not value:
            return "—"

        result = []

        for item in value:

            if isinstance(
                item,
                dict,
            ):

                item = (
                    item.get("order")
                    or item.get(
                        "order_label"
                    )
                    or item.get("name")
                    or item
                )

            try:

                number = float(item)

                if number.is_integer():

                    result.append(
                        f"{int(number)}X"
                    )

                else:

                    result.append(
                        f"{number:g}X"
                    )

            except Exception:

                text = str(item)

                if not text.endswith("X"):
                    text += "X"

                result.append(
                    text
                )

        return ", ".join(result)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    app = MeasurementManager()

    app.mainloop()

