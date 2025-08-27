import csv
import streamlit as st

st.set_page_config(page_title="Shift Counter", page_icon="⚙️", layout="centered")
st.title("Vitti's BFR Shift Counter")

st.caption("Counts total gear shifts and miss-shifts from a MoTeC i2 CSV. "
           "Neutral (0) and blanks in Gear are ignored (transient neutrals dropped).")
st.caption("Upload a CSV that contains exactly these channels: 'Engine Speed', 'Gear', and 'Gear Shift Request'.")

uploaded = st.file_uploader("Upload CSV", type=["csv"])
rpm_threshold = st.number_input("RPM start threshold", value=2800.0, step=100.0)
st.caption("Any shifts/requests before Engine Speed reaches this threshold will not be counted. This eliminates any manual shifting that may occur before the engine starts.")

RPM_COL  = "Engine Speed"
GEAR_COL = "Gear"
REQ_COL  = "Gear Shift Request"

def normalize_gear(cell):
    s = str(cell).strip()
    if not s:
        return None
    g = int(float(s))
    return g if g > 0 else None

def find_header_idx(lines):
    for i, line in enumerate(lines):
        if ('"Engine Speed"' in line) and ('"Gear"' in line) and ('"Gear Shift Request"' in line):
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

def count_total_shifts(rows, rpm_i, gear_i, threshold):
    start = find_start(rows, rpm_i, threshold)
    if start is None:
        return 0, start, None
    total = 0
    prev = None
    for row in rows[start:]:
        if len(row) <= gear_i: continue
        g = normalize_gear(row[gear_i])
        if g is None: continue
        if prev is not None and g != prev:
            total += 1
        prev = g
    start_rpm = float(rows[start][rpm_i]) if len(rows[start]) > rpm_i and rows[start][rpm_i] != "" else None
    return total, start, start_rpm

def normalize_request(cell):
    s = str(cell).strip()
    if not s:
        return None
    v = int(float(s))
    return v if v in (1,3,4) else None

def count_requests(rows, rpm_i, req_i, threshold):
    start = find_start(rows, rpm_i, threshold)
    if start is None:
        return 0
    requests = 0
    prev = None
    for row in rows[start:]:
        if len(row) <= req_i: continue
        v = normalize_request(row[req_i])
        if v is None: continue
        if prev is not None and prev == 1 and v in (3,4) and v != prev:
            requests += 1
        prev = v
    return requests

if uploaded:
    data_text = uploaded.getvalue().decode("utf-8-sig", errors="ignore")
    lines = data_text.splitlines(keepends=True)

    header_idx = find_header_idx(lines)
    if header_idx is None:
        st.error("Oh No! You exported the wrong channels 😔 We need Gear, Engine Speed, and Gear Shift Request only")
        st.stop()

    reader = csv.reader(lines[header_idx:])
    headers = next(reader)  # header row
    next(reader, None)      # skip the units row
    rows = list(reader)

    expected = {RPM_COL, GEAR_COL, REQ_COL}
    actual = [h.strip() for h in headers]
    if set(actual) != expected or len(actual) != 3:
        st.error(f"Ya got too many (or the wrong) channels 😔 We only want: {sorted(expected)}. You gave us: {actual}")
        st.stop()

    rpm_i = headers.index(RPM_COL)
    gear_i = headers.index(GEAR_COL)
    req_i = headers.index(REQ_COL)

    total_shifts, start_idx, start_rpm = count_total_shifts(rows, rpm_i, gear_i, rpm_threshold)
    requests = count_requests(rows, rpm_i, req_i, rpm_threshold)
    miss_shifts = max(requests - total_shifts, 0)

    st.subheader("Results")
    c1, c2 = st.columns([2, 1])
    with c1:
        st.metric("Total shifts", total_shifts)
    with c2:
        st.metric("Miss-Shifts", miss_shifts)

    st.caption(
        f"Start index: **{start_idx if start_idx is not None else 'n/a'}** · "
        f"Start RPM: **{start_rpm if start_rpm is not None else 'n/a'}** · "
        f"Requests: **{requests}**"
    )


else:
    st.info("Upload a CSV to begin.")

