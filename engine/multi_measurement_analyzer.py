from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from engine.spectrum import Spectrum
from engine.fft_image import FFTImageExtractor
from engine.frequency_engine import analyze_orders
from engine.fault_evidence import build_fault_evidence
from engine.fault_features import build_fault_features
from knowledge_matcher import KnowledgeMatcher


# ============================================================
# Measurement Evidence
# ============================================================

@dataclass
class MeasurementEvidence:
    measurement_id: str
    image_path: str
    bearing: Optional[str]
    direction: Optional[str]
    spectrum: Optional[Spectrum] = None
    order_analysis: Any = None
    fault_evidence: Any = None
    fault_features: Any = None
    database_matches: List[Any] = field(default_factory=list)
    extraction_diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "measurement_id": self.measurement_id,
            "image_path": self.image_path,
            "bearing": self.bearing,
            "direction": self.direction,
            "spectrum": (
                self.spectrum.to_dict()
                if self.spectrum is not None
                else None
            ),
            "order_analysis": self._safe_to_dict(self.order_analysis),
            "fault_evidence": self._safe_to_dict(self.fault_evidence),
            "fault_features": self._safe_to_dict(self.fault_features),
            "database_matches": [
                self._safe_to_dict(x)
                for x in self.database_matches
            ],
            "extraction_diagnostics": self.extraction_diagnostics,
        }

    @staticmethod
    def _safe_to_dict(obj):
        if obj is None:
            return None

        if hasattr(obj, "to_dict"):
            try:
                return obj.to_dict()
            except Exception:
                pass

        if hasattr(obj, "__dict__"):
            try:
                return dict(obj.__dict__)
            except Exception:
                pass

        return obj


# ============================================================
# Multi Measurement Analyzer
# ============================================================

