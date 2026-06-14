"""
02  Merge exposure and controls, run the credit DiD.  Mirrors the ai-exposure repo
    script 04 (FE panel, clustered SEs, year-by-year pre-trend).

Inputs under DATA:
  issuer_month_oas.csv          from 01 (issuer_key, date, zspread, asw, n_bonds, wal,
                                face_out, moodys, fitch)
  issuer_fundamentals.csv       LSEG latest-FY snapshot, one row per operating parent,
                                keyed by ultimate parent PermID (= issuer_key from 01),
                                monetary fields in USD (Curn=USD):
                                issuer_key, common_name, naics6, employees, revenue,
                                debt, net_debt, ebitda, assets, mktcap, ebit, int_exp
  industry_exposure_4d_2025.csv reused (naics4, capability, adoption)
  firm_ai_intensity.csv         reused; needs issuer_key (or permid) and ai_per_10k

Outcome Z-spread in bps (OAS is snapshot only). Exposure E = industry capability x
z(labor intensity), a static issuer trait. Because fundamentals are a static snapshot,
the baseline uses sector and month FE (no issuer FE, which would absorb the exposure
level); the event, triple difference and pre-trend specs keep issuer FE because their
regressors are exposure x time. post = date >= 2022-11. No em dashes anywhere.
"""
from pathlib import Path
import numpy as np, pandas as pd
from linearmodels.panel import PanelOLS

DATA = Path(__file__).resolve().parent.parent / "data"
num = lambda s: pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")
zsc = lambda s: (s - s.mean()) / s.std()
MOODY = {"Aaa":1,"Aa1":2,"Aa2":3,"Aa3":4,"A1":5,"A2":6,"A3":7,"Baa1":8,"Baa2":9,
         "Baa3":10,"Ba1":11,"Ba2":12,"Ba3":13,"B1":14,"B2":15,"B3":16,"Caa1":17,
         "Caa2":18,"Caa3":19,"Ca":20,"C":21}
CTRL    = ["lev", "log_assets", "log_mktcap", "wal"]   # full set, for the pooled baseline
CTRL_FE = ["wal"]                                      # time-varying only, for issuer-FE specs

pan = pd.read_csv(DATA / "issuer_month_oas.csv", parse_dates=["date"])
pan["issuer_key"] = pan.issuer_key.astype(str)
pan["fy"] = pan.date.dt.year
pan["rating_num"] = pan.moodys.map(MOODY) if "moodys" in pan.columns else np.nan
pan = pan[(pan.zspread >= 5) & (pan.zspread <= 3000)].copy()          # drop broken/defaulted spreads
pan["zspread"] = pan.zspread.clip(*pan.zspread.quantile([.01, .99]))  # winsorize 1/99

# fundamentals: static latest-FY snapshot per operating parent
f = pd.read_csv(DATA / "issuer_fundamentals.csv")
f["issuer_key"] = f.issuer_key.astype(str)
for c in ("employees","revenue","debt","net_debt","ebitda","assets","mktcap","ebit","int_exp"):
    f[c] = num(f[c])
f = f[(f.revenue > 0) & (f.employees > 0) & (f.assets > 0)].copy()
f["naics4"]     = f.naics6.astype(str).str[:4]
f["sector"]     = f.naics6.astype(str).str[:2]
f["labor_int"]  = f.employees / f.revenue * 1e6            # employees per $m revenue (USD)
f["labor_int"]  = f.labor_int.clip(*f.labor_int.quantile([.01, .99]))  # winsorize heavy skew
f["lev"]        = f.debt / f.assets
f["log_assets"] = np.log(f.assets)
f["log_mktcap"] = np.log(f.mktcap.clip(lower=1))
f["z_labor"]    = zsc(f.labor_int)
f = f[~f.sector.isin(["52", "92"])]                        # drop financials and government

exp = pd.read_csv(DATA / "industry_exposure_4d_2025.csv")
exp["naics4"] = exp.naics4.astype(str)
f = f.merge(exp[["naics4","capability","adoption"]], on="naics4", how="left")

