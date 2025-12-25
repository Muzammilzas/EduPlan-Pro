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
        padding: 30px;
        margin: 30px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        border-left: 5px solid #667eea;
    }
    
    .topic-header {
        font-size: 28px;
        font-weight: 700;
        color: #2d3748;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
    }
    
    .topic-number {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 15px;
        font-weight: 700;
        font-size: 22px;
        box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
    }
    
    .section-header {
        font-size: 20px;
        font-weight: 600;
        color: #4a5568;
        margin-top: 30px;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #e2e8f0;
    }
    
    .overview-box {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-left: 4px solid #667eea;
        padding: 20px;
        border-radius: 10px;
        margin: 15px 0;
        font-size: 16px;
        line-height: 1.7;
    }
    
    .objectives-list, .materials-list {
        background: #f7fafc;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    
    .list-item {
        padding: 10px 0;
        border-bottom: 1px solid #e2e8f0;
        font-size: 15px;
        line-height: 1.5;
    }
    
    .list-item:last-child {
        border-bottom: none;
    }
    
    .video-section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        margin: 25px 0 15px 0;
        font-size: 18px;
        font-weight: 600;
    }
    
    .video-container {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    
    .video-title {
        font-weight: 600;
        font-size: 16px;
        color: #2d3748;
        margin-bottom: 8px;
    }
    
    .video-channel {
        font-size: 13px;
        color: #718096;
        margin-bottom: 12px;
    }
    
    .video-description {
        font-size: 14px;
        color: #4a5568;
        margin-bottom: 15px;
        line-height: 1.5;
        font-style: italic;
    }
    
    .experiment-box {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border: 2px solid #fbbf24;
        border-radius: 12px;
        padding: 25px;
        margin: 25px 0;
    }
    
    .experiment-title {
        font-size: 22px;
        font-weight: 600;
        color: #92400e;
        margin-bottom: 20px;
    }
    
    .step-item {
        background: white;
        padding: 15px;
        margin: 12px 0;
        border-radius: 8px;
        border-left: 4px solid #fbbf24;
        font-size: 15px;
        line-height: 1.6;
    }
    
    .step-number {
        display: inline-block;
        background: #fbbf24;
        color: white;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        text-align: center;
        line-height: 30px;
        margin-right: 12px;
        font-weight: 600;
        font-size: 14px;
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
    
    st.markdown("### 📚 About EduPlan Pro")
    st.caption("🇺🇸 US School Curriculum")
    st.caption("📖 Flexible Topic Coverage")
    st.caption("🎬 Multiple Video Resources")
    st.caption("⚡ Real-time Generation")
    
    st.divider()
    
    if st.button("🔄 Start New Curriculum", use_container_width=True):
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

def extract_video_id(url):
    """Extract YouTube video ID from various URL formats."""
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
    """Generate FLEXIBLE curriculum topics based on real subject requirements."""
    prompt = f"""
You are a US curriculum expert. Generate a comprehensive Table of Contents for {subject}, Grade {grade}.

IMPORTANT INSTRUCTIONS:
1. Base the number of topics on the ACTUAL standard curriculum for this subject and grade level
2. DO NOT limit to exactly 8 topics - use the real number of chapters/units typically taught
3. Follow US education standards (NGSS for Science, Common Core for Math, NCSS for Social Studies, etc.)
4. Topics should be:
   - Age-appropriate for Grade {grade}
   - Aligned with national/state standards
   - Sequenced logically (foundational concepts first)
   - Cover the full academic year curriculum

Examples of typical topic counts:
- Physics Grade 9: Usually 10-12 major topics (Motion, Forces, Energy, Waves, Electricity, Magnetism, etc.)
- Chemistry Grade 10: Usually 10-14 topics (Atomic Structure, Periodic Table, Chemical Bonds, Reactions, etc.)
- Biology Grade 9: Usually 8-10 topics (Cell Biology, Genetics, Evolution, Ecology, etc.)
- Mathematics varies by course (Algebra I might have 8-10 units, Geometry 10-12 units)

Generate the COMPLETE, REALISTIC list of topics for {subject} Grade {grade}.

Output format STRICTLY (no introduction, no explanation):
1. Topic Name
2. Topic Name
3. Topic Name
... (continue for all topics in the actual curriculum)

OUTPUT ONLY THE NUMBERED LIST. No extra text.
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
        exp_guide = "Use ONLY safe, common household items (no hazardous chemicals, no sharp objects for young students)."
        video_guide = "Include DIY demonstrations using household materials that are safe for home experiments."

    MASTER_PROMPT = f"""
You are an expert US curriculum designer creating content for Grade {grade} {subject}.

Topic: {topic}
Mode: {exp_context}
Standards: US Education Standards (NGSS/Common Core/NCSS aligned)

Create a comprehensive, professional lesson plan following this structure:

1. TOPIC OVERVIEW
Write 4-5 sentences explaining:
- What this topic covers
- Why it's important for Grade {grade} students
- Real-world applications and relevance
- How it connects to prior and future learning

2. LEARNING OBJECTIVES
List 3-4 specific, measurable objectives using Bloom's Taxonomy action verbs:
- Students will be able to [understand/analyze/apply/create]...
- Each objective should be clear and assessable

3. REQUIRED MATERIALS
List 6-10 specific materials needed for the hands-on activity.
{exp_guide}
Be specific with quantities and specifications where relevant.

4. HANDS-ON EXPERIMENT/ACTIVITY
Create an engaging, grade-appropriate activity with:
- Descriptive, engaging title
- 7-10 detailed, numbered steps
- Safety considerations (if applicable)
- Expected outcomes/observations
- Discussion questions

5. EDUCATIONAL VIDEO RESOURCES
Provide 4-6 HIGH-QUALITY YouTube videos with REAL, WORKING URLs.

VIDEO SELECTION CRITERIA:
- Choose videos from VERIFIED educational channels ONLY:
  * Khan Academy (all subjects)
  * CrashCourse (Science, History, etc.)
  * TED-Ed (Various topics)
  * SciShow (Science)
  * Veritasium (Physics, Science)
  * National Geographic (Science, Geography)
  * Amoeba Sisters (Biology)
  * Bozeman Science (Biology, Chemistry)
  * The Organic Chemistry Tutor (Chemistry, Physics, Math)
  * MIT OpenCourseWare (Advanced topics)
  * Professor Dave Explains (Science, Math)

VIDEO DISTRIBUTION:
- 2-3 videos explaining THEORY/CONCEPTS (Type: "Theory")
- 2-3 videos showing EXPERIMENTS/DEMONSTRATIONS (Type: "Experiment Demo")
{video_guide}

For each video provide:
- title: Exact title of the video
- channel: Channel name
- url: Full working YouTube URL (https://www.youtube.com/watch?v=VIDEO_ID)
- description: Detailed description of what students will learn (2-3 sentences)
- type: "Theory" or "Experiment Demo"
- duration: Approximate video length

CRITICAL: All video URLs MUST be real, working YouTube links from popular educational videos.

OUTPUT AS VALID JSON:
{{
    "title": "{topic}",
    "overview": "comprehensive 4-5 sentence overview...",
    "objectives": [
        "Students will be able to...",
        "Students will be able to...",
        "Students will be able to...",
        "Students will be able to..."
    ],
    "materials": [
        "Material 1 with specifications",
        "Material 2 with specifications",
        "Material 3",
        "Material 4",
        "Material 5",
        "Material 6"
    ],
    "experiment": {{
        "title": "Engaging Experiment/Activity Title",
        "steps": [
            "Detailed step 1...",
            "Detailed step 2...",
            "Detailed step 3...",
            "Detailed step 4...",
            "Detailed step 5...",
            "Detailed step 6...",
            "Detailed step 7..."
        ]
    }},
    "videos": [
        {{
            "title": "Real Video Title From Channel",
            "channel": "Khan Academy",
            "url": "https://www.youtube.com/watch?v=REAL_VIDEO_ID",
            "description": "Detailed explanation of what this video teaches and why it's useful...",
            "type": "Theory",
            "duration": "10:30"
        }},
        {{
            "title": "Real Video Title",
            "channel": "CrashCourse",
            "url": "https://www.youtube.com/watch?v=REAL_VIDEO_ID",
            "description": "What students will learn from this video...",
            "type": "Theory",
            "duration": "12:15"
        }},
        {{
            "title": "Real Video Title",
            "channel": "TED-Ed",
            "url": "https://www.youtube.com/watch?v=REAL_VIDEO_ID",
            "description": "Visual explanation of concepts covered...",
            "type": "Theory",
            "duration": "5:45"
        }},
        {{
            "title": "Real Experiment Video Title",
            "channel": "SciShow",
            "url": "https://www.youtube.com/watch?v=REAL_VIDEO_ID",
            "description": "Demonstration showing practical application...",
            "type": "Experiment Demo",
            "duration": "8:20"
        }},
        {{
            "title": "Real Lab Demo Title",
            "channel": "Bozeman Science",
            "url": "https://www.youtube.com/watch?v=REAL_VIDEO_ID",
            "description": "Step-by-step laboratory procedure...",
            "type": "Experiment Demo",
            "duration": "15:30"
        }},
        {{
            "title": "Additional Resource",
            "channel": "Veritasium",
            "url": "https://www.youtube.com/watch?v=REAL_VIDEO_ID",
            "description": "Real-world application and extended learning...",
            "type": "Experiment Demo",
            "duration": "11:45"
        }}
    ]
}}

CRITICAL REQUIREMENTS:
- Output ONLY valid JSON (no markdown, no extra text)
- All URLs must be real working YouTube links
- Use well-known, popular educational videos
- Descriptions should be detailed and helpful for teachers
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an expert US curriculum designer who creates comprehensive lesson plans with real YouTube educational video resources."},
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
    """Render a professional embedded YouTube video player."""
    video_url = video.get('url', '')
    video_id = extract_video_id(video_url)
    
    if video_id:
        st.markdown(f"""
            <div class="video-container">
                <div class="video-title">📺 {video.get('title', 'Educational Video')}</div>
                <div class="video-channel">by {video.get('channel', 'YouTube')} • {video.get('duration', 'Duration varies')}</div>
                <div class="video-description">{video.get('description', 'Educational content covering key concepts.')}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Embed the video
        try:
            st.video(f"https://www.youtube.com/watch?v={video_id}")
        except:
            st.markdown(f"""
                <iframe width="100%" height="400" 
                src="https://www.youtube.com/embed/{video_id}" 
                frameborder="0" 
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                allowfullscreen>
                </iframe>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ Video not available: {video.get('title', 'Unknown')}")

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
        mode = st.radio("🏫 Learning Mode", ["Physical (Classroom)", "Online (Virtual)"])
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button("🚀 Generate Curriculum", type="primary", use_container_width=True):
            if not subject or not grade:
                st.warning("⚠️ Please enter both Subject and Grade Level")
            else:
                client = get_openai_client()
                with st.spinner("🧠 Analyzing curriculum standards and generating topics..."):
                    toc = get_table_of_contents(client, grade, subject)
                    if toc:
                        st.session_state.toc_text = toc
                        st.session_state.topics = parse_topics(toc)
                        if st.session_state.topics:
                            st.success(f"✅ Generated {len(st.session_state.topics)} topics based on standard curriculum!")
                            st.rerun()
                        else:
                            st.error("Failed to parse topics.
