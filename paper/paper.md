# Is AI displacement risk priced in corporate credit?

Yanick Annema. Working draft, June 2026.

## Summary

I test whether the risk that artificial intelligence displaces an issuer's workforce
shows up in the price of its bonds. The exposure measure combines how automatable an
industry's tasks are with how much labor weighs in the issuer's cost base, so two
firms in the same industry with different labor intensity get different exposure. The
outcome is the monthly Z-spread on senior unsecured USD bonds, 2015 to 2026, for 344
non-financial issuers. The answer is no, at least not robustly. Point estimates are
mostly the sign the disruption hypothesis predicts, more exposure goes with wider
spreads, but they are economically modest and do not clear conventional significance.
The one specification that comes close is a cross-section that conditions on the
credit rating, where a one standard deviation increase in exposure is associated with
about 14 basis points of extra spread (p = 0.086). Pre-trends are flat, so the design
is not driving the result. This extends an earlier null on equity pricing to a second
asset class, and it does so with a cleaner identification.

## Question

Generative AI can read two ways for a creditor. It can be an efficiency gain that
lowers costs and tightens spreads, or a competitive threat that erodes the revenue of
issuers whose work is automatable and widens them. Credit is an asymmetric claim, so
disruption risk should show up in spreads before it shows up in equity, if it shows up
anywhere. The existing literature on technology and bond spreads frames technology as
a positive, finds that corporate digital transformation lowers spreads, and is almost
entirely about Chinese issuers. Nobody has priced AI as a downside risk to the issuers
most exposed to it, and nobody has done it on US and global USD credit. That is the
gap this note addresses.

## Exposure measure

A pure industry exposure score cannot be identified once sector fixed effects are
included, because theoretical AI capability and observed adoption are almost perfectly
correlated at the industry level. To get firm level variation I interact two pieces.

Industry automatability is the employment weighted average AI exposure of the
occupations that make up an industry, built from the Eloundou et al. occupation scores
and the BLS OEWS national industry by occupation employment matrix. Firm labor
intensity is employees divided by revenue, in USD, winsorized at the first and
ninety ninth percentiles to tame a heavy right tail.

Firm exposure E is industry automatability times the standardized labor intensity. A
firm's cash flows are exposed to the automation shock in proportion to both how
automatable its industry is and how much labor weighs in its costs. This survives
sector fixed effects because labor intensity varies across firms within an industry.

## Data

The bond universe is every USD senior unsecured, fixed rate, non perpetual corporate
bond with at least 500 million USD outstanding, 7,190 bonds from LSEG. Each bond maps
to its operating parent through the LSEG ultimate parent identifier, which collapses
finance subsidiaries onto the parent that issues the financial statements (Ford Motor
Credit onto Ford, John Deere Capital onto Deere). That gives 1,391 distinct parents.
Dropping financials and government issuers and keeping parents that report employees
and revenue leaves 679 issuers. Fundamentals are a latest year snapshot pulled in USD,
so labor intensity is comparable across reporting currencies.

The outcome is the monthly Z-spread (LSEG TR.ZSpread), which has clean history back to
2015. Option adjusted spread is snapshot only in this entitlement, and the universe is
restricted to non callable and make whole bonds, so the lack of option adjustment in
the Z-spread costs nothing. Bond level spreads are aggregated to one face weighted
issuer month series, keeping bonds with one to twelve years to maturity. After merging
to fundamentals and exposure the panel is 22,414 issuer months across 344 issuers.

One data point is worth a sentence. Raw Z-spreads contain errors as large as 3.3
million basis points and a labor intensity tail above fifteen standard deviations.
Before any cleaning these leverage points produced coefficients in the hundreds and
thousands of basis points. Winsorizing the spread and the exposure at the first and
ninety ninth percentiles, and dropping spreads above 3,000 basis points as errors,
removes them and is the difference between noise and a usable estimate.

## Method

The outcome is the issuer month Z-spread in basis points. Specifications, in order of
how much they lean on the design:

