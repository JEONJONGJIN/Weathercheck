import os
import unittest
from datetime import datetime

import weather_core as app


class FixedLocationTests(unittest.TestCase):
    def test_configured_location_uses_environment_coordinates(self) -> None:
        original_lat = os.environ.get("WEATHERCHECK_LATITUDE")
        original_lon = os.environ.get("WEATHERCHECK_LONGITUDE")
        try:
            os.environ["WEATHERCHECK_LATITUDE"] = "37.1234"
            os.environ["WEATHERCHECK_LONGITUDE"] = "127.5678"
            location = app.configured_location()
            self.assertEqual(location.display_name, app.FIXED_LOCATION_LABEL)
            self.assertEqual(location.latitude, 37.1234)
            self.assertEqual(location.longitude, 127.5678)
        finally:
            if original_lat is None:
                os.environ.pop("WEATHERCHECK_LATITUDE", None)
            else:
                os.environ["WEATHERCHECK_LATITUDE"] = original_lat
            if original_lon is None:
                os.environ.pop("WEATHERCHECK_LONGITUDE", None)
            else:
                os.environ["WEATHERCHECK_LONGITUDE"] = original_lon

    def test_configured_location_requires_coordinates(self) -> None:
        original_lat = os.environ.get("WEATHERCHECK_LATITUDE")
        original_lon = os.environ.get("WEATHERCHECK_LONGITUDE")
        try:
            os.environ.pop("WEATHERCHECK_LATITUDE", None)
            os.environ.pop("WEATHERCHECK_LONGITUDE", None)
            location = app.configured_location()
            self.assertEqual(location.latitude, app.DEFAULT_LATITUDE)
            self.assertEqual(location.longitude, app.DEFAULT_LONGITUDE)
        finally:
            if original_lat is not None:
                os.environ["WEATHERCHECK_LATITUDE"] = original_lat
            if original_lon is not None:
                os.environ["WEATHERCHECK_LONGITUDE"] = original_lon


