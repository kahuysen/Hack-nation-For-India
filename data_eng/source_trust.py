"""
Source-authority trust for facility records (Track B).

Judges a record by WHERE its data came from, not what it claims. A record built
from the facility's own site + a government listing is trustworthy; one scraped
only from justDial + Facebook (or worse, a restaurant-review page) is not.

Two things here:
  1. top_domains(...)      -> profile the actual domains so you can EXPAND the
                             tier lists below to what's really in the data.
  2. add_source_trust(...) -> per-record source_trust [0,1], best tier, and flags
                             (e.g. irrelevant_source, social_only, no_primary).

Tier lists are India-focused seeds — run top_domains first and grow them.
"""
import json
import re

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import (ArrayType, BooleanType, DoubleType, IntegerType,
                               StringType, StructField, StructType)

try:
    from domain_tiers import DOMAIN_TIERS, TIER_WEIGHT, DEFAULT_TIER, CREDIBLE_TIERS
except ImportError:      # domain_tiers.py not uploaded to the workspace yet
    DOMAIN_TIERS, DEFAULT_TIER = {}, "unverified_own"
    TIER_WEIGHT = {"authoritative": 1.0, "primary": 0.9, "official_social": 0.75,
                   "health_directory": 0.55, "unverified_own": 0.55,
                   "general_directory": 0.35, "social": 0.2, "irrelevant": 0.0}
    CREDIBLE_TIERS = {"authoritative", "primary", "official_social", "health_directory"}

# --------------------------------------------------------------------------- #
# Source tiers (matched as substrings against the lowercased URL).
# Order of authority: authoritative > primary(own) > health_dir > gen_dir > social
# irrelevant is a red flag regardless of anything else.
# --------------------------------------------------------------------------- #
IRRELEVANT = [  # wrong-entity / noise -> misattribution risk
    "restaurant-guru", "zomato", "swiggy", "tripadvisor", "yelp", "makemytrip",
    "booking.com", "agoda", "magicbricks", "99acres", "olx", "quikr",
    "amazon.", "flipkart",
]
SOCIAL = [
    "facebook.com", "fb.com", "instagram.com", "linkedin.com", "twitter.com",
    "x.com", "youtube.com", "pinterest.com", "wa.me", "whatsapp",
]
GEN_DIR = [  # crowdsourced business directories
    "justdial", "onefivenine", "sulekha", "indiamart", "asklaila", "grotal",
    "yellowpages", "tradeindia", "cybo", "tuugo", "findglocal", "indiacom",
]
HEALTH_DIR = [  # health-specific aggregators (moderate authority)
    "practo", "meddco", "lybrate", "credihealth", "medindia", "1mg",
    "apollo247", "bajajfinservhealth", "drlogy", "clinicspots", "sehat",
    "curofy", "docprime", "ekincare",
]
AUTHORITATIVE = [  # government / accreditation / academic
    ".gov.in", ".nic.in", ".gov", "mohfw", "nabh", "nabl", "who.int",
    ".ac.in", ".edu", "nmc.org.in", "jointcommission",
]

_ALL_KNOWN = IRRELEVANT + SOCIAL + GEN_DIR + HEALTH_DIR + AUTHORITATIVE


def _urls(field: str):
    """Parse a list-encoded URL string field into a lowercased array<string>."""
    parsed = F.from_json(F.col(field).cast("string"), "array<string>")
    quoted = F.expr(
        f"""regexp_extract_all(coalesce(cast(`{field}` as string), ''), '"([^"]+)"', 1)"""
    )
    arr = F.coalesce(parsed, quoted, F.array().cast("array<string>"))
    return F.transform(arr, lambda u: F.lower(u))


def _host(url_col):
    """Registrable-ish host from a URL with or without scheme/www."""
    return F.regexp_extract(url_col, r"^(?:https?://)?(?:www\.)?([^/]+)", 1)


def top_domains(df: DataFrame, field: str = "websites",
                id_col: str = "unique_id") -> DataFrame:
    """Most common source domains, by facility coverage. Run this FIRST."""
    ex = (df.select(F.col(id_col).alias("fid"), F.explode(_urls(field)).alias("url"))
            .withColumn("domain", _host(F.col("url"))))
    return (ex.where(F.length("domain") > 0)
              .groupBy("domain")
              .agg(F.countDistinct("fid").alias("n_facilities"),
                   F.count("*").alias("n_total"))
              .orderBy(F.desc("n_facilities")))


def _has_any(urls, needles):
    pat = "(" + "|".join(n.replace(".", r"\.") for n in needles) + ")"
    return F.coalesce(F.exists(urls, lambda u: u.rlike(pat)), F.lit(False))


# --------------------------------------------------------------------------- #
# Record-level source trust, from the judged DOMAIN_TIERS map.
# We can't attribute facts to sources, so we score the credibility of the whole
# source portfolio: dominated by the BEST source (any fact could come from it),
# nudged up by corroboration and down by noise. A social URL matching the record's
# own facebookLink is promoted to "official_social".
# --------------------------------------------------------------------------- #
_QUOTED = re.compile(r'"([^"]+)"')
_HOST_RE = re.compile(r"^(?:https?://)?(?:www\.)?([^/]+)", re.I)


def _parse_urls_py(s):
    if not s:
        return []
    try:
        v = json.loads(s)
        if isinstance(v, list):
            return [str(x) for x in v]
    except Exception:
        pass
    return _QUOTED.findall(s)


