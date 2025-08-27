import csv
import streamlit as st

st.set_page_config(page_title="Shift Counter", page_icon="⚙️", layout="centered")
st.title("Vitti's BFR Shift Counter")

st.caption("Counts upshifts/downshifts from a MoTeC i2 CSV. "
           "Drops all false neutral readings.")
st.caption("Please upload a CSV file that only contains the channels 'Gear' and 'Engine Speed'")

uploaded = st.file_uploader("Upload CSV", type=["csv"])
rpm_threshold = st.number_input("RPM start threshold", value=2800.0, step=100.0)

RPM_COL = "Engine Speed"
GEAR_COL = "Gear"

def normalize_gear(cell):
    s = str(cell).strip()
    if not s:
        return None
    g = int(float(s))
    return g if g > 0 else None

def find_header_idx(lines):
    for i, line in enumerate(lines):
        if '"Engine Speed"' in line and '"Gear"' in line:
            return i
    return None

def find_start(rows, rpm_index, threshold):
    for k, r in enumerate(rows):
        if len(r) <= rpm_index: continue
        s = str(r[rpm_index]).strip()
        if not s: continue
        if float(s) >= threshold:
            return k
    return None

def count_shifts_after_start(rows, rpm_index, gear_index, threshold):
    start = find_start(rows, rpm_index, threshold)
    if start is None:
        return 0, 0, 0, None, None
    up = down = 0
    prev = None
    for row in rows[start:]:
        if len(row) <= gear_index: continue
        g = normalize_gear(row[gear_index])
        if g is None: continue
        if prev is not None and g != prev:
            if g > prev: up += 1
            else:        down += 1
        prev = g
    return up, down, up+down, start, (float(rows[start][rpm_index]) if len(rows[start]) > rpm_index and rows[start][rpm_index] != "" else None)

if uploaded:
    data_text = uploaded.getvalue().decode("utf-8-sig", errors="ignore")
    lines = data_text.splitlines(keepends=True)

    # find the header
    header_idx = find_header_idx(lines)
    if header_idx is None:
        st.error('Oh No! You exported the wrong channels 😔 We need Gear and Engine Speed only')
        st.stop()

    reader = csv.reader(lines[header_idx:])
    headers = next(reader)  # header row

    # check that we only have the two expected columns
    if len(headers) != 2 or RPM_COL not in headers or GEAR_COL not in headers:
        st.error(f"Ya got too many channels 😔 We only want: ['{RPM_COL}', '{GEAR_COL}']. You gave us: {headers}")
        st.stop()

    next(reader, None)  # skip the units row
    rows = list(reader)

    # column indices
    rpm_i = headers.index(RPM_COL)
    gear_i = headers.index(GEAR_COL)

    up, down, total, start_idx, start_rpm = count_shifts_after_start(rows, rpm_i, gear_i, rpm_threshold)

    st.subheader("Results")
    st.metric("Upshifts", up)
    st.metric("Downshifts", down)
    st.metric("Total shifts", total)

    st.caption(
        f"Start index: **{start_idx if start_idx is not None else 'n/a'}** · "
        f"Start RPM: **{start_rpm if start_rpm is not None else 'n/a'}**"
    )


else:
    st.info("Upload a CSV to begin.")
