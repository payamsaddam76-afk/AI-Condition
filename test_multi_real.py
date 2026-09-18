
from engine.multi_measurement_analyzer import MultiMeasurementAnalyzer
from database_engine import MachineContext

from engine.diagnostic_engine import (
    AIDiagnosticEngine,
    print_diagnostic_report,
)

from engine.measurement_recommender import (
    MeasurementRecommendationEngine,
    print_recommendation_report,
)
# ============================================================
# SETTINGS
# ============================================================

RPM = 1500

FREQUENCY_CALIBRATION = {
    "slope_hz_per_pixel": 0.60604178,
    "intercept_hz": -242.22631,
}


# ============================================================
# MACHINE CONTEXT
# ============================================================

context = MachineContext(
    equipment_type="Electric Motor",
    equipment_category="Rotating Machinery",
    brand="Test",
    model="Test Model",

    rpm=RPM,

    connection_type="Coupling",
    transmission_type="Direct Coupled",

    bearing_count=4,

    bearings=[
        "Rolling Element Bearing",
        "Rolling Element Bearing",
        "Rolling Element Bearing",
        "Rolling Element Bearing",
    ],

    measurement_point="Motor DE",
    direction="Horizontal",

    sensor_type="Accelerometer",
    analysis_mode="FFT",
)


# ============================================================
# CREATE ANALYZER
# ============================================================

analyzer = MultiMeasurementAnalyzer(
    rpm=RPM,

    machine_context=context,

    max_order=10,

    rpm_tolerance=10,

    percent_tolerance=3.0,

    frequency_calibration=FREQUENCY_CALIBRATION,
)


# ============================================================
# TEST MEASUREMENTS
# ============================================================

measurements = [

    {
        "id": "B1-H",
        "image": "test_fft.png",
        "bearing": "B1",
        "point": "Bearing 1",
        "direction": "Horizontal",
        "component": "Fan",
    },

    {
        "id": "B1-V",
        "image": "test_fft.png",
        "bearing": "B1",
        "point": "Bearing 1",
        "direction": "Vertical",
        "component": "Fan",
    },

    {
        "id": "B2-H",
        "image": "test_fft.png",
        "bearing": "B2",
        "point": "Bearing 2",
        "direction": "Horizontal",
        "component": "Fan",
    },

    {
        "id": "B2-V",
        "image": "test_fft.png",
        "bearing": "B2",
        "point": "Bearing 2",
        "direction": "Vertical",
        "component": "Fan",
    },
]


# ============================================================
# ANALYZE ALL MEASUREMENTS
# ============================================================

for item in measurements:

    analyzer.add_measurement(
        image_path=item["image"],

        measurement_id=item["id"],

        bearing_id=item["bearing"],

        point=item["point"],

        direction=item["direction"],

        component=item["component"],

        machine_name="Test Machine",

        sensor_type="Accelerometer",
    )


# ============================================================
# PRINT MEASUREMENTS
# ============================================================

analyzer.print_measurements()


# ============================================================
# MULTI-MEASUREMENT FUSION
# ============================================================

report = analyzer.fuse(
    expected_measurements=12
)


print()
print("=" * 75)
print("FINAL MULTI-MEASUREMENT FUSION")
print("=" * 75)


print(
    f"Measurements received : "
    f"{report.measurements_received}"
)


print(
    f"Expected measurements : "
    f"{report.expected_measurements}"
)


coverage = report.machine_measurement_coverage


print(
    f"Coverage              : "
    f"{report.measurements_received}/"
    f"{report.expected_measurements} "
    f"({coverage:.1f}%)"
)


for candidate in report.candidates:

    print(
        f"{candidate.mechanism:20} "
        f"{candidate.status:22} "
        f"support={candidate.support_count}"
    )


# ============================================================
# AI DIAGNOSTIC ENGINE
# ============================================================
diagnostic_engine = AIDiagnosticEngine()

diagnostic_report = diagnostic_engine.diagnose(
    report
)

print_diagnostic_report(
    diagnostic_report
)


# ============================================================
# ADDITIONAL MEASUREMENT RECOMMENDATION
# ============================================================

recommendation_engine = MeasurementRecommendationEngine()

recommendation_report = recommendation_engine.recommend(
    fusion_report=report,
    diagnostic_report=diagnostic_report,
)

print_recommendation_report(
    recommendation_report
)