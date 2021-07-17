from abc import ABC

from ztrack.tracking.params import Params
from ztrack.tracking.tracker import Tracker


class TailParams(Params):
    pass


class TailTracker(Tracker, ABC):
    pass
