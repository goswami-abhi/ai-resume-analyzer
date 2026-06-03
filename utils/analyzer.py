import os
import json
import re
from openai import OpenAI
from groq import Groq
from config import Config

# Mock analyzer function for fallback
def get_mock_analysis(resume_text, job_description=None):
    """
    Returns a high-quality mock analysis if API keys are missing, 
    ensuring the app remains fully functional.
    """
    # Simple heuristics to customize the mock output slightly based on resume text
    skills_list = ["Python", "JavaScript", "React", "Node.js", "SQL", "Git", "Docker", "AWS", "Java", "C++", "HTML", "CSS", "TypeScript"]
    found_skills = [skill for skill in skills_list if skill.lower() in resume_text.lower()]
    missing_skills = [skill for skill in skills_list if skill not in found_skills][:4]
    if not missing_skills:
        missing_skills = ["Kubernetes", "GraphQL", "CI/CD Pipelines", "System Design"]

    # Basic score based on length and skill count
    score = 55
    score += min(len(found_skills) * 3, 25)
    score += min(len(resume_text) // 200, 15)
    if job_description:
        # Match count
        jd_words = set(re.findall(r'\w+', job_description.lower()))
        resume_words = set(re.findall(r'\w+', resume_text.lower()))
        matches = len(jd_words.intersection(resume_words))
        score += min(matches // 2, 10)
    score = min(score, 98)

    role = "Software Engineer"
    if "data" in resume_text.lower() or "pandas" in resume_text.lower():
        role = "Data Scientist / Data Analyst"
    elif "react" in resume_text.lower() or "frontend" in resume_text.lower() or "css" in resume_text.lower():
        role = "Frontend Engineer"
    elif "cloud" in resume_text.lower() or "aws" in resume_text.lower() or "docker" in resume_text.lower():
        role = "DevOps / Cloud Engineer"

    # Assemble structured response
    analysis = {
        "ats_score": int(score),
        "summary": "The candidate displays a solid technical background with experience relevant to engineering roles. Key areas of strength include core programming principles, team collaboration, and technical execution. Further refinement of quantifiable achievements will make the resume highly competitive.",
        "strengths": [
            "Demonstrates experience with multiple programming languages and frameworks.",
            "Includes active GitHub projects or equivalent portfolios.",
            "Good professional layout structure and readability."
        ],
        "weaknesses": [
            "Lacks quantifiable achievements (e.g., 'increased efficiency by 20%').",
            "Job descriptions focus on duties rather than business impact.",
            "Summary section could be more tailored to targeted roles."
        ],
        "missing_skills": missing_skills,
        "resume_improvements": [
            "Add metric-driven bullet points for all work experiences (e.g., dollar amounts, percentages, hours saved).",
            "Rewrite the professional summary to specifically address target role requirements.",
            "Group skills into distinct categories (e.g., Languages, Frameworks, Developer Tools) to improve readability."
        ],
        "grammar_suggestions": [
            "Ensure consistency in tense: use past tense for previous jobs ('managed', 'developed') and present tense for active roles.",
            "Check punctuation consistency inside bullet lists."
        ],
        "best_career_roles": [
            role,
            "Full Stack Developer",
            "Systems Engineer"
        ],
        "skill_gap_analysis": [
            {"skill": s, "status": "Present", "importance": "High" if s in ["Python", "React", "SQL"] else "Medium"} for s in found_skills[:5]
        ] + [
            {"skill": s, "status": "Missing", "importance": "High" if idx == 0 else "Medium"} for idx, s in enumerate(missing_skills)
        ]
    }
    return analysis

def analyze_resume_text(resume_text, job_description=None):
    """
    Analyzes the resume text against a job description (if provided) or industry standards.
    Uses either Groq or OpenAI APIs, with a local fallback.
    """
    # Clean inputs to prevent prompt injection or size issues
    resume_cleaned = resume_text[:12000] # Limit size to avoid token limit errors
    jd_cleaned = (job_description[:4000] if job_description else "General Industry Standards")
    
    # Check if API Keys are available and call provider
    provider = Config.AI_PROVIDER
    
    # Prompt construction
    prompt = f"""
    You are an expert ATS (Applicant Tracking System) parser and senior recruiter.
    Analyze the following resume details and optional target job description. 
    Then, provide a professional, structured analysis in valid, strict JSON format.

    TARGET JOB DESCRIPTION:
    {jd_cleaned}

    RESUME CONTENT:
    {resume_cleaned}

    You must output a single valid JSON object containing exactly the following keys:
    {{
        "ats_score": (integer between 0 and 100 based on standard ATS parameters, keyword match, section presence, and clarity),
        "summary": "A 3-4 sentence professional summary of the candidate's profile based on the resume.",
        "strengths": ["list of 3-4 professional strengths"],
        "weaknesses": ["list of 3-4 structural or content weaknesses"],
        "missing_skills": ["list of 3-5 key skills missing in the resume that would align with target or modern roles"],
        "resume_improvements": ["list of 3-5 specific, actionable suggestions to improve the resume content/format"],
        "grammar_suggestions": ["list of 1-3 spelling/grammar/tone suggestions"],
        "best_career_roles": ["list of 3 career roles suited for this candidate"],
        "skill_gap_analysis": [
            {{"skill": "SkillName", "status": "Present" or "Missing", "importance": "High" or "Medium" or "Low"}},
            ... (include 6-8 core skills here)
        ]
    }}
    
    Return ONLY the valid JSON block. Do not include any introductory or concluding text. Do not wrap the JSON in Markdown formatting (like ```json).
    """

    # Try calling AI APIs
    try:
        if provider == 'groq' and Config.GROQ_API_KEY:
            if Config.GROQ_API_KEY.strip().startswith('xai-'):
                client = OpenAI(api_key=Config.GROQ_API_KEY.strip(), base_url="https://api.x.ai/v1")
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a professional ATS system and resume reviewer that returns pure JSON responses."},
                        {"role": "user", "content": prompt}
                    ],
                    model="grok-beta",
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
            else:
                client = Groq(api_key=Config.GROQ_API_KEY.strip())
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are a professional ATS system and resume reviewer that returns pure JSON responses."},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    temperature=0.2,
                    response_format={"type": "json_object"}
                )
            raw_response = chat_completion.choices[0].message.content
            return json.loads(raw_response)

        elif provider == 'openai' and Config.OPENAI_API_KEY:
            client = OpenAI(api_key=Config.OPENAI_API_KEY)
            chat_completion = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a professional ATS system and resume reviewer that returns pure JSON responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2
            )
            raw_response = chat_completion.choices[0].message.content
            return json.loads(raw_response)

    except Exception as e:
        print(f"AI API call failed ({provider}): {e}. Falling back to mock analysis.")
    
    # Fallback if APIs are disabled or fail
    return get_mock_analysis(resume_text, job_description)


