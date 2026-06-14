"""
03  Figures from the real estimates: the pre-trend, and the main coefficients by
    specification. Reads data/, writes figures/. Mirrors the panel build in 02.
"""
from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from linearmodels.panel import PanelOLS
from linearmodels.panel.utility import AbsorbingEffectError

DATA = Path(__file__).resolve().parent.parent / "data"
FIG  = Path(__file__).resolve().parent.parent / "figures"; FIG.mkdir(exist_ok=True)
num = lambda s: pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")
zsc = lambda s: (s - s.mean()) / s.std()
MOODY = {"Aaa":1,"Aa1":2,"Aa2":3,"Aa3":4,"A1":5,"A2":6,"A3":7,"Baa1":8,"Baa2":9,
         "Baa3":10,"Ba1":11,"Ba2":12,"Ba3":13,"B1":14,"B2":15,"B3":16,"Caa1":17,
         "Caa2":18,"Caa3":19,"Ca":20,"C":21}
CTRL = ["lev","log_assets","log_mktcap","wal"]; CTRL_FE = ["wal"]

pan = pd.read_csv(DATA/"issuer_month_oas.csv", parse_dates=["date"])
pan["issuer_key"] = pan.issuer_key.astype(str); pan["fy"] = pan.date.dt.year
pan["rating_num"] = pan.moodys.map(MOODY) if "moodys" in pan.columns else np.nan
pan = pan[(pan.zspread >= 5) & (pan.zspread <= 3000)].copy()
pan["zspread"] = pan.zspread.clip(*pan.zspread.quantile([.01, .99]))

f = pd.read_csv(DATA/"issuer_fundamentals.csv"); f["issuer_key"] = f.issuer_key.astype(str)
for c in ("employees","revenue","debt","net_debt","ebitda","assets","mktcap","ebit","int_exp"): f[c] = num(f[c])
f = f[(f.revenue > 0) & (f.employees > 0) & (f.assets > 0)].copy()
f["naics4"] = f.naics6.astype(str).str[:4]; f["sector"] = f.naics6.astype(str).str[:2]
f["labor_int"] = f.employees / f.revenue * 1e6
f["labor_int"] = f.labor_int.clip(*f.labor_int.quantile([.01, .99]))
f["lev"] = f.debt / f.assets; f["log_assets"] = np.log(f.assets); f["log_mktcap"] = np.log(f.mktcap.clip(lower=1))
f["z_labor"] = zsc(f.labor_int); f = f[~f.sector.isin(["52","92"])]
exp = pd.read_csv(DATA/"industry_exposure_4d_2025.csv"); exp["naics4"] = exp.naics4.astype(str)
f = f.merge(exp[["naics4","capability","adoption"]], on="naics4", how="left")
m = pan.merge(f[["issuer_key","sector","z_labor","capability","adoption","lev","log_assets","log_mktcap"]],
              on="issuer_key", how="inner")
m["post"] = (m.date >= "2022-11-01").astype(int); m["E"] = m.capability * m.z_labor; m["E_post"] = m.E * m.post
m["sector_code"] = m.sector.astype("category").cat.codes
m["sm"] = (m.sector + "_" + m.date.dt.strftime("%Y%m")).astype("category").cat.codes
m = m.dropna(subset=["zspread","E"]+CTRL); m["yr"] = m.date.dt.year

def fit(dv, rhs, entity, time, other):
    d = m.dropna(subset=[dv]+rhs+([other] if other else [])).set_index(["issuer_key","date"])
    kw = dict(entity_effects=entity, time_effects=time)
    if other: kw["other_effects"] = d[[other]]
    return PanelOLS(d[dv], d[rhs], **kw).fit(cov_type="clustered", cluster_entity=True)

# fig 1: pre-trend
yrs = sorted(y for y in m.yr.unique() if y != 2021)
for y in yrs: m[f"E_{y}"] = m.E * (m.yr == y)
rhs = [f"E_{y}" for y in yrs] + CTRL_FE
while True:
    try: r = fit("zspread", rhs, True, True, None); break
    except AbsorbingEffectError as ex:
        nr = [c for c in rhs if c not in str(ex)]
        if nr == rhs: raise
        rhs = nr
allyrs = sorted(m.yr.unique())
coef = [0.0 if y == 2021 else r.params.get(f"E_{y}", np.nan) for y in allyrs]
se   = [0.0 if y == 2021 else r.std_errors.get(f"E_{y}", np.nan) for y in allyrs]
plt.figure(figsize=(7,4)); plt.axhline(0, color="#888", lw=.8)
plt.axvline(2022.83, color="#c00", ls="--", lw=1, label="ChatGPT")
plt.errorbar(allyrs, coef, yerr=[1.96*x for x in se], fmt="o-", capsize=3, color="#2F5496")
plt.title("Pre-trend: exposure x year on Z-spread (base 2021)")
plt.ylabel("basis points"); plt.xlabel("year"); plt.legend(); plt.tight_layout()
plt.savefig(FIG/"fig1_pretrend.png", dpi=130); plt.close()

# fig 2: main coefficients by specification
specs = []
b = fit("zspread", ["E"]+CTRL, False, True, "sector_code"); specs.append(("baseline (sector+month FE)", b.params["E"], b.std_errors["E"]))
e = fit("zspread", ["E_post"]+CTRL_FE, True, False, "sm");  specs.append(("event (E x post)", e.params["E_post"], e.std_errors["E_post"]))
m["triple"] = m.capability*m.z_labor*m.post; m["cap_post"] = m.capability*m.post; m["lab_post"] = m.z_labor*m.post
t = fit("zspread", ["triple","cap_post","lab_post"]+CTRL_FE, True, False, "sm"); specs.append(("triple difference", t.params["triple"], t.std_errors["triple"]))
d = m.dropna(subset=["zspread","E","rating_num"]+CTRL).set_index(["issuer_key","date"])
rc = PanelOLS(d.zspread, d[["E"]+CTRL+["rating_num"]], time_effects=True, other_effects=d[["sector_code"]]
              ).fit(cov_type="clustered", cluster_entity=True)
specs.append(("cross-section, rating-controlled", rc.params["E"], rc.std_errors["E"]))
labels = [s[0] for s in specs]; vals = [s[1] for s in specs]; ses = [s[2] for s in specs]
plt.figure(figsize=(7.5,4)); yy = list(range(len(specs)))
plt.axvline(0, color="#888", lw=.8)
plt.errorbar(vals, yy, xerr=[1.96*x for x in ses], fmt="o", capsize=3, color="#2F5496")
plt.yticks(yy, labels); plt.gca().invert_yaxis()
plt.xlabel("exposure coefficient on Z-spread (basis points), 95% CI")
plt.title("AI displacement exposure and credit spread")
plt.tight_layout(); plt.savefig(FIG/"fig2_coefficients.png", dpi=130); plt.close()
print("wrote figures to", FIG)
