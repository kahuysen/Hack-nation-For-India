"""Medical Desert Planner — Hack-Nation Challenge 04 (Databricks x Virtue Foundation).

Streamlit Databricks App. Separates real medical deserts from data deserts:
a planner picks a capability + geography, sees trust-weighted coverage per
region, drills into the facility evidence behind each aggregate, and saves
planning scenarios.

Data source: reads the India 10k dataset from a Databricks table when
DATABRICKS_WAREHOUSE_ID / FACILITIES_TABLE are set; otherwise falls back to
the bundled sample CSV so the app runs anywhere.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from trust import (
    CAPABILITIES,
    TIER_CLAIMED_ONLY,
    TIER_CORROBORATED,
    classify_region,
    knowledge_score,
    score_facility,
)

st.set_page_config(page_title="Medical Desert Planner", page_icon="🏥", layout="wide")

SCENARIOS_PATH = Path("scenarios.json")  # TODO: replace with Lakebase table


# ---------------------------------------------------------------- data layer
@st.cache_data(ttl=600)
def load_facilities() -> pd.DataFrame:
    warehouse_id = os.getenv("DATABRICKS_WAREHOUSE_ID")
    table = os.getenv("FACILITIES_TABLE")
    if warehouse_id and table:
        from databricks import sql

        with sql.connect(
            server_hostname=os.getenv("DATABRICKS_HOST", "").removeprefix("https://"),
            http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        ) as conn:
            df = pd.read_sql(f"SELECT * FROM {table}", conn)
    else:
        df = pd.read_csv(Path(__file__).parent / "data" / "sample_facilities.csv")
    for col in ("capability", "procedure", "equipment", "description"):
        df[col] = df[col].fillna("")
    return df


@st.cache_data(ttl=600)
def assess(capability: str) -> pd.DataFrame:
    """Per-facility trust assessment for one capability."""
    df = load_facilities().copy()
    assessments = df.apply(lambda r: score_facility(r, capability), axis=1)
    df["tier"] = [a.tier for a in assessments]
    df["trust_weight"] = [a.weight for a in assessments]
    df["evidence"] = [a.evidence for a in assessments]
    df["knowledge"] = df.apply(knowledge_score, axis=1)
    return df


def region_rollup(df: pd.DataFrame, level: str) -> pd.DataFrame:
    grouped = df.groupby(level).agg(
        facilities=("facility_id", "count"),
        claiming=("tier", lambda t: (t != "Not claimed").sum()),
        corroborated=("tier", lambda t: (t == TIER_CORROBORATED).sum()),
        coverage=("trust_weight", "mean"),
        knowledge=("knowledge", "mean"),
    )
    grouped["status"] = [
        classify_region(c, k) for c, k in zip(grouped["coverage"], grouped["knowledge"])
    ]
    return grouped.sort_values(["coverage", "knowledge"]).reset_index()


# ---------------------------------------------------------------- persistence
def load_scenarios() -> list:
    if SCENARIOS_PATH.exists():
        return json.loads(SCENARIOS_PATH.read_text())
    return []


def save_scenario(scenario: dict) -> None:
    scenarios = load_scenarios()
    scenarios.append(scenario)
    SCENARIOS_PATH.write_text(json.dumps(scenarios, indent=2))


# ---------------------------------------------------------------- UI
st.title("🏥 Medical Desert Planner")
st.caption(
    "Trust-weighted healthcare coverage for India — separating **medical deserts** "
    "(verified gaps) from **data deserts** (we simply don't know)."
)

with st.sidebar:
    st.header("Planning question")
    capability = st.selectbox("Capability", CAPABILITIES)
    level = st.radio("Geography level", ["state", "district"], horizontal=True)
    st.divider()
    st.markdown(
        "**How to read the map**\n\n"
        "🔴 Medical desert — good data, no verified capability\n\n"
        "🟡 Data desert — too little data to judge\n\n"
        "🟠 Claimed, unverified — claims without corroboration\n\n"
        "🟢 Served — corroborated coverage"
    )

facilities = assess(capability)
regions = region_rollup(facilities, level)

tab_coverage, tab_drill, tab_scenarios = st.tabs(
    ["📊 Regional coverage", "🔍 Facility drill-down", "💾 Saved scenarios"]
)

with tab_coverage:
    st.subheader(f"{capability} coverage by {level}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Regions assessed", len(regions))
    col2.metric("Medical deserts", int(regions["status"].str.contains("Medical desert").sum()))
    col3.metric("Data deserts", int(regions["status"].str.contains("Data desert").sum()))
    st.dataframe(
        regions.rename(
            columns={
                level: level.title(),
                "facilities": "Facilities",
                "claiming": f"Claiming {capability}",
                "corroborated": "Corroborated",
                "coverage": "Trust-weighted coverage",
                "knowledge": "Knowledge score",
                "status": "Status",
            }
        ).style.format({"Trust-weighted coverage": "{:.2f}", "Knowledge score": "{:.2f}"}),
        use_container_width=True,
        hide_index=True,
    )
    st.info(
        "Coverage = mean trust weight of facilities (corroborated claim = 1.0, "
        "bare claim = 0.3). Knowledge = mean field-completeness. A region can look "
        "empty because nothing is there — or because nobody wrote it down. These are "
        "different problems with different fixes."
    )

with tab_drill:
    region_choice = st.selectbox(f"Inspect {level}", regions[level])
    subset = facilities[facilities[level] == region_choice]
    st.subheader(f"{len(subset)} facilities in {region_choice}")
    for _, row in subset.sort_values("trust_weight", ascending=False).iterrows():
        badge = {TIER_CORROBORATED: "🟢", TIER_CLAIMED_ONLY: "🟠"}.get(row["tier"], "⚪")
        with st.expander(f"{badge} {row['name']} — {row['tier']} ({capability})"):
            left, right = st.columns([2, 1])
            with left:
                st.markdown(f"**Description:** {row['description'] or '_missing_'}")
                if row["evidence"]:
                    st.markdown("**Evidence (the receipts):**")
                    for source, hits in row["evidence"]:
                        st.markdown(f"- `{source}` mentions: *{hits}*")
                elif row["tier"] == TIER_CLAIMED_ONLY:
                    st.warning(
                        f"Claims {capability} but no supporting mention in "
                        "procedure, equipment, or description."
                    )
            with right:
                st.markdown(f"**District:** {row['district']}  \n**PIN:** {row['pin']}")
                st.markdown(
                    f"**Capacity:** {row['capacity'] or 'unknown'}  \n"
                    f"**Doctors:** {row['numberDoctors'] or 'unknown'}"
                )
                st.progress(row["knowledge"], text=f"Data completeness {row['knowledge']:.0%}")

with tab_scenarios:
    st.subheader("Save this planning view")
    note = st.text_area("Planner note", placeholder="e.g. Prioritize NICU outreach in Araria — verify data desert first.")
    if st.button("💾 Save scenario", type="primary"):
        save_scenario(
            {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "capability": capability,
                "level": level,
                "note": note,
                "top_gaps": regions.head(5).to_dict(orient="records"),
            }
        )
        st.success("Scenario saved.")
    st.divider()
    for s in reversed(load_scenarios()):
        with st.expander(f"{s['capability']} by {s['level']} — {s['saved_at'][:16]}"):
            if s["note"]:
                st.markdown(f"> {s['note']}")
            st.dataframe(pd.DataFrame(s["top_gaps"]), use_container_width=True, hide_index=True)
