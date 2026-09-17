"""Strict PSPLIB single-mode parser and deterministic pilot selection.

The parser keeps PSPLIB's abstract time slots and renewable capacities.  It does
not attach weather observations or claim that these benchmark networks are
field projects; weather is an explicitly added scenario in later experiments.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import zipfile


@dataclass(frozen=True)
class NetworkTask:
    name: str
    duration: int
    predecessors: tuple[str, ...]
    demand: tuple[int, ...]


def _section(text: str, heading: str, next_heading: str | None = None) -> str:
    m = re.search(re.escape(heading) + r"\s*:\s*\n", text, flags=re.I)
    if not m:
        raise ValueError(f"missing PSPLIB section: {heading}")
    tail = text[m.end():]
    if next_heading:
        n = re.search(re.escape(next_heading) + r"\s*:\s*\n", tail, flags=re.I)
        if n:
            tail = tail[:n.start()]
    return tail


def _numeric_rows(section: str, expected: int, minimum: int) -> list[list[int]]:
    rows: list[list[int]] = []
    for line in section.splitlines():
        if not re.match(r"^\s*\d+\b", line):
            continue
        nums = [int(x) for x in re.findall(r"(?<![A-Za-z])[-+]?\d+(?![A-Za-z])", line)]
        if len(nums) >= minimum:
            rows.append(nums)
    if len(rows) != expected:
        raise ValueError(f"expected {expected} numeric rows, found {len(rows)}")
    return rows


def parse_psplib_sm(text: str) -> dict:
    """Parse one ``.sm`` instance and validate precedence/resource invariants."""
    jobs_match = re.search(r"jobs\s*\(incl\.\s*supersource/sink\s*\)\s*:\s*(\d+)", text, re.I)
    horizon_match = re.search(r"horizon\s*:\s*(\d+)", text, re.I)
    resource_match = re.search(r"renewable\s*:\s*(\d+)\s+R", text, re.I)
    if not (jobs_match and horizon_match and resource_match):
        raise ValueError("missing jobs, horizon or renewable-resource header")
    jobs, horizon, resource_count = map(int, (jobs_match.group(1), horizon_match.group(1), resource_match.group(1)))
    if jobs < 2 or resource_count < 1 or horizon < 1:
        raise ValueError("invalid PSPLIB dimensions")

    prec = _section(text, "PRECEDENCE RELATIONS", "REQUESTS/DURATIONS")
    prec_rows = _numeric_rows(prec, jobs, 3)
    successors: dict[int, tuple[int, ...]] = {}
    for row in prec_rows:
        job, mode_count, successor_count = row[:3]
        succ = tuple(row[3:])
        if mode_count != 1 or successor_count != len(succ) or not 1 <= job <= jobs:
            raise ValueError(f"invalid precedence row: {row}")
        if any(not 1 <= s <= jobs or s == job for s in succ):
            raise ValueError(f"invalid successor in row: {row}")
        successors[job] = succ
    if set(successors) != set(range(1, jobs + 1)):
        raise ValueError("precedence rows do not cover every job")

    req = _section(text, "REQUESTS/DURATIONS", "RESOURCEAVAILABILITIES")
    req_rows = _numeric_rows(req, jobs, 3 + resource_count)
    durations: dict[int, tuple[int, tuple[int, ...]]] = {}
    for row in req_rows:
        job, mode, duration = row[:3]
        demand = tuple(row[3:3 + resource_count])
        if mode != 1 or len(demand) != resource_count or not 1 <= job <= jobs:
            raise ValueError(f"invalid request row: {row}")
        if duration < 0 or any(x < 0 for x in demand):
            raise ValueError(f"negative duration or demand: {row}")
        durations[job] = (duration, demand)
    if set(durations) != set(range(1, jobs + 1)):
        raise ValueError("request rows do not cover every job")

    avail = _section(text, "RESOURCEAVAILABILITIES")
    avail_rows = _numeric_rows(avail, 1, resource_count)
    capacity = tuple(avail_rows[0][:resource_count])
    if len(capacity) != resource_count or any(x <= 0 for x in capacity):
        raise ValueError("invalid resource capacities")
    for job, (_, demand) in durations.items():
        if any(d > c for d, c in zip(demand, capacity)):
            raise ValueError(f"job {job} demand exceeds capacity")

    pred: dict[int, list[int]] = {j: [] for j in range(1, jobs + 1)}
    for job, succ in successors.items():
        for child in succ:
            pred[child].append(job)
    tasks = []
    for job in range(1, jobs + 1):
        duration, demand = durations[job]
        tasks.append(NetworkTask(str(job), duration, tuple(map(str, sorted(pred[job]))), demand))
    # Acyclicity check using the parsed graph.
    seen: set[int] = set()
    while len(seen) < jobs:
        ready = [j for j in range(1, jobs + 1) if j not in seen and set(pred[j]) <= seen]
        if not ready:
            raise ValueError("cyclic precedence graph")
        seen.update(ready)
    dummy_jobs = [t.name for t in tasks if t.duration == 0 and not any(t.demand)]
    return {
        "jobs_including_source_sink": jobs,
        "horizon": horizon,
        "renewable_resources": resource_count,
        "capacity": capacity,
        "tasks": [asdict(t) for t in tasks],
        "dummy_jobs": dummy_jobs,
        "time_units": "PSPLIB abstract time slots; no weather-hour mapping",
    }


def load_zip_instance(zip_path: str | Path, member: str) -> dict:
    zip_path = Path(zip_path)
    with zipfile.ZipFile(zip_path) as z:
        try:
            raw = z.read(member)
        except KeyError as exc:
            raise ValueError(f"instance not found: {member}") from exc
    result = parse_psplib_sm(raw.decode("latin1"))
    result.update({"source_archive": str(zip_path), "source_member": member,
                   "source_sha256": hashlib.sha256(raw).hexdigest()})
    return result


def deterministic_members(members: list[str], count: int = 12) -> list[str]:
    """Stratify by replicate index, then family index; never select by outcome."""
    names = sorted(m for m in members if re.fullmatch(r"j30\d+_\d+\.sm", m))
    if count < 1 or count > len(names):
        raise ValueError("invalid pilot count")
    # Families are encoded as j30<family>_<replicate>; take every fourth family
    # in the first replicate, then repeat for later replicates as needed.
    families = sorted({int(re.search(r"j30(\d+)_", n).group(1)) for n in names})
    chosen_families = families[::max(1, len(families) // min(count, len(families)))]
    selected = [f"j30{f}_1.sm" for f in chosen_families if f"j30{f}_1.sm" in names]
    if len(selected) < count:
        selected.extend(n for n in names if n not in selected)
    return selected[:count]


def write_pilot(zip_path: str | Path, output: str | Path, count: int = 12) -> dict:
    with zipfile.ZipFile(zip_path) as z:
        members = z.namelist()
    chosen = deterministic_members(members, count)
    payload = {"selection_rule": "deterministic family-stratified pilot; no outcome filtering",
               "instances": [load_zip_instance(zip_path, m) for m in chosen]}
    Path(output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("zip_path")
    ap.add_argument("output")
    ap.add_argument("--count", type=int, default=12)
    args = ap.parse_args()
    payload = write_pilot(args.zip_path, args.output, args.count)
    print(json.dumps({"status": "OK", "instances": len(payload["instances"]),
                      "output": args.output}, ensure_ascii=False))
