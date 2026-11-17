"""When a Site counts as sloped or steep (one definition; read through ``SiteContext``)."""

from __future__ import annotations

#: Relief (metres) from which a Site is sloped: the interview asks how the house meets
#: the slope and the program needs a slope strategy.
SLOPED_MIN_RELIEF_M = 2.0
#: Relief (metres) from which a Site is steep (agent contract §7: hillside construction).
STEEP_MIN_RELIEF_M = 8.0
#: Mean slope inside the parcel (percent) from which a Site is steep, whatever its relief.
STEEP_MIN_MEAN_SLOPE_PCT = 20.0
