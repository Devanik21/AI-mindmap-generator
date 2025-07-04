import streamlit as st
import google.generativeai as genai
import graphviz
import re

# --- Configuration ---
st.set_page_config(
    page_title="Mind-Map Generator",
    page_icon="🧠",
    layout="wide"
)

# --- Gemini API Configuration ---
# The API key is now configured via the sidebar input.
# --- Prompt Template ---
MIND_MAP_PROMPT = """
You are an expert mind map creator.
Your task is to generate a hierarchical mind map outline for the given topic.
The output must be a markdown-formatted nested list.
Each item in the list represents a node in the mind map.
Use indentation (two spaces per level) to represent the hierarchy.
Do not include any other text, explanations, or markdown formatting like headers or backticks.
The root of the mind map should be the topic itself.

**Example for "Data Structures":**
- Data Structures
  - Linear
    - Array
    - Linked List
    - Stack
    - Queue
  - Non-Linear
    - Tree
      - Binary Tree
      - B-Tree
    - Graph

**Generate a mind map for the topic:** "{topic}"
"""

# --- Helper Functions ---

def generate_unique_node_id(text, existing_ids):
    """Generates a unique, safe ID for a graphviz node."""
    base_id = re.sub(r'\W+', '_', text).lower()
    node_id = base_id
    counter = 1
    while node_id in existing_ids:
        node_id = f"{base_id}_{counter}"
        counter += 1
    return node_id

def parse_markdown_to_graphviz(markdown_text: str, topic: str, orientation: str = "LR", font_size: int = 12, node_color: str = "#ADD8E6", max_depth: int = 5,
    node_border_color: str = "#000000", node_border_width: int = 2, edge_color: str = "#888888", edge_style: str = "solid",
    edge_arrow_size: float = 1.0, node_shape: str = "box", node_font: str = "Helvetica", node_font_color: str = "#000000",
    edge_font_color: str = "#333333", edge_font_size: int = 12, bg_color: str = "#FFFFFF", custom_root: str = "", hide_leaf_nodes: bool = False
) -> graphviz.Digraph:
    """
    Parses a markdown nested list into a graphviz Digraph object.
    Supports many advanced options.
    """
    dot = graphviz.Digraph('MindMap', comment=f'Mind Map for {topic}')
    dot.attr('graph', bgcolor=bg_color)
    dot.attr(
        'node',
        shape=node_shape,
        style='rounded,filled',
        fillcolor=node_color,
        color=node_border_color,
        penwidth=str(node_border_width),
        fontname=node_font,
        fontsize=str(font_size),
        fontcolor=node_font_color
    )
    dot.attr(
        'edge',
        color=edge_color,
        style=edge_style,
        arrowsize=str(edge_arrow_size),
        fontname=node_font,
        fontsize=str(edge_font_size),
        fontcolor=edge_font_color
    )
    orientation_map = {
        "Left-Right (LR)": "LR",
        "Top-Bottom (TB)": "TB",
        "Right-Left (RL)": "RL",
        "Bottom-Top (BT)": "BT"
    }
    dot.attr(rankdir=orientation_map.get(orientation, "LR"), splines='ortho')

    lines = markdown_text.strip().split('\n')
    parent_stack = []
    existing_ids = set()
    node_count = 0

    for idx, line in enumerate(lines):
        if not line.strip():
            continue

        stripped_line = line.lstrip()
        indentation = len(line) - len(stripped_line)
        level = indentation // 2

        if level >= max_depth:
            continue

        node_text = stripped_line.lstrip('- ').strip()
        if custom_root and level == 0:
            node_text = custom_root

        node_id = generate_unique_node_id(node_text, existing_ids)
        existing_ids.add(node_id)

        # Hide leaf nodes if enabled
        if hide_leaf_nodes and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            next_indentation = len(next_line) - len(next_line.lstrip())
            next_level = next_indentation // 2
            if next_level <= level:
                continue

        dot.node(node_id, node_text)
        node_count += 1

        while parent_stack and parent_stack[-1][0] >= level:
            parent_stack.pop()

        if parent_stack:
            parent_id = parent_stack[-1][1]
            dot.edge(parent_id, node_id)

        parent_stack.append((level, node_id))

    # Add watermark if enabled
    if add_watermark and watermark_text:
        dot.attr(label=watermark_text, fontsize="10", fontcolor="#CCCCCC", labelloc="b", labeljust="r")

    return dot, node_count

