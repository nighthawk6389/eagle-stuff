# 12-call plan for the five-ingredient mixture (A–E, sum = 100%)

## Strategy

| Calls | Purpose | How they're chosen |
|---|---|---|
| 1 | Baseline | Centroid 20/20/20/20/20 |
| 2–6 | Screening | Five points, each 60% of one ingredient and 10% of the rest. Fixed in advance so every ingredient gets an equal test. |
| 7–11 | Search | Fit the noise-aware model (`mixopt.py`) to all results so far, then test the point with the highest expected improvement. Each call depends on every earlier result. |
| 12 | Confirm | Test the formulation the model would submit at that point. This checks it and adds a data point where it matters most. |
| Submit | Final pick | The formulation that maximises *predicted mean − 1 SD* after all 12 calls. This is not the single best reading, which is biased upward by noise. |

Why this shape:
- **5 ingredients but only 4 degrees of freedom.** Fixing four sets the fifth, so the model works on the simplex directly instead of dropping one ingredient.
- **12 calls is fewer than a full quadratic mixture model needs (15 terms).** A Gaussian process with its settings averaged over a grid copes better with so few points. It also estimates noise from the data rather than assuming it.
- **The screening points sit halfway to the corners, not at them.** Pure or 90% formulations are usually poor, so tests there are likely wasted. 60% is still far enough out to show each ingredient's effect clearly.

## Pre-experiment predictions (written before any results)

1. **Centroid (call 1).** I expect a middling score, around 45–65.
   - *High (>75):* balanced blends work and the optimum is probably interior. Search near the centre with small steps.
   - *Low (<35):* the good region is probably dominated by one or two ingredients. Lean on the screening directions and the edges.
2. **Screening points (calls 2–6).** I expect them to spread by 20+ points, with one or two ingredients clearly driving performance.
   - *One point well above the rest:* that ingredient is the main driver. Push further along that direction, even past 60%.
   - *All five below the centroid:* the ingredients work best together. The optimum is interior, so stop pushing extremes.
   - *All within ~5 of each other:* the landscape is flat near the centre and noise is comparable to real effects. Replicating becomes worth a call.
3. **First model-guided point (call 7).** I expect it to land inside its predicted 90% band.
   - *High (above the best so far):* the model's direction is right. Keep exploiting with smaller moves.
   - *Low:* the landscape is more rugged than the model assumed. Its uncertainty grows and it will explore elsewhere.
4. **Confirmation (call 12).** I expect it within about 1.5× noise of its prediction.
   - *Much lower:* the model chased noise. Fall back to the region with the most consistent high readings.

## Where this can fail

- **Narrow peaks.** Twelve points in a 4-D space leave large gaps. A sharp optimum away from every tested point can be missed entirely, and the model will report confidently smooth terrain there.
- **Cliffs and failure regions.** If, say, D > 40% collapses performance, a smooth model will blur the drop and may recommend a point too close to it.
- **Extremes left untested.** The screening design never goes past 60%. If the true optimum is near-pure (90%+ of one ingredient), only the search calls can find it.
- **Noise mis-estimated.** Without many replicates, the model can mistake noise for real bumps or real bumps for noise. Noise that varies by region makes this worse.
