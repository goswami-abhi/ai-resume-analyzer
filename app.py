import os
from flask import Flask, request, redirect, url_for, render_template, flash, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from bson import ObjectId

from config import Config
from utils.database import db, User, save_resume_analysis, get_resume_analysis, get_user_resume_history, delete_resume_analysis, get_admin_stats
from utils.parser import extract_resume_text
from utils.analyzer import analyze_resume_text, get_chatbot_response
from utils.pdf_generator import generate_pdf_report

# Initialize Flask App
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Security extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'error'

# Helper to verify file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

# Create a default admin user if not present in the DB
@app.before_request
def setup_default_admin():
    if db is not None:
        try:
            # Check if admin user exists
            admin = db.users.find_one({"role": "admin"})
            if not admin:
                # Create a default admin
                print("No admin user found. Creating default admin...")
                User.create_user("admin", "admin@cvision.com", "admin123", role="admin")
                print("Default admin created: admin@cvision.com / admin123")
        except Exception as e:
            print(f"Failed to setup default admin: {e}")


# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        user = User.get_by_email(email)
        if user and user.verify_password(password):
            login_user(user)
            flash("Welcome back! You have logged in successfully.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "error")
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template('register.html')
            
        try:
            user = User.create_user(username, email, password)
            login_user(user)
            flash("Registration successful! Welcome to CVision.", "success")
            return redirect(url_for('dashboard'))
        except ValueError as ve:
            flash(str(ve), "error")
        except Exception as e:
            flash("An error occurred during registration. Please try again.", "error")
            
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have logged out successfully.", "success")
    return redirect(url_for('index'))


# --- Public / Core Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        # Check if file part exists
        if 'resume' not in request.files:
            flash("No file selected.", "error")
            return redirect(request.url)
            
        file = request.files['resume']
        job_description = request.form.get('job_description', '').strip()
        
        if file.filename == '':
            flash("No file selected.", "error")
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                # Save file temporarily
                file.save(file_path)
                
                # Parse resume text
                resume_text = extract_resume_text(file_path)
                
                # Run AI Analysis
                analysis_result = analyze_resume_text(resume_text, job_description)
                ats_score = analysis_result.get('ats_score', 0)
                
                # Save to database
                analysis_id = save_resume_analysis(
                    user_id=current_user.id,
                    filename=filename,
                    file_path=file_path,
                    raw_text=resume_text,
                    job_description=job_description,
                    ats_score=ats_score,
                    analysis=analysis_result
                )
                
                # Clean up uploaded file (or leave it if database stores file paths)
                # In production, files can be stored in GridFS or S3. Here we keep it in static/uploads.
                
                flash("Resume analyzed successfully!", "success")
                return redirect(url_for('result', analysis_id=analysis_id))
                
            except Exception as e:
                flash(f"Error analyzing resume: {str(e)}", "error")
                return redirect(request.url)
        else:
            flash("Unsupported file format. Please upload PDF or DOCX files.", "error")
            return redirect(request.url)
            
    return render_template('upload.html')

@app.route('/dashboard')
@login_required
def dashboard():
    history = get_user_resume_history(current_user.id)
    
    # Calculate stats
    avg_score = 0
    max_score = 0
    if history:
        scores = [h['ats_score'] for h in history]
        avg_score = round(sum(scores) / len(scores))
        max_score = max(scores)
        
    return render_template('dashboard.html', history=history, avg_score=avg_score, max_score=max_score)

@app.route('/result/<analysis_id>')
@login_required
def result(analysis_id):
    resume = get_resume_analysis(analysis_id)
    
    # Verify report ownership
    if not resume or (resume.get('user_id') != current_user.id and current_user.role != 'admin'):
        flash("You are not authorized to view this analysis report.", "error")
        return redirect(url_for('dashboard'))
        
    return render_template('result.html', resume=resume)

@app.route('/delete/<analysis_id>', methods=['POST'])
@login_required
def delete_resume(analysis_id):
    success = delete_resume_analysis(analysis_id, current_user.id)
    if success:
        flash("Resume analysis deleted successfully.", "success")
    else:
        flash("Could not delete resume analysis.", "error")
    return redirect(url_for('dashboard'))


# --- Extra Features Routes ---

@app.route('/chat/<analysis_id>', methods=['POST'])
@login_required
def chat(analysis_id):
    """
    Handles chatbot assistant API requests about a specific resume.
    """
    resume = get_resume_analysis(analysis_id)
    if not resume or (resume.get('user_id') != current_user.id and current_user.role != 'admin'):
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({"response": "I didn't receive any message. How can I help you?"}), 400
        
    # Get recent chatbot history if available (could be implemented in session or database,
    # here we keep it stateless for simplicity and build history manually)
    history = []
    
    try:
        response_text = get_chatbot_response(resume['raw_text'], history, user_message)
        return jsonify({"response": response_text})
    except Exception as e:
        return jsonify({"response": f"I couldn't analyze that question: {str(e)}"}), 500

@app.route('/download_pdf/<analysis_id>')
@login_required
def download_pdf(analysis_id):
    """
    Generates and downloads the analysis report in PDF format.
    """
    resume = get_resume_analysis(analysis_id)
    if not resume or (resume.get('user_id') != current_user.id and current_user.role != 'admin'):
        flash("You are not authorized to access this report.", "error")
        return redirect(url_for('dashboard'))
        
    try:
        pdf_buffer = generate_pdf_report(resume)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"{resume['filename'].rsplit('.', 1)[0]}_Analysis_Report.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        flash(f"Failed to generate report PDF: {str(e)}", "error")
        return redirect(url_for('result', analysis_id=analysis_id))


# --- Admin Route ---

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for('dashboard'))
        
    stats = get_admin_stats()
    return render_template('admin.html', stats=stats)


# --- Application Run ---

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Run the server
    app.run(host='0.0.0.0', port=port, debug=True)
