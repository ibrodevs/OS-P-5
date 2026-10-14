import unittest

from sched import Process, calculate_metrics, simulate


SET1 = [
    Process("P1", 0, 8, 3, 0),
    Process("P2", 1, 4, 1, 1),
    Process("P3", 2, 9, 4, 2),
    Process("P4", 3, 5, 2, 3),
]


class SchedulerTests(unittest.TestCase):
    def assert_avg(self, algo, waiting, turnaround, **params):
        intervals = simulate(SET1, algo, **params)
        metrics = calculate_metrics(SET1, intervals)
        self.assertAlmostEqual(metrics["avg_waiting"], waiting)
        self.assertAlmostEqual(metrics["avg_turnaround"], turnaround)

    def test_fcfs_reference(self):
        self.assert_avg("fcfs", 8.75, 15.25)

    def test_srtf_reference(self):
        self.assert_avg("srtf", 6.5, 13.0)

    def test_rr_q3_reference(self):
        self.assert_avg("rr", 13.5, 20.0, quantum=3)

    def test_rr_boundary_arrival_before_requeue(self):
        ps = [Process("A", 0, 4, 0, 0), Process("B", 2, 1, 0, 1)]
        intervals = simulate(ps, "rr", quantum=2)
        self.assertEqual(
            [(x.start, x.end, x.pid) for x in intervals],
            [(0, 2, "A"), (2, 3, "B"), (3, 5, "A")],
        )

    def test_sjf_nonpreemptive(self):
        ps = [Process("A", 0, 5, 0, 0), Process("B", 1, 1, 0, 1)]
        intervals = simulate(ps, "sjf")
        self.assertEqual(
            [(x.start, x.end, x.pid) for x in intervals],
            [(0, 5, "A"), (5, 6, "B")],
        )

    def test_priority_is_preemptive(self):
        ps = [Process("A", 0, 5, 5, 0), Process("B", 2, 1, 0, 1)]
        intervals = simulate(ps, "priority")
        self.assertEqual(
            [(x.start, x.end, x.pid) for x in intervals],
            [(0, 2, "A"), (2, 3, "B"), (3, 6, "A")],
        )


if __name__ == "__main__":
    unittest.main()