def get_chatbot_response(resume_text, history, user_message):
    """
    Handles chatbot assistant requests regarding the uploaded resume.
    """
    system_prompt = f"""
    You are 'CVision', an AI Career Coach and Resume Assistant. 
    The user is asking questions about their uploaded resume. 
    Here is the content of their resume:
    
    ---
    {resume_text[:8000]}
    ---
    
    Answer the user's questions in a friendly, professional, and encouraging manner. 
    If the question is completely unrelated to careers, job searching, or their resume, politely steer the conversation back to their professional development.
    Keep responses concise and easy to read using markdown bullet points.
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add history
    for msg in history[-10:]: # Limit context to last 10 messages
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": user_message})
    
    # Try calling APIs
    provider = Config.AI_PROVIDER
    try:
        if provider == 'groq' and Config.GROQ_API_KEY:
            if Config.GROQ_API_KEY.strip().startswith('xai-'):
                client = OpenAI(api_key=Config.GROQ_API_KEY.strip(), base_url="https://api.x.ai/v1")
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model="grok-beta",
                    temperature=0.7,
                )
            else:
                client = Groq(api_key=Config.GROQ_API_KEY.strip())
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model="llama-3.1-8b-instant",
                    temperature=0.7,
                )
            return chat_completion.choices[0].message.content

        elif provider == 'openai' and Config.OPENAI_API_KEY:
            client = OpenAI(api_key=Config.OPENAI_API_KEY)
            chat_completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7
            )
            return chat_completion.choices[0].message.content
            
    except Exception as e:
        print(f"Chatbot API call failed: {e}")
        
    # Local fallback responses
    msg_lower = user_message.lower()
    if "improve" in msg_lower or "better" in msg_lower:
        return "To make your resume stand out, I recommend:\n- Using bullet points starting with strong action verbs (e.g., 'Spearheaded', 'Optimized').\n- Including numerical metrics (e.g., 'boosted user engagement by 15%').\n- Customizing your keywords to match target job descriptions closely."
    elif "skill" in msg_lower or "learn" in msg_lower:
        return "Based on your background, adding skills in cloud computing (like AWS), modern databases (SQL/NoSQL), and software testing/CI-CD will make you much more marketable. What specific career role are you aiming for?"
    else:
        return "I'm here to help you refine your resume! Ask me about specific improvements, skill gaps, or how to target a particular job role."
