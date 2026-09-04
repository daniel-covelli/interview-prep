# Problem 2: Video View Analytics
#
# You're building view analytics for a video platform. Record individual
# video views as they happen and return the top k most-watched videos, where
# k is a flexible input. Also support the same query restricted to a recent
# time window ("top k in the last hour").
#
#   va.record_view(video_id, timestamp)   one view at integer timestamp
#                                         (seconds; may arrive out of order)
#   va.top_k(k)                           all-time [(video_id, views)],
#                                         most viewed first
#   va.top_k_windowed(k, window, now)     same, but only counting views with
#                                         now - window < timestamp <= now
#
# Same k rules as Problem 1 (0 -> [], negative -> ValueError, ties in any
# order).
#
# Example:
#   va = VideoAnalytics()
#   va.record_view("cats", 100)
#   va.record_view("dogs", 130)
#   va.record_view("cats", 160)
#   va.record_view("cats", 240)
#   va.top_k(2)                     -> [("cats", 3), ("dogs", 1)]
#   va.top_k_windowed(2, 120, 250)  -> [("cats", 2)]   # only views in (130, 250]
#   va.top_k_windowed(5, 30, 300)   -> []
import bisect
from collections import Counter
from prep_lib import run_test_cases

class VideoAnalytics:
    def __init__(self):
        self.views = []
        self.is_sorted = False

    def record_view(self, video_id: str, timestamp: int):
        self.is_sorted = False
        self.views.append((timestamp, video_id))

    def top_k(self, k: int):
        if k < 0: raise ValueError

        self.__sort()

        return self.__top_k(k)

    def top_k_windowed(self, k: int, window: int, now: int):
        if k < 0: raise ValueError

        self.__sort()

        left = now - window
        lo = bisect.bisect_left(self.views, left, key=lambda x: x[0])

        while lo < len(self.views) and self.views[lo][0] == left: 
            lo += 1

        hi = bisect.bisect_right(self.views, now, key=lambda x: x[0])

        return self.__top_k(k, lo, hi)

    def __top_k(self, k:int, lo: int | None = None, hi: int | None = None):
        lo_i = lo if lo is not None else 0
        hi_i = hi if hi is not None else len(self.views)

        window = [item for _, item in self.views[lo_i:hi_i]]
        counts = Counter(window)

        top_k = counts.most_common(k)

        return top_k

    def __sort(self):
        if not self.is_sorted:
            self.views.sort(key=lambda x: x[0])
            self.is_sorted = True


if __name__ == "__main__":
    test_cases = [ 
        [
            ("record_view", ("cats", 100), None),
            ("record_view", ("dogs", 130), None),
            ("record_view", ("cats", 160), None),
            ("record_view", ("cats", 240), None),
            ("top_k_windowed", (2, 40, 130), [("cats", 1), ("dogs", 1)]),
            ("top_k", (2,), [("cats", 3), ("dogs", 1)]),
            ("top_k_windowed", (2, 120, 250), [("cats", 2)]),
        ],
        [
            ("record_view", ("v", 500), None),
            ("record_view", ("v", 100), None),
            ("record_view", ("v", 300), None),
            ("record_view", ("v", 200), None),
            ("record_view", ("v", 400), None),
            ("record_view", ("v", 100), None),
            ("record_view", ("w", 250), None),
            ("top_k", (2,), [("v", 6), ("w", 1)]),
            ("top_k_windowed", (5, 200, 450), [("v", 2)]),
        ],
    ]

    run_test_cases(test_cases, VideoAnalytics)