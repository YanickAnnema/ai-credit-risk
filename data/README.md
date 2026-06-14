# Data inputs

Scripts read these from `data/`. Licensed files are not redistributed; the `.gitignore`
blocks them. Build the licensed files from LSEG with the field lists below, then run the
code.

## Shared here (public-derived)

| File | What it is | Source and license |
|---|---|---|
| `industry_exposure_4d_2025.csv` | AI capability and adoption by 4 digit NAICS, employment weighted | Eloundou et al. GPT occupation scores and BLS OEWS May 2025 national industry employment. Public. |
| `firm_ai_intensity.csv` (optional) | Firm AI text intensity from 10-K filings, keyed by PermID | SEC EDGAR. Public. Used only for the adoption channel. |

## Licensed (LSEG, not included)

Build these with the LSEG Excel add-in. All monetary fundamentals are pulled in USD
(`Curn=USD`). Bonds map to the operating parent through `TR.UltimateParentId`.

### `bond_ref.csv`, one row per bond
`isin, issuer_name, ult_parent_id, coupon, maturity, seniority, currency, callable,
call_type (optional), face_out, issue_date, moodys, fitch`

Mnemonics: `TR.ISIN, TR.FiIssuerName, TR.UltimateParentId, TR.FiCouponRate,
TR.FiMaturityDate, TR.FiSeniorityTypeDescription, TR.FiCurrency, TR.FiIsCallable,
TR.FiFaceOutstanding, TR.FiIssueDate, TR.FiMoodysRating, TR.FiFitchsRating`.

Universe: USD, senior unsecured, fixed rate, non perpetual, amount outstanding at
least 500 million USD. Found through the Workspace Advanced Bond Search and exported,
because the worksheet SCREEN() function is not available in this build.

### `spread_history.csv`, long, one row per bond month
`isin, date, zspread`

Mnemonic: `TR.ZSpread` with `Frq=M` over the bond's life. Option adjusted spread is
snapshot only in this entitlement, so Z-spread is the outcome; the non callable filter
makes that valid.

### `issuer_fundamentals.csv`, one row per operating parent
`issuer_key, common_name, naics6, employees, revenue, debt, net_debt, ebitda, assets,
mktcap, ebit, int_exp`

`issuer_key` is the `TR.UltimateParentId` value. Mnemonics: `TR.CommonName,
TR.NAICSNationalIndustryCode, TR.CompanyNumEmploy`, and with `Curn=USD`: `TR.Revenue,
TR.TotalDebtOutstanding, TR.NetDebt, TR.EBITDA, TR.TotalAssets, TR.CompanyMarketCap,
TR.EBIT, TR.InterestExpense`. Latest fiscal year.

## Notes

- This LSEG entitlement does not expose a bond to issuer PermID link, dated rating
  history, or single name CDS. The issuer key is the ultimate parent PermID instead.
- CSVs saved from a European locale Excel come out semicolon delimited with comma
  decimals. Convert to standard comma and dot before the scripts read them.
