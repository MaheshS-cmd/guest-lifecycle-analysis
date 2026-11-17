"""
Portfolio view: the 1,492 hotels treated as one hotel group

Reads the output of clean_reviews.py and looks at the data hotel by hotel instead
of review by review. Every number in the README's "Portfolio view" section comes
from this script.

Usage:
    python portfolio_analysis.py reviews_lifecycle_clean.csv [brand_map.csv]

brand_map.csv is optional (columns: hotel_name, brand). Brands were matched from
hotel names using a private list of name patterns, and brand names are withheld on
purpose, so that file isn't in the repo. Without it, the brand comparison is skipped
and everything else still runs.

Outputs:
    portfolio_hotels.csv   one row per hotel (100+ reviews) with rates and flags
    printed summary        the figures used in the README

Method notes:
    - Only hotels with 100+ reviews are compared (1,080 hotels, 95% of reviews),
      so one or two reviews can't swing a hotel's rate.
    - A hotel is "flagged" on a measure when its complaint rate is more than two
      standard errors above the portfolio average, i.e. clearly above average for
      its review count, not just unlucky.
    - Tagging is keyword-based (see clean_reviews.py), so treat every figure as a
      strong pattern, not an exact count.
"""

import sys
import numpy as np
import pandas as pd

SRC = sys.argv[1]
BRANDS = sys.argv[2] if len(sys.argv) > 2 else None
MIN_REVIEWS = 100

CITY = {"Netherlands": "Amsterdam", "Spain": "Barcelona", "United Kingdom": "London",
        "Italy": "Milan", "France": "Paris", "Austria": "Vienna"}

MEASURES = {
    "neg_pre_arrival": "Pre-arrival complaints",
    "neg_arrival": "Arrival complaints",
    "issue_staff_service": "Staff complaints",
    "issue_cleanliness": "Cleanliness complaints",
    "issue_noise": "Noise complaints",
    "issue_climate": "Heating / air-con complaints",
    "issue_food_beverage": "Food and beverage complaints",
}
FRONT_OFFICE = ["neg_pre_arrival", "neg_arrival", "issue_staff_service"]


def pct(x):
    return f"{x:.1%}"


df = pd.read_csv(SRC, parse_dates=["review_date"])
df["city"] = df["country"].map(CITY)
portfolio = {m: df[m].mean() for m in MEASURES}

# 1. One row per hotel
hotels = df.groupby("hotel_name").agg(
    reviews=("reviewer_score", "size"),
    score=("reviewer_score", "mean"),
    city=("city", "first"),
    total_reviews_on_site=("total_number_of_reviews", "max"),
    **{m: (m, "mean") for m in MEASURES},
)
H = hotels[hotels["reviews"] >= MIN_REVIEWS].copy()
print(f"Hotels: {len(hotels):,}. Compared: {len(H):,} with {MIN_REVIEWS}+ reviews "
      f"({H['reviews'].sum() / len(df):.0%} of reviews)\n")

# 2. Spread between hotels and how concentrated each problem is
print("1. SPREAD AND CONCENTRATION")
k10 = int(round(len(H) * 0.10))
for m, label in MEASURES.items():
    complaints = H[m] * H["reviews"]
    worst = H.sort_values(m, ascending=False).head(k10)
    share = (worst[m] * worst["reviews"]).sum() / complaints.sum()
    median = H[m].median()
    to_median = ((H[m] - median).clip(lower=0) * H["reviews"]).sum() / complaints.sum()
    print(f"  {label:30s} portfolio {pct(portfolio[m])} | middle hotel {pct(median)} | "
          f"best 10% <= {pct(H[m].quantile(.1))}, worst 10% >= {pct(H[m].quantile(.9))} | "
          f"worst 10% of hotels = {share:.0%} of complaints | "
          f"all hotels above the middle brought to it: -{to_median:.0%}")

# 3. Which problems travel together across hotels
print("\n2. PROBLEMS THAT TRAVEL TOGETHER (correlation of hotel complaint rates)")
print(H[list(MEASURES)].corr().round(2).to_string())

# 4. Front office flags
for m in MEASURES:
    se = np.sqrt(portfolio[m] * (1 - portfolio[m]) / H["reviews"])
    H[f"flag_{m}"] = (H[m] > portfolio[m] + 2 * se).astype(int)
H["front_office_flags"] = H[[f"flag_{m}" for m in FRONT_OFFICE]].sum(axis=1)
H["priority_front_office"] = (H["front_office_flags"] >= 2).astype(int)

print("\n3. FRONT OFFICE FLAGS (pre-arrival, arrival, staff clearly above average)")
print(H.groupby("front_office_flags").agg(hotels=("reviews", "size"),
                                              reviews=("reviews", "sum"),
                                              avg_score=("score", "mean")).round(2).to_string())
P = H[H["priority_front_office"] == 1]
print(f"  Flagged on 2+: {len(P)} hotels ({len(P) / len(H):.0%} of hotels, "
      f"{P['reviews'].sum() / H['reviews'].sum():.0%} of reviews), avg score {P['score'].mean():.2f} "
      f"vs {H.loc[H['front_office_flags'] == 0, 'score'].mean():.2f} with no flags")
