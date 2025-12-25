import streamlit as st
import os
import re
import json
from openai import OpenAI

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EduPlan Pro", page_icon="🎓", layout="wide")

# --- CSS STYLING ---
st.markdown("""
    <style>
    .main-header {text-align: center; color: #333;}
    .topic-header {color: #2e86c1; border-bottom: 2px solid #2e86c1; padding-bottom: 10px; margin-top: 30px;}
    .sub-header {font-weight: bold; color: #555; margin-top: 15px;}
    .video-container {background-color: #000; padding: 5px; border-radius: 10px;}
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

    if st.button("🔄 Reset / Clear App"):
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
    prompt = f"""
    Generate a numbered Table of Contents (exactly 8 topics) for {subject}, Grade/Class: {grade}.
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
    # Context Logic
    if mode == "Physical (Classroom)":
        exp_context = "PHYSICAL CLASSROOM"
        exp_guide = "Use standard school science lab equipment. If the topic is purely theoretical, set 'experiment_possible' to false."
    else:
        exp_context = "VIRTUAL/ONLINE CLASS"
        exp_guide = "Use ONLY common household items safe for home use. If the topic is purely theoretical, set 'experiment_possible' to false."

    # --- UPDATED STRICT PROMPT ---
    MASTER_PROMPT = f"""
    You are EduPlan Pro, a curriculum expert for teachers.
    Subject: {subject} | Grade: {grade} | Topic: {topic} | Mode: {exp_context}

    CRITICAL VIDEO SOURCE RULES:
    1. Provide EXACT, PLAYABLE YouTube URLs (start with https://www.youtube.com/watch?v=...).
    2. SOURCES MUST BE ONLY FROM: Khan Academy, CrashCourse, PBS Learning Media, National Geographic, TED-Ed, SciShow, Smithsonian, Amoeba Sisters, BBC Bitesize.
    3. Do NOT invent links. If a specific video doesn't exist, find the closest matching topic from the allowed channels.
    4. Video Content: Must be complete, detailed lessons (not shorts).
    5. NO REPETITION: Do not use the same video link twice.

    Experiment Instructions: {exp_guide}
    
    OUTPUT JSON FORMAT ONLY. Structure:
    {{
        "title": "{topic}",
        "overview": "Brief explanation of core concepts (2-3 sentences).",
        "objectives": ["Goal 1", "Goal 2", "Goal 3"],
        "materials": ["Item 1", "Item 2"],
        "experiment_possible": true/false,
        "experiment": {{
            "title": "Name of experiment",
            "steps": ["Step 1", "Step 2", "Step 3", "Step 4"]
        }},
        "video_links": [
            {{"title": "Video Title 1", "url": "https://www.youtube.com/watch?v=..."}},
            {{"title": "Video Title 2", "url": "https://www.youtube.com/watch?v=..."}}
        ], 
        "assessment": ["Method 1", "Method 2"]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={ "type": "json_object" }, 
        messages=[
            {"role": "system", "content": "You are a curriculum assistant. You only provide real, working YouTube links from official educational channels."},
            {"role": "user", "content": MASTER_PROMPT}
        ],
        temperature=0.5 # Lower temperature reduces hallucinations (fake links)
    )
    
    try:
        data = json.loads(response.choices[0].message.content)
        return data, response.usage.total_tokens
    except:
        return None, 0

def convert_json_to_txt(json_list, subject, grade):
    full_text = f"CURRICULUM PLAN: {subject} ({grade})\n" + "="*50 + "\n\n"
    
    for item in json_list:
        full_text += f"### TOPIC: {item.get('title')}\n"
        full_text += f"OVERVIEW: {item.get('overview')}\n\n"
        
        full_text += "LEARNING OBJECTIVES:\n"
        for obj in item.get('objectives', []):
            full_text += f"- {obj}\n"
        
        if item.get('experiment_possible'):
            full_text += "\nEXPERIMENT:\n"
            full_text += f"Title: {item.get('experiment', {}).get('title')}\n"
            for step in item.get('experiment', {}).get('steps', []):
                full_text += f"- {step}\n"
            
        full_text += "\nVIDEO RESOURCES:\n"
        for vid in item.get('video_links', []):
            full_text += f"- {vid.get('title')}: {vid.get('url')}\n"
            
        full_text += "\n" + "-"*50 + "\n\n"
        
    return full_text

# --- MAIN APP UI ---

st.title("🎓 EduPlan Pro")
st.markdown("### AI Curriculum & Lesson Planner")
st.markdown("---")

# Center Inputs
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    subject = st.text_input("Enter Subject", placeholder="e.g. Physics")
with col2:
    grade = st.text_input("Grade Level", placeholder="e.g. 8")
with col3:
    mode = st.radio("Mode", ["Physical (Classroom)", "Online (Virtual)"])

st.markdown("---")

# SECTION 1: Generate Topics
if not st.session_state.topics:
    col_c = st.columns([1, 2, 1])
    with col_c[1]:
        if st.button("🚀 Generate Table of Contents", type="primary", use_container_width=True):
            if not subject or not grade:
                st.warning("Please fill in Subject and Grade.")
            else:
                client = get_client()
                with st.spinner("Brainstorming topics..."):
                    toc = get_table_of_contents(client, grade, subject)
                    if toc:
                        st.session_state.toc_text = toc
                        st.session_state.topics = parse_topics(toc)
                        st.rerun()

# SECTION 2: Generate Content
elif not st.session_state.generated_content:
    st.info(f"Topics found for **{subject}**")
    with st.expander("View Topics", expanded=False):
        st.text(st.session_state.toc_text)
    
    col_sel1, col_sel2 = st.columns([1, 2])
    with col_sel1:
        selection_mode = st.radio("Selection:", ["Generate ALL", "Select Single Topic"])
    
    selected_topics = []
    if selection_mode == "Select Single Topic":
        with col_sel2:
            chosen = st.selectbox("Choose Topic:", st.session_state.topics)
            idx = st.session_state.topics.index(chosen) + 1
            selected_topics = [(idx, chosen)]
    else:
        selected_topics = [(i+1, t) for i, t in enumerate(st.session_state.topics)]

    if st.button(f"✨ Generate Content ({len(selected_topics)} Topics)", type="primary"):
        client = get_client()
        progress_bar = st.progress(0)
        
        for i, (seq, topic_name) in enumerate(selected_topics):
            data, tokens = generate_topic_json(client, grade, subject, mode, topic_name, seq)
            if data:
                st.session_state.generated_content.append(data)
            progress_bar.progress((i + 1) / len(selected_topics))
        
        st.rerun()

# SECTION 3: DISPLAY RESULTS
else:
    st.success("✅ Curriculum Generated Successfully!")
    
    # DOWNLOAD
    txt_data = convert_json_to_txt(st.session_state.generated_content, subject, grade)
    st.download_button(
        "📥 Download Full Plan (.txt)",
        data=txt_data,
        file_name=f"Curriculum_{subject}_{grade}.txt",
        mime="text/plain"
    )
    
    st.divider()

    # RICH UI DISPLAY
    for idx, item in enumerate(st.session_state.generated_content):
        with st.container():
            st.markdown(f"<h2 class='topic-header'>📌 Topic {idx+1}: {item.get('title')}</h2>", unsafe_allow_html=True)
            
            # Overview
            st.info(f"**Overview:** {item.get('overview')}")
            
            # Objectives & Materials
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<div class='sub-header'>🎯 Learning Objectives</div>", unsafe_allow_html=True)
                for obj in item.get('objectives', []):
                    st.write(f"• {obj}")
            with c2:
                st.markdown("<div class='sub-header'>🧪 Required Materials</div>", unsafe_allow_html=True)
                if item.get('materials'):
                    for mat in item.get('materials', []):
                        st.write(f"• {mat}")
                else:
                    st.write("No specific materials required.")
            
            # EXPERIMENT SECTION
            st.markdown("---")
            if item.get('experiment_possible'):
                st.markdown(f"### ⚡ Experiment: {item.get('experiment', {}).get('title')}")
                with st.expander("📝 View Experiment Steps", expanded=True):
                    steps = item.get('experiment', {}).get('steps', [])
                    for i, step in enumerate(steps, 1):
                        st.write(f"**{i}.** {step}")
            else:
                st.warning("📘 **Theoretical Topic:** No physical lab experiment is required for this section.")

            # VIDEO SECTION (PLAYABLE EMBEDS)
            st.markdown("<div class='sub-header'>🎥 Recommended Videos (Official Sources)</div>", unsafe_allow_html=True)
            
            videos = item.get('video_links', [])
            v_cols = st.columns(2) # Grid layout
            
            for v_idx, vid in enumerate(videos):
                url = vid.get('url')
                title = vid.get('title')
                
                with v_cols[v_idx % 2]:
                    if "youtube.com" in url or "youtu.be" in url:
                        # Streamlit Video Player
                        st.caption(f"**{title}**")
                        st.video(url)
                    else:
                        # Fallback if link is weird
                        st.error(f"⚠️ Link unavailable: {title}")

            st.markdown("---")
