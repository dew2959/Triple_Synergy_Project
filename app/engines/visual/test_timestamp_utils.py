import unittest
from app.engines.visual.timestamp_utils import compute_timestamp_ms


class TestTimestampUtils(unittest.TestCase):
    def test_base_alignment_nonzero_start(self):
        base = None
        prev = -1

        ts, base, prev = compute_timestamp_ms(
            raw_pos_msec=250.0, pos_frames=0, fps=30.0,
            base_ts_ms=base, prev_ts_ms=prev
        )
        self.assertEqual(ts, 0)

        ts2, base, prev = compute_timestamp_ms(
            raw_pos_msec=283.3, pos_frames=1, fps=30.0,
            base_ts_ms=base, prev_ts_ms=prev
        )
        self.assertGreater(ts2, ts)

    def test_pos_msec_goes_backward_strict_increasing(self):
        base = None
        prev = -1

        ts1, base, prev = compute_timestamp_ms(
            raw_pos_msec=100.0, pos_frames=0, fps=30.0,
            base_ts_ms=base, prev_ts_ms=prev
        )
        ts2, base, prev = compute_timestamp_ms(
            raw_pos_msec=133.3, pos_frames=1, fps=30.0,
            base_ts_ms=base, prev_ts_ms=prev
        )
        ts3, base, prev = compute_timestamp_ms(
            raw_pos_msec=120.0, pos_frames=2, fps=30.0,
            base_ts_ms=base, prev_ts_ms=prev
        )
        self.assertEqual(ts3, ts2 + 1)

    def test_pos_msec_same_value_multiple_times(self):
        base = None
        prev = -1

        ts1, base, prev = compute_timestamp_ms(
            raw_pos_msec=100.0, pos_frames=0, fps=30.0,
            base_ts_ms=base, prev_ts_ms=prev
        )
        ts2, base, prev = compute_timestamp_ms(
            raw_pos_msec=100.0, pos_frames=0, fps=30.0,
            base_ts_ms=base, prev_ts_ms=prev
        )
        ts3, base, prev = compute_timestamp_ms(
            raw_pos_msec=100.0, pos_frames=0, fps=30.0,
            base_ts_ms=base, prev_ts_ms=prev
        )
        self.assertEqual((ts1, ts2, ts3), (0, 1, 2))

    def test_invalid_fps_raises(self):
        with self.assertRaises(ValueError):
            compute_timestamp_ms(
                raw_pos_msec=100.0, pos_frames=0, fps=0.0,
                base_ts_ms=None, prev_ts_ms=-1
            )


if __name__ == "__main__":
    unittest.main()
