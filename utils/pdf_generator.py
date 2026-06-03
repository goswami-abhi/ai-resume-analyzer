import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf_report(resume_data):
    """
    Generates a professional PDF report from the resume analysis data.
    Returns a BytesIO stream containing the binary PDF content.
    """
    buffer = io.BytesIO()
    
    # Setup document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    primary_color = colors.HexColor("#7c3aed")   # Violet
    secondary_color = colors.HexColor("#0891b2") # Cyan
    dark_color = colors.HexColor("#0f172a")      # Slate
    light_bg = colors.HexColor("#f8fafc")        # Light gray
    text_color = colors.HexColor("#334155")
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceAfter=25
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=dark_color,
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=text_color,
        spaceAfter=10
    )
    
    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=text_color,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=6
    )
    
    story = []
    
    # 1. Header Section
    story.append(Paragraph("CVision AI Resume Analysis Report", title_style))
    story.append(Paragraph(f"Document Name: {resume_data['filename']}  |  Analyzed On: {resume_data['created_at'].strftime('%Y-%m-%d %H:%M')}", subtitle_style))
    story.append(Spacer(1, 10))
    
    # 2. Score Highlight Box
    score = resume_data['ats_score']
    status = "Highly Compatible" if score >= 80 else ("Action Required" if score >= 60 else "Incompatible Structure")
    status_color = "#10b981" if score >= 80 else ("#f59e0b" if score >= 60 else "#ef4444")
    
    score_table_data = [
        [
            Paragraph(f"<b>ATS SCORE</b><br/><font size=32 color='{primary_color.hexval()}'><b>{score}%</b></font>", body_style),
            Paragraph(f"<b>STATUS EVALUATION</b><br/><font size=14 color='{status_color}'><b>{status}</b></font><br/>Industry compliance indicators mapping score matches.", body_style)
        ]
    ]
    
    score_table = Table(score_table_data, colWidths=[150, 380])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 15),
        ('LINELEFT', (0,0), (0,-1), 4, primary_color),
        ('BOTTOMPADDING', (0,0), (-1,-1), 15),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 20))
    
    # 3. Summary Section
    story.append(Paragraph("Profile Summary", section_heading))
    story.append(Paragraph(resume_data['analysis']['summary'], body_style))
    story.append(Spacer(1, 10))
    
    # 4. Strengths & Weaknesses
    story.append(Paragraph("Core Profile Breakdown", section_heading))
    
    breakdown_data = [
        [
            Paragraph("<b>Core Strengths</b>", body_style),
            Paragraph("<b>Structural Weaknesses</b>", body_style)
        ]
    ]
    
    # Populate bullet points
    strengths_html = "".join([f"• {s}<br/>" for s in resume_data['analysis']['strengths']])
    weaknesses_html = "".join([f"• {w}<br/>" for w in resume_data['analysis']['weaknesses']])
    
    breakdown_data.append([
        Paragraph(strengths_html, body_style),
        Paragraph(weaknesses_html, body_style)
    ])
    
    breakdown_table = Table(breakdown_data, colWidths=[260, 260])
    breakdown_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BACKGROUND', (0,0), (-1,0), light_bg),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor("#cbd5e1")),
        ('LINEAFTER', (0,0), (0,-1), 1, colors.HexColor("#e2e8f0")),
    ]))
    story.append(breakdown_table)
    story.append(Spacer(1, 15))
    
    # 5. Missing Skills Page Break
    story.append(PageBreak())
    
    # 6. Skill Deficiencies
    story.append(Paragraph("Identified Skill Gaps", section_heading))
    story.append(Paragraph("The following key skills are currently missing from your resume or lack sufficient context:", body_style))
    for skill in resume_data['analysis']['missing_skills']:
        story.append(Paragraph(f"• <b>{skill}</b>", bullet_style))
    story.append(Spacer(1, 15))
    
    # 7. Action Plan
    story.append(Paragraph("Actionable Recommendations", section_heading))
    for imp in resume_data['analysis']['resume_improvements']:
        story.append(Paragraph(f"➔ {imp}", bullet_style))
    story.append(Spacer(1, 10))
    
    if resume_data['analysis'].get('grammar_suggestions'):
        story.append(Paragraph("Grammar & Tone Improvements", section_heading))
        for gram in resume_data['analysis']['grammar_suggestions']:
            story.append(Paragraph(f"• {gram}", bullet_style))
        story.append(Spacer(1, 10))
        
    # 8. Best Career Roles
    story.append(Paragraph("Recommended Career Trajectories", section_heading))
    roles_str = ", ".join(resume_data['analysis']['best_career_roles'])
    story.append(Paragraph(f"Based on your profile, the best matching roles are: <b>{roles_str}</b>", body_style))
    
    # Build Document
    doc.build(story)
    buffer.seek(0)
    return buffer