1. Baseline cross-section. Z-spread on exposure with sector and month fixed effects.
   No issuer fixed effects, because exposure is a static issuer trait that issuer
   effects would absorb. Controls are leverage, log assets, log market cap, and
   weighted average life.
2. Event. Exposure interacted with a post indicator for November 2022, with issuer and
   sector by month fixed effects so the 2022 rate cycle is absorbed within each sector.
3. Triple difference. Industry automatability times labor intensity times post, which
   isolates the labor displacement channel.
4. Pre-trend. Exposure interacted with each calendar year, base year 2021.
5. Specification curve over outcome, exposure source, and rating sample.

Standard errors are clustered by issuer, and by issuer and month together in a
robustness check.

## Results

The table is a null with right signed point estimates.

| Specification | Estimate | p value |
|---|---|---|
| Baseline, sector and month FE | +19.0 bps | 0.16 |
| Event, exposure times post | +13.6 bps | 0.37 |
| Triple difference | +43.0 bps | 0.28 |
| Log Z-spread baseline | +0.047 log points | 0.46 |
| Log Z-spread event | +0.079 log points | 0.16 |
| Event, two way clustering | +13.6 bps | 0.36 |
| Cross-section controlling for rating | +14.1 bps | 0.086 |
| Adoption channel, US subset, displacement | +6.9 bps | 0.71 |
| Adoption channel, US subset, adoption (firm AI text) | +4.2 bps | 0.18 |

Every point estimate is positive, which is the direction the disruption hypothesis
predicts: issuers more exposed to AI displacement trade somewhat wider. None of the
headline specifications is significant at five percent. The pre-trend is flat, with
year coefficients between minus twenty one and plus seventeen basis points and no
trend (Figure 1), so the post 2022 comparison is not built on a pre-existing
divergence. The specification curve shows the effect is positive in the full sample
and in investment grade, and flips negative in high yield, with nothing significant.
Figure 2 collects the main coefficients with their confidence intervals.

![Figure 1. Pre-trend, exposure times year on Z-spread, base 2021.](../figures/fig1_pretrend.png)

![Figure 2. Exposure coefficient on Z-spread by specification, 95 percent intervals.](../figures/fig2_coefficients.png)

The cross-section that conditions on the credit rating is the exception worth naming.
Within a rating notch, a one standard deviation increase in exposure is associated
with about fourteen basis points of additional spread, significant at ten percent but
not five. One reading is that rating agencies have not yet absorbed AI displacement
risk, so it survives in the spread only after the rating is held fixed. That is a
hypothesis the data here cannot confirm, not a conclusion.

Adding the firm level AI text measure, available for the 255 US filers in the panel,
gives no sign of the pattern the digital transformation literature would predict. In
that work, firms that adopt technology trade tighter. Here, in one regression that
includes both channels, the displacement exposure is +6.9 basis points (p = 0.71) and
the adoption measure is +4.2 basis points (p = 0.18). Both are small, both positive,
neither significant. Talking about AI in a filing does not buy an issuer a tighter
spread, and being exposed to displacement does not clearly cost one. The opposite
signs the contrast was designed to detect do not appear.

## Limitations

Exposure is a static snapshot, so the design identifies dynamic effects through the
interaction with time rather than within issuer changes in labor intensity. The
adoption channel is included, using the firm level AI text measure for the US filers
in the panel, and it is null, so the displacement versus adoption contrast does not
separate in credit. The sample is investment grade heavy, where spreads are compressed
and any displacement premium is hardest to detect. And the exposure measure is
industry automatability scaled by firm labor intensity, which is a proxy for the true
object, the share of an issuer's cash flows at risk from automation.

## Conclusion

AI displacement risk is not robustly priced in corporate credit spreads through early
2026, even though the point estimates lean the way the disruption story predicts and
the cross-section that controls for rating is marginally significant. The contribution
is a clean, well identified null on a question where the prior literature only studied
technology as a credit positive and only in one country. A null that survives a flat
pre-trend, two way clustering, a log outcome, and a rating control is a finding about
how slowly credit markets, or the issuers themselves, are repricing for AI, not an
absence of evidence.
