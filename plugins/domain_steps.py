# FILE: antsim/plugins/doamin_steps.py
# FILE: antsim/plugins/domain_steps.py
"""Domain-specific steps as intent producers (pure).

Provides core ant behaviors from the legacy system, reimplemented as
pure intent-producing steps compatible with the new architecture.

Design:
- Pure functions: read worker/environment/BB, produce intents only
- No world mutation; execution happens via IntentExecutor
- Clear logging of decisions and context
- Idempotent within a tick
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from pluggy import HookimplMarker

# Tolerant imports for intents
try:
    from ..core.executor import MoveIntent, DepositPheromoneIntent, FeedIntent, CustomIntent
except Exception:
    MoveIntent = None  # type: ignore
    DepositPheromoneIntent = None  # type: ignore
    FeedIntent = None  # type: ignore
    CustomIntent = None  # type: ignore

hookimpl = HookimplMarker("antsim")
log = logging.getLogger(__name__)


@hookimpl
def register_steps() -> Dict[str, callable]:
    """Expose domain steps."""
    return {
        "leave_nest": leave_nest_step,
        "enter_nest": enter_nest_step,
        "search_food_randomly": search_food_randomly_step,
        "collect_food": collect_food_step,
        "return_to_nest": return_to_nest_step,
        # pure intent-only neighbor feeding step (domain)
        "feed_neighbor": feed_neighbor_step,
        # migration Step 12 - reimplement domain steps as pure intent producers
        "move_to_food": move_to_food_step,
        "follow_pheromone": follow_pheromone_step,
        # deadlock resolver for mutual feeding
        "resolve_mutual_feeding": resolve_mutual_feeding_step,
    }


# --------- Helpers (pure) ---------

def _bb_get(bb_or_worker: Any, key: str, default=None):
    """Safe getter for blackboard or worker attributes."""
    # Try blackboard first
    bb = getattr(bb_or_worker, "blackboard", None)
    if bb and hasattr(bb, "get"):
        try:
            return bb.get(key, default)
        except Exception:
            pass
    # Fallback to direct attribute
    return getattr(bb_or_worker, key, default)


def _bb_pos(worker: Any) -> Tuple[int, int]:
    """Get worker position from blackboard or attributes."""
    pos = _bb_get(worker, "position", [0, 0])
    if isinstance(pos, (list, tuple)) and len(pos) == 2:
        return int(pos[0]), int(pos[1])
    return 0, 0


def _env_bounds(env: Any) -> Optional[Tuple[int, int]]:
    """Get environment bounds if available."""
    w = getattr(env, "width", None)
    h = getattr(env, "height", None)
    if isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0:
        return w, h
    return None


def _in_bounds(pos: Tuple[int, int], bounds: Optional[Tuple[int, int]]) -> bool:
    """Check if position is within bounds."""
    if not bounds:
        return True
    x, y = pos
    w, h = bounds
    return 0 <= x < w and 0 <= y < h


def _get_cell_type(env: Any, pos: Tuple[int, int]) -> Optional[str]:
    """Get cell type at position."""
    try:
        if hasattr(env, "grid"):
            x, y = pos
            cell = env.grid[y][x]
            return getattr(cell, "cell_type", None)
    except Exception:
        pass
    return None


def _is_cell_free(env: Any, pos: Tuple[int, int]) -> bool:
    """Check if cell is free (no wall, no ant)."""
    try:
        if hasattr(env, "grid"):
            x, y = pos
            cell = env.grid[y][x]
            if hasattr(cell, "cell_type") and getattr(cell, "cell_type") in ("w", "wall"):
                return False
            if hasattr(cell, "ant") and getattr(cell, "ant") is not None:
                return False
            return True
    except Exception:
        pass
    return True


def _next_step_towards(src: Tuple[int, int], dst: Tuple[int, int], env: Any) -> Optional[Tuple[int, int]]:
    """Choose a single-step neighbor that reduces distance; prefer 4-neighborhood, then diagonals."""
    if src == dst:
        return None
    sx, sy = src
    dx = 0 if dst[0] == sx else (1 if dst[0] > sx else -1)
    dy = 0 if dst[1] == sy else (1 if dst[1] > sy else -1)
    candidate_order: List[Tuple[int, int]] = []
    # 4-neighborhood first
    if dx != 0:
        candidate_order.append((sx + dx, sy))
    if dy != 0:
        candidate_order.append((sx, sy + dy))
    # allow diagonal as fallback (executor permits 8-neighborhood)
    if dx != 0 and dy != 0:
        candidate_order.append((sx + dx, sy + dy))
    # mild detours
    candidate_order.extend([(sx + 1, sy), (sx - 1, sy), (sx, sy + 1), (sx, sy - 1)])
    bounds = _env_bounds(env)
    def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    for nx, ny in candidate_order:
        np = (nx, ny)
        if not _in_bounds(np, bounds):
            continue
        if not _is_cell_free(env, np):
            continue
        if manhattan(np, dst) <= manhattan(src, dst):
            return np
    for nx, ny in candidate_order:
        np = (nx, ny)
        if _in_bounds(np, bounds) and _is_cell_free(env, np):
            return np
    return None


# --------- Domain Steps (pure) ---------

def leave_nest_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Leave nest by moving to an adjacent non-nest cell.
    Preconditions:
    - Worker must be at entry position
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)

    # Check if at entry
    at_entry = _bb_get(worker, "at_entry", False)
    if not at_entry:
        log.info("step=leave_nest worker=%s status=not_at_entry pos=%s", wid, pos)
        return {"status": "FAILURE"}

    # Find adjacent non-nest, non-wall cells
    x, y = pos
    bounds = _env_bounds(environment)
    directions = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    valid_exits = []
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        npos = (nx, ny)
        if not _in_bounds(npos, bounds):
            continue
        cell_type = _get_cell_type(environment, npos)
        if cell_type in ('nest', 'w', 'wall', 'e'):
            continue
        if _is_cell_free(environment, npos):
            valid_exits.append(npos)

    if not valid_exits:
        log.info("step=leave_nest worker=%s status=no_valid_exit pos=%s", wid, pos)
        return {"status": "FAILURE"}

    target = valid_exits[0]
    intent = {"type": "MOVE", "payload": {"target": list(target)}} if MoveIntent is None else MoveIntent(target=target)  # type: ignore
    log.info("step=leave_nest worker=%s decision pos=%s target=%s exits_found=%d", wid, pos, target, len(valid_exits))
    return {"status": "SUCCESS", "intents": [intent]}


def enter_nest_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Enter nest by moving to an adjacent nest cell.
    Preconditions:
    - Worker must be at entry position
    - Worker must not already be in nest
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)

    # Check if already in nest
    in_nest = _bb_get(worker, "in_nest", False)
    if in_nest:
        log.info("step=enter_nest worker=%s status=already_in_nest pos=%s", wid, pos)
        return {"status": "SUCCESS"}

    # Check if at entry
    at_entry = _bb_get(worker, "at_entry", False)
    if not at_entry:
        log.info("step=enter_nest worker=%s status=not_at_entry pos=%s", wid, pos)
        return {"status": "FAILURE"}

    # Find adjacent nest cells
    x, y = pos
    bounds = _env_bounds(environment)
    directions = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    valid_nest_cells = []
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        npos = (nx, ny)
        if not _in_bounds(npos, bounds):
            continue
        cell_type = _get_cell_type(environment, npos)
        if cell_type == 'nest' and _is_cell_free(environment, npos):
            valid_nest_cells.append(npos)

    if not valid_nest_cells:
        log.info("step=enter_nest worker=%s status=no_free_nest_cell pos=%s", wid, pos)
        return {"status": "FAILURE"}

    target = valid_nest_cells[0]
    intent = {"type": "MOVE", "payload": {"target": list(target)}} if MoveIntent is None else MoveIntent(target=target)  # type: ignore
    log.info("step=enter_nest worker=%s decision pos=%s target=%s nest_cells_found=%d", wid, pos, target, len(valid_nest_cells))
    return {"status": "SUCCESS", "intents": [intent]}


def search_food_randomly_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Search for food using random movement with pheromone deposit.
    Simple implementation: random valid move + optional pheromone deposit.
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    bounds = _env_bounds(environment)

    # Find valid adjacent cells
    x, y = pos
    directions = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    valid_moves = []
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        npos = (nx, ny)
        if _in_bounds(npos, bounds) and _is_cell_free(environment, npos):
            valid_moves.append(npos)

    if not valid_moves:
        log.info("step=search_food_randomly worker=%s status=no_valid_moves pos=%s", wid, pos)
        return {"status": "FAILURE"}

    import random
    target = random.choice(valid_moves)

    intents = []
    intents.append({"type": "MOVE", "payload": {"target": list(target)}} if MoveIntent is None else MoveIntent(target=target))  # type: ignore
    # Optional exploration pheromone
    intents.append({"type": "PHEROMONE", "payload": {"ptype": "exploration", "strength": 1}} if DepositPheromoneIntent is None else DepositPheromoneIntent(ptype="exploration", strength=1))  # type: ignore

    log.info("step=search_food_randomly worker=%s decision pos=%s target=%s options=%d", wid, pos, target, len(valid_moves))
    return {"status": "SUCCESS", "intents": intents}


def collect_food_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Collect food at current position or adjacent cells.

    Pure step: does not mutate the environment. Produces a COLLECT_FOOD intent
    that is applied by the IntentExecutor. Executor updates worker social stomach
    (respecting capacity) and reduces source food if present.

    Returns:
    - SUCCESS with collect intent if food is detected and within reach
    - FAILURE if no food nearby or prerequisites not met
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)

    # Check if food detected
    food_detected = _bb_get(worker, "food_detected", False)
    food_position = _bb_get(worker, "food_position", None)

    if not food_detected:
        log.info("step=collect_food worker=%s status=no_food_detected pos=%s", wid, pos)
        return {"status": "FAILURE"}

    # Verify reachability: at or adjacent to food
    if food_position:
        try:
            fx, fy = int(food_position[0]), int(food_position[1])
        except Exception:
            log.info("step=collect_food worker=%s status=invalid_food_position pos=%s food_pos=%s", wid, pos, food_position)
            return {"status": "FAILURE"}
        if abs(pos[0] - fx) > 1 or abs(pos[1] - fy) > 1:
            log.info("step=collect_food worker=%s status=food_too_far pos=%s food_pos=%s", wid, pos, food_position)
            return {"status": "FAILURE"}

    # Create intent using typed CustomIntent if available (fallback to dict)
    payload = {
        "position": [pos[0], pos[1]],
        "food_position": list(food_position) if isinstance(food_position, (list, tuple)) else [pos[0], pos[1]],
        "amount": 10  # default collection amount (executor clamps to capacity/source)
    }
    if CustomIntent is None:
        intent = {"type": "COLLECT_FOOD", "payload": payload}
    else:
        intent = CustomIntent(name="COLLECT_FOOD", payload=payload)  # type: ignore

    # Also deposit food pheromone (helps other workers)
    pher = {"type": "PHEROMONE", "payload": {"ptype": "food", "strength": 3}} if DepositPheromoneIntent is None else DepositPheromoneIntent(ptype="food", strength=3)  # type: ignore

    log.info("step=collect_food worker=%s decision pos=%s food_pos=%s amount=%s", wid, pos, payload["food_position"], payload["amount"])
    return {"status": "SUCCESS", "intents": [intent, pher]}


def return_to_nest_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Return to nest by following pheromones or moving towards entry.
    - SUCCESS if already in nest
    - RUNNING with move intent if progressing
    - FAILURE if stuck
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)

    # Check if already in nest
    in_nest = _bb_get(worker, "in_nest", False)
    if in_nest:
        log.info("step=return_to_nest worker=%s status=already_in_nest pos=%s", wid, pos)
        return {"status": "SUCCESS"}

    # Check for pheromone
    pheromone_detected = _bb_get(worker, "pheromone_detected", False)
    pheromone_position = _bb_get(worker, "pheromone_position", None)

    target = None
    if pheromone_detected and pheromone_position:
        try:
            px, py = int(pheromone_position[0]), int(pheromone_position[1])
        except Exception:
            px, py = pos
        dx = 1 if px > pos[0] else (-1 if px < pos[0] else 0)
        dy = 1 if py > pos[1] else (-1 if py < pos[1] else 0)
        target = (pos[0] + dx, pos[1] + dy)
        log.debug("step=return_to_nest using pheromone gradient towards %s", pheromone_position)
    else:
        # fallback: local cardinal move
        bounds = _env_bounds(environment)
        x, y = pos
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        options = []
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if _in_bounds((nx, ny), bounds) and _is_cell_free(environment, (nx, ny)):
                options.append((nx, ny))
        if options:
            import random
            target = random.choice(options)

    if not target:
        log.info("step=return_to_nest worker=%s status=no_valid_move pos=%s", wid, pos)
        return {"status": "FAILURE"}

    bounds = _env_bounds(environment)
    if not _in_bounds(target, bounds) or not _is_cell_free(environment, target):
        log.info("step=return_to_nest worker=%s status=target_invalid pos=%s target=%s", wid, pos, target)
        return {"status": "FAILURE"}

    intents = []
    intents.append({"type": "MOVE", "payload": {"target": list(target)}} if MoveIntent is None else MoveIntent(target=target))  # type: ignore
    intents.append({"type": "PHEROMONE", "payload": {"ptype": "nest_seeking", "strength": 2}} if DepositPheromoneIntent is None else DepositPheromoneIntent(ptype="nest_seeking", strength=2))  # type: ignore

    log.info("step=return_to_nest worker=%s decision pos=%s target=%s pheromone_guided=%s", wid, pos, target, bool(pheromone_detected))
    return {"status": "RUNNING", "intents": intents}


def feed_neighbor_step(worker: Any, environment: Any, amount: Optional[int] = None, **kwargs) -> Dict[str, Any]:
    """
    Feed a hungry neighboring worker using social stomach content.
    Pure step: reads BB, emits a FeedIntent; no world mutation here.

    Preconditions (from BB):
    - 'hungry_neighbor_id' present (int)
    - 'social_stomach' > 0
    """
    wid = getattr(worker, "id", "?")
    target_id = _bb_get(worker, "hungry_neighbor_id", None)
    social = _bb_get(worker, "social_stomach", 0)

    if target_id is None:
        log.debug("step=feed_neighbor worker=%s status=no_target", wid)
        return {"status": "FAILURE"}

    try:
        social_val = int(social)
    except Exception:
        social_val = 0

    if social_val <= 0:
        log.debug("step=feed_neighbor worker=%s status=no_social_food target=%s", wid, target_id)
        return {"status": "FAILURE"}

    if FeedIntent is None:
        payload = {"target_id": int(target_id)}
        if amount is not None:
            payload["amount"] = int(amount)
        intent = {"type": "FEED", "payload": payload}
    else:
        intent = FeedIntent(target_id=int(target_id), amount=None if amount is None else int(amount))  # type: ignore

    log.info("step=feed_neighbor worker=%s target=%s amount=%s", wid, target_id, amount)
    return {"status": "SUCCESS", "intents": [intent]}


def move_to_food_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Move one step towards a suitable collection position near detected food.
    - Reads BB keys: food_detected (bool), food_position ([x,y])
    - If already at/adjacent to food: SUCCESS (no intent)
    - Else: propose one MoveIntent towards nearest valid collection cell (or directly to food)
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    detected = bool(_bb_get(worker, "food_detected", False))
    food_pos = _bb_get(worker, "food_position", None)

    if not detected or not food_pos or not isinstance(food_pos, (list, tuple)) or len(food_pos) != 2:
        log.info("step=move_to_food worker=%s status=no_food_detected pos=%s", wid, pos)
        return {"status": "FAILURE"}

    fx, fy = int(food_pos[0]), int(food_pos[1])
    if abs(pos[0] - fx) <= 1 and abs(pos[1] - fy) <= 1:
        log.info("step=move_to_food worker=%s status=at_collection_pos pos=%s food=%s", wid, pos, (fx, fy))
        return {"status": "SUCCESS"}

    candidates: List[Tuple[int, int]] = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            npos = (fx + dx, fy + dy)
            if _in_bounds(npos, _env_bounds(environment)) and _is_cell_free(environment, npos):
                candidates.append(npos)

    target = None
    if candidates:
        candidates.sort(key=lambda p: abs(p[0] - pos[0]) + abs(p[1] - pos[1]))
        target = candidates[0]
    else:
        target = (fx, fy)

    next_pos = _next_step_towards(pos, target, environment)
    if next_pos is None:
        log.info("step=move_to_food worker=%s status=blocked pos=%s target=%s", wid, pos, target)
        return {"status": "FAILURE"}

    intent = {"type": "MOVE", "payload": {"target": [next_pos[0], next_pos[1]]}} if MoveIntent is None else MoveIntent(target=next_pos)  # type: ignore
    log.info("step=move_to_food worker=%s decision pos=%s food=%s target=%s next=%s", wid, pos, (fx, fy), target, next_pos)
    return {"status": "RUNNING", "intents": [intent]}


def follow_pheromone_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Move one step along detected pheromone gradient towards pheromone_position.
    Returns:
      - SUCCESS if already at pheromone position
      - RUNNING with one MoveIntent if progressing
      - FAILURE if no pheromone detected or blocked
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)
    detected = bool(_bb_get(worker, "pheromone_detected", False))
    ph_pos = _bb_get(worker, "pheromone_position", None)

    if not detected or not ph_pos or not isinstance(ph_pos, (list, tuple)) or len(ph_pos) != 2:
        log.info("step=follow_pheromone worker=%s status=no_pheromone pos=%s", wid, pos)
        return {"status": "FAILURE"}

    tx, ty = int(ph_pos[0]), int(ph_pos[1])
    target = (tx, ty)
    if pos == target:
        log.info("step=follow_pheromone worker=%s status=on_target pos=%s", wid, pos)
        return {"status": "SUCCESS"}

    next_pos = _next_step_towards(pos, target, environment)
    if next_pos is None:
        log.info("step=follow_pheromone worker=%s status=blocked pos=%s target=%s", wid, pos, target)
        return {"status": "FAILURE"}

    intent = {"type": "MOVE", "payload": {"target": [next_pos[0], next_pos[1]]}} if MoveIntent is None else MoveIntent(target=next_pos)  # type: ignore
    log.info("step=follow_pheromone worker=%s decision pos=%s target=%s next=%s", wid, pos, target, next_pos)
    return {"status": "RUNNING", "intents": [intent]}


def resolve_mutual_feeding_step(worker: Any, environment: Any, **kwargs) -> Dict[str, Any]:
    """
    Resolve mutual feeding deadlocks between two hungry neighbors.

    Strategy (pure, BB read-only + env read-only):
    - Preconditions: worker.individual_hungry, hungry_neighbor_id present, worker.social_stomach > 0
    - Compute hunger ratios (individual_stomach/hunger_threshold) for worker and neighbor.
      The more hungry (smaller ratio) should be fed.
    - On tie, use (environment.cycle_count + worker.id) parity to alternate fairness.
    - If worker should feed neighbor -> emit FeedIntent (amount optional).
      Else -> SUCCESS without intents (yield), allowing the other ant to feed.
    """
    wid = getattr(worker, "id", "?")
    pos = _bb_pos(worker)

    # Preconditions from BB
    indiv_hungry = bool(_bb_get(worker, "individual_hungry", False))
    social = _bb_get(worker, "social_stomach", 0)
    try:
        social_val = int(social)
    except Exception:
        social_val = 0
    neighbor_id = _bb_get(worker, "hungry_neighbor_id", None)

    if not indiv_hungry or neighbor_id is None:
        log.debug("step=resolve_mutual_feeding worker=%s status=not_applicable pos=%s hungry=%s neighbor=%s", wid, pos, indiv_hungry, neighbor_id)
        return {"status": "FAILURE"}

    if social_val <= 0:
        # Worker cannot feed; yield
        log.info("step=resolve_mutual_feeding worker=%s status=no_social_food pos=%s neighbor=%s", wid, pos, neighbor_id)
        return {"status": "SUCCESS"}

    # Lookup neighbor
    neighbor = None
    get_by_id = getattr(environment, "get_ant_by_id", None)
    if callable(get_by_id):
        try:
            neighbor = get_by_id(int(neighbor_id))
        except Exception:
            neighbor = None

    if neighbor is None:
        log.info("step=resolve_mutual_feeding worker=%s status=neighbor_not_found neighbor=%s", wid, neighbor_id)
        return {"status": "FAILURE"}

    # Extract neighbor hunger info best-effort (BB preferred)
    n_bb = getattr(neighbor, "blackboard", None)
    if n_bb and hasattr(n_bb, "get"):
        n_indiv = n_bb.get("individual_stomach", None)
        n_thr = n_bb.get("hunger_threshold", None)
        n_hungry = bool(n_bb.get("individual_hungry", False))
    else:
        n_indiv = getattr(neighbor, "current_stomach", None)
        n_thr = getattr(neighbor, "hunger_threshold", None)
        n_hungry = bool(getattr(neighbor, "individual_hungry", False))

    # If neighbor not hungry, nothing to resolve here
    if not n_hungry or n_indiv is None or n_thr in (None, 0):
        log.info("step=resolve_mutual_feeding worker=%s status=neighbor_not_hungry neighbor=%s", wid, neighbor_id)
        return {"status": "SUCCESS"}

    # Compute hunger ratios (smaller => more hungry)
    try:
        w_indiv = int(_bb_get(worker, "individual_stomach", 0))
        w_thr = int(_bb_get(worker, "hunger_threshold", 1))
    except Exception:
        w_indiv, w_thr = 0, 1
    try:
        n_indiv_val = int(n_indiv)
        n_thr_val = int(n_thr) if n_thr not in (None, 0) else 1
    except Exception:
        n_indiv_val, n_thr_val = 0, 1

    w_ratio = float(w_indiv) / float(w_thr) if w_thr > 0 else 1.0
    n_ratio = float(n_indiv_val) / float(n_thr_val) if n_thr_val > 0 else 1.0

    # Tie-breaker via cycle parity
    cycle = int(getattr(environment, "cycle_count", 0))
    neighbor_more_hungry = n_ratio < w_ratio
    worker_more_hungry = w_ratio < n_ratio
    tie = abs(n_ratio - w_ratio) < 1e-9

    decision = "yield"
    if neighbor_more_hungry:
        decision = "feed_neighbor"
    elif worker_more_hungry:
        decision = "yield"
    else:
        decision = "feed_neighbor" if ((cycle + int(wid)) % 2 == 0) else "yield"

    if decision == "feed_neighbor":
        amount = None
        if "amount" in kwargs and kwargs["amount"] is not None:
            try:
                amount = int(kwargs["amount"])
            except Exception:
                amount = None

        if FeedIntent is None:
            payload = {"target_id": int(neighbor_id)}
            if amount is not None:
                payload["amount"] = amount
            intent = {"type": "FEED", "payload": payload}
        else:
            intent = FeedIntent(target_id=int(neighbor_id), amount=amount)  # type: ignore

        log.info(
            "step=resolve_mutual_feeding worker=%s decision=feed target=%s w_ratio=%.3f n_ratio=%.3f cycle=%s",
            wid, neighbor_id, w_ratio, n_ratio, cycle
        )
        return {"status": "SUCCESS", "intents": [intent]}

    # Yield: succeed without intents to let the other side act
    log.info(
        "step=resolve_mutual_feeding worker=%s decision=yield target=%s w_ratio=%.3f n_ratio=%.3f cycle=%s",
        wid, neighbor_id, w_ratio, n_ratio, cycle
    )
    return {"status": "SUCCESS"}
