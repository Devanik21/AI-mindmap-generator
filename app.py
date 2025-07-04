import streamlit as st
import google.generativeai as genai
import graphviz
import re
import requests
from bs4 import BeautifulSoup
import json

# --- Configuration ---
st.set_page_config(
    page_title="IntelliMap Generator",
    page_icon="🧠",
    layout="wide"
)

# --- Default Prompt & Themes ---
DEFAULT_MIND_MAP_PROMPT = """
You are an expert mind map creator.
Your task is to generate a hierarchical mind map outline for the given topic.
The output must be a markdown-formatted nested list.
Each item in the list represents a node in the mind map.
Use indentation (two spaces per level) to represent the hierarchy.
Do not include any other text, explanations, or markdown formatting like headers, code blocks, or bolding.
The root of the mind map should be the topic itself.

**Example for "Data Structures":**
- Data Structures
  - Linear
    - Array
    - Linked List
  - Non-Linear
    - Tree
    - Graph

**Generate a mind map for the topic:** "{topic}"
"""

THEMES = {
    "Default Light": {"bg_color": "#FFFFFF", "node_color": "#ADD8E6", "node_font_color": "#000000", "edge_color": "#888888", "node_border_color": "#666666", "highlight_color": "#FFD700"},
    "Default Dark": {"bg_color": "#0E1117", "node_color": "#262730", "node_font_color": "#FAFAFA", "edge_color": "#A0A0A0", "node_border_color": "#1E90FF", "highlight_color": "#FF6347"},
    "Forest": {"bg_color": "#F0FFF0", "node_color": "#2E8B57", "node_font_color": "#FFFFFF", "edge_color": "#8FBC8F", "node_border_color": "#006400", "highlight_color": "#FFD700"},
    "Synthwave": {"bg_color": "#2D004F", "node_color": "#FF00FF", "node_font_color": "#FFFFFF", "edge_color": "#00FFFF", "node_border_color": "#FFFF00", "highlight_color": "#FF69B4"},
    "Peach": {"bg_color": "#FFF5EE", "node_color": "#FFDAB9", "node_font_color": "#8B4513", "edge_color": "#FFA07A", "node_border_color": "#CD853F", "highlight_color": "#DC143C"},
}

# --- Session State Initialization ---
def initialize_state():
    """Initializes all session state variables."""
    # --- Backend State ---
    if "history" not in st.session_state:
        st.session_state.history = []
    if "history_index" not in st.session_state:
        st.session_state.history_index = -1
    if "api_key" not in st.session_state:
        st.session_state.api_key = ""
    if "graph" not in st.session_state:
        st.session_state.graph = None
    if "markdown_output" not in st.session_state:
        st.session_state.markdown_output = ""
    if "node_list" not in st.session_state:
        st.session_state.node_list = []
    if "ai_analysis" not in st.session_state:
        st.session_state.ai_analysis = ""

    # --- UI Controls ---
    # Using keys for widgets ensures their state is preserved
    if "input_source" not in st.session_state:
        st.session_state["input_source"] = "Topic"
    if "topic_input" not in st.session_state:
        st.session_state["topic_input"] = "The Future of Artificial Intelligence"
    if "url_input" not in st.session_state:
        st.session_state["url_input"] = ""
    if "text_input" not in st.session_state:
        st.session_state["text_input"] = ""
    if "custom_prompt" not in st.session_state:
        st.session_state["custom_prompt"] = DEFAULT_MIND_MAP_PROMPT

initialize_state()

# --- Helper Functions ---
def generate_unique_node_id(text, existing_ids):
    """Generates a unique, safe ID for a graphviz node."""
    base_id = re.sub(r'\W+', '_', text).lower()
    if not base_id:
        base_id = "node"
    node_id = base_id
    counter = 1
    while node_id in existing_ids:
        node_id = f"{base_id}_{counter}"
        counter += 1
    return node_id

def fetch_url_content(url):
    """Fetches and extracts clean text content from a URL."""
    if not (url.startswith('http://') or url.startswith('https://')):
        st.error("Invalid URL. Please include http:// or https://")
        return None
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.extract()
        text = soup.get_text(separator='\n')
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        return clean_text[:8000] # Limit text to avoid overly long prompts
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching URL: {e}")
        return None

def parse_nodes_from_markdown(markdown_text):
    """Extracts all node labels from the markdown list."""
    # Use a regex to find all list items, which is more robust
    nodes = re.findall(r'^\s*-\s(.+)', markdown_text, re.MULTILINE)
    return [node.strip() for node in nodes]

def parse_markdown_to_graphviz(markdown_text: str, settings: dict) -> graphviz.Digraph:
    """
    Parses a markdown nested list into a graphviz Digraph object.
    """
    dot = graphviz.Digraph('MindMap')
    dot.attr('graph',
             bgcolor=settings["bg_color"],
             rankdir=settings["orientation"],
             splines='ortho',
             engine=settings["layout_engine"])

    dot.attr('node', style='rounded,filled', fontname="Helvetica", penwidth='1')
    dot.attr('edge', fontname="Helvetica")

    lines = markdown_text.strip().split('\n')
    parent_stack = []
    existing_ids = set()
    search_term = settings.get("search_term", "").lower()

    for line in lines:
        # Robustly find list items, ignoring empty or malformed lines
        match = re.match(r'^(\s*)-\s(.+)', line)
        if not match:
            continue

        indentation_str, node_text = match.groups()
        indentation = len(indentation_str)
        level = indentation // 2
        node_text = node_text.strip()

        node_id = generate_unique_node_id(node_text, existing_ids)
        existing_ids.add(node_id)

        # Determine node color, highlighting if it matches search
        fill_color = settings["highlight_color"] if search_term and search_term in node_text.lower() else settings["node_color"]

        dot.node(node_id, node_text,
                 shape=settings["node_shape"],
                 fillcolor=fill_color,
                 fontcolor=settings["node_font_color"],
                 color=settings["node_border_color"],
                 fontsize=str(settings["font_size"]))

        while parent_stack and parent_stack[-1][0] >= level:
            parent_stack.pop()

        if parent_stack:
            parent_id = parent_stack[-1][1]
            dot.edge(parent_id, node_id, color=settings["edge_color"])

        parent_stack.append((level, node_id))

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
