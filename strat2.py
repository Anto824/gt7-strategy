# streamlit_strategy_simulator.py
# Multi-stop strategy simulator with web interface using Streamlit

import itertools
import pandas as pd
from itertools import accumulate
import streamlit as st

# --- Sidebar configuration ---
st.sidebar.header("Race Configuration")
race_length = st.sidebar.number_input(
    "Total Race Laps", min_value=1, value=50, step=1
)
pit_time = st.sidebar.number_input(
    "Pit Stop Time (sec)", min_value=0.0, value=25.0, step=0.1
)
fuel_max_laps = st.sidebar.number_input(
    "Max Laps per Fuel Tank", min_value=1, value=20, step=1
)

st.sidebar.header("Tire Compounds")
compounds = {}
compound_names = ["Soft", "Medium", "Hard"]
for name in compound_names:
    max_laps = st.sidebar.number_input(
        f"{name} - Max Laps before Wear", min_value=1, value=15 if name=='Soft' else 25 if name=='Medium' else 40, step=1
    )
    base_time = st.sidebar.number_input(
        f"{name} - Base Lap Time (sec)", min_value=0.0, value=90.0 if name=='Soft' else 92.0 if name=='Medium' else 95.0, step=0.1
    )
    compounds[name] = {"max_laps": max_laps, "base_time": base_time}

max_stops = st.sidebar.slider(
    "Max Pit Stops", min_value=0, max_value=5, value=3
)

# --- Helper functions ---
def generate_partitions(total, parts):
    """Yield lists of `parts` positive integers summing to `total`."""
    if parts == 1:
        yield [total]
        return
    for i in range(1, total - parts + 2):
        for tail in generate_partitions(total - i, parts - 1):
            yield [i] + tail

@st.cache_data
def compute_strategy_time(sequence, stint_laps):
    total_time = 0.0
    # Check each stint viability and accumulate time
    for compound, laps in zip(sequence, stint_laps):
        data = compounds[compound]
        if laps > data['max_laps'] or laps > fuel_max_laps:
            return None
        total_time += data['base_time'] * laps
    total_time += (len(sequence) - 1) * pit_time
    return total_time

# --- Simulation ---
if st.button("Run Simulation"):
    results = []
    for stops in range(max_stops + 1):
        stints = stops + 1
        for sequence in itertools.product(compounds.keys(), repeat=stints):
            if len(set(sequence)) < 2:
                continue
            for stint_laps in generate_partitions(race_length, stints):
                time = compute_strategy_time(sequence, stint_laps)
                if time is None:
                    continue
                pit_laps = list(accumulate(stint_laps))[:-1]
                results.append({
                    'Tire Sequence': ' → '.join(sequence),
                    'Stint Laps': ', '.join(map(str, stint_laps)),
                    'Pit Stop Laps': ', '.join(map(str, pit_laps)),
                    'Pit Stops': stops,
                    'Total Time (s)': time
                })
    if results:
        df = pd.DataFrame(results)
        df['Total Time (s)'] = df['Total Time (s)'].round(2)
        best = df.nsmallest(10, 'Total Time (s)')
        st.subheader("Top 10 Optimal Strategies")
        st.dataframe(best)
    else:
        st.warning("No viable strategies found. Adjust your parameters.")
