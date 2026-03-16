import unittest

import weather_core as app


class ParseLatLonTests(unittest.TestCase):
    def test_accepts_valid_coordinates(self) -> None:
        self.assertEqual(app.parse_lat_lon("37.5665,126.9780"), (37.5665, 126.978))

    def test_rejects_invalid_coordinates(self) -> None:
        self.assertIsNone(app.parse_lat_lon("200,100"))


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
