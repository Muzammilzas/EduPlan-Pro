import streamlit as st
import os
import re
import json
from openai import OpenAI
import requests

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EduPlan Pro", page_icon="🎓", layout="wide")

# --- CSS STYLING ---
st.markdown("""
    <style>
    .main-header {text-align: center; color: #333;}
    .topic-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 30px 0 20px 0;
        font-size: 24px;
        font-weight: bold;
    }
    .sub-header {
        font-weight: bold; 
        color: #555; 
        margin-top: 20px; 
        margin-bottom: 10px;
        font-size: 18px;
        border-left: 4px solid #667eea;
        padding-left: 10px;
    }
    .video-container {
        background-color: #f8f9fa; 
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #ddd; 
        margin-bottom: 15px;
    }
    .video-title {
        font-weight: bold; 
        font-size: 14px; 
        color: #333; 
        margin-bottom: 8px;
    }
    .channel-name {
        font-size: 12px; 
        color: #666; 
        margin-bottom: 10px;
    }
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

# --- SIDEBAR: API KEYS ---
with st.sidebar:
    st.header("🔐 Settings")
    
    # OpenAI API Key
    openai_key_input = st.text_input("Enter OpenAI API Key", type="password", placeholder="sk-...")
    if openai_key_input:
        openai_api_key = openai_key_input.strip()
    elif "OPENAI_API_KEY" in st.secrets:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
    else:
        openai_api_key = None
    
    # YouTube API Key
    youtube_key_input = st.text_input("Enter YouTube Data API Key", type="password", placeholder="AIza...")
    if youtube_key_input:
        youtube_api_key = youtube_key_input.strip()
    elif "YOUTUBE_API_KEY" in st.secrets:
        youtube_api_key = st.secrets["YOUTUBE_API_KEY"]
    else:
        youtube_api_key = None
    
    st.divider()
    st.caption("📌 Get YouTube API Key from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)")
    
    st.divider()
    if st.button("🗑️ Reset / New Search"):
        st.session_state.topics = []
        st.session_state.generated_content = []
        st.session_state.toc_text = ""
        st.rerun()

# --- HELPER FUNCTIONS ---
def get_openai_client():
    if not openai_api_key:
        st.error("⚠️ Please enter your OpenAI API Key in the sidebar.")
        st.stop()
    return OpenAI(api_key=openai_api_key)

def search_youtube_videos(query, max_results=3):
    """Search YouTube using the Data API and return video IDs and metadata."""
    if not youtube_api_key:
        st.warning("⚠️ YouTube API Key required to fetch videos. Using search fallback.")
        return []
    
    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": youtube_api_key,
            "videoEmbeddable": "true",
            "order": "relevance"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        videos = []
        for item in data.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            channel = item["snippet"]["channelTitle"]
            videos.append({
                "video_id": video_id,
                "title": title,
                "channel": channel,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            })
        
        return videos
    
    except Exception as e:
        st.error(f"YouTube API Error: {e}")
        return []

def get_table_of_contents(client, grade, subject):
    """Generate exactly 8 topics for the curriculum."""
    prompt = f"""
    Generate a numbered Table of Contents (exactly 8 key topics) for {subject}, Grade {grade}.
    Output format STRICTLY:
    1. Topic Name
    2. Topic Name
    ...
    8. Topic Name
    
    Do not add any introduction or explanation. Just the numbered list.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error: {e}")
        return None

def parse_topics(toc_text):
    """Extract topic names from numbered list."""
    lines = toc_text.split('\n')
    topics = []
    for line in lines:
        clean_line = re.sub(r'^\d+\.\s*', '', line).strip()
        if clean_line:
            topics.append(clean_line)
    return topics

def generate_topic_content(client, grade, subject, mode, topic, sequence_num):
    """Generate structured content for a single topic with video search queries."""
    
    # Context Logic
    if mode == "Physical (Classroom)":
        exp_context = "PHYSICAL LAB"
        exp_guide = "Use standard school lab equipment (microscopes, beakers, circuits, etc.)."
    else:
        exp_context = "HOME/VIRTUAL"
        exp_guide = "Use ONLY common household items (safe DIY experiments)."

    MASTER_PROMPT = f"""
You are EduPlan Pro, an expert curriculum designer.

Subject: {subject}
Grade: {grade}
Topic: {topic}
Mode: {exp_context}

CREATE A STRUCTURED LESSON PLAN WITH THE FOLLOWING:

1. TOPIC OVERVIEW (2-3 sentences explaining core concepts)

2. LEARNING OBJECTIVES (List exactly 3 clear, measurable goals)

3. REQUIRED MATERIALS (List specific items needed for the experiment. {exp_guide})

4. PRACTICAL EXPERIMENT
   - Experiment Title
   - Step-by-step instructions (5-7 numbered steps)

5. VIDEO SEARCH QUERIES
   Create 2 specific search queries to find:
   - Theory Video Query: A search term to find conceptual/theory videos (e.g., "Khan Academy photosynthesis grade 8")
   - Experiment Video Query: A search term to find demonstration/experiment videos (e.g., "home photosynthesis experiment DIY")

OUTPUT AS JSON:
{{
    "title": "{topic}",
    "overview": "Brief explanation...",
    "objectives": ["Objective 1", "Objective 2", "Objective 3"],
    "materials": ["Material 1", "Material 2", "Material 3"],
    "experiment": {{
        "title": "Experiment name",
        "steps": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"]
    }},
    "video_queries": {{
        "theory": "specific search query for theory video",
        "experiment": "specific search query for experiment demo"
    }}
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"}, 
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs JSON."},
                {"role": "user", "content": MASTER_PROMPT}
            ],
            temperature=0.7
        )
        
        data = json.loads(response.choices[0].message.content)
        return data, response.usage.total_tokens
    
    except Exception as e:
        st.error(f"Error generating content: {e}")
        return None, 0

def render_video_section(videos, section_title):
    """Render videos with embedded players."""
    if not videos:
        st.warning(f"No videos found for {section_title}")
        return
    
    st.markdown(f"<div class='sub-header'>🎥 {section_title}</div>", unsafe_allow_html=True)
    
    for video in videos:
        with st.container():
            st.markdown(f"""
                <div class="video-container">
                    <div class="video-title">📺 {video['title']}</div>
                    <div class="channel-name">by {video['channel']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Embed YouTube video
            st.video(f"https://www.youtube.com/watch?v={video['video_id']}")
            st.markdown("---")

# --- MAIN APP UI ---
st.title("🎓 EduPlan Pro")
st.markdown("### AI-Powered Curriculum & Lesson Planner")
st.markdown("---")

# 1. LANDING PAGE INPUTS
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    subject = st.text_input("Enter Subject", placeholder="e.g. Physics, Biology, Chemistry")
with col2:
    grade = st.text_input("Grade Level", placeholder="e.g. 8")
with col3:
    mode = st.radio("Learning Mode", ["Physical (Classroom)", "Online (Virtual)"])

st.markdown("---")

# STEP 1: Generate Table of Contents
if not st.session_state.topics:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 Generate Table of Contents", type="primary", use_container_width=True):
            if not subject or not grade:
                st.warning("⚠️ Please fill in Subject and Grade.")
            else:
                client = get_openai_client()
                with st.spinner("🧠 Generating curriculum structure..."):
                    toc = get_table_of_contents(client, grade, subject)
                    if toc:
                        st.session_state.toc_text = toc
                        st.session_state.topics = parse_topics(toc)
                        st.rerun()

# STEP 2: Topic Selection
elif not st.session_state.generated_content:
    st.success(f"✅ Topics Generated for **{subject} - Grade {grade}**")
    
    # Show TOC
    with st.expander("📂 View Table of Contents", expanded=True):
        st.text(st.session_state.toc_text)
    
    st.markdown("### Step 2: Generate Detailed Lesson Plans")
    
    # Selection Mode
    col_sel1, col_sel2 = st.columns([1, 2])
    with col_sel1:
        selection_mode = st.radio("Choose Generation Type:", 
                                  ["Generate ALL Topics", "Select Specific Topics"])
    
    selected_topics = []
    
    if selection_mode == "Select Specific Topics":
        with col_sel2:
            chosen = st.multiselect("Select topics to generate:", st.session_state.topics)
            selected_topics = [(st.session_state.topics.index(t)+1, t) for t in chosen]
    else:
        selected_topics = [(i+1, t) for i, t in enumerate(st.session_state.topics)]
    
    # Generate Button
    if st.button(f"✨ Generate Content for {len(selected_topics)} Topic(s)", type="primary"):
        if not selected_topics:
            st.warning("⚠️ Please select at least one topic.")
        else:
            client = get_openai_client()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, (seq, topic_name) in enumerate(selected_topics):
                status_text.text(f"Processing: {topic_name}...")
                
                # Generate content structure
                data, tokens = generate_topic_content(client, grade, subject, mode, topic_name, seq)
                
                if data:
                    # Search for videos
                    theory_query = data.get('video_queries', {}).get('theory', f"{subject} {topic_name} theory")
                    exp_query = data.get('video_queries', {}).get('experiment', f"{topic_name} experiment demonstration")
                    
                    data['theory_videos'] = search_youtube_videos(theory_query, max_results=2)
                    data['experiment_videos'] = search_youtube_videos(exp_query, max_results=2)
                    
                    st.session_state.generated_content.append(data)
                
                progress_bar.progress((i + 1) / len(selected_topics))
            
            status_text.text("✅ Generation Complete!")
            st.rerun()

# STEP 3: Display Generated Content (Linear Layout)
else:
    st.success(f"✅ Curriculum Generated Successfully for **{subject} - Grade {grade}**")
    st.markdown("---")
    
    # Display each topic sequentially
    for idx, item in enumerate(st.session_state.generated_content):
        
        # Topic Header
        st.markdown(f"""
            <div class='topic-header'>
                📌 Topic {idx+1}: {item.get('title', 'Untitled')}
            </div>
        """, unsafe_allow_html=True)
        
        # Overview
        st.info(f"**📖 Overview:** {item.get('overview', 'No overview available')}")
        
        # Two Columns: Objectives & Materials
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='sub-header'>🎯 Learning Objectives</div>", unsafe_allow_html=True)
            for obj in item.get('objectives', []):
                st.write(f"• {obj}")
        
        with col2:
            st.markdown("<div class='sub-header'>🧪 Required Materials</div>", unsafe_allow_html=True)
            for mat in item.get('materials', []):
                st.write(f"• {mat}")
        
        # Theory Videos
        theory_vids = item.get('theory_videos', [])
        if theory_vids:
            render_video_section(theory_vids, "Theory & Concepts")
        
        # Experiment Videos
        exp_vids = item.get('experiment_videos', [])
        if exp_vids:
            render_video_section(exp_vids, f"Experiment Demonstrations ({mode})")
        
        # Experiment Instructions
        exp_data = item.get('experiment', {})
        st.markdown(f"<div class='sub-header'>⚡ Hands-On Experiment: {exp_data.get('title', 'Activity')}</div>", unsafe_allow_html=True)
        
        with st.expander("📋 View Step-by-Step Instructions", expanded=True):
            for i, step in enumerate(exp_data.get('steps', []), 1):
                st.write(f"**{i}.** {step}")
        
        # Spacer between topics
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("---")
