"""
Educational Programming Platform - Local Prototype
Learn programming logic before syntax with plain-English input and step-by-step visualization.
Fully local: no external API calls, no internet connection required.
"""

import streamlit as st
from interpreter import ProgramInterpreter
from parser import parse_program, ir_to_python, ir_to_cpp, ir_to_java, SYNTAX_GUIDE, ParseError

# Page config
st.set_page_config(
    page_title="LearnCode - Programming by Logic",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Theme handling (dark mode toggle, GitHub-style dark theme)
# ---------------------------------------------------------------------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

LIGHT_VARS = {
    "bg": "#FFFFFF",
    "bg_secondary": "#F3F4F6",
    "text": "#1F2937",
    "border": "#D0D7DE",
    "accent": "#3B82F6",
    "var_bg": "#f0f4f8",
    "output_bg": "#ecfdf5",
    "output_border": "#10b981",
    "error_bg": "#fef2f2",
    "error_text": "#991b1b",
    "error_border": "#dc2626",
    "code_bg": "#F6F8FA",
}

# GitHub dark theme palette
DARK_VARS = {
    "bg": "#0d1117",
    "bg_secondary": "#161b22",
    "text": "#c9d1d9",
    "border": "#30363d",
    "accent": "#58a6ff",
    "var_bg": "#161b22",
    "output_bg": "#0f2a1d",
    "output_border": "#3fb950",
    "error_bg": "#2d1214",
    "error_text": "#f85149",
    "error_border": "#f85149",
    "code_bg": "#161b22",
}

V = DARK_VARS if st.session_state.dark_mode else LIGHT_VARS

# Base app styling + component classes, all driven off the V dict above
st.markdown(f"""
<style>
    /* Overall app background/text (GitHub-like when dark mode is on) */
    .stApp {{
        background-color: {V['bg']};
        color: {V['text']};
    }}
    section[data-testid="stSidebar"] {{
        background-color: {V['bg_secondary']};
        border-right: 1px solid {V['border']};
    }}
    section[data-testid="stSidebar"] * {{
        color: {V['text']};
    }}
    .stApp, .stApp p, .stApp span, .stApp label, .stApp li, h1, h2, h3, h4 {{
        color: {V['text']};
    }}
    div[data-testid="stMetricValue"] {{
        color: {V['accent']};
    }}
    .stTextArea textarea {{
        background-color: {V['bg_secondary']};
        color: {V['text']};
        border: 1px solid {V['border']};
    }}
    .stButton button {{
        background-color: {V['bg_secondary']};
        color: {V['text']};
        border: 1px solid {V['border']};
    }}
    .stButton button:hover {{
        border-color: {V['accent']};
        color: {V['accent']};
    }}
    .stTabs [data-baseweb="tab"] {{
        color: {V['text']};
    }}
    .stCodeBlock, pre {{
        background-color: {V['code_bg']} !important;
    }}

    .variable-display {{
        background: {V['var_bg']};
        color: {V['text']};
        padding: 12px;
        border-radius: 6px;
        font-family: monospace;
        margin: 5px 0;
        border: 1px solid {V['border']};
    }}
    .output-display {{
        background: {V['output_bg']};
        color: {V['text']};
        padding: 12px;
        border-radius: 6px;
        border-left: 3px solid {V['output_border']};
        font-family: monospace;
    }}
    .error-display {{
        background: {V['error_bg']};
        color: {V['error_text']};
        padding: 12px;
        border-radius: 6px;
        border-left: 3px solid {V['error_border']};
    }}
    .syntax-card {{
        background: {V['bg_secondary']};
        border: 1px solid {V['border']};
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }}
    .syntax-card code {{
        background: {V['code_bg']};
        padding: 2px 6px;
        border-radius: 4px;
    }}
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "trace_history" not in st.session_state:
    st.session_state.trace_history = None
if "current_step" not in st.session_state:
    st.session_state.current_step = 0
if "ir_data" not in st.session_state:
    st.session_state.ir_data = None

# Header
header_col1, header_col2 = st.columns([5, 1])
with header_col1:
    st.title("🧠 LearnCode - Programming by Logic")
    st.markdown("**Learn programming logic first, syntax second.** Write in plain English, see step-by-step execution. Runs 100% locally.")
with header_col2:
    mode_label = "🌙 Dark" if st.session_state.dark_mode else "☀️ Light"
    if st.button(mode_label, use_container_width=True):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ How It Works")
    st.markdown("""
    1. **Write your idea** in plain English
    2. **Local parser** converts it to structured steps
    3. **Interpreter executes** safely
    4. **Visualizer shows** every step
    5. **Code mapper** shows equivalent Python / C++ / Java
    """)

    st.divider()
    st.header("📚 Example Prompts")
    examples = [
        "Create x with 10. Add 5 to x. Print x.",
        "Set y to 0. Repeat 5 times, add 2 to y. Print y.",
        "Create n with 20. If n > 10, print 'Big'. Otherwise print 'Small'.",
    ]
    for i, example in enumerate(examples, 1):
        if st.button(f"📝 Example {i}", use_container_width=True):
            st.session_state.user_input = example

    st.divider()
    st.caption("Supported: SET/ADD/SUBTRACT/MULTIPLY/DIVIDE, PRINT, IF/OTHERWISE, REPEAT N times.")

# Main content area
col1, col2 = st.columns([1, 1], gap="medium")

with col1:
    st.header("1️⃣ Your Program")
    user_input = st.text_area(
        "Tell the computer what to do:",
        value=st.session_state.get("user_input", ""),
        placeholder="Example: Create x with 10. Add 5 to x. Print x.",
        height=120,
        key="user_input"
    )

    col_run, col_reset = st.columns(2)
    with col_run:
        run_button = st.button("▶️ Run Program", use_container_width=True)
    with col_reset:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.trace_history = None
            st.session_state.current_step = 0
            st.session_state.ir_data = None
            st.rerun()

with col2:
    st.header("2️⃣ Execution Trace")

    if st.session_state.trace_history is None:
        st.info("👈 Enter a program and click 'Run Program' to see execution steps here.")
    else:
        trace = st.session_state.trace_history
        total_steps = trace.get("total_steps", 0)

        if total_steps == 0:
            st.warning("❌ No steps executed. Check your input.")
        else:
            col_prev, col_step, col_next = st.columns(3)
            with col_prev:
                if st.button("⬅️ Previous"):
                    st.session_state.current_step = max(0, st.session_state.current_step - 1)
                    st.rerun()
            with col_step:
                st.metric("Step", f"{st.session_state.current_step + 1}/{total_steps}")
            with col_next:
                if st.button("Next ➡️"):
                    st.session_state.current_step = min(total_steps - 1, st.session_state.current_step + 1)
                    st.rerun()

            steps = trace.get("steps", [])
            if steps and st.session_state.current_step < len(steps):
                current_step_data = steps[st.session_state.current_step]

                st.markdown(f"### Step {current_step_data.get('step', '?')}: {current_step_data.get('operation', 'UNKNOWN')}")

                if "error" in current_step_data:
                    st.markdown(f'<div class="error-display">{current_step_data["error"]}</div>', unsafe_allow_html=True)
                else:
                    skip_keys = {'step', 'operation', 'timestamp', 'variables_before',
                                 'variables_at_check', 'variables_at_print', 'variables_after'}
                    step_details = {k: v for k, v in current_step_data.items() if k not in skip_keys}
                    for key, value in step_details.items():
                        if key not in ['old_value', 'new_value']:
                            st.write(f"**{key.replace('_', ' ').title()}:** `{value}`")

# Tabs: Variables, Output, Generated Code, Syntax Guide
st.divider()
tab1, tab2, tab3, tab4 = st.tabs(["📊 Variables", "📤 Output", "💾 Generated Code", "📖 Syntax Guide"])

with tab1:
    if st.session_state.trace_history is None:
        st.info("Run a program to see variable states.")
    else:
        trace = st.session_state.trace_history
        steps = trace.get("steps", [])
        if st.session_state.current_step < len(steps):
            current_step_data = steps[st.session_state.current_step]
            variables = current_step_data.get("variables_after", trace.get("final_variables", {}))
            if variables:
                st.markdown("**Current Variables:**")
                for var_name, var_value in variables.items():
                    st.markdown(f'<div class="variable-display">{var_name} = {var_value}</div>', unsafe_allow_html=True)
            else:
                st.write("No variables defined yet.")

with tab2:
    if st.session_state.trace_history is None:
        st.info("Run a program to see output.")
    else:
        output = st.session_state.trace_history.get("output", [])
        if output:
            st.markdown("**Program Output:**")
            for line in output:
                st.markdown(f'<div class="output-display">{line}</div>', unsafe_allow_html=True)
        else:
            st.write("No output generated.")

with tab3:
    if st.session_state.ir_data is None:
        st.info("Run a program to see generated code.")
    else:
        lang = st.selectbox("Language", ["Python", "C++", "Java"], key="codegen_lang")
        if lang == "Python":
            st.code(ir_to_python(st.session_state.ir_data), language="python")
        elif lang == "C++":
            st.code(ir_to_cpp(st.session_state.ir_data), language="cpp")
        elif lang == "Java":
            st.code(ir_to_java(st.session_state.ir_data), language="java")

with tab4:
    st.markdown("Every sentence pattern the app currently understands. Combine several with periods, e.g. `Create x with 10. Add 5 to x. Print x.`")
    for entry in SYNTAX_GUIDE:
        patterns_html = "<br>".join(f"<code>{p}</code>" for p in entry["patterns"])
        st.markdown(
            f"""<div class="syntax-card">
                <b>{entry['category']}</b><br>
                {patterns_html}<br>
                <i>Example:</i> <code>{entry['example']}</code>
            </div>""",
            unsafe_allow_html=True,
        )

# Run button action
if run_button:
    if not user_input.strip():
        st.error("❌ Please enter a program first.")
    else:
        try:
            ir_data = parse_program(user_input)
            st.session_state.ir_data = ir_data

            interpreter = ProgramInterpreter()
            trace = interpreter.execute_ir(ir_data)
            st.session_state.trace_history = trace
            st.session_state.current_step = 0

            st.success("✅ Program executed successfully!")
            st.rerun()
        except ParseError as e:
            st.error(f"❌ Couldn't understand that: {e}")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Footer
st.divider()
st.caption("🧠 LearnCode - runs fully offline, no API keys needed.")
