import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import pydeck as pdk
from scipy.interpolate import griddata
import numpy as np

st.set_page_config(page_title="Formation Tops Viewer", layout="wide")
st.title("🌋 Subsurface Formation Tops - Geological Viewer")

# --- Initialize session state ---
if "wells_data" not in st.session_state:
    st.session_state["wells_data"] = []

# --- Formation color codes ---
formation_colors = {
    "Top_Shale": [127, 127, 127],
    "Sand_A": [255, 215, 0],
    "Sand_B": [255, 160, 122],
    "Limestone": [176, 196, 222],
    "Dolomite": [210, 180, 140]
}

# --- Add New Well ---
st.header("➕ Add or Edit Well Data")
with st.form("well_form"):
    well_name = st.text_input("Well Name")
    x_loc = st.number_input("Location X", value=0.0)
    y_loc = st.number_input("Location Y", value=0.0)

    formation_names = st.text_area("Formation Names (comma-separated)", "Top_Shale, Sand_A, Sand_B")
    formation_depths = st.text_area("Top Depths (comma-separated, meters)", "500, 750, 980")

    edit_index = st.selectbox("Edit Existing Well (optional)", options=["None"] + [f["well_name"] for f in st.session_state.wells_data])
    submitted = st.form_submit_button("Save Well")

    if submitted:
        try:
            formations = [f.strip() for f in formation_names.split(",")]
            depths = [float(d.strip()) for d in formation_depths.split(",")]
            if len(formations) != len(depths):
                st.error("Formation names and depths count must match!")
            else:
                new_entry = {
                    "well_name": well_name,
                    "x": x_loc,
                    "y": y_loc,
                    "formations": formations,
                    "depths": depths
                }
                if edit_index != "None":
                    # Update existing
                    for i, w in enumerate(st.session_state.wells_data):
                        if w["well_name"] == edit_index:
                            st.session_state.wells_data[i] = new_entry
                            st.success(f"Well '{edit_index}' updated.")
                            break
                else:
                    st.session_state.wells_data.append(new_entry)
                    st.success(f"Well '{well_name}' added.")
        except ValueError:
            st.error("Depths must be valid numbers.")

# --- Delete Well ---
st.header("❌ Delete a Well")
if st.session_state.wells_data:
    delete_well = st.selectbox("Select well to delete", [w["well_name"] for w in st.session_state.wells_data])
    if st.button("Delete Well"):
        st.session_state.wells_data = [w for w in st.session_state.wells_data if w["well_name"] != delete_well]
        st.success(f"Deleted well: {delete_well}")

# --- Show Well Data ---
st.header("📋 All Entered Wells")
for well in st.session_state.wells_data:
    st.subheader(f"📍 {well['well_name']} (X: {well['x']}, Y: {well['y']})")
    df = pd.DataFrame({
        "Formation": well["formations"],
        "Top Depth (m)": well["depths"]
    })
    st.dataframe(df)

# --- Cross-section Plot ---
st.header("📊 Cross-section View")
if st.session_state.wells_data:
    fig, ax = plt.subplots(figsize=(12, 6))
    for idx, well in enumerate(st.session_state.wells_data):
        x_pos = idx * 1.5
        for form, depth in zip(well["formations"], well["depths"]):
            color = [c / 255 for c in formation_colors.get(form, [0, 0, 255])]
            ax.plot([x_pos - 0.2, x_pos + 0.2], [depth, depth], label=form if idx == 0 else "", lw=3, color=color)
            ax.text(x_pos + 0.3, depth, form, va='center', fontsize=8)
        ax.text(x_pos, -50, well["well_name"], ha='center', fontsize=10, rotation=45)
    ax.set_ylim(ax.get_ylim()[1], ax.get_ylim()[0])
    ax.set_ylabel("Depth (m)")
    ax.set_xticks([])
    ax.legend(loc='upper right')
    ax.grid(True)
    st.pyplot(fig)

# --- 3D Map ---
st.header("🌍 3D Interactive Map")
map_data = []
for well in st.session_state.wells_data:
    for form, depth in zip(well["formations"], well["depths"]):
        map_data.append({
            "well": well["well_name"],
            "formation": form,
            "x": well["x"],
            "y": well["y"],
            "depth": depth,
            "color": formation_colors.get(form, [0, 0, 255])
        })
df_map = pd.DataFrame(map_data)
if not df_map.empty:
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position='[x, y]',
        get_fill_color='[color[0], color[1], color[2], 160]',
        get_radius=50,
        pickable=True,
        auto_highlight=True,
    )
    view_state = pdk.ViewState(
        longitude=df_map["x"].mean(),
        latitude=df_map["y"].mean(),
        zoom=5,
        pitch=40,
    )
    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{well}\n{formation} @ {depth}m"}))

# --- Interpolation ---
st.header("🔵 Interpolated Formation Surface")
formation_to_plot = st.selectbox("Select Formation to Interpolate", list(formation_colors.keys()))
interp_data = df_map[df_map["formation"] == formation_to_plot]
if len(interp_data) >= 3:
    grid_x, grid_y = np.meshgrid(
        np.linspace(interp_data["x"].min(), interp_data["x"].max(), 100),
        np.linspace(interp_data["y"].min(), interp_data["y"].max(), 100),
    )
    grid_z = griddata(
        (interp_data["x"], interp_data["y"]),
        interp_data["depth"],
        (grid_x, grid_y),
        method='cubic'
    )
    fig = plt.figure(figsize=(10, 6))
    ax = fig.add_subplot(111, projection='3d')
    ax.plot_surface(grid_x, grid_y, grid_z, cmap='viridis', edgecolor='none')
    ax.set_title(f"Interpolated Surface - {formation_to_plot}")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Depth (m)")
    st.pyplot(fig)
else:
    st.warning("Need at least 3 points for interpolation.")
