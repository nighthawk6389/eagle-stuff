"""Dry-run the 12-call protocol against random synthetic 'labs' to check that it beats simple
alternatives and to find out where it fails. These synthetic labs are NOT the real lab.

python sim.py [n_functions] [noise_sd]
"""
import sys
import numpy as np
from multiprocessing import Pool
import mixopt as mo


def make_lab(seed):
    rng = np.random.default_rng(seed)
    kind = ["bumps", "quad"][seed % 2]
    if kind == "bumps":
        K = rng.integers(1, 4)
        C = rng.dirichlet(np.ones(5), K)
        W = rng.uniform(0.12, 0.35, K)
        A = rng.uniform(0.3, 1.0, K)
        A[0] = 1.0
        beta = rng.normal(0, 0.3, 5)

        def raw(X):
            d2 = ((X[:, None, :] - C[None]) ** 2).sum(-1)
            return (A * np.exp(-d2 / (2 * W**2))).sum(1) + X @ beta
    else:
        b1 = rng.normal(0, 1, 5)
        b2 = rng.normal(0, 3, (5, 5))
        b3 = rng.normal(0, 10, (5, 5, 5)) * (rng.random((5, 5, 5)) < 0.15)

        def raw(X):
            return (X @ b1 + np.einsum("ni,ij,nj->n", X, b2, X)
                    + np.einsum("ni,ijk,nj,nk->n", X, b3, X, X))
    Z = rng.dirichlet(np.ones(5) * 0.7, 200000)
    v = raw(Z)
    vmax = mo.refine(raw, Z[np.argsort(v)[-5:]], rng, iters=150)[1].max()
    vmin = v.min()
    lo, hi = rng.uniform(5, 30), rng.uniform(80, 95)

    def f(X):
        return lo + (hi - lo) * (raw(np.atleast_2d(X)) - vmin) / (vmax - vmin)
    return f, hi, kind


def run(args):
    seed, noise = args
    f, fmax, kind = make_lab(seed)
    rng = np.random.default_rng(10_000 + seed)
    obs = lambda X: np.clip(f(X) + rng.normal(0, noise, len(np.atleast_2d(X))), 0, 100)
    res = {"kind": kind}

    def adaptive(X, y, n_ei, confirm):
        X, y = list(X), list(y)
        for _ in range(n_ei):
            gp = mo.GridGP().fit(np.array(X), np.array(y))
            x, _, _ = mo.suggest_next(gp, rng, np.array(X))
            x = mo.round_pct(x) / 100
            X.append(x); y.append(obs(x[None])[0])
        if confirm:
            gp = mo.GridGP().fit(np.array(X), np.array(y))
            x = mo.round_pct(mo.recommend(gp, rng, np.array(X))) / 100
            X.append(x); y.append(obs(x[None])[0])
        X, y = np.array(X), np.array(y)
        gp = mo.GridGP().fit(X, y)
        rec = mo.recommend(gp, rng, X)
        pm, ps = gp.predict(rec[None])
        return X, y, rec, pm[0], ps[0]

    gap = lambda x: fmax - f(x[None])[0]

    X0 = mo.axial_design(0.6)
    y0 = obs(X0)
    X, y, rec, pm, ps = adaptive(X0, y0, 5, True)
    res["axial60+EI5+confirm"] = gap(rec)
    res["  same, submit best observed"] = gap(X[np.argmax(y)])
    res["_cover"] = abs(f(rec[None])[0] - pm) <= 1.645 * ps
    X, y, rec, _, _ = adaptive(X0, y0, 6, False)
    res["axial60+EI6"] = gap(rec)

    X0b = mo.axial_design(0.5)
    X, y, rec, _, _ = adaptive(X0b, obs(X0b), 5, True)
    res["axial50+EI5+confirm"] = gap(rec)

    R = rng.dirichlet(np.ones(5), 6)
    X, y, rec, _, _ = adaptive(R, obs(R), 5, True)
    res["random6+EI5+confirm"] = gap(rec)

    R = rng.dirichlet(np.ones(5), 12)
    yr = obs(R)
    res["random12, best observed"] = gap(R[np.argmax(yr)])
    gp = mo.GridGP().fit(R, yr)
    res["random12, GP recommend"] = gap(mo.recommend(gp, rng, R))
    res["centroid only"] = gap(mo.CENTROID)
    return res


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    noise = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
    with Pool(4) as p:
        out = p.map(run, [(s, noise) for s in range(n)])
    keys = [k for k in out[0] if k not in ("kind", "_cover")]
    print(f"{n} synthetic labs, noise sd {noise}. Shortfall vs true optimum (score points):")
    print(f"{'strategy':<32}{'median':>8}{'mean':>8}{'p90':>8}{'within 5':>10}")
    for k in keys:
        g = np.array([o[k] for o in out])
        print(f"{k:<32}{np.median(g):8.1f}{g.mean():8.1f}{np.percentile(g, 90):8.1f}{(g <= 5).mean():10.0%}")
    for kind in ("bumps", "quad"):
        g = np.array([o["axial60+EI5+confirm"] for o in out if o["kind"] == kind])
        print(f"main strategy on {kind:<6}: median {np.median(g):.1f}, p90 {np.percentile(g, 90):.1f}")
    print(f"90% interval covered true value of submission: {np.mean([o['_cover'] for o in out]):.0%}")
