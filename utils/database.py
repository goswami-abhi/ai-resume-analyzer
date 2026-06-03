import datetime
import sqlite3
import json
from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_login import UserMixin
from config import Config

# Initialize Database Clients
client = None
db = None
SQLITE_FILE = 'local_database.db'

# Try connecting to MongoDB first
try:
    client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
    # Check if connection is successful
    client.server_info()
    db = client.get_database()
    print("Successfully connected to MongoDB!")
    
    # Create indexes
    db.users.create_index("email", unique=True)
    db.users.create_index("username", unique=True)
except (ConnectionFailure, Exception) as e:
    print(f"MongoDB connection failed: {e}. Activating SQLite fallback database...")
    db = None

# Local SQLite Helpers
_sqlite_initialized = False

def get_sqlite_conn(initialize=True):
    global _sqlite_initialized
    if initialize and not _sqlite_initialized and db is None:
        _sqlite_initialized = True
        init_sqlite()
    conn = sqlite3.connect(SQLITE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite():
    try:
        conn = get_sqlite_conn(initialize=False)
        cursor = conn.cursor()
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT,
                role TEXT,
                created_at TEXT
            )
        ''')
        # Create resumes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resumes (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                filename TEXT,
                file_path TEXT,
                raw_text TEXT,
                job_description TEXT,
                ats_score INTEGER,
                analysis TEXT,
                created_at TEXT
            )
        ''')
        
        # Insert default admin user if not present
        cursor.execute("SELECT 1 FROM users WHERE role = 'admin'")
        if not cursor.fetchone():
            hashed_password = generate_password_hash("admin123").decode('utf-8')
            user_id = str(ObjectId())
            created_at = datetime.datetime.utcnow().isoformat()
            cursor.execute(
                "INSERT INTO users (id, username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, "admin", "admin@cvision.com", hashed_password, "admin", created_at)
            )
            print("Default admin user initialized in local SQLite database: admin@cvision.com / admin123")
            
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to initialize local SQLite database: {e}")

# Initialize SQLite database if MongoDB is not connected
if db is None:
    init_sqlite()


class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.password_hash = user_data['password_hash']
        self.role = user_data.get('role', 'user')
        self.created_at = user_data.get('created_at', datetime.datetime.utcnow())

    @staticmethod
    def get_by_id(user_id):
        if db is not None:
            try:
                user_data = db.users.find_one({"_id": ObjectId(user_id)})
                if user_data:
                    return User(user_data)
            except Exception:
                return None
        else:
            try:
                conn = get_sqlite_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    user_data = {
                        '_id': row['id'],
                        'username': row['username'],
                        'email': row['email'],
                        'password_hash': row['password_hash'],
                        'role': row['role'],
                        'created_at': datetime.datetime.fromisoformat(row['created_at'])
                    }
                    return User(user_data)
            except Exception as e:
                print(f"SQLite User get_by_id failed: {e}")
        return None

    @staticmethod
    def get_by_email(email):
        if db is not None:
            user_data = db.users.find_one({"email": email.strip().lower()})
            if user_data:
                return User(user_data)
        else:
            try:
                conn = get_sqlite_conn()
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
                row = cursor.fetchone()
                conn.close()
                if row:
                    user_data = {
                        '_id': row['id'],
                        'username': row['username'],
                        'email': row['email'],
                        'password_hash': row['password_hash'],
                        'role': row['role'],
                        'created_at': datetime.datetime.fromisoformat(row['created_at'])
                    }
                    return User(user_data)
            except Exception as e:
                print(f"SQLite User get_by_email failed: {e}")
        return None

    @staticmethod
    def create_user(username, email, password, role='user'):
        if db is not None:
            # Check if user exists
            if db.users.find_one({"email": email.strip().lower()}):
                raise ValueError("Email already registered.")
            if db.users.find_one({"username": username.strip()}):
                raise ValueError("Username already taken.")
                
            hashed_password = generate_password_hash(password).decode('utf-8')
            user_doc = {
                "username": username.strip(),
                "email": email.strip().lower(),
                "password_hash": hashed_password,
                "role": role,
                "created_at": datetime.datetime.utcnow()
            }
            result = db.users.insert_one(user_doc)
            user_doc['_id'] = result.inserted_id
            return User(user_doc)
        else:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            
            # Check if email/username exists
            cursor.execute("SELECT 1 FROM users WHERE email = ?", (email.strip().lower(),))
            if cursor.fetchone():
                conn.close()
                raise ValueError("Email already registered.")
                
            cursor.execute("SELECT 1 FROM users WHERE username = ?", (username.strip(),))
            if cursor.fetchone():
                conn.close()
                raise ValueError("Username already taken.")
                
            hashed_password = generate_password_hash(password).decode('utf-8')
            user_id = str(ObjectId())
            created_at = datetime.datetime.utcnow().isoformat()
            
            cursor.execute(
                "INSERT INTO users (id, username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username.strip(), email.strip().lower(), hashed_password, role, created_at)
            )
            conn.commit()
            conn.close()
            
            user_data = {
                '_id': user_id,
                'username': username.strip(),
                'email': email.strip().lower(),
                'password_hash': hashed_password,
                'role': role,
                'created_at': datetime.datetime.fromisoformat(created_at)
            }
            return User(user_data)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)