class MultiMeasurementAnalyzer:

    def __init__(
        self,
        rpm: Optional[float] = None,
        machine_name: Optional[str] = None,
        machine_context: Any = None,
        frequency_calibration: Optional[Dict[str, float]] = None,
    ):
        """
        Multi-measurement analyzer.

        IMPORTANT:
        --------------------------------------------------------
        frequency_calibration is OPTIONAL.

        It must NOT be automatically created from RPM.

        Correct flow:

            Image
              ↓
            Extract actual FFT frequencies
              ↓
            Detect / determine frequency scale
              ↓
            Spectrum
              ↓
            Order analysis using RPM

        RPM is used ONLY for order analysis.
        RPM must never be used to manufacture FFT frequencies.
        """

        self.rpm = rpm
        self.machine_name = machine_name
        self.machine_context = machine_context

        # Optional external calibration.
        #
        # This is kept only for cases where the caller has
        # genuinely detected the calibration for this image.
        #
        # There is NO default calibration here.
        self.frequency_calibration = (
            dict(frequency_calibration)
            if frequency_calibration
            else None
        )

        self.measurements: List[MeasurementEvidence] = []

        self.matcher = KnowledgeMatcher()

    # ========================================================
    # Logging
    # ========================================================

    def _log(self, message: str):
        print(f"[MultiMeasurementAnalyzer] {message}")

    # ========================================================
    # Helpers
    # ========================================================

    @staticmethod
    def _safe_float(value, default=None):
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _get_peak_frequency(peak):
        """
        Supports both old and new Peak implementations.

        Preferred field:
            frequency_hz

        Legacy fallback:
            frequency
        """

        frequency = getattr(peak, "frequency_hz", None)

        if frequency is None:
            frequency = getattr(peak, "frequency", None)

        return frequency

    @staticmethod
    def _get_peak_amplitude(peak):
        return getattr(peak, "amplitude", None)

    @staticmethod
    def _get_peak_prominence(peak):
        return getattr(peak, "prominence", None)

    # ========================================================
    # Print Spectrum Peaks
    # ========================================================

    def _print_spectrum(self, spectrum: Spectrum):

        print()
        print("=" * 75)
        print("IMAGE → SPECTRUM")
        print("=" * 75)

        if spectrum is None:
            print("Spectrum: None")
            print("=" * 75)
            return

        peaks = getattr(spectrum, "peaks", []) or []

        if not peaks:
            print("No peaks extracted.")
            print("=" * 75)
            return

        print()
        print(f"{'Frequency (Hz)':<20}{'Amplitude':<20}")
        print("-" * 40)

        for peak in peaks:

            frequency = self._get_peak_frequency(peak)
            amplitude = self._get_peak_amplitude(peak)

            print(
                f"{str(frequency):<20}"
                f"{str(amplitude):<20}"
            )

        print("=" * 75)

    # ========================================================
    # Extract One Image
    # ========================================================

    def analyze_image(
        self,
        image_path: str,
        bearing: Optional[str] = None,
        direction: Optional[str] = None,
        measurement_id: Optional[str] = None,
        rpm: Optional[float] = None,
        machine_name: Optional[str] = None,
    ) -> MeasurementEvidence:

        image_path = str(Path(image_path))

        if not Path(image_path).exists():
            raise FileNotFoundError(
                f"FFT image not found: {image_path}"
            )

        current_rpm = (
            self._safe_float(rpm)
            if rpm is not None
            else self._safe_float(self.rpm)
        )

        current_machine_name = (
            machine_name
            if machine_name is not None
            else self.machine_name
        )

        if measurement_id is None:

            measurement_id = (
                f"{bearing or 'UnknownBearing'}_"
                f"{direction or 'UnknownDirection'}"
            )

        self._log(
            f"Analyzing image: {image_path}"
        )

        self._log(
            f"Bearing={bearing}, "
            f"Direction={direction}, "
            f"RPM={current_rpm}"
        )

        # ====================================================
        # 1. Create extractor
        # ====================================================

        extractor = FFTImageExtractor(image_path)

        # ====================================================
        # 2. Apply calibration ONLY if explicitly supplied
        # ====================================================

        if self.frequency_calibration:

            slope = self.frequency_calibration.get(
                "slope_hz_per_pixel"
            )

            intercept = self.frequency_calibration.get(
                "intercept_hz"
            )

            if (
                slope is not None
                and intercept is not None
            ):

                self._log(
                    "Using externally supplied "
                    "frequency calibration."
                )

                extractor.set_frequency_calibration(
                    slope_hz_per_pixel=float(slope),
                    intercept_hz=float(intercept),
                )

            else:

                self._log(
                    "WARNING: Invalid frequency calibration. "
                    "Ignoring it."
                )

        else:

            self._log(
                "No external frequency calibration supplied."
            )

            self._log(
                "Frequency must be determined by the "
                "image extractor itself."
            )

        # ====================================================
        # 3. IMAGE → SPECTRUM
        # ====================================================

        spectrum = extractor.create_spectrum_from_image(
            rpm=current_rpm,
            machine_name=current_machine_name,
            measurement_point=bearing,
            direction=direction,
        )

        # ====================================================
        # 4. Print extracted spectrum
        # ====================================================

        self._print_spectrum(spectrum)

        # ====================================================
        # 5. Extraction diagnostics
        # ====================================================

        extraction_diagnostics = {}

        try:
            debug_data = extractor.get_debug_data()

            if isinstance(debug_data, dict):
                extraction_diagnostics = debug_data

        except Exception as exc:

            extraction_diagnostics = {
                "debug_error": str(exc)
            }

        # ====================================================
        # 6. Validate spectrum
        # ====================================================

        if spectrum is None:

            raise ValueError(
                f"FFT extraction returned None for: "
                f"{image_path}"
            )

        try:
            spectrum.validate()

        except Exception as exc:

            self._log(
                f"Spectrum validation warning: {exc}"
            )

        peaks = getattr(
            spectrum,
            "peaks",
            []
        ) or []

        # ====================================================
        # 7. IMPORTANT SAFETY CHECK
        #
        # Do not perform order analysis if there are
        # no actual frequency peaks.
        #
        # This prevents fake order information.
        # ====================================================

        valid_peak_count = 0

        for peak in peaks:

            frequency = self._safe_float(
                self._get_peak_frequency(peak)
            )

            amplitude = self._safe_float(
                self._get_peak_amplitude(peak)
            )

            if (
                frequency is not None
                and frequency >= 0
                and amplitude is not None
            ):
                valid_peak_count += 1

        order_result = None
        fault_evidence = None
        fault_features = None
        database_matches = []

        # ====================================================
        # 8. ORDER ANALYSIS
        # ====================================================

        if current_rpm is None or current_rpm <= 0:

            self._log(
                "RPM unavailable/invalid."
            )

            self._log(
                "Order analysis skipped."
            )

        elif valid_peak_count == 0:

            self._log(
                "No valid frequency peaks extracted."
            )

            self._log(
                "Order analysis skipped."
            )

        else:

            self._log(
                f"Running order analysis on "
                f"{valid_peak_count} valid peaks."
            )

            try:

                order_result = analyze_orders(
                    spectrum,
                    rpm=current_rpm,
                    max_order=10,
                    rpm_tolerance=10,
                    percent_tolerance=3.0,
                )

            except TypeError:

                # Compatibility fallback for versions where
                # analyze_orders uses a different signature.

                try:

                    order_result = analyze_orders(
                        spectrum,
                        current_rpm,
                    )

                except Exception as exc:

                    self._log(
                        f"Order analysis failed: {exc}"
                    )

                    order_result = None

            except Exception as exc:

                self._log(
                    f"Order analysis failed: {exc}"
                )

                order_result = None

        # ====================================================
        # 9. FAULT EVIDENCE
        # ====================================================

        if order_result is not None:

            try:

                fault_evidence = build_fault_evidence(
                    order_result
                )

            except TypeError:

                try:

                    fault_evidence = build_fault_evidence(
                        spectrum=spectrum,
                        order_analysis=order_result,
                    )

                except Exception as exc:

                    self._log(
                        f"Fault evidence failed: {exc}"
                    )

            except Exception as exc:

                self._log(
                    f"Fault evidence failed: {exc}"
                )

        # ====================================================
        # 10. FAULT FEATURES
        # ====================================================

        if fault_evidence is not None:

            try:

                fault_features = build_fault_features(
                    fault_evidence
                )

            except TypeError:

                try:

                    fault_features = build_fault_features(
                        spectrum=spectrum,
                        fault_evidence=fault_evidence,
                    )

                except Exception as exc:

                    self._log(
                        f"Fault feature extraction failed: {exc}"
                    )

            except Exception as exc:

                self._log(
                    f"Fault feature extraction failed: {exc}"
                )

        # ====================================================
        # 11. DATABASE MATCHING
        # ====================================================

        if (
            fault_features is not None
            or fault_evidence is not None
        ):

            try:

                database_matches = (
                    self.matcher.match(
                        fault_features
                        if fault_features is not None
                        else fault_evidence
                    )
                )

                if database_matches is None:
                    database_matches = []

                if not isinstance(
                    database_matches,
                    list
                ):
                    database_matches = list(
                        database_matches
                    )

            except Exception as exc:

                self._log(
                    f"Database matching failed: {exc}"
                )

                database_matches = []

        # ====================================================
        # 12. Create Measurement Evidence
        # ====================================================

        measurement = MeasurementEvidence(
            measurement_id=measurement_id,
            image_path=image_path,
            bearing=bearing,
            direction=direction,
            spectrum=spectrum,
            order_analysis=order_result,
            fault_evidence=fault_evidence,
            fault_features=fault_features,
            database_matches=database_matches,
            extraction_diagnostics=extraction_diagnostics,
        )

        # ====================================================
        # 13. Store
        # ====================================================

        self.measurements.append(
            measurement
        )

        self._log(
            f"Measurement stored: {measurement_id}"
        )

        return measurement

    # ========================================================
    # Add Existing Measurement
    # ========================================================

    def add_measurement(
        self,
        measurement: MeasurementEvidence
    ):

        if measurement is None:
            return

        self.measurements.append(
            measurement
        )

    # ========================================================
    # Analyze Multiple Images
    # ========================================================

    def analyze_images(
        self,
        measurements: List[Dict[str, Any]]
    ) -> List[MeasurementEvidence]:

        results = []

        for item in measurements:

            if not isinstance(item, dict):
                continue

            image_path = item.get(
                "image_path"
            )

            if not image_path:
                continue

            result = self.analyze_image(
                image_path=image_path,
                bearing=item.get("bearing"),
                direction=item.get("direction"),
                measurement_id=item.get(
                    "measurement_id"
                ),
                rpm=item.get("rpm"),
                machine_name=item.get(
                    "machine_name"
                ),
            )

            results.append(result)

        return results

    # ========================================================
    # Print Measurement Summary
    # ========================================================

    def print_measurement_summary(self):

        print()
        print("=" * 75)
        print("MULTI-MEASUREMENT SUMMARY")
        print("=" * 75)

        print(
            f"Measurements received: "
            f"{len(self.measurements)}"
        )

        print()

        if not self.measurements:

            print("No measurements.")
            print("=" * 75)
            return

        for index, measurement in enumerate(
            self.measurements,
            start=1
        ):

            spectrum = measurement.spectrum

            peaks = (
                getattr(
                    spectrum,
                    "peaks",
                    []
                )
                if spectrum is not None
                else []
            )

            print(
                f"{index:3d}. "
                f"{measurement.measurement_id:<25} "
                f"Bearing={str(measurement.bearing):<8} "
                f"Direction={str(measurement.direction):<10} "
                f"Peaks={len(peaks)}"
            )

        print("=" * 75)

    # ========================================================
    # FUSE
    # ========================================================

    def fuse(
        self,
        expected_measurements: Optional[int] = None,
        expected_slots: Optional[List[Any]] = None,
    ):
        """
        Run multi-measurement evidence fusion.

        This function intentionally does NOT assume that a
        missing measurement means "healthy".

        Missing measurements are simply missing evidence.
        """

        self.print_measurement_summary()

        # Import lazily to avoid circular imports.
        from evidence_fusion import EvidenceFusionEngine

        engine = EvidenceFusionEngine(
            measurements=self.measurements,
            expected_slots=expected_slots,
        )

        report = engine.fuse(
            expected_measurements=expected_measurements,
            expected_slots=expected_slots,
        )

        return report

    # ========================================================
    # Get Measurements
    # ========================================================

    def get_measurements(self) -> List[MeasurementEvidence]:

        return list(
            self.measurements
        )

    # ========================================================
    # Clear
    # ========================================================

    def clear(self):

        self.measurements.clear()

        self._log(
            "All measurements cleared."
        )