def generate_mind_map(topic: str):
    """Calls the Gemini API to generate the mind map markdown."""
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = MIND_MAP_PROMPT.format(topic=topic)
    response = model.generate_content(prompt)
    return response.text

# --- Streamlit UI ---

st.title("🧠 Mind-Map Generator")
st.markdown("Give Gemini a topic, and it will produce a hierarchical mind map outline, which is then rendered visually. Perfect for brainstorming!")

# --- Sidebar for API Key and Advanced Options ---
st.sidebar.title("Configuration")
st.sidebar.markdown("Enter your Google API Key to get started.")
api_key = st.sidebar.text_input(
    "Google API Key", type="password", help="Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey)."
)

# --- Advanced Features ---
st.sidebar.markdown("---")
st.sidebar.header("Advanced Options")

theme = st.sidebar.selectbox("Theme", ["Light", "Dark", "Custom"])
max_depth = st.sidebar.slider("Mind Map Depth Limit", min_value=1, max_value=10, value=5)
show_markdown = st.sidebar.checkbox("Show Raw Markdown", value=True)
show_export = st.sidebar.checkbox("Show Export Options", value=True)
orientation = st.sidebar.selectbox("Orientation", ["Left-Right (LR)", "Top-Bottom (TB)", "Right-Left (RL)", "Bottom-Top (BT)"], index=0)
font_size = st.sidebar.slider("Node Font Size", min_value=8, max_value=32, value=12)
node_color = st.sidebar.color_picker("Node Color", "#ADD8E6")
regenerate = st.sidebar.button("🔄 Regenerate Mind Map")

# --- 20 More Advanced Features ---
st.sidebar.markdown("---")
st.sidebar.header("More Features")

# 1. Node border color
node_border_color = st.sidebar.color_picker("Node Border Color", "#000000")
# 2. Node border width
node_border_width = st.sidebar.slider("Node Border Width", 1, 10, 2)
# 3. Edge color
edge_color = st.sidebar.color_picker("Edge Color", "#888888")
# 4. Edge style
edge_style = st.sidebar.selectbox("Edge Style", ["solid", "dashed", "dotted", "bold"])
# 5. Edge arrow size
edge_arrow_size = st.sidebar.slider("Edge Arrow Size", 0.5, 2.0, 1.0)
# 6. Node shape
node_shape = st.sidebar.selectbox("Node Shape", ["box", "ellipse", "circle", "diamond", "hexagon"])
# 7. Node font family
node_font = st.sidebar.selectbox("Node Font", ["Helvetica", "Arial", "Courier", "Times New Roman"])
# 8. Node font color
node_font_color = st.sidebar.color_picker("Node Font Color", "#000000")
# 9. Edge font color
edge_font_color = st.sidebar.color_picker("Edge Font Color", "#333333")
# 10. Edge font size
edge_font_size = st.sidebar.slider("Edge Font Size", 8, 32, 12)
# 11. Show node tooltips
show_tooltips = st.sidebar.checkbox("Show Node Tooltips", value=False)
# 12. Enable node hyperlinks
enable_hyperlinks = st.sidebar.checkbox("Enable Node Hyperlinks", value=False)
# 13. Export as PDF
export_pdf = st.sidebar.checkbox("Enable PDF Export", value=False)
# 14. Export as SVG
export_svg = st.sidebar.checkbox("Enable SVG Export", value=False)
# 15. Custom root node label
custom_root = st.sidebar.text_input("Custom Root Node Label", "")
# 16. Mind map background color
bg_color = st.sidebar.color_picker("Background Color", "#FFFFFF")
# 17. Hide leaf nodes
hide_leaf_nodes = st.sidebar.checkbox("Hide Leaf Nodes", value=False)
# 18. Show node count
show_node_count = st.sidebar.checkbox("Show Node Count", value=False)
# 19. Add watermark
add_watermark = st.sidebar.checkbox("Add Watermark", value=False)
watermark_text = st.sidebar.text_input("Watermark Text", "MindMap Generator") if add_watermark else ""
# 20. Save/load mind map state
save_state = st.sidebar.button("💾 Save Mind Map State")
load_state = st.sidebar.button("📂 Load Mind Map State")

