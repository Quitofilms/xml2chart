import streamlit as st
import xml.etree.ElementTree as ET
import math
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import mm
from reportlab.lib import colors
import io

# --- UI Setup ---
st.set_page_config(page_title="Pro Chord Grid Web", layout="centered")
st.title("Pro Chord Grid Web v1.9.1")
st.write("Convert MusicXML to professional rhythmic chord charts.")

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("Chart Settings")
    cols = st.slider("Measures per row", 4, 8, 4)
    start_bar = st.number_input("Start Measure", min_value=1, value=1)
    end_bar = st.number_input("End Measure (0 for all)", min_value=0, value=0)
    
    st.subheader("Formatting")
    include_slashes = st.checkbox("Include Rhythmic Slashes (////)", value=True)
    include_bass = st.checkbox("Include Bass Notes (e.g., /B)", value=True)
    
    st.subheader("Symbol Swap")
    find_str = st.text_input("Find (e.g., -)", value="-")
    replace_str = st.text_input("Replace (e.g., m)", value="m")

# --- Logic Engine (v1.9.1) ---
def generate_pdf(xml_data):
    tree = ET.parse(xml_data)
    root = tree.getroot()
    measures = []
    part = root.find(".//part[@id='P1']") or root.find(".//part")
    
    t = root.find(".//work-title")
    song_title = t.text if t is not None else "CHORD CHART"
    time_node = root.find(".//attributes/time")
    time_sig = f"{time_node.find('beats').text}/{time_node.find('beat-type').text}" if time_node is not None else "4/4"

    first_chord_found, internal_count = False, 1 
    for m in part.findall("measure"):
        chords_in_m, harmony_tags = [], m.findall("harmony")
        rehearsal = m.find(".//rehearsal")
        reh_text = rehearsal.text if rehearsal is not None else None
        
        if not first_chord_found and not harmony_tags: continue
        if harmony_tags:
            first_chord_found = True
            for h in harmony_tags:
                # Handle Accidentals
                root_node = h.find(".//root-step")
                alter_node = h.find(".//root-alter")
                kind_node = h.find("kind")
                offset = h.find("offset")
                bass_step_node = h.find("bass/bass-step")
                bass_alter_node = h.find("bass/bass-alter")
                
                step = root_node.text if root_node is not None else ""
                if alter_node is not None:
                    if alter_node.text == "1": step += "#"
                    elif alter_node.text == "-1": step += "b"
                
                kind = kind_node.get("text") if kind_node is not None and kind_node.get("text") is not None else ""
                chord_text = f"{step}{kind}".replace("major-seventh", "Maj7").replace("minor-seventh", "m7").replace("major-sixth", "6")
                
                if find_str: chord_text = chord_text.replace(find_str, replace_str)
                
                if include_bass and bass_step_node is not None:
                    bass_text = bass_step_node.text
                    if bass_alter_node is not None:
                        if bass_alter_node.text == "1": bass_text += "#"
                        elif bass_alter_node.text == "-1": bass_text += "b"
                    chord_text += f"/{bass_text}"
                
                off_val = int(offset.text) if offset is not None else 0
                chords_in_m.append({"text": chord_text, "offset": off_val})
        
        limit = end_bar if end_bar > 0 else 9999
        if start_bar <= internal_count <= limit:
            measures.append({"num": str(internal_count), "chords": chords_in_m, "rehearsal": reh_text})
        internal_count += 1

    # PDF Rendering
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=portrait(A4))
    w, h = portrait(A4)
    margin = 15*mm
    total_rows = math.ceil(len(measures) / cols)
    title_y, grid_top = h - 25*mm, h - 30*mm
    ch = 22*mm
    cw = (w - (2*margin)) / cols
    curr_x, curr_y = margin, grid_top - ch

    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, title_y, song_title.upper())
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w - margin - 10*mm, title_y, time_sig)

    for i, m in enumerate(measures):
        c.setStrokeColor(colors.black); c.setLineWidth(0.7)
        if m['rehearsal']:
            c.setFont("Helvetica-Bold", 10); c.rect(curr_x, curr_y + ch + 1*mm, 6*mm, 6*mm)
            c.drawCentredString(curr_x + 3*mm, curr_y + ch + 2.5*mm, m['rehearsal'])
        c.line(curr_x, curr_y, curr_x, curr_y + ch)
        if (i + 1) % cols == 0 or (i + 1) == len(measures):
            if (i + 1) == len(measures):
                c.setLineWidth(2); c.line(curr_x + cw, curr_y, curr_x + cw, curr_y + ch)
                c.setLineWidth(0.5); c.line(curr_x + cw - 1*mm, curr_y, curr_x + cw - 1*mm, curr_y + ch)
            else: c.line(curr_x + cw, curr_y, curr_x + cw, curr_y + ch)
        c.setLineWidth(0.7); c.line(curr_x, curr_y, curr_x + cw, curr_y)
        c.setFont("Helvetica", 7); c.drawString(curr_x + 1.5*mm, curr_y + ch - 4*mm, str(m['num']))
        
        chords, col_w = m['chords'], cw / 4
        if not chords and include_slashes:
            c.setStrokeColor(colors.grey); c.setLineWidth(0.4)
            for s in range(4):
                sx = curr_x + (col_w * s) + (col_w/2)
                c.line(sx - 2*mm, curr_y + (ch/2) - 3*mm, sx + 2*mm, curr_y + (ch/2) + 3*mm)
        
        c.setFont("Helvetica-Bold", 14)
        for idx, chord in enumerate(chords[:4]):
            c.drawString(curr_x + (col_w * idx) + 2*mm, curr_y + (ch/2) - 2*mm, chord['text'])

        curr_x += cw
        if (i + 1) % cols == 0:
            curr_x, curr_y = margin, curr_y - ch
    
    c.save()
    buf.seek(0)
    return buf, song_title

# --- Web Interface ---
uploaded_file = st.file_uploader("Choose a MusicXML file", type=["xml", "musicxml"])

if uploaded_file:
    pdf_output, song_name = generate_pdf(uploaded_file)
    st.success(f"Generated {song_name}")
    st.download_button(
        label="Download PDF",
        data=pdf_output,
        file_name=f"{song_name}.pdf",
        mime="application/pdf"
    )
