"""Decision-aligned calibration of forecast gust to contract-exceedance probability.

The object being calibrated is not "forecast wind error".  It is the probability
that a *contract-relevant* event occurs:

    Y = 1[any hour in the next L hours has observed gust > threshold]

given the archived forecast for exactly that block.  This is the quantity a
scheduler actually needs, and it is the quantity whose mis-calibration produces
avoidable stops or unsafe work.

Two calibrators are provided and both are fitted only on their own split:
``binned`` (monotone binned frequency estimate, the primary model because it
makes no functional assumption) and ``logistic`` (smooth single-covariate
baseline).  Both return P(Y=1 | predictor), and both refuse to extrapolate
silently: predictions outside the fitted support are clipped and the fraction of
clipped predictions is reported.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

MIN_BIN_COUNT = 200


def _check(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or len(x) == 0:
        raise ValueError("x and y must be equal-length non-empty 1-D arrays")
    if not np.isfinite(x).all():
        raise ValueError("predictor contains non-finite values; imputation is not allowed")
    if not np.isin(y, (0.0, 1.0)).all():
        raise ValueError("labels must be binary")
    return x, y


@dataclass
class BinnedCalibrator:
    """Monotone binned frequency estimate of P(Y=1 | x)."""

    model_id: str = "binned"
    bin_edges: np.ndarray | None = None
    bin_prob: np.ndarray | None = None
    n_fit: int = 0
    base_rate: float = 0.0
    clipped_low: int = 0
    clipped_high: int = 0

    def fit(self, x: np.ndarray, y: np.ndarray, *, max_bins: int = 40,
            min_count: int = MIN_BIN_COUNT) -> BinnedCalibrator:
        x, y = _check(x, y)
        self.n_fit = len(x)
        self.base_rate = float(y.mean())
        order = np.argsort(x, kind="stable")
        xs, ys = x[order], y[order]
        # Equal-count bins on the sorted sample, so every bin is large enough and
        # the frequency estimate inside it is a genuine conditional frequency.
        n_bins = max(2, min(max_bins, len(x) // min_count))
        bounds = np.unique(np.linspace(0, len(x), n_bins + 1).round().astype(int))
        rates: list[float] = []
        weights: list[float] = []
        bin_last: list[float] = []
        for lo, hi in zip(bounds[:-1], bounds[1:]):
            if hi <= lo:
                continue
            rates.append(float(ys[lo:hi].mean()))
            weights.append(float(hi - lo))
            bin_last.append(float(xs[hi - 1]))
        if not rates:
            rates, weights = [float(ys.mean())], [float(len(ys))]
            bin_last = [float(xs[-1])]
        probs, counts = _pava(np.array(rates, dtype=float), np.array(weights, dtype=float))
        # Rebuild edges so that block k spans the bins it merged, keeping the
        # edge list aligned with the pooled probabilities.
        edges = [float(xs[0])]
        cursor = 0.0
        for count in counts:
            cursor += count
            edges.append(bin_last[min(int(cursor), len(bin_last)) - 1])
        edges[0] = float(xs[0])
        edges[-1] = float(xs[-1])
        if len(edges) != len(probs) + 1:
            raise AssertionError("bin edges and probabilities are inconsistent")
        for i in range(1, len(edges)):
            edges[i] = max(edges[i], edges[i - 1] + 1e-9)
        self.bin_edges = np.array(edges, dtype=float)
        self.bin_prob = probs
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.bin_edges is None or self.bin_prob is None:
            raise RuntimeError("calibrator is not fitted")
        x = np.asarray(x, dtype=float)
        lo, hi = self.bin_edges[0], self.bin_edges[-1]
        self.clipped_low += int((x < lo).sum())
        self.clipped_high += int((x > hi).sum())
        idx = np.clip(np.searchsorted(self.bin_edges, x, side="right") - 1,
                      0, len(self.bin_prob) - 1)
        return self.bin_prob[idx]


@dataclass
class LogisticCalibrator:
    """Single-covariate logistic calibration, the smooth baseline model."""

    model_id: str = "logistic"
    coef: float = 0.0
    intercept: float = 0.0
    scale: float = 1.0
    n_fit: int = 0
    base_rate: float = 0.0

    def fit(self, x: np.ndarray, y: np.ndarray, *, l2: float = 1e-6) -> LogisticCalibrator:
        x, y = _check(x, y)
        self.n_fit = len(x)
        self.base_rate = float(y.mean())
        self.scale = float(max(x.std(), 1e-9))
        z = (x - x.mean()) / self.scale
        beta = np.zeros(2)
        for _ in range(200):
            eta = beta[0] + beta[1] * z
            p = 1.0 / (1.0 + np.exp(-np.clip(eta, -30, 30)))
            w = np.clip(p * (1 - p), 1e-9, None)
            grad = np.array([np.sum(p - y), np.sum((p - y) * z)]) + l2 * beta
            hess = np.array([[np.sum(w), np.sum(w * z)],
                             [np.sum(w * z), np.sum(w * z * z)]]) + l2 * np.eye(2)
            step = np.linalg.solve(hess, grad)
            beta -= step
            if np.max(np.abs(step)) < 1e-10:
                break
        self.intercept = float(beta[0] - beta[1] * x.mean() / self.scale)
        self.coef = float(beta[1] / self.scale)
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        eta = self.intercept + self.coef * x
        return 1.0 / (1.0 + np.exp(-np.clip(eta, -30, 30)))


def _pava(values: np.ndarray, weights: np.ndarray | None = None
          ) -> tuple[np.ndarray, np.ndarray]:
    """Weighted pool-adjacent-violators.

    Returns ``(probabilities, counts)``: the fitted non-decreasing level of each
    block and the number of original bins merged into it, so the caller can keep
    its bin-edge list aligned with the merged blocks.
    """
    values = np.asarray(values, dtype=float)
    if weights is None:
        weights = np.ones_like(values)
    weights = np.asarray(weights, dtype=float)
    if len(values) != len(weights) or len(values) == 0:
        raise ValueError("values and weights must be non-empty and equal length")
    blocks: list[list[float]] = []  # [weighted_sum, weight, bin_count]
    for value, weight in zip(values, weights):
        blocks.append([value * weight, weight, 1.0])
        while len(blocks) >= 2:
            prev_mean = blocks[-2][0] / blocks[-2][1]
            curr_mean = blocks[-1][0] / blocks[-1][1]
            if prev_mean <= curr_mean + 1e-15:
                break
            merged = [blocks[-2][0] + blocks[-1][0],
                      blocks[-2][1] + blocks[-1][1],
                      blocks[-2][2] + blocks[-1][2]]
            blocks[-2:] = [merged]
    probs = np.array([b[0] / b[1] for b in blocks], dtype=float)
    counts = np.array([int(b[2]) for b in blocks], dtype=float)
    return probs, counts


@dataclass
class CalibrationBundle:
    """All calibrators needed for one (threshold, horizon) target."""

    threshold: float
    horizon: int
    calibrators: dict[str, object] = field(default_factory=dict)
    diagnostics: dict[str, dict] = field(default_factory=dict)

    def add(self, key: str, model) -> None:
        self.calibrators[key] = model

    def p(self, key: str, x: np.ndarray) -> np.ndarray:
        if key not in self.calibrators:
            raise KeyError(f"no calibrator {key}")
        return self.calibrators[key].predict(x)

    def as_dict(self) -> dict:
        return {
            "threshold": self.threshold,
            "horizon": self.horizon,
            "models": {k: m.model_id for k, m in self.calibrators.items()},
            "n_fit": {k: m.n_fit for k, m in self.calibrators.items()},
            "diagnostics": self.diagnostics,
        }


def reliability_table(p: np.ndarray, y: np.ndarray, bins: int = 10,
                      edges: np.ndarray | None = None) -> list[dict]:
    """Reliability curve plus Brier decomposition inputs for one predictor.

    Bin membership is resolved once per forecast with ``searchsorted``, so each
    forecast contributes to exactly one bin and the bin counts sum to
    ``len(p)``.  The earlier ``(p >= lo) & (p <= hi)`` form put every boundary
    value into both neighbouring bins and therefore returned counts that
    exceeded the sample size, which invalidated the reliability curve and any
    Brier decomposition built on it.
    """
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=float)
    if edges is None:
        edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    edges = np.asarray(edges, dtype=float)
    if edges.size < 2:
        return []
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, edges.size - 2)
    rows = []
    for k in range(edges.size - 1):
        sel = idx == k
        if not sel.any():
            continue
        rows.append({"p_mean": float(p[sel].mean()), "obs_freq": float(y[sel].mean()),
                     "n": int(sel.sum()), "lo": float(edges[k]), "hi": float(edges[k + 1])})
    assert sum(r["n"] for r in rows) == p.size, "reliability bins overlap or omit samples"
    return rows


def brier(p: np.ndarray, y: np.ndarray) -> float:
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=float)
    return float(np.mean((p - y) ** 2))


def brier_skill_score(p: np.ndarray, y: np.ndarray, reference: np.ndarray) -> float:
    bs = brier(p, y)
    ref = brier(reference, y)
    if ref == 0:
        return float("nan")
    return float(1.0 - bs / ref)