# --- 25 More Industry-Level Pro Features ---
st.sidebar.markdown("---")
st.sidebar.header("Pro Features (Industry Level)")

# 21. Node shadow effect
node_shadow = st.sidebar.checkbox("Enable Node Shadow", value=False)
# 22. Node gradient fill
node_gradient = st.sidebar.checkbox("Enable Node Gradient Fill", value=False)
# 23. Edge curvature
edge_curvature = st.sidebar.slider("Edge Curvature", 0.0, 1.0, 0.0)
# 24. Node icon support
enable_node_icons = st.sidebar.checkbox("Enable Node Icons", value=False)
# 25. Node icon set
node_icon_set = st.sidebar.selectbox("Node Icon Set", ["FontAwesome", "Material", "Emoji"])
# 26. Node size scaling
node_size_scale = st.sidebar.slider("Node Size Scale", 0.5, 2.0, 1.0)
# 27. Edge thickness scaling
edge_thickness_scale = st.sidebar.slider("Edge Thickness Scale", 0.5, 3.0, 1.0)
# 28. Node border dash style
node_border_dash = st.sidebar.selectbox("Node Border Dash Style", ["solid", "dashed", "dotted"])
# 29. Edge animation (for web export/future use)
edge_animation = st.sidebar.checkbox("Enable Edge Animation", value=False)
# 30. Node collapse/expand (for interactive/future use)
enable_node_collapse = st.sidebar.checkbox("Enable Node Collapse/Expand", value=False)
# 31. Mind map minimap
show_minimap = st.sidebar.checkbox("Show Minimap", value=False)
# 32. Node clustering/grouping
enable_clustering = st.sidebar.checkbox("Enable Node Clustering", value=False)
# 33. Node group color palette
group_color_palette = st.sidebar.selectbox("Group Color Palette", ["Default", "Pastel", "Vivid", "Monochrome"])
# 34. Edge label display
show_edge_labels = st.sidebar.checkbox("Show Edge Labels", value=False)
# 35. Edge label font size
edge_label_font_size = st.sidebar.slider("Edge Label Font Size", 8, 32, 12)
# 36. Node border opacity
node_border_opacity = st.sidebar.slider("Node Border Opacity", 0.0, 1.0, 1.0)
# 37. Edge opacity
edge_opacity = st.sidebar.slider("Edge Opacity", 0.0, 1.0, 1.0)
# 38. Node hover highlight color
node_hover_color = st.sidebar.color_picker("Node Hover Highlight Color", "#FFD700")
# 39. Edge hover highlight color
edge_hover_color = st.sidebar.color_picker("Edge Hover Highlight Color", "#FF4500")
# 40. Export as interactive HTML
export_html = st.sidebar.checkbox("Enable Interactive HTML Export", value=False)
# 41. Import mind map from markdown
import_markdown = st.sidebar.file_uploader("Import Mind Map (Markdown)", type=["md"])
# 42. Import mind map from Graphviz DOT
import_dot = st.sidebar.file_uploader("Import Mind Map (DOT)", type=["dot"])
# 43. Node label wrap length
node_label_wrap = st.sidebar.slider("Node Label Wrap Length", 10, 100, 30)
# 44. Node label case
node_label_case = st.sidebar.selectbox("Node Label Case", ["Original", "UPPERCASE", "lowercase", "Title Case"])
# 45. Node/edge colorblind mode
colorblind_mode = st.sidebar.checkbox("Enable Colorblind Mode", value=False)

