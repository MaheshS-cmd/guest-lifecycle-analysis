"""
Guest Lifecycle Sentiment Analyser

Source: Hotel_Reviews.csv (515,738 Booking.com reviews, 1,492 European hotels, 2015-2017)


Methodology note:
  Lifecycle tagging is KEYWORD-BASED, not machine learning. A review is tagged to a
  stage if its text contains words associated with that stage. A single review can
  touch multiple stages (guests often mention booking, room, and checkout in one
  paragraph), so stage flags are independent columns, not one exclusive category.

  Sentiment polarity is NOT computed here, Booking.com's review form already splits
  guest feedback into separate "Positive_Review" and "Negative_Review" boxes. We use
  that existing split rather than re-deriving it.

Output: reviews_lifecycle_clean.csv
"""

import pandas as pd
import re

SRC = "Hotel_Reviews.csv"
OUT = "reviews_lifecycle_clean.csv"

# 1. LOAD

df = pd.read_csv(SRC)
print(f"Raw shape: {df.shape}")


# 2. CLEAN KNOWN DATA ISSUES

# 2a. Whitespace: Hotel_Name, Reviewer_Nationality and review text all carry
#     leading/trailing spaces from the original scrape.
for col in ["Hotel_Name", "Reviewer_Nationality", "Negative_Review", "Positive_Review"]:
    df[col] = df[col].str.strip()

# 2a-ii. 523 reviewers left nationality blank. Label as 'Unknown' rather than
#     dropping the review — the feedback is still valid without knowing origin.
df["Reviewer_Nationality"] = df["Reviewer_Nationality"].replace("", "Unknown")

# 2b. Placeholder text: guests who left no complaint get the literal string
#     "No Negative"; no praise gets "No Positive". These are NOT real feedback —
#     flag them so they can be excluded from text analysis, but keep the rows,
#     because "guest had nothing negative to say" is itself a useful signal.
df["has_negative_feedback"] = (df["Negative_Review"] != "No Negative").astype(int)
df["has_positive_feedback"] = (df["Positive_Review"] != "No Positive").astype(int)

# 2c. Missing geo: 3,268 rows have no lat/lng (hotels that failed geocoding).
#     Geo isn't needed for lifecycle analysis, so keep the rows and leave the
#     nulls as-is rather than dropping real reviews over a non-essential field.

# 2d. Dates: convert to real datetime so SQL/Power BI can do time analysis.
df["review_date"] = pd.to_datetime(df["Review_Date"], format="%m/%d/%Y")

# 2e. days_since_review is text ("0 days", "15 days") — strip to a number.
df["days_since_review_num"] = (
    df["days_since_review"].str.replace(r"\s*days?", "", regex=True).astype(int)
)

# 2f. City: the last word of Hotel_Address is the country, the word before the
#     postcode block is the city. Extract country simply — it's the last token.
df["country"] = df["Hotel_Address"].str.strip().str.split().str[-1]
# The Milan/Barcelona addresses end in "Italy"/"Spain"; UK ones end in "Kingdom".
df["country"] = df["country"].replace({"Kingdom": "United Kingdom"})


# 3. EXTRACT STRUCTURED FIELDS FROM THE MESSY 'Tags' COLUMN
#    Raw format: "[' Leisure trip ', ' Couple ', ' Duplex Double Room ', ' Stayed 6 nights ']"


def get_nights(tag_text):
    """Pull the night count out of 'Stayed N nights'."""
    match = re.search(r"Stayed (\d+) night", tag_text)
    return int(match.group(1)) if match else None

def get_trip_type(tag_text):
    """Business vs Leisure."""
    if "Business trip" in tag_text:
        return "Business"
    if "Leisure trip" in tag_text:
        return "Leisure"
    return "Unknown"

def get_traveller_type(tag_text):
    """Who the guest travelled with."""
    for t in ["Family with young children", "Family with older children",
              "Travelers with friends", "Solo traveler", "Couple", "Group"]:
        if t in tag_text:
            return t
    return "Unknown"

def get_submitted_mobile(tag_text):
    """Did they post from a phone? Proxy for how soon after the stay they wrote it."""
    return int("Submitted from a mobile device" in tag_text)

df["nights_stayed"]   = df["Tags"].apply(get_nights)
df["trip_type"]       = df["Tags"].apply(get_trip_type)
df["traveller_type"]  = df["Tags"].apply(get_traveller_type)
df["mobile_submission"] = df["Tags"].apply(get_submitted_mobile)

# nights_stayed fails to parse on a tiny number of rows — fill with median rather
# than dropping the review, since the review text is still valid feedback.
df["nights_stayed"] = df["nights_stayed"].fillna(df["nights_stayed"].median())

# Group nights into bands for reporting
df["stay_length_band"] = pd.cut(
    df["nights_stayed"],
    bins=[0, 1, 3, 7, 100],
    labels=["1 night", "2-3 nights", "4-7 nights", "8+ nights"],
)