m = pan.merge(f[["issuer_key","sector","z_labor","capability","adoption",
                 "lev","log_assets","log_mktcap"]], on="issuer_key", how="inner")

# optional firm AI text measure (adoption channel); aligns on PermID = issuer_key
aip = DATA / "firm_ai_intensity.csv"
ai = pd.read_csv(aip) if aip.exists() and aip.stat().st_size > 0 else pd.DataFrame()
if "issuer_key" not in ai.columns and "permid" in ai.columns:
    ai["issuer_key"] = ai.permid.astype(str).str.replace(r"\.0$", "", regex=True)
if {"issuer_key","ai_per_10k"} <= set(ai.columns):
    ai["issuer_key"] = ai.issuer_key.astype(str)
    cap99 = num(ai.ai_per_10k).quantile(.99)
    ai["z_ai"] = zsc(np.log1p(num(ai.ai_per_10k).clip(upper=cap99)))
    m = m.merge(ai[["issuer_key","z_ai"]].drop_duplicates("issuer_key"), on="issuer_key", how="left")
    print(f"firm AI measure matched: {m.z_ai.notna().sum()} issuer-months, "
          f"{m.loc[m.z_ai.notna(),'issuer_key'].nunique()} issuers (US 10-K subset)")

m["post"]        = (m.date >= "2022-11-01").astype(int)
m["E"]           = m.capability * m.z_labor
m["E_post"]      = m.E * m.post
m["sector_code"] = m.sector.astype("category").cat.codes
m["sm"]          = (m.sector + "_" + m.date.dt.strftime("%Y%m")).astype("category").cat.codes
m = m.dropna(subset=["zspread","E"] + CTRL)
print(f"panel: {len(m)} issuer-months, {m.issuer_key.nunique()} parents, "
      f"{m.date.min().date()}..{m.date.max().date()}")

def pooled(dv, rhs):                                       # sector FE + month FE, no issuer FE
    d = m.dropna(subset=[dv]+rhs).set_index(["issuer_key","date"])
    return PanelOLS(d[dv], d[rhs], time_effects=True, other_effects=d[["sector_code"]]
                    ).fit(cov_type="clustered", cluster_entity=True)

def twfe(dv, rhs):                                         # issuer FE + month FE
    d = m.dropna(subset=[dv]+rhs).set_index(["issuer_key","date"])
    return PanelOLS(d[dv], d[rhs], entity_effects=True, time_effects=True
                    ).fit(cov_type="clustered", cluster_entity=True)

def smfe(dv, rhs):                                         # issuer FE + sector-month FE
    d = m.dropna(subset=[dv]+rhs+["sm"]).set_index(["issuer_key","date"])
    return PanelOLS(d[dv], d[rhs], entity_effects=True, other_effects=d[["sm"]]
                    ).fit(cov_type="clustered", cluster_entity=True)

def twfe_safe(dv, rhs):                                    # twfe, dropping any absorbed terms
    from linearmodels.panel.utility import AbsorbingEffectError
    cur = list(rhs)
    while cur:
        try:
            return twfe(dv, cur)
        except AbsorbingEffectError as ex:
            drop = [c for c in cur if c in str(ex)]
            if not drop:
                raise
            cur = [c for c in cur if c not in drop]
    raise RuntimeError("all regressors absorbed")

# 1 baseline cross-section: exposure level on spread, sector + month FE (no issuer FE)
b = pooled("zspread", ["E"]+CTRL)
print(f"[baseline]    E {b.params['E']:+.2f} bps (p {b.pvalues['E']:.3f})  n={int(b.nobs)}")

# 2 event: E x post, issuer FE + sector-month FE absorbs the rate cycle per sector
e = smfe("zspread", ["E_post"]+CTRL_FE)
print(f"[event smFE]  E_post {e.params['E_post']:+.2f} bps (p {e.pvalues['E_post']:.3f})")

