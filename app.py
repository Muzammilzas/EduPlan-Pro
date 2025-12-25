import streamlit as st
import os
import re
import json
from openai import OpenAI

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EduPlan Pro", page_icon="🎓", layout="wide")

# --- MODERN CSS STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 40px;
        border-radius: 15px;
        margin-bottom: 30px;
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
    }
    
    .topic-card {
        background: white;
        border-radius: 15px;
        padding: 35px;
        margin: 30px 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-left: 5px solid #667eea;
    }
    
    .topic-header {
        font-size: 30px;
        font-weight: 700;
        color: #2d3748;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
    }
    
    .topic-number {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        width: 55px;
        height: 55px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 20px;
        font-weight: 700;
        font-size: 24px;
        box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
    }
    
    .section-header {
        font-size: 20px;
        font-weight: 600;
        color: #4a5568;
        margin-top: 30px;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 3px solid #e2e8f0;
    }
    
    .overview-box {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-left: 4px solid #667eea;
        padding: 25px;
        border-radius: 10px;
        margin: 15px 0;
        font-size: 16px;
        line-height: 1.8;
    }
    
    .objectives-list, .materials-list {
        background: #f7fafc;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    .list-item {
        padding: 12px 0;
        border-bottom: 1px solid #e2e8f0;
        font-size: 15px;
        line-height: 1.6;
    }
    
    .list-item:last-child {
        border-bottom: none;
    }
    
    .video-section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 25px;
        border-radius: 10px;
        margin: 30px 0 20px 0;
        font-size: 19px;
        font-weight: 600;
    }
    
    .video-scroll-container {
        display: flex;
        overflow-x: auto;
        gap: 20px;
        padding: 20px 0;
        scroll-behavior: smooth;
        -webkit-overflow-scrolling: touch;
    }
    
    .video-scroll-container::-webkit-scrollbar {
        height: 8px;
    }
    
    .video-scroll-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }
    
    .video-scroll-container::-webkit-scrollbar-thumb {
        background: #667eea;
        border-radius: 10px;
    }
    
    .video-scroll-container::-webkit-scrollbar-thumb:hover {
        background: #764ba2;
    }
    
    .video-container {
        background: white;
        border-radius: 12px;
        padding: 20px;
        min-width: 400px;
        max-width: 400px;
        flex-shrink: 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    
    @media (max-width: 768px) {
        .video-container {
            min-width: 300px;
            max-width: 300px;
        }
    }
    
    .video-title {
        font-weight: 600;
        font-size: 17px;
        color: #2d3748;
        margin-bottom: 8px;
    }
    
    .video-channel {
        font-size: 14px;
        color: #718096;
        margin-bottom: 12px;
    }
    
    .video-description {
        font-size: 14px;
        color: #4a5568;
        margin-bottom: 15px;
        line-height: 1.6;
        padding: 10px;
        background: #f7fafc;
        border-radius: 6px;
        font-style: italic;
    }
    
    .experiment-box {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border: 2px solid #fbbf24;
        border-radius: 12px;
        padding: 30px;
        margin: 30px 0;
    }
    
    .experiment-title {
        font-size: 24px;
        font-weight: 600;
        color: #92400e;
        margin-bottom: 20px;
    }
    
    .step-item {
        background: white;
        padding: 18px;
        margin: 12px 0;
        border-radius: 8px;
        border-left: 4px solid #fbbf24;
        font-size: 15px;
        line-height: 1.7;
    }
    
    .step-number {
        display: inline-block;
        background: #fbbf24;
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        text-align: center;
        line-height: 32px;
        margin-right: 12px;
        font-weight: 600;
        font-size: 15px;
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
if 'subject_name' not in st.session_state:
    st.session_state.subject_name = ""
if 'grade_level' not in st.session_state:
    st.session_state.grade_level = ""
if 'mode' not in st.session_state:
    st.session_state.mode = "Physical (Classroom)"

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔐 Settings")
    
    api_key_input = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    if api_key_input:
        openai_api_key = api_key_input.strip()
    elif "OPENAI_API_KEY" in st.secrets:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
    else:
        openai_api_key = None
    
    st.divider()
    
    st.markdown("### 📚 Features")
    st.caption("✅ Smart Topic Generation")
    st.caption("✅ Flexible Chapter Count")
    st.caption("✅ Multiple Video Resources")
    st.caption("✅ Embedded Video Players")
    st.caption("✅ No API Limits")
    
    st.divider()
    
    if st.button("🔄 Start New Curriculum", use_container_width=True):
        st.session_state.topics = []
        st.session_state.generated_content = []
        st.session_state.toc_text = ""
        st.session_state.subject_name = ""
        st.session_state.grade_level = ""
        st.session_state.mode = "Physical (Classroom)"
        st.rerun()

# --- HELPER FUNCTIONS ---
def get_openai_client():
    if not openai_api_key:
        st.error("⚠️ Please enter your OpenAI API Key in the sidebar.")
        st.stop()
    return OpenAI(api_key=openai_api_key)

def extract_video_id(url):
    """Extract YouTube video ID from various URL formats."""
    if not url:
        return None
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_table_of_contents(client, grade, subject):
    """Generate REALISTIC curriculum topics based on actual subject standards."""
    
    prompt = f"""
You are a US curriculum expert with deep knowledge of standard textbooks and curriculum frameworks.

TASK: Generate the complete Table of Contents for {subject}, Grade {grade} based on ACTUAL US curriculum standards.

CRITICAL INSTRUCTIONS:
1. Research what topics are ACTUALLY taught in {subject} for Grade {grade} in US schools
2. The number of topics should match REAL textbook chapter counts:
   - Physics: typically 10-14 major topics
   - Chemistry: typically 10-14 major topics  
   - Biology: typically 9-12 major topics
   - Algebra: typically 8-11 units
   - Geometry: typically 10-12 units
   - US History: typically 10-15 units
   - World History: typically 12-16 units

3. Topics must be:
   - Aligned with NGSS (Science), Common Core (Math), or NCSS (Social Studies)
   - Age-appropriate for Grade {grade}
   - Sequenced in the order they're typically taught
   - Use proper terminology from standard textbooks

4. Include the FULL CURRICULUM - don't abbreviate or skip topics

EXAMPLES OF REAL CURRICULA:
- Chemistry Grade 10: Atomic Structure, Periodic Table, Chemical Bonding, Chemical Reactions, Stoichiometry, Gas Laws, Solutions, Acids and Bases, Thermochemistry, Kinetics, Equilibrium, Electrochemistry, Organic Chemistry
- Physics Grade 9: Motion and Forces, Energy and Work, Momentum, Waves, Sound, Light, Electricity, Magnetism, Heat and Temperature, Simple Machines

Output format STRICTLY:
1. Topic Name
2. Topic Name
3. Topic Name
... (continue for ALL topics in the standard curriculum)

OUTPUT ONLY THE NUMBERED LIST. No introduction, no conclusion, no extra text.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a US curriculum expert who generates realistic, standards-aligned topic lists."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generating curriculum: {e}")
        return None

def parse_topics(toc_text):
    """Extract clean topic names from numbered list."""
    lines = toc_text.split('\n')
    topics = []
    for line in lines:
        clean_line = re.sub(r'^\d+\.\s*', '', line).strip()
        if clean_line and len(clean_line) > 3:
            topics.append(clean_line)
    return topics

def generate_topic_content(client, grade, subject, mode, topic, sequence_num):
    """Generate comprehensive lesson content with MULTIPLE relevant videos."""
    
    if mode == "Physical (Classroom)":
        exp_context = "PHYSICAL CLASSROOM LAB"
        exp_guide = "Use standard school science lab equipment (microscopes, beakers, graduated cylinders, safety goggles, Bunsen burners, etc.)."
        video_guide = "Include formal laboratory demonstrations showing proper equipment usage and safety procedures."
    else:
        exp_context = "HOME/VIRTUAL LEARNING"
        exp_guide = "Use ONLY safe, common household items (no hazardous chemicals, no dangerous equipment)."
        video_guide = "Include DIY demonstrations using household materials that are safe for home experiments."

    MASTER_PROMPT = f"""
You are an expert US curriculum designer creating a comprehensive lesson plan.

Subject: {subject}
Grade: {grade}
Topic: {topic}
Mode: {exp_context}

Create a detailed, professional lesson plan with the following structure:

1. TOPIC OVERVIEW
Write 4-5 sentences that explain:
- What this topic covers
- Why it matters for Grade {grade} students
- Real-world applications
- How it connects to other topics

2. LEARNING OBJECTIVES
List 3-4 specific, measurable objectives:
- Use action verbs (understand, analyze, calculate, demonstrate, etc.)
- Make them assessable
- Align with US standards

3. REQUIRED MATERIALS
List 6-10 specific materials needed.
{exp_guide}
Be precise with quantities and specifications.

4. HANDS-ON ACTIVITY
Create an engaging activity with:
- Creative, descriptive title
- 7-10 detailed, numbered steps
- Safety notes (if applicable)
- Expected outcomes

5. VIDEO RESOURCES - PROVIDE REAL YOUTUBE URLS
Find 4-6 high-quality educational videos with REAL, WORKING YouTube URLs.

TRUSTED CHANNELS TO USE:
- Khan Academy
- CrashCourse
- TED-Ed
- SciShow
- Veritasium
- National Geographic
- Amoeba Sisters (Biology)
- Bozeman Science
- The Organic Chemistry Tutor
- Professor Dave Explains
- MIT OpenCourseWare

VIDEO REQUIREMENTS:
- Provide ACTUAL YouTube URLs (https://www.youtube.com/watch?v=...)
- 2-3 videos on THEORY/CONCEPTS (Type: "Theory")
- 2-3 videos on EXPERIMENTS/DEMOS (Type: "Experiment Demo")
{video_guide}

For each video provide:
- title: Exact video title from YouTube
- channel: Channel name
- url: Complete working YouTube URL
- description: What students learn (2-3 sentences)
- type: "Theory" or "Experiment Demo"
- duration: Estimated length

OUTPUT AS VALID JSON:
{{
    "title": "{topic}",
    "overview": "Comprehensive 4-5 sentence overview...",
    "objectives": [
        "Students will be able to...",
        "Students will be able to...",
        "Students will be able to...",
        "Students will be able to..."
    ],
    "materials": [
        "Material 1",
        "Material 2",
        "Material 3",
        "Material 4",
        "Material 5",
        "Material 6"
    ],
    "experiment": {{
        "title": "Activity Title",
        "steps": [
            "Step 1...",
            "Step 2...",
            "Step 3...",
            "Step 4...",
            "Step 5...",
            "Step 6...",
            "Step 7..."
        ]
    }},
    "videos": [
        {{
            "title": "Real Video Title",
            "channel": "Khan Academy",
            "url": "https://www.youtube.com/watch?v=REAL_ID",
            "description": "Detailed description of video content...",
            "type": "Theory",
            "duration": "10:30"
        }},
        {{
            "title": "Real Video Title",
            "channel": "CrashCourse",
            "url": "https://www.youtube.com/watch?v=REAL_ID",
            "description": "What students learn...",
            "type": "Theory",
            "duration": "12:00"
        }},
        {{
            "title": "Real Video Title",
            "channel": "TED-Ed",
            "url": "https://www.youtube.com/watch?v=REAL_ID",
            "description": "Visual explanation...",
            "type": "Theory",
            "duration": "5:30"
        }},
        {{
            "title": "Real Experiment Video",
            "channel": "SciShow",
            "url": "https://www.youtube.com/watch?v=REAL_ID",
            "description": "Practical demonstration...",
            "type": "Experiment Demo",
            "duration": "8:45"
        }},
        {{
            "title": "Real Lab Demo",
            "channel": "Bozeman Science",
            "url": "https://www.youtube.com/watch?v=REAL_ID",
            "description": "Step-by-step procedure...",
            "type": "Experiment Demo",
            "duration": "15:20"
        }},
        {{
            "title": "Additional Resource",
            "channel": "Veritasium",
            "url": "https://www.youtube.com/watch?v=REAL_ID",
            "description": "Real-world application...",
            "type": "Experiment Demo",
            "duration": "11:00"
        }}
    ]
}}

CRITICAL: Output ONLY valid JSON. All URLs must be real working YouTube links from popular educational videos.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a US curriculum expert creating detailed lesson plans with real YouTube video resources."},
                {"role": "user", "content": MASTER_PROMPT}
            ],
            temperature=0.7
        )
        
        data = json.loads(response.choices[0].message.content)
        return data, response.usage.total_tokens
    
    except Exception as e:
        st.error(f"Error generating content: {e}")
        return None, 0

def render_embedded_video(video, index):
    """Render embedded YouTube video with full details."""
    video_url = video.get('url', '')
    video_id = extract_video_id(video_url)
    
    if video_id:
        st.markdown(f"""
            <div class="video-container">
                <div class="video-title">📺 {video.get('title', 'Educational Video')}</div>
                <div class="video-channel">by {video.get('channel', 'YouTube')} • {video.get('duration', 'Length varies')}</div>
                <div class="video-description">📝 {video.get('description', 'Educational content covering key concepts.')}</div>
                <iframe width="100%" height="225" 
                src="https://www.youtube.com/embed/{video_id}" 
                frameborder="0" 
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen
                style="border-radius: 8px; margin-top: 10px;">
                </iframe>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="video-container">
                <div class="video-title">⚠️ {video.get('title', 'Video Unavailable')}</div>
                <div class="video-channel">by {video.get('channel', 'YouTube')}</div>
                <div class="video-description">Unable to load video. Please check the URL.</div>
            </div>
        """, unsafe_allow_html=True)

# --- MAIN APP ---
st.markdown("""
    <div class="main-header">
        <h1 style="margin:0; font-size: 42px;">🎓 EduPlan Pro</h1>
        <p style="margin:10px 0 0 0; font-size: 18px; opacity: 0.9;">AI-Powered US Curriculum Designer</p>
    </div>
""", unsafe_allow_html=True)

# STEP 1: Input Form
if not st.session_state.topics:
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        subject = st.text_input("📚 Enter Subject", placeholder="Physics, Chemistry, Biology, Algebra, etc.")
    
    with col2:
        grade = st.text_input("🎯 Grade Level", placeholder="e.g. 9")
    
    with col3:
        st.session_state.mode = st.radio("🏫 Learning Mode", ["Physical (Classroom)", "Online (Virtual)"], index=0 if st.session_state.mode == "Physical (Classroom)" else 1)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button("🚀 Generate Curriculum", type="primary", use_container_width=True):
            if not subject or not grade:
                st.warning("⚠️ Please enter both Subject and Grade Level")
            else:
                st.session_state.subject_name = subject
                st.session_state.grade_level = grade
                
                client = get_openai_client()
                with st.spinner("🧠 Analyzing curriculum standards and generating topics..."):
                    toc = get_table_of_contents(client, grade, subject)
                    if toc:
                        st.session_state.toc_text = toc
                        st.session_state.topics = parse_topics(toc)
                        if st.session_state.topics:
                            st.success(f"✅ Generated {len(st.session_state.topics)} topics!")
                            st.rerun()
                        else:
                            st.error("Failed to parse topics. Please try again.")

# STEP 2: Topic Selection
elif not st.session_state.generated_content:
    st.success(f"✅ Generated **{len(st.session_state.topics)} Topics** for {st.session_state.subject_name} - Grade {st.session_state.grade_level}")
    
    # Display TOC
    with st.expander(f"📖 View Complete Curriculum ({len(st.session_state.topics)} Topics)", expanded=True):
        cols = st.columns(2)
        mid_point = (len(st.session_state.topics) + 1) // 2
        
        with cols[0]:
            for i, topic in enumerate(st.session_state.topics[:mid_point], 1):
                st.markdown(f"**{i}.** {topic}")
        
        with cols[1]:
            for i, topic in enumerate(st.session_state.topics[mid_point:], mid_point + 1):
                st.markdown(f"**{i}.** {topic}")
    
    st.markdown("---")
    st.markdown("### 📝 Step 2: Generate Detailed Lesson Plans")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selection_type = st.radio(
            "Choose Generation Mode:",
            ["All Topics (Recommended)", "Select Specific Topics"]
        )
    
    selected_topics = []
    
    if selection_type == "Select Specific Topics":
        with col2:
            chosen = st.multiselect(
                "Select topics:", 
                st.session_state.topics,
                help="Select one or more topics to generate"
            )
            selected_topics = [(st.session_state.topics.index(t)+1, t) for t in chosen]
    else:
        selected_topics = [(i+1, t) for i, t in enumerate(st.session_state.topics)]
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button(f"✨ Generate {len(selected_topics)} Lesson Plan(s)", type="primary", use_container_width=True):
        if not selected_topics:
            st.warning("⚠️ Please select at least one topic")
        else:
            client = get_openai_client()
            progress_bar = st.progress(0)
            status = st.empty()
            
            for i, (seq, topic_name) in enumerate(selected_topics):
                status.info(f"⏳ Generating: **{topic_name}** ({i+1}/{len(selected_topics)})")
                
                data, tokens = generate_topic_content(
                    client, 
                    st.session_state.grade_level, 
                    st.session_state.subject_name, 
                    st.session_state.mode, 
                    topic_name, 
                    seq
                )
                
                if data:
                    st.session_state.generated_content.append(data)
                
                progress_bar.progress((i + 1) / len(selected_topics))
            
            status.success("✅ All lesson plans generated!")
            st.balloons()
            st.rerun()

# STEP 3: Display Generated Content
else:
    st.success(f"🎉 Complete Curriculum: **{st.session_state.subject_name} - Grade {st.session_state.grade_level}** ({len(st.session_state.generated_content)} Topics)")
    
    # Display each topic
    for idx, item in enumerate(st.session_state.generated_content):
        
        st.markdown(f"""
            <div class="topic-card">
                <div class="topic-header">
                    <span class="topic-number">{idx+1}</span>
                    <span>{item.get('title', 'Untitled Topic')}</span>
                </div>
        """, unsafe_allow_html=True)
        
        # Overview
        st.markdown(f"""
            <div class="overview-box">
                <strong style="color: #667eea; font-size: 18px;">📖 Overview</strong><br><br>
                {item.get('overview', 'No overview available')}
            </div>
        """, unsafe_allow_html=True)
        
        # Two columns: Objectives & Materials
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="section-header">🎯 Learning Objectives</div>', unsafe_allow_html=True)
            st.markdown('<div class="objectives-list">', unsafe_allow_html=True)
            for obj in item.get('objectives', []):
                st.markdown(f'<div class="list-item">✓ {obj}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="section-header">🧪 Required Materials</div>', unsafe_allow_html=True)
            st.markdown('<div class="materials-list">', unsafe_allow_html=True)
            for mat in item.get('materials', []):
                st.markdown(f'<div class="list-item">• {mat}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Videos Section
        videos = item.get('videos', [])
        if videos:
            st.markdown('<div class="section-header">🎬 Educational Video Resources</div>', unsafe_allow_html=True)
            
            # Separate by type
            theory_videos = [v for v in videos if v.get('type') == 'Theory']
            experiment_videos = [v for v in videos if v.get('type') == 'Experiment Demo']
            
            
            if theory_videos:
                st.markdown(f'<div class="video-section-header">🧠 Conceptual Learning ({len(theory_videos)} Videos)</div>', unsafe_allow_html=True)
                st.markdown('<div class="video-scroll-container">', unsafe_allow_html=True)
                for i, video in enumerate(theory_videos):
                    render_embedded_video(video, i)
                st.markdown('</div>', unsafe_allow_html=True)
            
            if experiment_videos:
                st.markdown(f'<div class="video-section-header">🔬 Experiments & Demonstrations ({len(experiment_videos)} Videos)</div>', unsafe_allow_html=True)
                st.markdown('<div class="video-scroll-container">', unsafe_allow_html=True)
                for i, video in enumerate(experiment_videos):
                    render_embedded_video(video, i)
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Experiment Section
        exp = item.get('experiment', {})
        if exp:
            st.markdown(f"""
                <div class="experiment-box">
                    <div class="experiment-title">⚗️ Hands-On Activity: {exp.get('title', 'Experiment')}</div>
            """, unsafe_allow_html=True)
            
            for i, step in enumerate(exp.get('steps', []), 1):
                st.markdown(f"""
                    <div class="step-item">
                        <span class="step-number">{i}</span>
                        {step}
                    </div>
                """, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<br><br>", unsafe_allow_html=True)
