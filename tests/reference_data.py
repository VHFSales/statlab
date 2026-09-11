"""Reference datasets and independently-known expected values (V-1, spec 89).

Values here are hand-computed or derived from closed-form identities, NOT from a
statistical library (the offline sandbox has none). Where a value is a rounded
textbook figure, the tolerance reflects that rounding. When run in an environment
with SciPy/statsmodels, tests in test_oracle.py cross-check these.
"""

# Classic 3-group balanced ANOVA example.
# A=[6,8,4,5,3,4] B=[8,12,9,11,6,8] C=[13,9,11,8,7,12]
ANOVA3 = {
    "A": [6, 8, 4, 5, 3, 4],
    "B": [8, 12, 9, 11, 6, 8],
    "C": [13, 9, 11, 8, 7, 12],
    # exact:
    "ss_between": 84.0,
    "ss_within": 68.0,
    "ss_total": 152.0,
    "df_between": 2,
    "df_within": 15,
    "F": 9.264705882352942,
    # p verified via exact closed form P(F>f)=(1+2F/n)^(-n/2) for df1=2:
    "p": 0.0023987773293929087,
    "eta2": 84.0 / 152.0,
}

# Two groups for the F = t^2 identity.
TWO_GROUPS = {
    "A": [10.2, 10.8, 11.1, 10.6, 10.4],
    "B": [13.5, 14.0, 13.8, 14.2, 13.9],
}

# Heteroscedastic 3-group dataset for Welch / Games-Howell.
HETERO3 = {
    "A": [27, 26, 21, 24, 15, 18, 25, 23],
    "B": [19, 18, 20, 21, 22, 17],
    "C": [40, 38, 42, 39, 41, 44, 43],
}

# Studentized-range critical values q_{0.05}(k, nu) from standard tables (Harter).
Q_CRIT_05 = {
    (2, 10): 3.1511,
    (3, 10): 3.8768,
    (3, 16): 3.6493,
    (4, 20): 3.9583,
    (5, 30): 4.1021,
    (3, "inf"): 3.3145,
}
