from __future__ import annotations

from .config import V1SimulationConfig


def run_v1_simulation(config: V1SimulationConfig):
    raise RuntimeError(
        "run_v1_simulation has been deprecated; use scsp.engine.run_simulation "
        "or scsp.astra_sim_bridge.run_astra_simulation."
    )