class HelpersTests(unittest.TestCase):
    def test_summarize_window_returns_max(self) -> None:
        self.assertEqual(app.summarize_window([10, None, 42, 18]), 42)

    def test_summarize_temperature_returns_min_and_max(self) -> None:
        self.assertEqual(app.summarize_temperature([4, None, 9, -2]), (-2, 9))

    def test_numeric_spread_returns_difference(self) -> None:
        self.assertEqual(app.numeric_spread([4, None, 9, -2]), 11)

    def test_sample_every_n_rows_limits_output(self) -> None:
        rows = [{"time": str(index)} for index in range(24)]
        sampled = app.sample_every_n_rows(rows, target_count=8)
        self.assertEqual(len(sampled), 8)

    def test_sample_every_3_hours_keeps_three_hour_spacing(self) -> None:
        rows = [{"time": str(index)} for index in range(24)]
        sampled = app.sample_every_3_hours(rows, target_count=8)
        self.assertEqual(len(sampled), 8)
        self.assertEqual(sampled[1]["time"], "3")

    def test_translate_condition_text_returns_korean(self) -> None:
        self.assertEqual(app.translate_condition_text("Patchy rain nearby"), "주변에 비 가능성")
        self.assertEqual(app.translate_condition_text("Heavy snow"), "강한 눈")

    def test_translate_met_symbol_returns_korean(self) -> None:
        self.assertEqual(app.translate_met_symbol("partlycloudy_day"), "구름 조금")
        self.assertEqual(app.translate_met_symbol("rainshowers_day"), "소나기")

    def test_kma_grid_from_lat_lon_returns_integer_grid(self) -> None:
        nx, ny = app.kma_grid_from_lat_lon(37.9851297299633, 126.886246142811)
        self.assertIsInstance(nx, int)
        self.assertIsInstance(ny, int)

    def test_kma_condition_text_prefers_precipitation(self) -> None:
        self.assertEqual(app.kma_condition_text("1", "0"), "맑음")
        self.assertEqual(app.kma_condition_text("4", "1"), "비")

    def test_latest_kma_mid_base_datetime_returns_supported_cycle(self) -> None:
        value = app.latest_kma_mid_base_datetime()
        self.assertEqual(len(value), 12)
        self.assertIn(value[8:10], {"06", "18"})

    def test_wind_direction_text_maps_degrees_to_compass(self) -> None:
        self.assertEqual(app.wind_direction_text("0"), "북")
        self.assertEqual(app.wind_direction_text("90"), "동")

    def test_windy_precip_type_text_maps_codes(self) -> None:
        self.assertEqual(app.windy_precip_type_text(1), "비")
        self.assertIsNone(app.windy_precip_type_text(0))

    def test_future_timeline_rows_filters_past_entries(self) -> None:
        now = datetime(2026, 3, 16, 10, 30, tzinfo=app.KST)
        rows = [
            {"time": "2026-03-16T09:00", "temperature_c": "1.0", "precip_probability": "0.0"},
            {"time": "2026-03-16T11:00", "temperature_c": "2.0", "precip_probability": "10.0"},
            {"time": "2026-03-16T12:00", "temperature_c": "3.0", "precip_probability": "20.0"},
        ]
        filtered = app.future_timeline_rows(rows, now=now)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["time"], "2026-03-16T11:00")

    def test_active_providers_for_app_includes_both_kma_sources(self) -> None:
        original_data_key = os.environ.get("DATA_GO_KR_SERVICE_KEY")
        original_apihub_key = os.environ.get("KMA_APIHUB_AUTH_KEY")
        try:
            os.environ["DATA_GO_KR_SERVICE_KEY"] = "data-key"
            os.environ["KMA_APIHUB_AUTH_KEY"] = "hub-key"
            providers = app.active_providers_for_app()
            provider_names = [name for name, _ in providers]
            self.assertIn("기상청 단기예보(data.go.kr)", provider_names)
            self.assertIn("기상청 단기예보(API 허브)", provider_names)
        finally:
            if original_data_key is None:
                os.environ.pop("DATA_GO_KR_SERVICE_KEY", None)
            else:
                os.environ["DATA_GO_KR_SERVICE_KEY"] = original_data_key
            if original_apihub_key is None:
                os.environ.pop("KMA_APIHUB_AUTH_KEY", None)
            else:
                os.environ["KMA_APIHUB_AUTH_KEY"] = original_apihub_key

    def test_parse_kma_apihub_grid_value_reads_expected_cell(self) -> None:
        row = ",".join(str(index) for index in range(149))
        raw_text = ",\n".join([row] * 253)
        value = app.parse_kma_apihub_grid_value(raw_text, nx=61, ny=133)
        self.assertEqual(value, 60.0)

    def test_active_providers_for_app_includes_openweather(self) -> None:
        original_key = os.environ.get("OPENWEATHER_API_KEY")
        try:
            os.environ["OPENWEATHER_API_KEY"] = "owm-key"
            providers = app.active_providers_for_app()
            provider_names = [name for name, _ in providers]
            self.assertIn("OpenWeather", provider_names)
        finally:
            if original_key is None:
                os.environ.pop("OPENWEATHER_API_KEY", None)
            else:
                os.environ["OPENWEATHER_API_KEY"] = original_key


class ConsensusTests(unittest.TestCase):
    def test_build_consensus_aggregates_summary_and_timeline(self) -> None:
        providers = [
            {
                "provider": "A",
                "current_temp_c": "10.0",
                "next_6h_precip_probability": "20.0",
                "timeline": [
                    {"time": "2026-03-16T00:00:00+00:00", "temperature_c": "10.0", "precip_probability": "20.0"},
                    {"time": "2026-03-16T03:00:00+00:00", "temperature_c": "11.0", "precip_probability": "30.0"},
                ],
            },
            {
                "provider": "B",
                "current_temp_c": "16.0",
                "next_6h_precip_probability": "50.0",
                "timeline": [
                    {"time": "2026-03-16T00:00:00+00:00", "temperature_c": "14.0", "precip_probability": "40.0"},
                    {"time": "2026-03-16T03:00:00+00:00", "temperature_c": "13.0", "precip_probability": "35.0"},
                ],
            },
            {"provider": "C", "error": "failed"},
        ]
        consensus = app.build_consensus(providers)
        self.assertEqual(consensus["successful_provider_count"], 2)
        self.assertEqual(consensus["failed_provider_count"], 1)
        self.assertEqual(consensus["current_temp_spread_c"], "6.0")
        self.assertEqual(consensus["next_6h_precip_spread_probability"], "30.0")
        self.assertEqual(consensus["timeline"][0]["temperature_spread_c"], "4.0")
        self.assertEqual(consensus["timeline"][0]["precip_spread_probability"], "20.0")


if __name__ == "__main__":
    unittest.main()
