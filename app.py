import streamlit as st
import os
import re
from openai import OpenAI

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EduPlan Pro", page_icon="🎓", layout="wide")

# --- CSS STYLING ---
st.markdown("""
    <style>
    .stTextArea textarea {font-size: 14px;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'topics' not in st.session_state:
    st.session_state.topics = []
if 'generated_plan' not in st.session_state:
    st.session_state.generated_plan = ""
if 'toc_text' not in st.session_state:
    st.session_state.toc_text = ""

# --- SIDEBAR: SETTINGS ---
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # Secure API Key Handling
    api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-proj")
    
    # Try to load from secrets if input is empty
    if not api_key and "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]

    st.divider()
    
    # Inputs
    subject = st.text_input("Subject", placeholder="e.g. Physics")
    grade = st.selectbox("Grade Level", [f"Grade {i}" for i in range(1, 13)] + ["University"])
    mode = st.radio("Learning Mode", ["Physical", "Online"])
    
    st.divider()
    if st.button("🔄 Reset App"):
        st.session_state.topics = []
        st.session_state.generated_plan = ""
        st.rerun()

# --- HELPER FUNCTIONS ---
def get_client():
    if not api_key:
        st.error("Please enter your OpenAI API Key in the sidebar.")
        st.stop()
    return OpenAI(api_key=api_key)

def get_table_of_contents(client, grade, subject):
    prompt = f"""
    Generate a numbered Table of Contents (exactly 8 topics) for {subject}, {grade}.
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
    if mode.lower() == "physical":
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
st.title("🎓 EduPlan Pro: AI Curriculum Generator")
st.markdown(f"**Generating Plan for:** `{subject}` | `{grade}` | Mode: `{mode}`")

# SECTION 1: Generate Topics
if not st.session_state.topics:
    if st.button("🚀 Generate Table of Contents", type="primary"):
        if not subject:
            st.warning("Please enter a subject first.")
        else:
            client = get_client()
            with st.spinner("Brainstorming topics..."):
                toc = get_table_of_contents(client, grade, subject)
                if toc:
                    st.session_state.toc_text = toc
                    st.session_state.topics = parse_topics(toc)
                    st.rerun()

# SECTION 2: Select & Generate Content
else:
    st.subheader("Step 2: Select Topics")
    
    # Display the TOC
    st.info("Here are the suggested topics:")
    st.text(st.session_state.toc_text)
    
    # Selection Logic
    selection_mode = st.radio("Selection Type:", ["Generate ALL Topics", "Select Single Topic"], horizontal=True)
    
    selected_topics = []
    if selection_mode == "Select Single Topic":
        chosen_topic = st.selectbox("Choose a topic:", st.session_state.topics)
        # Find index for correct numbering
        idx = st.session_state.topics.index(chosen_topic) + 1
        selected_topics = [(idx, chosen_topic)]
    else:
        selected_topics = [(i+1, t) for i, t in enumerate(st.session_state.topics)]

    # Generate Button
    if st.button(f"✨ Generate Curriculum ({len(selected_topics)} topics)", type="primary"):
        client = get_client()
        full_content = f"CURRICULUM PLAN: {subject.upper()} ({grade})\nMODE: {mode.upper()}\n" + "="*50 + "\n\n"
        
        progress_bar = st.progress(0)
        total_steps = len(selected_topics)
        total_tokens = 0
        
        for i, (seq, topic_name) in enumerate(selected_topics):
            with st.spinner(f"Writing content for: {topic_name}..."):
                content, tokens = generate_topic_content(client, grade, subject, mode, topic_name, seq)
                full_content += content + "\n\n"
                total_tokens += tokens
                progress_bar.progress((i + 1) / total_steps)
        
        # Add usage report
        full_content += f"\n💰 TOKEN USAGE: {total_tokens}"
        st.session_state.generated_plan = full_content
        st.success("Generation Complete!")

# SECTION 3: Results & Download
if st.session_state.generated_plan:
    st.divider()
    st.subheader("📄 Generated Curriculum")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_area("Preview", st.session_state.generated_plan, height=500)
    with col2:
        st.download_button(
            label="📥 Download .txt File",
            data=st.session_state.generated_plan,
            file_name=f"Curriculum_{subject}_{grade}.txt",
            mime="text/plain"
        )
