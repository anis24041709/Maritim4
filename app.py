import json
import time
import threading
import streamlit as st
import folium
from streamlit_folium import st_folium
import websocket

st.set_page_config(
    page_title="AIS Schiffstracker",
    layout="wide"
)

API_KEY = st.secrets["AISSTREAM_API_KEY"]

# Session State
if "position" not in st.session_state:
    st.session_state.position = None

if "ship_name" not in st.session_state:
    st.session_state.ship_name = ""

if "search_running" not in st.session_state:
    st.session_state.search_running = False


def ais_search(target_imo):
    found = False

    def on_open(ws):
        subscribe_message = {
            "APIKey": API_KEY,
            "BoundingBoxes": [[[-90, -180], [90, 180]]]
        }

        ws.send(json.dumps(subscribe_message))

    def on_message(ws, message):
        nonlocal found

        if found:
            return

        try:
            data = json.loads(message)

            meta = data.get("MetaData", {})

            imo = str(meta.get("IMO", ""))

            if imo == target_imo:

                lat = meta.get("latitude")
                lon = meta.get("longitude")

                ship_name = meta.get(
                    "ShipName",
                    f"IMO {imo}"
                )

                st.session_state.position = (
                    float(lat),
                    float(lon)
                )

                st.session_state.ship_name = ship_name

                found = True

                ws.close()

        except Exception:
            pass

    ws = websocket.WebSocketApp(
        "wss://stream.aisstream.io/v0/stream",
        on_open=on_open,
        on_message=on_message
    )

    ws.run_forever()


st.title("🚢 AIS Schiffstracker")

imo = st.text_input(
    "IMO-Nummer eingeben",
    placeholder="z.B. 9387421"
)

if st.button("Schiff suchen"):

    if not imo.strip():
        st.error("Bitte eine IMO-Nummer eingeben.")
    else:

        st.session_state.position = None
        st.session_state.ship_name = ""
        st.session_state.search_running = True

        thread = threading.Thread(
            target=ais_search,
            args=(imo.strip(),),
            daemon=True
        )

        thread.start()

        with st.spinner(
            "Suche nach AIS-Daten..."
        ):
            timeout = 30

            start = time.time()

            while (
                st.session_state.position is None
                and time.time() - start < timeout
            ):
                time.sleep(1)

        st.session_state.search_running = False

if st.session_state.position:

    lat, lon = st.session_state.position

    st.success(
        f"Gefunden: {st.session_state.ship_name}"
    )

    st.write(
        f"Latitude: {lat:.6f} | Longitude: {lon:.6f}"
    )

    m = folium.Map(
        location=[lat, lon],
        zoom_start=8
    )

    folium.Marker(
        [lat, lon],
        popup=st.session_state.ship_name,
        tooltip=st.session_state.ship_name
    ).add_to(m)

    st_folium(
        m,
        width=None,
        height=600
    )

elif not st.session_state.search_running:
    st.info(
        "Noch keine Position gefunden."
    )
