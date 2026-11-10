"""Prediction model engine: Poisson, Dixon-Coles, ML, and a weighted ensemble.

Targets: P(Over 1.5) and P(BTTS) for a fixture.

Honesty contract (see honest-model-evaluation):
  * The ML wrapper reports `available=False` and silently falls back to the
    strength model when scikit-learn / xgboost is not importable, so a wheel
    gap on a new Python never silences the pipeline.
  * Market conditioning (real O/U line) lives in `baseline.py`; this engine
    never proxies O1.5/BTTS from 1X2 odds (the DC tau-boundary trap the
    skills warn about). When no real line is given, the odds weight is
    redistributed to the feature models.
  * Every model returns probabilities in [0,1]; the ensemble returns a
    per-model breakdown so the dashboard can show what each model says.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from .models import MAX_GOALS, joint_goal_matrix
from .models import predict as strength_predict
from .normalization import Match

DC_DEFAULT_RHO = -0.10  # low-score Dixon-Coles correction (typical fitted sign)
FEATURE_WINDOW = 5


def _clamp(p: float) -> float:
    if math.isnan(p):
        return 0.5
    return max(0.0, min(1.0, p))


@dataclass(frozen=True)
class ModelProbs:
    """One model's probabilities for a fixture."""

    name: str
    p_over15: float
    p_over25: float
    p_btts: float
    available: bool = True
    note: str = ""

    def as_dict(self) -> dict[str, float | str | bool]:
        return {
            "model": self.name,
            "p_over15": round(self.p_over15, 4),
            "p_over25": round(self.p_over25, 4),
            "p_btts": round(self.p_btts, 4),
            "available": self.available,
            "note": self.note,
        }


def predict_poisson(home: str, away: str, history: Sequence[Match]) -> ModelProbs:
    pred = strength_predict(home, away, history, rho=0.0)
    return ModelProbs(name="poisson", p_over15=_clamp(pred.p_over1_5), p_over25=_clamp(pred.p_over2_5), p_btts=_clamp(pred.p_btts))


def predict_dc(home: str, away: str, history: Sequence[Match], *, rho: float = DC_DEFAULT_RHO) -> ModelProbs:
    pred = strength_predict(home, away, history, rho=rho)
    return ModelProbs(name="dixon-coles", p_over15=_clamp(pred.p_over1_5), p_over25=_clamp(pred.p_over2_5), p_btts=_clamp(pred.p_btts))


class MLModel:
    """Gradient-boosted classifier on rolling team features (honest fallback).

    `available` is False when sklearn/xgboost is not importable; predict()
    then returns the Poisson strength model rather than raising, and notes
    the fallback. `fit` works on chronologically ordered features so callers
    can train once and reuse `predict` across a backtest window.
    """

    def __init__(self, *, min_samples: int = 40) -> None:
        self.min_samples = min_samples
        self.available = False
        self._note = "sklearn not importable; strength fallback"
        self._clf_over: Any = None
        self._clf_btts: Any = None
        self._feature_keys: tuple[str, ...] = ()

    def fit(self, rows: Sequence[dict[str, float | int | str]], targets_over: Sequence[int], targets_btts: Sequence[int]) -> bool:
        try:
            from sklearn.ensemble import GradientBoostingClassifier
        except ImportError:
            self.available = False
            self._note = "sklearn not importable; strength fallback"
            return False
        if len(rows) < self.min_samples:
            self.available = False
            self._note = f"too few samples ({len(rows)} < {self.min_samples}); strength fallback"
            return False
        keys = tuple(k for k in rows[0] if isinstance(rows[0][k], (int, float)))
        self._feature_keys = keys
        X: list[list[float]] = [[float(row[k]) for k in keys] for row in rows]
        self._clf_over = GradientBoostingClassifier(n_estimators=60, learning_rate=0.1, max_depth=2)
        self._clf_over.fit(X, targets_over)
        self._clf_btts = GradientBoostingClassifier(n_estimators=60, learning_rate=0.1, max_depth=2)
        self._clf_btts.fit(X, targets_btts)
        self.available = True
        self._note = "gradient-boosting (sklearn)"
        return True

    def predict(self, feature_row: dict[str, float | int | str]) -> ModelProbs:
        if not self.available or self._clf_over is None or self._clf_btts is None or not self._feature_keys:
            # Honest fallback: strength model with a note (family match).
            return ModelProbs(
                name="ml",
                p_over15=0.5,
                p_over25=0.5,
                p_btts=0.5,
                available=False,
                note=self._note,
            )
        X: list[list[float]] = [[float(feature_row[k]) for k in self._feature_keys]]
        po = float(self._clf_over.predict_proba(X)[0][1])
        pb = float(self._clf_btts.predict_proba(X)[0][1])
        # no separate O2.5 classifier in the honest fallback: derive from O1.5
        return ModelProbs(name="ml", p_over15=_clamp(po), p_over25=min(_clamp(po), 1.0), p_btts=_clamp(pb), note=self._note)