for m in FRONT_OFFICE + ["issue_cleanliness"]:
    s = (P[m] * P["reviews"]).sum() / (H[m] * H["reviews"]).sum()
    print(f"    share of {MEASURES[m].lower()}: {s:.0%}")

# 5. Busy hotels
print("\n4. BUSY HOTELS (fifths by total reviews on Booking.com, a proxy for guest volume)")
H["volume_fifth"] = pd.qcut(H["total_reviews_on_site"], 5, labels=["1 quietest", "2", "3", "4", "5 busiest"])
print(H.groupby("volume_fifth", observed=True).agg(hotels=("reviews", "size"),
                                                   avg_score=("score", "mean"),
                                                   arrival=("neg_arrival", "mean"),
                                                   staff=("issue_staff_service", "mean")).round(3).to_string())
monthly = df.groupby(df["review_date"].dt.month)["neg_arrival"].mean()
print(f"  Arrival complaints by month: peak {pct(monthly.max())} (month {monthly.idxmax()}), "
      f"low {pct(monthly.min())} (month {monthly.idxmin()})")

# 6. Do weak hotels improve on their own?
print("\n5. PERSISTENCE: year 1 (Aug 2015 - Jul 2016) vs year 2 (Aug 2016 - Aug 2017)")
df["year"] = np.where(df["review_date"] < "2016-08-01", "Y1", "Y2")
by_year = df.groupby(["hotel_name", "year"]).agg(
    n=("reviewer_score", "size"), score=("reviewer_score", "mean"),
    **{m: (m, "mean") for m in MEASURES}).unstack("year")
both = by_year[(by_year["n"]["Y1"] >= 75) & (by_year["n"]["Y2"] >= 75)]
print(f"  Hotels with 75+ reviews in both years: {len(both)}")
for m in ["score"] + list(MEASURES):
    y1, y2 = both[m]["Y1"], both[m]["Y2"]
    q1, q2 = pd.qcut(y1, 4, labels=False), pd.qcut(y2, 4, labels=False)
    worst_q, better = (0, q2 >= 2) if m == "score" else (3, q2 <= 1)
    stayed = (q2[q1 == worst_q] == worst_q).mean()
    moved_up = better[q1 == worst_q].mean()
    label = "Review score" if m == "score" else MEASURES[m]
    print(f"  {label:30s} worst quarter in year 1 still worst in year 2: {stayed:.0%} | "
          f"reached the better half: {moved_up:.0%}")

# 6b. Bottom-quarter hotels: the ones that climbed vs the ones that stayed
bottom = both[pd.qcut(both["score"]["Y1"], 4, labels=False) == 0]
climbed = pd.qcut(both["score"]["Y2"], 4, labels=False)[bottom.index] >= 1
print(f"\n  Bottom quarter on score in year 1: {len(bottom)} hotels; climbed {climbed.sum()} "
      f"({climbed.mean():.0%}), stayed {(~climbed).sum()}")
print(f"  Starting score: climbed {bottom['score']['Y1'][climbed].mean():.2f}, stayed {bottom['score']['Y1'][~climbed].mean():.2f}")
for m, label in MEASURES.items():
    y1, y2 = bottom[m]["Y1"], bottom[m]["Y2"]
    up = y2[climbed].mean() / y1[climbed].mean() - 1
    stay = y2[~climbed].mean() / y1[~climbed].mean() - 1
    print(f"  {label:30s} change: climbed {up:+.0%} | stayed {stay:+.0%}")

# 7. How much do city and brand explain?
def explained(frame, group, m):
    total = ((frame[m] - frame[m].mean()) ** 2).sum()
    between = ((frame.groupby(group)[m].transform("mean") - frame[m].mean()) ** 2).sum()
    return between / total

print("\n6. HOW MUCH CITY AND BRAND EXPLAIN (share of hotel-to-hotel differences)")
for m, label in MEASURES.items():
    print(f"  {label:30s} city {explained(H, 'city', m):.0%}")

if BRANDS:
    b = pd.read_csv(BRANDS)
    HB = H.join(b.set_index("hotel_name"), how="inner")
    families = HB["brand"].value_counts()
    HB = HB[HB["brand"].isin(families[families >= 15].index)]
    print(f"  Brand families with 15+ hotels: {HB['brand'].nunique()} ({len(HB)} hotels)")
    for m, label in MEASURES.items():
        print(f"  {label:30s} brand {explained(HB, 'brand', m):.0%}")
    print("  Arrival complaint range inside each brand family (names withheld):")
    for i, (_, g) in enumerate(HB.groupby("brand")):
        print(f"    Brand {chr(65 + i)} ({len(g)} hotels): {pct(g['neg_arrival'].min())} to {pct(g['neg_arrival'].max())}")
else:
    print("  Brand comparison skipped (no brand map supplied).")

H.reset_index().to_csv("portfolio_hotels.csv", index=False)
print("\nSaved portfolio_hotels.csv")
