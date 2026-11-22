"""Sequential design for a 5-ingredient mixture (A..E sum to 100%) under a noisy, unknown response.

Model: Gaussian process on the simplex (Matern-5/2, isotropic, constant mean) with the
hyperparameters (length-scale, noise ratio) *averaged over a grid* weighted by marginal
likelihood, instead of a single point estimate. With only 6-12 points, a single MLE fit
of the length-scale is unstable; averaging keeps the uncertainty honest.

Usage:
    python mixopt.py log.csv            # fit, print diagnostics, suggest next call
    python mixopt.py log.csv --final    # print the formulation to submit
log.csv columns: call,A,B,C,D,E,score,why   (percentages)
"""
import sys, csv
import numpy as np

NAMES = "ABCDE"
CENTROID = np.full(5, 0.2)


def axial_design(level=0.6):
    """Centroid plus one point enriched in each ingredient (level), others equal."""
    pts = [CENTROID.copy()]
    for i in range(5):
        p = np.full(5, (1 - level) / 4)
        p[i] = level
        pts.append(p)
    return np.array(pts)


# --------------------------------------------------------------------------- GP
def matern52(X1, X2, ls):
    d = np.sqrt(np.maximum(((X1[:, None, :] - X2[None, :, :]) ** 2).sum(-1), 0)) / ls
    s5 = np.sqrt(5) * d
    return (1 + s5 + 5 * d**2 / 3) * np.exp(-s5)


class GridGP:
    """GP with constant mean, sigma_f^2 and mean profiled out, (ls, ratio) averaged on a grid."""

    def __init__(self, ls_grid=None, ratio_grid=None):
        self.ls_grid = ls_grid if ls_grid is not None else np.geomspace(0.12, 1.6, 10)
        # ratio = noise variance / signal variance
        self.ratio_grid = ratio_grid if ratio_grid is not None else np.geomspace(0.003, 1.0, 9)

    def fit(self, X, y):
        X, y = np.asarray(X, float), np.asarray(y, float)
        n = len(y)
        self.X, self.y = X, y
        self.models, lmls = [], []
        one = np.ones(n)
        for ls in self.ls_grid:
            K0 = matern52(X, X, ls)
            for r in self.ratio_grid:
                K = K0 + r * np.eye(n)
                L = np.linalg.cholesky(K + 1e-10 * np.eye(n))
                Ki1 = np.linalg.solve(L.T, np.linalg.solve(L, one))
                Kiy = np.linalg.solve(L.T, np.linalg.solve(L, y))
                mu = (one @ Kiy) / (one @ Ki1)
                res = y - mu
                alpha = np.linalg.solve(L.T, np.linalg.solve(L, res))
                s2 = max(res @ alpha / n, 1e-6)
                logdet = 2 * np.log(np.diag(L)).sum()
                # profile (restricted-ish) log-likelihood
                lml = -0.5 * n * np.log(s2) - 0.5 * logdet - 0.5 * np.log(one @ Ki1)
                lmls.append(lml)
                Linv = np.linalg.inv(L)
                self.models.append(dict(ls=ls, r=r, Kinv=Linv.T @ Linv, mu=mu, alpha=alpha, s2=s2, Ki1=Ki1))
        lmls = np.array(lmls)
        w = np.exp(lmls - lmls.max())
        w = w / w.sum()
        keep = w > 1e-4
        self.models = [m for m, k in zip(self.models, keep) if k]
        self.w = w[keep] / w[keep].sum()
        return self

    def _predict_each(self, Xs):
        D = np.sqrt(np.maximum(((Xs[:, None, :] - self.X[None, :, :]) ** 2).sum(-1), 0))
        cache, out = {}, []
        one = np.ones(len(self.y))
        for m in self.models:
            ls = m["ls"]
            if ls not in cache:
                d = D / ls
                s5 = np.sqrt(5) * d
                cache[ls] = (1 + s5 + 5 * d**2 / 3) * np.exp(-s5)
            ks = cache[ls]
            mean = m["mu"] + ks @ m["alpha"]
            var = 1 - np.einsum("ij,jk,ik->i", ks, m["Kinv"], ks, optimize=True)
            u = 1 - ks @ m["Ki1"]  # uncertainty in the constant mean
            var = var + u**2 / (one @ m["Ki1"])
            out.append((mean, np.maximum(var, 1e-9) * m["s2"], m["r"] * m["s2"]))
        return out

    def predict(self, Xs, return_parts=False):
        Xs = np.atleast_2d(Xs)
        parts = self._predict_each(Xs)
        means = np.array([p[0] for p in parts])
        vars_ = np.array([p[1] for p in parts])
        mean = self.w @ means
        var = self.w @ (vars_ + means**2) - mean**2
        if return_parts:
            return mean, np.sqrt(np.maximum(var, 1e-12)), parts
        return mean, np.sqrt(np.maximum(var, 1e-12))

    def noise_sd(self):
        return float(np.sqrt(sum(w * m["r"] * m["s2"] for w, m in zip(self.w, self.models))))

    def ls_mean(self):
        return float(np.exp(sum(w * np.log(m["ls"]) for w, m in zip(self.w, self.models))))

    def expected_improvement(self, Xs, best):
        from scipy.stats import norm
        Xs = np.atleast_2d(Xs)
        ei = np.zeros(len(Xs))
        for w, (mean, var, _) in zip(self.w, self._predict_each(Xs)):
            s = np.sqrt(var)
            z = (mean - best) / s
            ei += w * ((mean - best) * norm.cdf(z) + s * norm.pdf(z))
        return ei


