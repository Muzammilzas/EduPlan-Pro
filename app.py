import streamlit as st
import os
import re
import json
from openai import OpenAI

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EduPlan Pro", page_icon="🎓", layout="wide")

# --- CSS STYLING (Restoring the "Pro" Look) ---
st.markdown("""
    <style>
    .main-header {text-align: center; color: #333;}
    .topic-header {color: #2e86c1; border-bottom: 2px solid #2e86c1; padding-bottom: 10px; margin-top: 40px;}
    .sub-header {font-weight: bold; color: #555; margin-top: 15px; margin-bottom: 5px;}
    .video-card {
        background-color: #f8f9fa; 
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #ddd; 
        margin-bottom: 10px;
        text-align: center;
    }
    .video-title {font-weight: bold; font-size: 14px; color: #333; margin-bottom: 5px; height: 40px; overflow: hidden;}
    .channel-name {font-size: 12px; color: #666; margin-bottom: 10px;}
    .watch-btn {
        display: inline-block;
        background-color: #FF0000;
        color: white;
        padding: 8px 16px;
        text-decoration: none;
        border-radius: 4px;
        font-weight: bold;
        font-size: 13px;
    }
    .watch-btn:hover {background-color: #cc0000; color: white;}
    div[data-testid="stToolbar"] {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if 'topics' not in st.session_state:
    st.session_state.topics = []
if 'generated_content' not in st.session_state:
    st.session_state.generated_content = [] 
if 'toc_text' not in st.session_state:
    st.session_state.toc_text = ""

# --- SIDEBAR: API KEY ---
with st.sidebar:
    st.header("🔐 Settings")
    api_key_input = st.text_input("Enter OpenAI API Key", type="password", placeholder="sk-...")
    
    if api_key_input:
        api_key = api_key_input.strip()
    elif "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = None

    st.divider()
    if st.button("🗑️ Reset / New Search"):
        st.session_state.topics = []
        st.session_state.generated_content = []
        st.session_state.toc_text = ""
        st.rerun()

# --- HELPER FUNCTIONS ---
def get_client():
    if not api_key:
        st.error("⚠️ Please enter your OpenAI API Key in the sidebar.")
        st.stop()
    return OpenAI(api_key=api_key)

def get_table_of_contents(client, grade, subject):
    # Generates a clear list of topics first
    prompt = f"""
    Generate a numbered Table of Contents (exactly 6 key topics) for {subject}, Grade {grade}.
    Output format STRICTLY:
    1. Topic Name
    2. Topic Name
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def parse_topics(toc_text):
    lines = toc_text.split('\n')
    topics = []
    for line in lines:
        clean_line = re.sub(r'^\d+\.\s*', '', line).strip()
        if clean_line:
            topics.append(clean_line)
    return topics

def generate_topic_json(client, grade, subject, mode, topic, sequence_num):
    # Context Logic for Experiment
    if mode == "Physical (Classroom)":
        exp_context = "PHYSICAL LAB"
        exp_guide = "Experiment must use standard school lab equipment (microscopes, beakers, circuits)."
    else:
        exp_context = "HOME/VIRTUAL"
        exp_guide = "Experiment must use ONLY household items (DIY style)."

    # --- PROMPT: FOCUS ON SEARCH TERMS INSTEAD OF BROKEN LINKS ---
    MASTER_PROMPT = f"""
    You are EduPlan Pro, a curriculum expert.
    Subject: {subject} | Grade: {grade} | Topic: {topic} | Mode: {exp_context}

    GOAL: Create a structured lesson plan with VERIFIED video resources.

    VIDEO INSTRUCTIONS:
    1. Do NOT guess random YouTube URLs. They often break.
    2. Instead, provide the EXACT TITLE and CHANNEL NAME of real, famous educational videos.
    3. Sources allowed: CrashCourse, Khan Academy, TED-Ed, SciShow, National Geographic, Veritasium, Amoeba Sisters.
    
    OUTPUT JSON STRUCTURE:
    {{
        "title": "{topic}",
        "overview": "2 sentence summary.",
        "objectives": ["Goal 1", "Goal 2", "Goal 3"],
        "materials": ["Item 1", "Item 2", "Item 3"],
        "theory_video": {{
            "title": "Exact Title of a Theory Video",
            "channel": "Channel Name (e.g. CrashCourse)"
        }},
        "experiment_video": {{
            "title": "Exact Title of an Experiment/Demo Video",
            "channel": "Channel Name (e.g. SciShow or DIY Science)"
        }},
        "experiment_guide": {{
            "title": "Experiment Name",
            "steps": ["Step 1", "Step 2", "Step 3", "Step 4"]
        }}
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" }, 
        messages=[
            {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
            {"role": "user", "content": MASTER_PROMPT}
        ],
        temperature=0.5
    )
    
    try:
        data = json.loads(response.choices[0].message.content)
        return data, response.usage.total_tokens
    except:
        return None, 0

def render_video_button(video_data):
    """Creates a clean HTML button that searches YouTube for the video."""
    if not video_data:
        return
    
    title = video_data.get('title', 'Video Resource')
    channel = video_data.get('channel', 'YouTube')
    
    # Create a reliable search query URL
    query = f"{title} {channel}".replace(" ", "+")
    search_url = f"https://www.youtube.com/results?search_query={query}"
    
    # Render the Card
    st.markdown(f"""
        <div class="video-card">
            <div class="video-title">📺 {title}</div>
            <div class="channel-name">by {channel}</div>
            <a href="{search_url}" target="_blank" class="watch-btn">
                ▶ Watch on YouTube
            </a>
        </div>
    """, unsafe_allow_html=True)

# --- MAIN APP UI ---

st.title("🎓 EduPlan Pro")
st.markdown("### AI Curriculum & Lesson Planner")
st.markdown("---")

# 1. LANDING PAGE INPUTS
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    subject = st.text_input("Enter Subject", placeholder="e.g. Physics")
with col2:
    grade = st.text_input("Grade Level", placeholder="e.g. 8")
with col3:
    mode = st.radio("Learning Mode", ["Physical (Classroom)", "Online (Virtual)"])

st.markdown("---")

# SECTION 1: Generate Topics (Table of Contents)
if not st.session_state.topics:
    # Center Button
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 Generate Table of Contents", type="primary", use_container_width=True):
            if not subject or not grade:
                st.warning("⚠️ Please fill in Subject and Grade.")
            else:
                client = get_client()
                with st.spinner("Brainstorming curriculum..."):
                    toc = get_table_of_contents(client, grade, subject)
                    if toc:
                        st.session_state.toc_text = toc
                        st.session_state.topics = parse_topics(toc)
                        st.rerun()

# SECTION 2: Topic Selection
elif not st.session_state.generated_content:
    st.success(f"✅ Topics Found for **{subject} - {grade}**")
    
    # Show TOC in a clean box
    with st.expander("📂 View Full Table of Contents", expanded=True):
        st.text(st.session_state.toc_text)
    
    st.subheader("Step 2: Generate Lesson Plans")
    
    # Selection
    col_sel1, col_sel2 = st.columns([1, 2])
    with col_sel1:
        selection_mode = st.radio("Selection Type:", ["Generate ALL Topics", "Select Single Topic"])
    
    selected_topics = []
    if selection_mode == "Select Single Topic":
        with col_sel2:
            chosen_topic = st.selectbox("Choose a topic:", st.session_state.topics)
            idx = st.session_state.topics.index(chosen_topic) + 1
            selected_topics = [(idx, chosen_topic)]
    else:
        selected_topics = [(i+1, t) for i, t in enumerate(st.session_state.topics)]

    # Generate Content Button
    if st.button(f"✨ Generate Content for {len(selected_topics)} Topic(s)", type="primary"):
        client = get_client()
        progress_bar = st.progress(0)
        
        for i, (seq, topic_name) in enumerate(selected_topics):
            data, tokens = generate_topic_json(client, grade, subject, mode, topic_name, seq)
            if data:
                st.session_state.generated_content.append(data)
            progress_bar.progress((i + 1) / len(selected_topics))
        
        st.rerun()

# SECTION 3: LANDING PAGE RESULTS (Linear Layout)
else:
    st.success("✅ Curriculum Generated Successfully!")
    
    # Download Button (Top Right)
    # Note: We can add the TXT download logic here if needed, but keeping it minimal for UI.
    
    # Display each topic one after another (Ascending Order)
    for idx, item in enumerate(st.session_state.generated_content):
        
        # 1. Topic Header
        st.markdown(f"<h2 class='topic-header'>📌 Topic {idx+1}: {item.get('title')}</h2>", unsafe_allow_html=True)
        
        # 2. Overview (Blue Box)
        st.info(f"**Overview:** {item.get('overview')}")
        
        # 3. Two Columns: Objectives & Materials
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='sub-header'>🎯 Learning Objectives</div>", unsafe_allow_html=True)
            for obj in item.get('objectives', []):
                st.write(f"• {obj}")
        
        with c2:
            st.markdown("<div class='sub-header'>🧪 Required Materials</div>", unsafe_allow_html=True)
            for mat in item.get('materials', []):
                st.write(f"• {mat}")
        
        # 4. Videos Section (The Fix)
        st.markdown("<div class='sub-header'>🎥 Recommended Videos</div>", unsafe_allow_html=True)
        v1, v2 = st.columns(2)
        
        with v1:
            st.caption("🧠 **Theory & Concept**")
            render_video_button(item.get('theory_video'))
            
        with v2:
            st.caption(f"⚡ **Experiment ({mode})**")
            render_video_button(item.get('experiment_video'))

        # 5. Experiment Instructions
        st.markdown(f"<div class='sub-header'>⚡ Experiment: {item.get('experiment_guide', {}).get('title')}</div>", unsafe_allow_html=True)
        with st.expander(f"📝 View Step-by-Step Instructions ({mode})", expanded=True):
            for step in item.get('experiment_guide', {}).get('steps', []):
                st.write(f"1. {step}")
        
        # Spacer
        st.markdown("<br><br>", unsafe_allow_html=True)