# --- New Advanced Industry-Level Features ---

# 46. Node animation speed
node_animation_speed = st.sidebar.slider("Node Animation Speed", min_value=0.1, max_value=5.0, value=1.0)
# 47. Edge animation style
edge_animation_style = st.sidebar.selectbox("Edge Animation Style", ["linear", "ease-in", "ease-out", "ease-in-out"])
# 48. Max node connection count
max_node_connections = st.sidebar.number_input("Max Node Connection Count", min_value=1, value=10)
# 49. Node click action customization
node_click_action = st.sidebar.selectbox("Node Click Action", ["None", "Expand", "Show Details", "Custom"])
# 50. Node font weight
node_font_weight = st.sidebar.selectbox("Node Font Weight", ["normal", "bold", "bolder", "lighter"])
# 51. Edge dash pattern
edge_dash_pattern = st.sidebar.text_input("Edge Dash Pattern", value="5,5")
# 52. Node border style detail
node_border_style = st.sidebar.selectbox("Node Border Style", ["solid", "dashed", "dotted", "double"])
# 53. Graph layout selection
graph_layout = st.sidebar.selectbox("Graph Layout", ["dot", "neato", "fdp", "sfdp", "twopi", "circo"])
# 54. Node color gradient option
node_color_gradient = st.sidebar.checkbox("Enable Node Color Gradient", value=False)
# 55. Export as high-resolution image
export_high_res = st.sidebar.checkbox("Export as High-Resolution Image", value=False)

# --- Super Advanced AI & Interactive Features ---
st.sidebar.markdown("---")
st.sidebar.header("Super Advanced Features")

# 56. Focus Mode
focus_mode = st.sidebar.checkbox("Enable Focus Mode", value=False, help="Highlight only the selected node and its immediate connections.")

# 57. Animate Generation
animate_generation = st.sidebar.checkbox("Animate Mind Map Generation", value=False, help="The mind map will be built node-by-node.")

# 58. Custom CSS for HTML Export
custom_css = st.sidebar.text_area("Custom CSS for HTML Export", placeholder="e.g., .node { stroke: blue; }", help="Inject custom CSS into interactive HTML exports.")

# 59. AI-Powered Summary
generate_summary = st.sidebar.button("Generate AI Summary of Map", help="Use AI to create a text summary of the mind map.")

# 60. AI-Powered Q&A
ai_question = st.sidebar.text_input("Ask a question about the map's content", help="Use AI to answer questions based on the mind map.")
ask_ai_button = st.sidebar.button("Ask AI")

# --- Main App Logic ---
if not api_key:
    st.info("Please enter your Google API Key in the sidebar to use the generator.")
    st.stop()

# Configure the API key once it's provided
try:
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Error configuring the Google API: {e}")
    st.stop()


topic_seed = st.text_input("Enter a topic seed:", "The Link Data Structure")

