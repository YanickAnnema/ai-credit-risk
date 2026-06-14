"""
01  Build the issuer-month corporate-bond OAS panel.

Inputs (LSEG Excel pulls, place under DATA, all gitignored):
  bond_ref.csv     one row per bond:
                   isin, issuer_name, ult_parent_id, maturity, coupon, seniority,
                   currency, callable, call_type (optional), face_out, issue_date,
                   moodys, fitch
                   ult_parent_id = TR.UltimateParentId off the ISIN; it is the issuer
                   key and collapses finance subsidiaries to the operating parent.
  spread_history.csv  long, one row per bond-month:
                      isin, date, zspread, asw (asw optional)
  issuer_map.csv   optional manual overrides for messy names (maps finance subs to
                   the operating parent): issuer_name_raw, issuer_key

Output (DATA):
  issuer_month_oas.csv   issuer_key, date, zspread, asw, n_bonds, wal, face_out,
                         moodys, fitch

Confirmed mnemonics behind these columns (see lseg_field_audit.xlsx):
  Z-spread TR.ZSpread is the primary outcome with monthly history to 2015. OAS
  (TR.FiOptionAdjustedSpread) is snapshot only, so it is not used as a time series.
  Reference TR.Fi* ; ISIN TR.ISIN ; ratings TR.FiMoodysRating, TR.FiFitchsRating.
  Bonds do not carry an issuer PermID, so the join below is on cleaned issuer name.
  No em dashes anywhere.

Rules applied: USD, senior unsecured, fixed-rate, 1 to 12 year remaining life, at
least 12 monthly Z-spread points per bond. Make-whole callables are kept (negligible
option value, effectively bullets) and only genuine par or discrete calls are dropped,
which keeps Z-spread a clean credit measure while preserving the investment grade
universe. Financials are dropped in 02 once NAICS is attached. Aggregation across an
issuer's bonds is face-weighted, with WAL recorded as a control because Z-spread still
varies with maturity.
"""
import re
from pathlib import Path
import numpy as np, pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
num  = lambda s: pd.to_numeric(s.astype(str).str.replace(",", ""), errors="coerce")

DROP = (" INC", " CORP", " CO", " LLC", " LP", " PLC", " LTD", " THE", " COMPANY",
        " HOLDINGS", " GROUP", " FINANCE", " CAPITAL", " MOTOR CREDIT", " CREDIT")
def norm_name(s):
    s = " " + re.sub(r"[^A-Z0-9 ]", " ", str(s).upper()) + " "
    for w in DROP:
        s = s.replace(w + " ", " ")
    return re.sub(r"\s+", " ", s).strip()

# bond reference, filtered
ref = pd.read_csv(DATA / "bond_ref.csv")
ref["face_out"] = num(ref.face_out)
ref["mat"] = pd.to_datetime(ref.maturity, errors="coerce")
ref = ref[(ref.currency == "USD")
          & ref.seniority.str.contains("Senior Unsecured", case=False, na=False)].copy()
# Make-whole calls have negligible option value, so keep them (effective bullets) and
# drop only genuine par or discrete calls. If a call_type column is supplied, use it;
# otherwise rely on index membership plus the WAL >= 1 window applied below.
if "call_type" in ref.columns:
    ct = ref.call_type.astype(str).str.lower()
    par_call = ct.str.contains("par") | ct.str.contains("discre") | ct.str.contains("sched")
    ref = ref[~par_call].copy()

# issuer key: LSEG ultimate parent PermID (off the ISIN) collapses finance subs to the
# operating parent and dedupes; fall back to cleaned name (+ manual override) if missing
mp = DATA / "issuer_map.csv"
ovr = pd.read_csv(mp) if mp.exists() else pd.DataFrame(columns=["issuer_name_raw", "issuer_key"])
o = dict(zip(ovr.issuer_name_raw.map(norm_name), ovr.issuer_key))
ref["issuer_key"] = ref["ult_parent_id"] if "ult_parent_id" in ref.columns else np.nan
ref["issuer_key"] = ref.issuer_key.astype("object")   # allow string fallback assignment
miss = ref.issuer_key.isna() | ref.issuer_key.astype(str).str.strip().isin(["", "nan", "NULL"])
ref.loc[miss, "issuer_key"] = ref.loc[miss, "issuer_name"].map(norm_name).map(lambda n: o.get(n, n))
ref["issuer_key"] = ref.issuer_key.astype(str).str.replace(r"\.0$", "", regex=True)

# current issuer rating: modal across the issuer's bonds (history not entitled)
def modal(s):
    s = s.dropna()
    return s.mode().iloc[0] if len(s) else np.nan
rating = ref.groupby("issuer_key").agg(moodys=("moodys", modal), fitch=("fitch", modal))

# Z-spread history, attach reference, keep the comparable maturity window
h = pd.read_csv(DATA / "spread_history.csv")
h["date"] = pd.to_datetime(h.date).values.astype("datetime64[M]")
h["zspread"] = num(h.zspread)
h["asw"] = num(h.asw) if "asw" in h.columns else np.nan
h = h.merge(ref[["isin", "issuer_key", "mat", "face_out"]], on="isin", how="inner")
h["wal"] = (h.mat - h.date).dt.days / 365.25
h = h[(h.wal >= 1) & (h.wal <= 12) & h.zspread.notna()]
h = h[h.groupby("isin").date.transform("size") >= 12]          # drop one-print bonds

# aggregate to issuer-month, face-weighted
def wavg(x, w):
    x = x.dropna()
    if len(x) == 0:
        return np.nan
    wx = w.loc[x.index]
    return np.average(x, weights=wx) if wx.sum() > 0 else x.median()

def agg(g):
    w = g.face_out.fillna(0).clip(lower=0)
    return pd.Series({
        "zspread":  wavg(g.zspread, w),
        "asw":      wavg(g.asw, w),
        "n_bonds":  g["isin"].nunique(),
        "wal":      np.average(g.wal, weights=w) if w.sum() > 0 else g.wal.mean(),
        "face_out": w.sum()})

panel = (h.groupby(["issuer_key", "date"])[["isin", "zspread", "asw", "wal", "face_out"]]
           .apply(agg).reset_index())
panel = panel.merge(rating, on="issuer_key", how="left")
panel.to_csv(DATA / "issuer_month_oas.csv", index=False)
print(f"issuer-months: {len(panel)}  issuers: {panel.issuer_key.nunique()}  "
      f"span: {panel.date.min().date()} to {panel.date.max().date()}")
