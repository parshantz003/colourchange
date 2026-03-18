import streamlit as st
import zipfile
import io
import re
import base64
from pathlib import Path
from cairosvg import svg2pdf 
from cairosvg import svg2png

st.set_page_config(page_title="Bulk SVG 2-Color Changer", layout="wide")
st.title("🎨 Parshant Bulk SVG 2-Color Changer (ZIP Support)")
st.write("Upload a **ZIP** containing one folder with multiple .svg files using the **same 2 colors**.")

# ────────────────────────────────────────────────.
# FILE UPLOAD
# ────────────────────────────────────────────────
uploaded_zip = st.file_uploader(
    "Upload ZIP file containing folder with .svg icons",
    type=["zip"],
    help="The ZIP should contain exactly one top-level folder with .svg files inside."
)

if uploaded_zip is not None:
    with zipfile.ZipFile(uploaded_zip, 'r') as zf:
        file_list = zf.namelist()

        # Find all .svg files
        svg_paths = [p for p in file_list if p.lower().endswith('.svg')]

        if not svg_paths:
            st.error("No .svg files found in the ZIP.")
            st.stop()

        # Detect common folder prefix
        common_prefix = Path(svg_paths[0]).parent.as_posix() if svg_paths else ""
        if common_prefix:
            st.info(f"Detected folder structure: **{common_prefix}/** containing {len(svg_paths)} SVG files")

        # ────────────────────────────────────────────────
        # Read first SVG to detect colors
        # ────────────────────────────────────────────────
        first_svg_path = svg_paths[0]
        with zf.open(first_svg_path) as f:
            original_content = f.read().decode('utf-8')

        hex_matches = re.findall(r'#([0-9a-fA-F]{3,8})\b', original_content)
        detected = sorted(list(set(['#' + c.upper() for c in hex_matches])))

        st.subheader("Detected Colors (from first file)")

        if len(detected) == 2:
            st.success(f"Found exactly 2 colors:")
            col1, col2 = st.columns(2)
            col1.metric("Color 1", detected[0])
            col2.metric("Color 2", detected[1])
            old_color1, old_color2 = detected
        else:
            st.warning(f"Detected {len(detected)} colors — manual selection required")
            col1, col2 = st.columns(2)
            old_color1 = col1.color_picker("Original Color 1", "#0077C8")
            old_color2 = col2.color_picker("Original Color 2", "#00A676")

        # ────────────────────────────────────────────────
        # New colors selection
        # ────────────────────────────────────────────────
        st.subheader("Choose replacement colors")
        col1, col2 = st.columns(2)
        new_color1 = col1.color_picker("New Color 1", value="#FF5500", key="new1")
        new_color2 = col2.color_picker("New Color 2", value="#00AAFF", key="new2")

        # ────────────────────────────────────────────────
        # Format selection
        # ────────────────────────────────────────────────
        st.subheader("Select output formats")
        col_a, col_b, col_c = st.columns(3)
        want_svg = col_a.checkbox("SVG", value=True)
        want_pdf = col_b.checkbox("PDF", value=True)
        want_xml = col_c.checkbox("XML", value=True)
        want_png = col_a.checkbox("PNG", value=True)

        if not (want_svg or want_pdf or want_xml or want_png):
            st.warning("Please select at least one output format.")

        # ────────────────────────────────────────────────
        # Process button
        # ────────────────────────────────────────────────
        if st.button("🔄 Recolor & Generate Selected Formats", type="primary", use_container_width=True):

            if not (want_svg or want_pdf or want_xml or want_png):
                st.error("No formats selected. Please choose at least one format above.")
            else:
                with st.spinner(f"Processing {len(svg_paths)} files..."):

                    output_zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(output_zip_buffer, "w", zipfile.ZIP_DEFLATED) as out_zip:

                        for rel_path in svg_paths:
                            with zf.open(rel_path) as f:
                                content = f.read().decode('utf-8')

                            # Replace colors (case insensitive)
                            content = content.replace(old_color1, new_color1)
                            content = content.replace(old_color1.lower(), new_color1.lower())
                            content = content.replace(old_color2, new_color2)
                            content = content.replace(old_color2.lower(), new_color2.lower())

                            # Prepare paths
                            base_name = Path(rel_path).stem
                            folder = Path(rel_path).parent.as_posix() + "/" if Path(rel_path).parent.as_posix() else ""

                            # 1. SVG
                            if want_svg:
                                out_zip.writestr(rel_path, content.encode('utf-8'))

                            # 2. PDF
                            if want_pdf:
                                try:
                                    pdf_bytes = svg2pdf(bytestring=content.encode('utf-8'))
                                    pdf_path = folder + base_name + ".pdf"
                                    out_zip.writestr(pdf_path, pdf_bytes)
                                except Exception as pdf_err:
                                    st.warning(f"PDF failed for {rel_path}: {pdf_err}")

                            # 3. XML
                            if want_xml:
                                xml_path = folder + base_name + ".xml"
                                out_zip.writestr(xml_path, content.encode('utf-8'))
                            # 3. PNG
                            if want_png:
                                png_bytes = svg2png(bytestring=content.encode('utf-8'))
                                png_path = folder + base_name + ".png"
                                out_zip.writestr(png_path, png_bytes)

                    output_zip_buffer.seek(0)

                selected_formats = []
                if want_svg: selected_formats.append(".svg")
                if want_pdf: selected_formats.append(".pdf")
                if want_xml: selected_formats.append(".xml")
                if want_png: selected_formats.append(".png")

                st.success(f"Done! {len(svg_paths)} files processed → formats: {', '.join(selected_formats)}")

                # Download button
                st.download_button(
                    label=f"📦 Download ZIP ({' + '.join(selected_formats)})",
                    data=output_zip_buffer,
                    file_name="recolored_icons.zip",
                    mime="application/zip",
                    use_container_width=True
                )

                # Safe SVG preview (first file)
                st.subheader("Preview of first recolored SVG")
                if content.strip():
                    b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
                    html = f'''
                    <div style="text-align: center; margin: 1.5rem 0;">
                        <img src="data:image/svg+xml;base64,{b64}"
                             style="width: 280px; max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
                             alt="Recolored SVG Preview">
                    </div>
                    '''
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    st.info("No content to preview")