# Resume History Helper Functions

def save_resume_analysis(user_id, filename, file_path, raw_text, job_description, ats_score, analysis):
    """
    Saves a resume analysis result to the database (MongoDB or local SQLite).
    """
    if db is not None:
        resume_doc = {
            "user_id": ObjectId(user_id) if user_id else None,
            "filename": filename,
            "file_path": file_path,
            "raw_text": raw_text,
            "job_description": job_description,
            "ats_score": ats_score,
            "analysis": analysis,
            "created_at": datetime.datetime.utcnow()
        }
        result = db.resumes.insert_one(resume_doc)
        return str(result.inserted_id)
    else:
        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            analysis_id = str(ObjectId())
            created_at = datetime.datetime.utcnow().isoformat()
            
            cursor.execute(
                "INSERT INTO resumes (id, user_id, filename, file_path, raw_text, job_description, ats_score, analysis, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (analysis_id, str(user_id) if user_id else None, filename, file_path, raw_text, job_description, ats_score, json.dumps(analysis), created_at)
            )
            conn.commit()
            conn.close()
            return analysis_id
        except Exception as e:
            print(f"SQLite save_resume_analysis failed: {e}")
            return str(ObjectId())

def get_resume_analysis(analysis_id):
    """
    Retrieves a single resume analysis by ID.
    """
    if db is not None:
        try:
            doc = db.resumes.find_one({"_id": ObjectId(analysis_id)})
            if doc:
                doc['_id'] = str(doc['_id'])
                if doc.get('user_id'):
                    doc['user_id'] = str(doc['user_id'])
                return doc
        except Exception as e:
            print(f"Error retrieving MongoDB analysis: {e}")
    else:
        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM resumes WHERE id = ?", (analysis_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                doc = {
                    '_id': row['id'],
                    'user_id': row['user_id'],
                    'filename': row['filename'],
                    'file_path': row['file_path'],
                    'raw_text': row['raw_text'],
                    'job_description': row['job_description'],
                    'ats_score': row['ats_score'],
                    'analysis': json.loads(row['analysis']),
                    'created_at': datetime.datetime.fromisoformat(row['created_at'])
                }
                return doc
        except Exception as e:
            print(f"Error retrieving SQLite analysis: {e}")
    return None