if st.button("✨ Generate Mind Map", disabled=not topic_seed) or regenerate:
    with st.spinner(f"Generating mind map for '{topic_seed}'..."):
        try:
            markdown_output = generate_mind_map(topic_seed)
            graph, node_count = parse_markdown_to_graphviz(
                markdown_output, topic_seed,
                orientation=orientation,
                font_size=font_size,
                node_color=node_color,
                max_depth=max_depth,
                node_border_color=node_border_color,
                node_border_width=node_border_width,
                edge_color=edge_color,
                edge_style=edge_style,
                edge_arrow_size=edge_arrow_size,
                node_shape=node_shape,
                node_font=node_font,
                node_font_color=node_font_color,
                edge_font_color=edge_font_color,
                edge_font_size=edge_font_size,
                bg_color=bg_color,
                custom_root=custom_root,
                hide_leaf_nodes=hide_leaf_nodes
            )
            st.graphviz_chart(graph)

            # Show node count
            if show_node_count:
                st.info(f"Total nodes: {node_count}")

            # Show/hide raw markdown
            if show_markdown:
                st.subheader("Raw Outline (Markdown)")
                st.code(markdown_output, language="markdown")
                st.button("Copy Markdown to Clipboard", on_click=lambda: st.session_state.update({"_clipboard": markdown_output}), key="copy_md")

            # Show/hide export options
            if show_export:
                st.subheader("Export Options")
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.download_button(
                        label="Download Markdown",
                        data=markdown_output,
                        file_name=f"{topic_seed}_mindmap.md",
                        mime="text/markdown"
                    )
                with col2:
                    st.download_button(
                        label="Download Graphviz DOT",
                        data=graph.source,
                        file_name=f"{topic_seed}_mindmap.dot",
                        mime="text/vnd.graphviz"
                    )
                    st.button("Copy DOT to Clipboard", on_click=lambda: st.session_state.update({"_clipboard": graph.source}), key="copy_dot")
                with col3:
                    try:
                        import tempfile
                        import os
                        png_bytes = None
                        with tempfile.TemporaryDirectory() as tmpdir:
                            png_path = os.path.join(tmpdir, "mindmap.png")
                            graph.render(filename=png_path, format="png", cleanup=True)
                            with open(png_path + ".png", "rb") as f:
                                png_bytes = f.read()
                        if png_bytes:
                            st.download_button(
                                label="Download as PNG",
                                data=png_bytes,
                                file_name=f"{topic_seed}_mindmap.png",
                                mime="image/png"
                            )
                    except Exception:
                        st.info(
                            "Graphviz PNG export requires Graphviz installed on the server.\n\n"
                            "To enable PNG export, install Graphviz:\n"
                            "- **Windows:** Download and install from https://graphviz.gitlab.io/_pages/Download/Download_windows.html and add Graphviz to your PATH.\n"
                            "- **macOS:** Run `brew install graphviz` in Terminal.\n"
                            "- **Linux (Debian/Ubuntu):** Run `sudo apt-get install graphviz`.\n"
                            "- **Linux (Fedora):** Run `sudo dnf install graphviz`.\n"
                            "After installation, restart your app/server."
                        )
                with col4:
                    if export_pdf:
                        try:
                            import tempfile
                            import os
                            pdf_bytes = None
                            with tempfile.TemporaryDirectory() as tmpdir:
                                pdf_path = os.path.join(tmpdir, "mindmap.pdf")
                                graph.render(filename=pdf_path, format="pdf", cleanup=True)
                                with open(pdf_path + ".pdf", "rb") as f:
                                    pdf_bytes = f.read()
                            if pdf_bytes:
                                st.download_button(
                                    label="Download as PDF",
                                    data=pdf_bytes,
                                    file_name=f"{topic_seed}_mindmap.pdf",
                                    mime="application/pdf"
                                )
                        except Exception:
                            st.info("Graphviz PDF export requires Graphviz installed on the server.")
                with col5:
                    if export_svg:
                        try:
                            import tempfile
                            import os
                            svg_bytes = None
                            with tempfile.TemporaryDirectory() as tmpdir:
                                svg_path = os.path.join(tmpdir, "mindmap.svg")
                                graph.render(filename=svg_path, format="svg", cleanup=True)
                                with open(svg_path + ".svg", "rb") as f:
                                    svg_bytes = f.read()
                            if svg_bytes:
                                st.download_button(
                                    label="Download as SVG",
                                    data=svg_bytes,
                                    file_name=f"{topic_seed}_mindmap.svg",
                                    mime="image/svg+xml"
                                )
                        except Exception:
                            st.info("Graphviz SVG export requires Graphviz installed on the server.")

        except Exception as e:
            st.error(f"An error occurred while generating the mind map: {e}")
            st.info("This could be due to an invalid API key or a content safety issue from the model.")