# 3 triple difference: automatability x labor x post
m["cap_post"] = m.capability * m.post
m["lab_post"] = m.z_labor * m.post
m["triple"]   = m.capability * m.z_labor * m.post
t = smfe("zspread", ["triple","cap_post","lab_post"]+CTRL_FE)
print(f"[triple]      cap x labor x post {t.params['triple']:+.2f} bps (p {t.pvalues['triple']:.3f})")

# 4 pre-trend: E x year, base 2021
m["yr"] = m.date.dt.year
yrs = sorted(y for y in m.yr.unique() if y != 2021)
for y in yrs:
    m[f"E_{y}"] = m.E * (m.yr == y)
pt = twfe_safe("zspread", [f"E_{y}" for y in yrs] + CTRL_FE)
print("[pre-trend] E x year (base 2021):")
print("  " + "  ".join(f"{y}:{(0.0 if y==2021 else pt.params.get(f'E_{y}', float('nan'))):+.1f}"
                        for y in sorted(m.yr.unique())))

# 5 adoption vs displacement: opposite signs expected
if "z_ai" in m.columns:
    m["ai_post"] = m.z_ai * m.post
    ad = smfe("zspread", ["E_post","ai_post"]+CTRL_FE)
    print(f"[adopt v disp] displacement {ad.params['E_post']:+.2f} (p {ad.pvalues['E_post']:.3f})  "
          f"adoption {ad.params['ai_post']:+.2f} (p {ad.pvalues['ai_post']:.3f})  n={int(ad.nobs)}")

# 6 specification curve: outcome x exposure source x sample
rows = []
samples = {"all": m.index == m.index, "IG": m.rating_num <= 10, "HY": m.rating_num > 10}
outcomes = [c for c in ("zspread","asw") if c in m.columns and m[c].notna().any()]
for dv in outcomes:
    for src in ("capability","adoption"):
        mm = m.assign(Ex=m[src] * m.z_labor * m.post)
        for samp, mask in samples.items():
            d = mm[mask].dropna(subset=[dv,"Ex"]+CTRL_FE+["sm"]).set_index(["issuer_key","date"])
            if len(d) < 500:
                continue
            r = PanelOLS(d[dv], d[["Ex"]+CTRL_FE], entity_effects=True,
                         other_effects=d[["sm"]]).fit(cov_type="clustered", cluster_entity=True)
            rows.append((dv, src, samp, round(r.params["Ex"],2), round(r.pvalues["Ex"],3), int(r.nobs)))
spec = pd.DataFrame(rows, columns=["outcome","exposure","sample","beta","p","n"])
print("\nspecification curve:"); print(spec.to_string(index=False))
spec.to_csv(DATA / "spec_curve.csv", index=False)

# 7 robustness
print("\n-- robustness --")
m["lz"] = np.log(m.zspread)                                 # log Z-spread outcome
lb = pooled("lz", ["E"]+CTRL)
print(f"[log baseline]   E {lb.params['E']:+.4f} log-pts (p {lb.pvalues['E']:.3f})")
le = smfe("lz", ["E_post"]+CTRL_FE)
print(f"[log event]      E_post {le.params['E_post']:+.4f} log-pts (p {le.pvalues['E_post']:.3f})")

d = m.dropna(subset=["zspread","E_post"]+CTRL_FE+["sm"]).set_index(["issuer_key","date"])
e2 = PanelOLS(d.zspread, d[["E_post"]+CTRL_FE], entity_effects=True, other_effects=d[["sm"]]
              ).fit(cov_type="clustered", cluster_entity=True, cluster_time=True)
print(f"[event 2-way cl] E_post {e2.params['E_post']:+.2f} bps (p {e2.pvalues['E_post']:.3f})  "
      "(cluster issuer + month)")

dr = m.dropna(subset=["zspread","E","rating_num","sector_code"]+CTRL).set_index(["issuer_key","date"])
rc = PanelOLS(dr.zspread, dr[["E"]+CTRL+["rating_num"]], time_effects=True,
              other_effects=dr[["sector_code"]]).fit(cov_type="clustered", cluster_entity=True)
print(f"[rating-ctrl base] E {rc.params['E']:+.2f} bps (p {rc.pvalues['E']:.3f})  n={int(rc.nobs)}")