def _host_py(u):
    if not u:
        return ""
    m = _HOST_RE.match(u.strip().lower())
    return m.group(1) if m else ""


def _score_record(websites, facebook_link, official_website):
    urls = _parse_urls_py(websites)
    fb = (facebook_link or "").strip().lower()
    off = _host_py(official_website)
    tiers, official_in_sources = [], False
    for u in urls:
        d = _host_py(u)
        if not d:
            continue
        t = DOMAIN_TIERS.get(d, DEFAULT_TIER)
        if off and off in d:                          # matches the curated officialWebsite
            t = "primary"                             # -> verified own site
            official_in_sources = True
        elif t == "social" and fb and (fb in u.lower() or u.lower() in fb):
            t = "official_social"                     # the facility's OWN verified account
        tiers.append(t)
    n_total = len(tiers)
    if n_total == 0:
        return (0, 0, 0, "none", 0.0, ["no_sources"], False)
    n_credible = sum(1 for t in tiers if t in CREDIBLE_TIERS)     # authoritative/primary/official_social/health_dir
    n_noise = sum(1 for t in tiers if t == "irrelevant")
    n_unverified = sum(1 for t in tiers if t == "unverified_own")
    # source_trust = fraction of a record's sources that are trustworthy
    source_trust = round(n_credible / n_total, 3)
    best_tier = max(tiers, key=lambda t: TIER_WEIGHT.get(t, 0.0))  # label only (ordinal)
    flags = []
    if n_noise:
        flags.append("irrelevant_source")
    if n_credible == 0:
        flags.append("no_credible_source")
    if n_credible == 0 and n_noise == 0 and n_unverified == n_total:
        flags.append("unverified_only")     # sole sources are unjudged own-domains: low CONFIDENCE, not proven noise
    if not off:
        flags.append("no_official_site")
    return (n_total, n_credible, n_noise, best_tier, source_trust, flags, official_in_sources)


_SOURCE_TRUST_SCHEMA = StructType([
    StructField("n_sources", IntegerType()),
    StructField("n_credible_sources", IntegerType()),
    StructField("n_noise_sources", IntegerType()),
    StructField("source_tier", StringType()),
    StructField("source_trust", DoubleType()),
    StructField("source_flags", ArrayType(StringType())),
    StructField("official_in_sources", BooleanType()),
])


def add_source_trust(df: DataFrame, field: str = "websites") -> DataFrame:
    """
    Add record-level source-provenance trust from the judged DOMAIN_TIERS map.
    source_trust = fraction of the record's websites that are trustworthy.
      n_sources           : int    number of source URLs
      n_credible_sources  : int    how many are trustworthy (credible tiers)
      n_noise_sources     : int    how many are irrelevant/noise
      source_tier         : str    the record's best source tier (label only)
      source_trust        : double [0,1] = n_credible_sources / n_sources
      source_flags        : array<string>
                            (no_sources / irrelevant_source / no_credible_source /
                             unverified_only / no_official_site)
      official_in_sources : bool   officialWebsite domain appears among the sources

    Requires domain_tiers.py on the path (import at top of this module).
    """
    _udf = F.udf(_score_record, _SOURCE_TRUST_SCHEMA)
    return (df.withColumn("_st", _udf(F.col(field).cast("string"),
                                      F.col("facebookLink").cast("string"),
                                      F.col("officialWebsite").cast("string")))
              .select("*", "_st.*").drop("_st"))


def _domain_tier(d):
    """Auto-classify a single domain into a tier (for the review file)."""
    d = F.lower(d)

    def _m(lst):
        return d.rlike("(" + "|".join(n.replace(".", r"\.") for n in lst) + ")")

    return (F.when(_m(IRRELEVANT), "irrelevant")
             .when(_m(AUTHORITATIVE), "authoritative")
             .when(_m(HEALTH_DIR), "health_directory")
             .when(_m(GEN_DIR), "general_directory")
             .when(_m(SOCIAL), "social")
             .otherwise("unknown_or_primary"))   # high-freq ones here = a directory I missed


def export_domains(df: DataFrame, field: str = "websites",
                   out_path: str = "/tmp/domains_to_judge.txt",
                   id_col: str = "unique_id", min_facilities: int = 1):
    """
    Write every distinct source domain to a tab-separated txt for manual review,
    sorted by facility coverage, with the current auto-tier and an empty YOUR_TIER
    column to fill in. You then re-import the judged file as the authoritative map.

    On Databricks, pass a Unity Catalog Volume path so you can download/edit it, e.g.
      "/Volumes/<catalog>/<schema>/<volume>/domains_to_judge.txt"
    Returns (out_path, n_domains).
    """
    td = (top_domains(df, field, id_col)
          .withColumn("auto_tier", _domain_tier(F.col("domain")))
          .where(F.col("n_facilities") >= min_facilities)
          .orderBy(F.desc("n_facilities")))
    rows = td.collect()
    with open(out_path, "w") as fh:
        fh.write("domain\tn_facilities\tn_total\tauto_tier\tYOUR_TIER\n")
        for r in rows:
            fh.write(f"{r['domain']}\t{r['n_facilities']}\t{r['n_total']}\t{r['auto_tier']}\t\n")
    return out_path, len(rows)