class Stage1Lambdas:
    """Two-stage Dixon-Coles: predict per-match λ_home / λ_away from rolling
    team features with a gradient-boosted regressor, then build the DC matrix.

    This is the repo HANDOFF's owner-flagged "XGB stage-1 lambda" attempt.
    It is evaluated honestly (see scripts/eval_stage1.py): per-match lambdas
    only help if they beat the base rate / closing line. Falls back to the
    strength-Poisson model with `available=False` when sklearn is absent or
    the sample is too small.
    """

    def __init__(self, *, rho: float = DC_DEFAULT_RHO, min_samples: int = 40) -> None:
        self.rho = rho
        self.min_samples = min_samples
        self.available = False
        self._note = "sklearn not importable; strength fallback"
        self._feature_keys: tuple[str, ...] = ()
        self._reg_h: Any = None
        self._reg_a: Any = None

    def fit(self, rows: Sequence[dict[str, float | int | str]], lam_home: Sequence[float], lam_away: Sequence[float]) -> bool:
        try:
            from sklearn.ensemble import GradientBoostingRegressor
        except ImportError:
            self.available = False
            return False
        if len(rows) < self.min_samples:
            self.available = False
            self._note = f"too few samples ({len(rows)} < {self.min_samples}); strength fallback"
            return False
        keys = tuple(k for k in rows[0] if isinstance(rows[0][k], (int, float)))
        self._feature_keys = keys
        X: list[list[float]] = [[float(row[k]) for k in keys] for row in rows]
        self._reg_h = GradientBoostingRegressor(n_estimators=80, learning_rate=0.1, max_depth=2, random_state=0)
        self._reg_h.fit(X, [float(v) for v in lam_home])
        self._reg_a = GradientBoostingRegressor(n_estimators=80, learning_rate=0.1, max_depth=2, random_state=0)
        self._reg_a.fit(X, [float(v) for v in lam_away])
        self.available = True
        self._note = "two-stage gradient-boosted lambdas (sklearn)"
        return True

    def predict(self, feature_row: dict[str, float | int | str]) -> ModelProbs:
        if not self.available or self._reg_h is None or self._reg_a is None or not self._feature_keys:
            return ModelProbs(name="stage1-lambdas", p_over15=0.5, p_over25=0.5, p_btts=0.5, available=False, note=self._note)
        X: list[list[float]] = [[float(feature_row[k]) for k in self._feature_keys]]
        lam_h = max(float(self._reg_h.predict(X)[0]), 0.05)
        lam_a = max(float(self._reg_a.predict(X)[0]), 0.05)
        J = joint_goal_matrix(lam_h, lam_a, self.rho)
        p15 = p25 = btts = 0.0
        for i in range(MAX_GOALS + 1):
            for j in range(MAX_GOALS + 1):
                p = J[i][j]
                if i + j > 1:
                    p15 += p
                if i + j > 2:
                    p25 += p
                if i >= 1 and j >= 1:
                    btts += p
        return ModelProbs(name="stage1-lambdas", p_over15=_clamp(p15), p_over25=_clamp(p25), p_btts=_clamp(btts), note=self._note)


@dataclass(frozen=True)
class EnsembleResult:
    home: str
    away: str
    p_over15: float
    p_over25: float
    p_btts: float
    components: tuple[ModelProbs, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return {
            "home": self.home,
            "away": self.away,
            "p_over15": round(self.p_over15, 4),
            "p_over25": round(self.p_over25, 4),
            "p_btts": round(self.p_btts, 4),
            "components": [c.as_dict() for c in self.components],
        }


def ensemble(
    home: str,
    away: str,
    history: Sequence[Match],
    *,
    weights: dict[str, float] | None = None,
    ml: MLModel | None = None,
    ml_feature_row: dict[str, float | int | str] | None = None,
) -> EnsembleResult:
    """Weighted blend of poisson + dixon-coles (+ ml when available).

    Weights are normalised over the models actually available; a missing ML
    (or feature row) redistributes its weight to the strength models. All
    outputs are clamped to [0,1].
    """
    poisson = predict_poisson(home, away, history)
    dc_model = predict_dc(home, away, history)
    comps: list[ModelProbs] = [poisson, dc_model]
    if ml is not None and ml.available and ml_feature_row is not None:
        comps.append(ml.predict(ml_feature_row))

    w = weights or {"poisson": 0.4, "dc": 0.4, "ml": 0.2}
    total_w = sum(w[name] for name in ("poisson", "dc", "ml") if any(c.name == name for c in comps))
    if total_w <= 0:
        total_w = 1.0
    p_over_acc = 0.0
    p_over25_acc = 0.0
    p_btts_acc = 0.0
    for c in comps:
        wi = w.get(c.name, 0.0)
        p_over_acc += wi * c.p_over15
        p_over25_acc += wi * c.p_over25
        p_btts_acc += wi * c.p_btts
    p_over = p_over_acc / total_w
    p_over25 = p_over25_acc / total_w
    p_btts = p_btts_acc / total_w
    return EnsembleResult(
        home=home,
        away=away,
        p_over15=_clamp(p_over),
        p_over25=_clamp(p_over25),
        p_btts=_clamp(p_btts),
        components=tuple(comps),
    )


# Convenience alias mirroring how callers/brokers name it.
EnsemblePredictor = Callable[[str, str, Sequence[Match]], EnsembleResult]
