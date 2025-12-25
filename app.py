import streamlit as st
import os
import re
from openai import OpenAI

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EduPlan Pro", page_icon="🎓", layout="wide")

# --- CSS STYLING (To make it look pro) ---
st.markdown("""
    <style>
    .stTextArea textarea {font-size: 14px;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    footer {visibility: hidden;}
    .main-header {text-align: center; color: #333;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'topics' not in st.session_state:
    st.session_state.topics = []
if 'generated_plan' not in st.session_state:
    st.session_state.generated_plan = ""
if 'toc_text' not in st.session_state:
    st.session_state.toc_text = ""

# --- SIDEBAR: API KEY ONLY ---
with st.sidebar:
    st.header("🔐 Settings")
    st.info("Your API Key is not saved in code. It is only used for this session.")
    
    # Secure API Key Input
    api_key_input = st.text_input("Enter OpenAI API Key", type="password", placeholder="sk-...")
    
    # 1. Use input key if provided
    if api_key_input:
        api_key = api_key_input.strip() # Remove accidental spaces
    # 2. Fallback to secrets (for local dev)
    elif "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = None

    if st.button("🔄 Reset / Clear App"):
        st.session_state.topics = []
        st.session_state.generated_plan = ""
        st.session_state.toc_text = ""
        st.rerun()

# --- HELPER FUNCTIONS ---
def get_client():
    if not api_key:
        st.error("⚠️ Please enter your OpenAI API Key in the sidebar to proceed.")
        st.stop()
    return OpenAI(api_key=api_key)

def get_table_of_contents(client, grade, subject):
    prompt = f"""
    Generate a numbered Table of Contents (exactly 8 topics) for {subject}, Grade/Class: {grade}.
    Output format STRICTLY:
    1. Topic Name
    2. Topic Name
    Do not add any intro or outro text.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error fetching topics: {e}")
        return None

def parse_topics(toc_text):
    lines = toc_text.split('\n')
    topics = []
    for line in lines:
        clean_line = re.sub(r'^\d+\.\s*', '', line).strip()
        if clean_line:
            topics.append(clean_line)
    return topics

def generate_topic_content(client, grade, subject, mode, topic, sequence_num):
    # Context Logic
    if mode == "Physical (Classroom)":
        exp_type = "LABORATORY EXPERIMENT"
        exp_context = "PHYSICAL CLASSROOM"
        exp_guide = "Use standard school science lab equipment."
    else:
        exp_type = "HOME-BASED EXPERIMENT"
        exp_context = "VIRTUAL/ONLINE CLASS"
        exp_guide = "Use ONLY common household items safe for home use."

    MASTER_PROMPT = f"""
    You are EduPlan Pro.
    Target Audience: Teachers.
    Subject: {subject}
    Grade Level: {grade}
    Topic: {topic}
    Mode: {exp_context}

    CRITICAL INSTRUCTIONS:
    1. Output plain text only.
    2. {exp_guide}

    OUTPUT STRUCTURE:
    ### TOPIC {sequence_num}: {topic}
    1. TOPIC OVERVIEW
    2. LEARNING OBJECTIVES (3 goals)
    3. REQUIRED MATERIALS
    4. PRACTICAL EXPERIMENT ({exp_context}) - Type: {exp_type}
    5. VIDEOS (Youtube Links for Theory & Experiment)
    6. ASSESSMENT METHODS
    --------------------------------------------------
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a curriculum expert."},
            {"role": "user", "content": MASTER_PROMPT}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content, response.usage.total_tokens

# --- MAIN APP LAYOUT ---

st.title("🎓 EduPlan Pro")
st.markdown("### AI Curriculum & Lesson Planner")
st.markdown("---")

# --- CENTER INPUTS (Main Interface) ---
# Using columns to put inputs side-by-side
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    subject = st.text_input("Enter Subject", placeholder="e.g. Physics, History, Math")

with col2:
    # CHANGED: Now a manual text entry
    grade = st.text_input("Grade / Class Level", placeholder="e.g. 8, A-Level, Year 10")

with col3:
    mode = st.radio("Learning Mode", ["Physical (Classroom)", "Online (Virtual)"])

st.markdown("---")

# SECTION 1: Generate Topics
if not st.session_state.topics:
    # Center the button
    col_centered = st.columns([1, 2, 1])
    with col_centered[1]:
        generate_btn = st.button("🚀 Generate Table of Contents", type="primary", use_container_width=True)

    if generate_btn:
        if not subject or not grade:
            st.warning("⚠️ Please fill in both Subject and Grade Level.")
        else:
            client = get_client()  # This checks API key
            with st.spinner(f"🤖 Brainstorming topics for {subject} ({grade})..."):
                toc = get_table_of_contents(client, grade, subject)
                if toc:
                    st.session_state.toc_text = toc
                    st.session_state.topics = parse_topics(toc)
                    st.rerun()

# SECTION 2: Select & Generate Content
else:
    st.success(f"✅ Topics Found for **{subject} - {grade}**")
    
    # Show Topics in an Expander (Collapsible)
    with st.expander("📂 View Topic List", expanded=True):
        st.text(st.session_state.toc_text)
    
    st.subheader("Step 2: Generate Full Plan")
    
    # Selection Logic
    col_sel1, col_sel2 = st.columns([1, 2])
    with col_sel1:
        selection_mode = st.radio("Selection Type:", ["Generate ALL Topics", "Select Single Topic"])
    
    selected_topics = []
    if selection_mode == "Select Single Topic":
        with col_sel2:
            chosen_topic = st.selectbox("Choose a topic to generate:", st.session_state.topics)
            # Find index for correct numbering
            idx = st.session_state.topics.index(chosen_topic) + 1
            selected_topics = [(idx, chosen_topic)]
    else:
        selected_topics = [(i+1, t) for i, t in enumerate(st.session_state.topics)]

    # Generate Button
    if st.button(f"✨ Generate Content for {len(selected_topics)} Topic(s)", type="primary"):
        client = get_client()
        full_content = f"CURRICULUM PLAN: {subject.upper()} ({grade})\nMODE: {mode.upper()}\n" + "="*50 + "\n\n"
        
        progress_bar = st.progress(0)
        total_steps = len(selected_topics)
        total_tokens = 0
        
        for i, (seq, topic_name) in enumerate(selected_topics):
            status_text = f"Writing content for Topic {seq}: {topic_name}..."
            # Create a placeholder to show current status text
            status_placeholder = st.empty()
            status_placeholder.text(status_text)
            
            content, tokens = generate_topic_content(client, grade, subject, mode, topic_name, seq)
            full_content += content + "\n\n"
            total_tokens += tokens
            progress_bar.progress((i + 1) / total_steps)
            status_placeholder.empty() # Clear text
        
        # Add usage report
        full_content += f"\n💰 TOKEN USAGE: {total_tokens}"
        st.session_state.generated_plan = full_content
        st.success("Generation Complete!")

# SECTION 3: Results & Download
if st.session_state.generated_plan:
    st.divider()
    st.subheader("📄 Final Curriculum Plan")
    
    st.download_button(
        label="📥 Download Plan (.txt)",
        data=st.session_state.generated_plan,
        file_name=f"Curriculum_{subject}_{grade}.txt",
        mime="text/plain",
        type="primary"
    )

    st.text_area("Preview:", st.session_state.generated_plan, height=600)