# 4. LIFECYCLE STAGE TAGGING
#    Each stage gets a keyword list. A review is flagged for a stage if its
#    text contains any of that stage's keywords. Reviews can hit multiple stages.


LIFECYCLE_KEYWORDS = {
    "pre_arrival": [
        "booking", "booked", "reservation", "reserved", "confirm", "website",
        "email", "contacted", "communication", "request", "price we paid",
    ],
    "arrival": [
        "check in", "check-in", "checkin", "reception", "welcome", "arrival",
        "arrived", "lobby", "queue", "front desk", "greeted", "luggage",
    ],
    "in_stay": [
        "room", "bed", "sleep", "noise", "noisy", "clean", "dirty", "shower",
        "bathroom", "wifi", "pillow", "towel", "maintenance", "staff",
        "service", "breakfast", "restaurant", "bar", "food", "pool", "gym",
        "air conditioning", "heating",
    ],
    "checkout": [
        "check out", "check-out", "checkout", "bill", "invoice", "charged",
        "payment", "departure", "leaving",
    ],
    "post_stay": [
        "recommend", "return", "come back", "value for money", "worth",
        "would not stay", "stay again", "never again", "book again",
    ],
}

def flag_stage(text_series, keywords):
    """Return 1/0 flag: does this text mention any of these keywords?"""
    pattern = "|".join([re.escape(k) for k in keywords])
    return text_series.str.lower().str.contains(pattern, regex=True, na=False).astype(int)

for stage, keywords in LIFECYCLE_KEYWORDS.items():
    # Only tag stages against REAL feedback, not the "No Negative" placeholder.
    neg_text = df["Negative_Review"].where(df["has_negative_feedback"] == 1, "")
    pos_text = df["Positive_Review"].where(df["has_positive_feedback"] == 1, "")
    df[f"neg_{stage}"] = flag_stage(neg_text, keywords)
    df[f"pos_{stage}"] = flag_stage(pos_text, keywords)


# 5. TAG SPECIFIC IN-STAY ISSUES
#    In-Stay is by far the biggest stage, so break it into the actual
#    operational issues underneath it.


ISSUE_KEYWORDS = {
    "cleanliness":  ["dirty", "not clean", "unclean", "stain", "mould", "mold", "dust", "hair in"],
    "noise":        ["noise", "noisy", "loud", "could hear", "thin wall", "disturb"],
    "room_size":    ["small room", "tiny room", "room was small", "cramped", "no space"],
    "bathroom":     ["shower", "bathroom", "toilet", "hot water"],
    "sleep_quality":["bed", "pillow", "mattress", "uncomfortable", "could not sleep"],
    "staff_service":["staff", "rude", "unfriendly", "unhelpful", "attitude"],
    "food_beverage":["breakfast", "food", "restaurant", "coffee", "dinner"],
    "wifi":         ["wifi", "wi-fi", "internet", "connection"],
    "climate":      ["air conditioning", "aircon", "heating", "too hot", "too cold", "temperature"],
}

for issue, keywords in ISSUE_KEYWORDS.items():
    neg_text = df["Negative_Review"].where(df["has_negative_feedback"] == 1, "")
    df[f"issue_{issue}"] = flag_stage(neg_text, keywords)


# 6. SCORE BANDS — for comparing what happy vs unhappy guests talk about

df["score_band"] = pd.cut(
    df["Reviewer_Score"],
    bins=[0, 6, 8, 9, 10],
    labels=["Detractor (<=6)", "Passive (6-8)", "Satisfied (8-9)", "Promoter (9-10)"],
)


# 7. TRIM TO THE COLUMNS WE ACTUALLY NEED AND EXPORT
#    Drop the full review text — it's 200MB+ of free text that Power BI can't
#    use and SQL doesn't need. The tags derived from it are what we analyse.

keep_cols = [
    "Hotel_Name", "country", "review_date", "Reviewer_Nationality",
    "Reviewer_Score", "Average_Score", "score_band",
    "trip_type", "traveller_type", "nights_stayed", "stay_length_band",
    "mobile_submission", "days_since_review_num",
    "Review_Total_Negative_Word_Counts", "Review_Total_Positive_Word_Counts",
    "has_negative_feedback", "has_positive_feedback",
] + [f"neg_{s}" for s in LIFECYCLE_KEYWORDS] \
  + [f"pos_{s}" for s in LIFECYCLE_KEYWORDS] \
  + [f"issue_{i}" for i in ISSUE_KEYWORDS]

clean = df[keep_cols].copy()
clean.columns = [c.lower() for c in clean.columns]

clean.to_csv(OUT, index=False)
print(f"Saved: {OUT} ({clean.shape[0]:,} rows, {clean.shape[1]} columns)")
