import itertools
import streamlit as st
import pandas as pd
from itertools import accumulate
from typing import Iterator, List

# --- Sidebar configuration ---
st.sidebar.header("Race Configuration")
race_length = st.sidebar.number_input(
    "Total Race Laps", min_value=1, value=50, step=1, format="%d"
)
pit_time = st.sidebar.number_input(
    "Pit Stop Time (sec)", min_value=0.0, value=25.0, step=0.1
)
fuel_max_laps = st.sidebar.number_input(
    "Max Laps per Fuel Tank", min_value=1, value=20, step=1, format="%d"
)
st.sidebar.header("Tire Compounds")
compounds = {}
compound_names = ["Soft", "Medium", "Hard"]
for name in compound_names:
    max_laps = st.sidebar.number_input(
        f"{name} - Max Laps before Wear", min_value=1,
        value=15 if name=='Soft' else 25 if name=='Medium' else 40,
        step=1, format="%d"
    )
    base_time = st.sidebar.number_input(
        f"{name} - Base Lap Time (sec)", min_value=0.0,
        value=90.0 if name=='Soft' else 92.0 if name=='Medium' else 95.0,
        step=0.1
    )
    compounds[name] = {"max_laps": max_laps, "base_time": base_time}
max_stops = st.sidebar.slider(
    "Max Pit Stops", min_value=0, max_value=3, value=2
)

# --- Helper functions ---
def generate_bounded_partitions(total: int, bounds: List[int]) -> Iterator[List[int]]:
    """
    Génére toutes les partitions de total en len(bounds) parts, chaque part i entre 1 et bounds[i].
    """
    def backtrack(remaining, idx, path):
        if idx == len(bounds) - 1:
            if 1 <= remaining <= bounds[idx]:
                yield path + [remaining]
            return
        for i in range(1, min(bounds[idx], remaining - (len(bounds) - idx - 1)) + 1):
            yield from backtrack(remaining - i, idx + 1, path + [i])
    yield from backtrack(total, 0, [])

@st.cache_data
def compute_strategy_time(
    sequence: List[str], stint_laps: List[int], compounds: dict,
    fuel_max: int, pit: float
) -> float:
    """
    Calcule le temps total d'une stratégie donnée, ou renvoie None si non-viable.
    """
    total = 0.0
    for comp, laps in zip(sequence, stint_laps):
        data = compounds[comp]
        if laps > data['max_laps'] or laps > fuel_max:
            return None
        total += data['base_time'] * laps
    total += (len(sequence) - 1) * pit
    return total

# --- Simulation ---
if st.button("Run Simulation"):
    # Pré-calcule du nombre total de séquences pour la barre de progression
    total_sequences = sum(
        len(compounds) ** (stops + 1) for stops in range(max_stops + 1)
    )
    seq_counter = 0

    progress_bar = st.progress(0)
    progress_text = st.empty()
    results = []

    with st.spinner("Running simulation, please wait..."):
        for stops in range(max_stops + 1):
            stints = stops + 1
            for sequence in itertools.product(compounds.keys(), repeat=stints):
                # Incrémente la progression dès qu'une séquence est traitée
                seq_counter += 1
                pct = seq_counter / total_sequences
                progress_bar.progress(pct)
                progress_text.text(f"Progression: {int(pct * 100)}%")

                # Filtre basique pour éviter les séquences unicolor
                if len(set(sequence)) < 2:
                    continue

                # Génère et teste les partitions viables
                bounds = [min(compounds[c]['max_laps'], fuel_max_laps) for c in sequence]
                for stint_laps in generate_bounded_partitions(race_length, bounds):
                    time = compute_strategy_time(
                        sequence, stint_laps, compounds, fuel_max_laps, pit_time
                    )
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

    if not results:
        st.warning("No viable strategies found. Adjust your parameters.")
    else:
        df = pd.DataFrame(results)
        df['Total Time (s)'] = df['Total Time (s)'].round(2)

        # --- Filtres interactifs ---
        st.sidebar.header("Filter Results")
        stops_filter = st.sidebar.multiselect(
            "Pit Stops", options=sorted(df['Pit Stops'].unique()), default=sorted(df['Pit Stops'].unique())
        )
        comp_filter = st.sidebar.multiselect(
            "Tire Compound in Sequence", options=compound_names, default=compound_names
        )
        df_filtered = df[
            df['Pit Stops'].isin(stops_filter) &
            df['Tire Sequence'].apply(
                lambda s: any(c in comp_filter for c in s.split(' → '))
            )
        ]

        # Affiche top 10
        best = df_filtered.nsmallest(10, 'Total Time (s)')
        st.subheader("Top 10 Optimal Strategies")
        st.dataframe(best)

        # --- Graphique ---
        st.subheader("Comparaison des Temps")
        chart_data = best.set_index('Tire Sequence')['Total Time (s)']
        st.bar_chart(chart_data)