def get_user_resume_history(user_id):
    """
    Retrieves all resume analyses for a specific user, sorted by date descending.
    """
    if db is not None:
        try:
            cursor = db.resumes.find({"user_id": ObjectId(user_id)}).sort("created_at", -1)
            history = []
            for doc in cursor:
                doc['_id'] = str(doc['_id'])
                doc['user_id'] = str(doc['user_id'])
                history.append(doc)
            return history
        except Exception as e:
            print(f"Error retrieving history: {e}")
            return []
    else:
        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM resumes WHERE user_id = ? ORDER BY created_at DESC", (str(user_id),))
            rows = cursor.fetchall()
            conn.close()
            history = []
            for row in rows:
                history.append({
                    '_id': row['id'],
                    'user_id': row['user_id'],
                    'filename': row['filename'],
                    'file_path': row['file_path'],
                    'raw_text': row['raw_text'],
                    'job_description': row['job_description'],
                    'ats_score': row['ats_score'],
                    'analysis': json.loads(row['analysis']),
                    'created_at': datetime.datetime.fromisoformat(row['created_at'])
                })
            return history
        except Exception as e:
            print(f"Error retrieving SQLite history: {e}")
            return []

def delete_resume_analysis(analysis_id, user_id):
    """
    Deletes a specific analysis document for a given user.
    """
    if db is not None:
        try:
            res = db.resumes.delete_one({"_id": ObjectId(analysis_id), "user_id": ObjectId(user_id)})
            return res.deleted_count > 0
        except Exception as e:
            print(f"Error deleting analysis: {e}")
            return False
    else:
        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM resumes WHERE id = ? AND user_id = ?", (analysis_id, str(user_id)))
            res = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return res
        except Exception as e:
            print(f"Error deleting SQLite analysis: {e}")
            return False

def get_admin_stats():
    """
    Retrieves global database statistics for the admin dashboard.
    """
    if db is not None:
        try:
            total_users = db.users.count_documents({})
            total_resumes = db.resumes.count_documents({})
            
            # Calculate average ATS score
            pipeline = [
                {"$group": {"_id": None, "avg_score": {"$avg": "$ats_score"}}}
            ]
            agg = list(db.resumes.aggregate(pipeline))
            avg_ats_score = round(agg[0]["avg_score"], 1) if agg else 0
            
            # Get 5 recent uploads with user info
            recent_cursor = db.resumes.find().sort("created_at", -1).limit(5)
            recent_uploads = []
            for doc in recent_cursor:
                user_info = "Anonymous"
                if doc.get('user_id'):
                    user = db.users.find_one({"_id": doc['user_id']})
                    if user:
                        user_info = user.get('email', user['username'])
                
                recent_uploads.append({
                    "id": str(doc['_id']),
                    "filename": doc['filename'],
                    "user": user_info,
                    "ats_score": doc['ats_score'],
                    "created_at": doc['created_at'].strftime("%Y-%m-%d %H:%M")
                })
                
            return {
                "total_users": total_users,
                "total_resumes": total_resumes,
                "avg_ats_score": avg_ats_score,
                "recent_uploads": recent_uploads
            }
        except Exception as e:
            print(f"Error retrieving admin stats: {e}")
    else:
        try:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            
            cursor.execute("SELECT count(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            cursor.execute("SELECT count(*), avg(ats_score) FROM resumes")
            res_row = cursor.fetchone()
            total_resumes = res_row[0] if res_row[0] else 0
            avg_ats_score = round(res_row[1], 1) if res_row[1] else 0
            
            cursor.execute("SELECT * FROM resumes ORDER BY created_at DESC LIMIT 5")
            rows = cursor.fetchall()
            recent_uploads = []
            for row in rows:
                user_info = "Anonymous"
                if row['user_id']:
                    cursor.execute("SELECT username, email FROM users WHERE id = ?", (row['user_id'],))
                    u_row = cursor.fetchone()
                    if u_row:
                        user_info = u_row['email'] or u_row['username']
                recent_uploads.append({
                    "id": row['id'],
                    "filename": row['filename'],
                    "user": user_info,
                    "ats_score": row['ats_score'],
                    "created_at": datetime.datetime.fromisoformat(row['created_at']).strftime("%Y-%m-%d %H:%M")
                })
            conn.close()
            return {
                "total_users": total_users,
                "total_resumes": total_resumes,
                "avg_ats_score": avg_ats_score,
                "recent_uploads": recent_uploads
            }
        except Exception as e:
            print(f"Error retrieving SQLite admin stats: {e}")
            
    return {
        "total_users": 0,
        "total_resumes": 0,
        "avg_ats_score": 0,
        "recent_uploads": []
    }
