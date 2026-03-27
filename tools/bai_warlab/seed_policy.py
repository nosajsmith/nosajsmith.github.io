from __future__ import annotations

from typing import Iterable, List

from .models import SeedPolicy


DEFAULT_BASE_SEED = 0


def schedule_seeds(*, runs: int, base_seed: int | None = None) -> List[int]:
    run_count = int(runs)
    if run_count <= 0:
        raise ValueError(f"runs must be positive, got {runs!r}")
    start = DEFAULT_BASE_SEED if base_seed is None else int(base_seed)
    return [start + index for index in range(run_count)]


def resolve_seed_policy(
    *,
    count: int | None = None,
    seed_start: int | None = None,
    seeds: Iterable[int] | None = None,
) -> SeedPolicy:
    if seeds is not None:
        seed_list = [int(value) for value in seeds]
        if not seed_list:
            raise ValueError("explicit seeds must not be empty")
        return SeedPolicy(kind="explicit", seeds=seed_list, base_seed=seed_list[0], count=len(seed_list))

    run_count = int(count or 1)
    scheduled = schedule_seeds(runs=run_count, base_seed=seed_start)
    return SeedPolicy(
        kind="scheduled",
        seeds=scheduled,
        base_seed=DEFAULT_BASE_SEED if seed_start is None else int(seed_start),
        count=run_count,
    )


__all__ = ["DEFAULT_BASE_SEED", "resolve_seed_policy", "schedule_seeds"]