# ------------------------------------------------------------------ search
def candidates(rng, X=None, n=16000):
    parts = [rng.dirichlet(np.ones(5) * a, n // 4) for a in (0.5, 1.0, 2.0, 5.0)]
    C = np.vstack(parts)
    if X is not None and len(X):
        # local perturbations around observed points
        loc = np.repeat(X, 200, axis=0) + rng.normal(0, 0.06, (200 * len(X), 5))
        loc = np.clip(loc, 0, None)
        loc /= loc.sum(1, keepdims=True)
        C = np.vstack([C, loc])
    return C


def refine(fun, X0, rng, iters=60, batch=24, step=0.05):
    """Stochastic hill-climb on the simplex, all starts in parallel (maximize fun)."""
    X0 = np.atleast_2d(X0).copy()
    k0 = len(X0)
    fx = fun(X0)
    for k in range(iters):
        s = step * (1 - k / iters) + 0.003
        P = np.repeat(X0, batch, axis=0) + rng.normal(0, s, (k0 * batch, 5))
        P = np.clip(P, 0, None)
        P /= P.sum(1, keepdims=True)
        fp = fun(P).reshape(k0, batch)
        j = fp.argmax(1)
        better = fp[np.arange(k0), j] > fx
        X0[better] = P.reshape(k0, batch, 5)[np.arange(k0), j][better]
        fx[better] = fp[np.arange(k0), j][better]
    return X0, fx


def argmax_on_simplex(fun, rng, X=None, top=8):
    C = candidates(rng, X)
    v = fun(C)
    idx = np.argsort(v)[-top:]
    Xr, fr = refine(fun, C[idx], rng)
    i = int(np.argmax(fr))
    return Xr[i], fr[i]


def round_pct(x, step=1):
    """Round fractions to integer percentages summing to 100 (largest remainder)."""
    raw = np.asarray(x) * 100 / step
    fl = np.floor(raw)
    short = int(round(100 / step - fl.sum()))
    order = np.argsort(-(raw - fl))
    fl[order[:short]] += 1
    return fl * step


def suggest_next(gp, rng, X):
    m_obs, _ = gp.predict(X)
    incumbent = m_obs.max()
    x, ei = argmax_on_simplex(lambda Z: gp.expected_improvement(Z, incumbent), rng, X)
    return x, ei, incumbent


def recommend(gp, rng, X, kappa=1.0):
    """Formulation to submit: maximize posterior mean - kappa * sd (avoid lucky-but-unsupported)."""
    def f(Z):
        m, s = gp.predict(Z)
        return m - kappa * s
    x, _ = argmax_on_simplex(f, rng, X)
    return x


# ------------------------------------------------------------------ CLI
def load_log(path):
    rows = list(csv.DictReader(open(path)))
    X = np.array([[float(r[k]) for k in NAMES] for r in rows]) / 100
    y = np.array([float(r["score"]) for r in rows])
    return rows, X, y


def fmt(x):
    p = round_pct(x)
    return "/".join(f"{int(v)}" for v in p)


def main():
    path = sys.argv[1]
    final = "--final" in sys.argv
    rng = np.random.default_rng(0)
    rows, X, y = load_log(path)
    gp = GridGP().fit(X, y)
    m, s = gp.predict(X)
    print(f"n={len(y)}  noise sd ~ {gp.noise_sd():.2f}  length-scale ~ {gp.ls_mean():.2f}")
    print("call  A/B/C/D/E        obs    fit   sd")
    for r, xi, yi, mi, si in zip(rows, X, y, m, s):
        print(f"{r['call']:>4}  {fmt(xi):<16} {yi:6.1f} {mi:6.1f} {si:4.1f}")
    rec = recommend(gp, rng, X)
    rm, rs = gp.predict(round_pct(rec)[None] / 100)
    print(f"\nRecommend (mean - 1sd): {fmt(rec)}   predicted {rm[0]:.1f} +/- {rs[0]:.1f}")
    pm = argmax_on_simplex(lambda Z: gp.predict(Z)[0], rng, X)[0]
    pmm, pms = gp.predict(pm[None])
    print(f"Max posterior mean:     {fmt(pm)}   predicted {pmm[0]:.1f} +/- {pms[0]:.1f}")
    if not final:
        x, ei, inc = suggest_next(gp, rng, X)
        nm, ns = gp.predict(round_pct(x)[None] / 100)
        print(f"Next (max EI over incumbent {inc:.1f}): {fmt(x)}  EI={ei:.2f}  "
              f"predicted {nm[0]:.1f} +/- {ns[0]:.1f}")


if __name__ == "__main__":
    main()
