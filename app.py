import os
import logging
import uuid
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import google.generativeai as genai
import mysql.connector
from mysql.connector import Error
from mysql.connector.pooling import MySQLConnectionPool

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '2f8b60bda6a957bc9415dcb4774887f2')

# Ensure logs directory exists
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Set up logging
log_file = os.path.join(log_dir, 'app.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# MySQL configuration - make it optional
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'root@123'),
    'database': os.getenv('MYSQL_DB', 'college_mentor')
}

# Configure Gemini API
model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')  # Use experimental model
        logger.info("Gemini API configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {e}")
        model = None
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")

# Database connection pool - make it optional
db_pool = None
try:
    db_pool = MySQLConnectionPool(
        pool_name="mentor_pool",
        pool_size=5,
        pool_reset_session=True,
        **MYSQL_CONFIG
    )
    logger.info("MySQL connection pool initialized successfully")
except Exception as e:
    logger.warning(f"MySQL connection pool not available: {e}")
    logger.info("Application will run without database persistence")

def get_db_connection():
    """Get database connection with error handling"""
    try:
        if db_pool:
            return db_pool.get_connection()
        else:
            return mysql.connector.connect(**MYSQL_CONFIG)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def initialize_database():
    """Initialize database tables if they don't exist"""
    try:
        conn = get_db_connection()
        if not conn:
            logger.warning("Database not available - skipping initialization")
            return False
        
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        tables = [
            '''CREATE TABLE IF NOT EXISTS electives (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                branch VARCHAR(255) NOT NULL,
                prerequisites TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS clubs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                branch VARCHAR(255) NOT NULL,
                description TEXT,
                activities TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS internships (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                branch VARCHAR(255) NOT NULL,
                skills_required TEXT,
                description TEXT,
                company_type VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS recommendations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                branch VARCHAR(255) NOT NULL,
                interests TEXT,
                goals TEXT,
                recommendation LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )'''
        ]
        
        for table_sql in tables:
            cursor.execute(table_sql)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database tables initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

# Initialize database on startup
initialize_database()

# Route for homepage
@app.route('/')
def index():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        logger.info(f"New session started: {session['session_id']}")
    return render_template('index.html')

# Route to get autocomplete suggestions
@app.route('/get_suggestions', methods=['POST'])
def get_suggestions():
    try:
        field = request.form.get('field')
        query = request.form.get('query')
        
        if not field or not query or len(query) < 2:
            return jsonify({'suggestions': []})

        # Fallback suggestions if Gemini is not available
        fallback_suggestions = {
            'goals': [
                f"Become a {query} specialist in leading tech companies",
                f"Start an innovative {query} startup company",
                f"Pursue advanced research in {query} field",
                f"Work on cutting-edge {query} projects globally",
                f"Lead {query} teams in Fortune 500 companies"
            ]
        }

        if not model:
            logger.warning("Gemini API not available, using fallback suggestions")
            return jsonify({'suggestions': fallback_suggestions.get(field, [
                "Explore career opportunities in your field",
                "Build expertise through hands-on projects",
                "Network with industry professionals",
                "Pursue continuous learning and skill development",
                "Consider leadership roles in your domain"
            ])})

        prompt = f"""
        Generate 5 concise, relevant career goal suggestions for a college student interested in: '{query}'.
        Focus on realistic, achievable career paths and professional development goals.
        Return only a simple list format without any extra formatting or explanations.
        Example format:
        - Become a data scientist at a tech company
        - Start a fintech startup
        - Pursue PhD in machine learning
        - Work as AI consultant for Fortune 500
        - Lead data teams at innovative companies
        """
        
        try:
            response = model.generate_content(prompt)
            suggestions_text = response.text.strip()
            
            # Parse suggestions from the response
            suggestions = []
            for line in suggestions_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                    suggestion = line[1:].strip()
                    if suggestion:
                        suggestions.append(suggestion)
            
            # If parsing failed, use fallback
            if len(suggestions) < 3:
                suggestions = fallback_suggestions.get(field, [
                    f"Specialize in {query} technology",
                    f"Lead {query} projects in industry",
                    f"Research and develop {query} solutions",
                    f"Consult on {query} implementations",
                    f"Build {query}-focused products"
                ])
            
            logger.info(f"Suggestions generated for {field}: {query}")
            return jsonify({'suggestions': suggestions[:5]})
            
        except Exception as api_error:
            logger.error(f"Gemini API error: {api_error}")
            return jsonify({'suggestions': fallback_suggestions.get(field, [
                "Explore career opportunities in your field",
                "Build expertise through hands-on projects",
                "Network with industry professionals",
                "Pursue continuous learning and development",
                "Consider leadership roles in your domain"
            ])})
            
    except Exception as e:
        logger.error(f"Error in get_suggestions: {e}")
        return jsonify({'suggestions': [
            "Explore your interests deeper",
            "Build practical skills",
            "Network with professionals",
            "Gain hands-on experience",
            "Consider interdisciplinary approaches"
        ]})

def get_branch_data(branch):
    """Get branch-specific data from database with comprehensive fallbacks"""
    electives = []
    clubs = []
    internships = []
    
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            
            # Get electives
            cursor.execute("SELECT name, prerequisites, description FROM electives WHERE branch = %s", (branch,))
            electives = [(row[0], row[1] or 'None', row[2] or '') for row in cursor.fetchall()]
            
            # Get clubs
            cursor.execute("SELECT name, description, activities FROM clubs WHERE branch = %s", (branch,))
            clubs = [(row[0], row[1] or '', row[2] or '') for row in cursor.fetchall()]
            
            # Get internships
            cursor.execute("SELECT name, skills_required, description, company_type FROM internships WHERE branch = %s", (branch,))
            internships = [(row[0], row[1] or '', row[2] or '', row[3] or '') for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error fetching branch data: {e}")
    
    # Enhanced fallback data based on branch
    if not electives:
        if "Computer Science" in branch or "IT" in branch or "Software" in branch:
            electives = [
                ("Advanced Algorithms & Data Structures", "Basic programming, DSA fundamentals", "Deep dive into complex algorithms and optimization"),
                ("Machine Learning & AI", "Statistics, Python programming", "Hands-on ML projects and AI applications"),
                ("Cloud Computing & DevOps", "Basic networking, Linux", "AWS/Azure certification and deployment strategies")
            ]
        elif "Mechanical" in branch or "Automobile" in branch:
            electives = [
                ("Advanced CAD & Simulation", "Engineering graphics, basic CAD", "SolidWorks, ANSYS simulation projects"),
                ("Renewable Energy Systems", "Thermodynamics, fluid mechanics", "Solar, wind, and hybrid energy solutions"),
                ("Robotics & Automation", "Control systems, programming", "Industrial robotics and automation projects")
            ]
        elif "Electrical" in branch or "Electronics" in branch:
            electives = [
                ("Embedded Systems Design", "Microprocessors, C programming", "IoT projects and embedded applications"),
                ("Power Systems & Smart Grid", "Circuit analysis, power electronics", "Modern power distribution and smart grid tech"),
                ("VLSI Design", "Digital electronics, HDL", "Chip design and semiconductor applications")
            ]
        else:
            electives = [
                (f"Advanced {branch} Applications", "Core subject completion", "Specialized applications in your field"),
                ("Research Methodology", "Basic coursework", "Scientific research and publication techniques"),
                ("Industry Integration", "Foundational knowledge", "Real-world applications and case studies")
            ]
    
    if not clubs:
        clubs = [
            (f"{branch} Professional Society", f"Professional development in {branch}", "Industry workshops, guest lectures, networking events"),
            ("Innovation & Entrepreneurship Club", "Startup incubation and innovation projects", "Pitch competitions, business plan development, mentorship"),
            ("Technical Research Club", "Academic research and publication support", "Research projects, paper presentations, conference participation")
        ]
    
    if not internships:
        internships = [
            (f"Industry Internship - {branch}", "Technical skills, communication, teamwork", f"Practical experience in {branch} industry", "Industry"),
            ("Research Internship", "Analytical thinking, research methodology", "Academic research with faculty guidance", "Research Institute"),
            ("Startup Internship", "Adaptability, multi-tasking, innovation mindset", "Dynamic startup environment experience", "Startup")
        ]
    
    return electives, clubs, internships

# Route to handle recommendations
@app.route('/get_recommendations', methods=['POST'])
def get_recommendations():
    try:
        # Get form data
        branch = request.form.get('branch', '').strip()
        year = request.form.get('year', '2nd Year').strip()
        interests = request.form.get('interests-value', '').strip()
        goals = request.form.get('goals', '').strip()

        # Validate input
        if not all([branch, interests, goals]):
            logger.warning("Incomplete form data in get_recommendations")
            return jsonify({'error': 'Please fill all required fields including selecting at least one interest.'}), 400

        # Get branch-specific data
        electives, clubs, internships = get_branch_data(branch)
        
        logger.info(f"Generating recommendations for {branch} student with interests: {interests}")

        # Enhanced fallback recommendation if Gemini is not available
        if not model:
            logger.warning("Gemini API not available, using structured fallback recommendation")
            
            fallback_recommendation = f"""
# 🎓 Personalized Academic & Career Recommendations

## 📋 Your Profile
- **Branch:** {branch}
- **Year:** {year}
- **Interests:** {interests}
- **Career Goals:** {goals}

## 🎓 Recommended Electives

### 1. {electives[0][0]}
**Why This Fits:** This course aligns perfectly with your interests in {interests.split(',')[0].strip()} and supports your career goals.

**Key Benefits:**
- Develops critical skills relevant to your field
- Provides hands-on experience with industry tools
- Opens pathways to specialized career opportunities

**Prerequisites:** {electives[0][1]}

### 2. {electives[1][0] if len(electives) > 1 else 'Advanced Specialization Course'}
**Why This Fits:** Complements your interests while building analytical and technical skills.

**Key Benefits:**
- Enhances problem-solving capabilities
- Provides theoretical foundation for practical applications
- Builds portfolio of relevant projects

**Prerequisites:** {electives[1][1] if len(electives) > 1 else 'Core coursework completion'}

### 3. {electives[2][0] if len(electives) > 2 else 'Industry-Focused Elective'}
**Why This Fits:** Bridges the gap between academic knowledge and real-world applications.

**Key Benefits:**
- Exposure to cutting-edge technologies
- Networking opportunities with professionals
- Capstone project experience

**Prerequisites:** {electives[2][1] if len(electives) > 2 else 'Advanced foundation courses'}

## 🏛️ Recommended Club

### {clubs[0][0]}
**Why This Club:** Perfect match for your interests and career aspirations in {branch}.

**Activities & Benefits:**
- Technical workshops and skill development
- Networking with alumni and industry professionals
- Competitions and project showcases
- Leadership development opportunities

## 💼 Recommended Internship

### {internships[0][0]}
**Perfect Match Because:** Aligns with your interests in {interests.split(',')[0].strip()} and career goals.

**What You'll Gain:**
- Real-world application of academic knowledge
- Industry-specific tools and technology experience
- Professional network and mentorship opportunities
- Resume-building practical experience

**Required Skills:** {internships[0][1]}

## 🎯 Action Plan

**Immediate Steps (This Semester):**
1. Enroll in the top recommended elective for next semester
2. Join the recommended club and attend orientation sessions
3. Start building relevant skills through online courses

**Medium-term Goals (Next 6-12 months):**
1. Complete at least 2 recommended electives
2. Take active role in club activities and projects
3. Begin internship application process early

**Long-term Vision (1-2 years):**
1. Secure internship opportunity in your field
2. Build strong professional network
3. Develop expertise that sets you apart

## 📈 Additional Recommendations

**Skill Development Focus:**
- Technical skills related to {interests.split(',')[0].strip()}
- Communication and presentation skills  
- Project management and teamwork

**Networking Strategy:**
- Attend industry conferences and webinars
- Connect with alumni in your field
- Join professional associations

**Portfolio Building:**
- Document all projects and achievements
- Create online presence (LinkedIn, GitHub, personal website)
- Collect recommendations from professors and supervisors

---
*Remember: Success comes from consistent effort and strategic choices. Focus on quality over quantity and always align decisions with your long-term career goals.*
            """
            
            # Try to save to database if available
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO recommendations (session_id, branch, interests, goals, recommendation) VALUES (%s, %s, %s, %s, %s)",
                        (session['session_id'], branch, interests, goals, fallback_recommendation)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
            except Exception as db_error:
                logger.error(f"Failed to save recommendation to database: {db_error}")
            
            return jsonify({'recommendation': fallback_recommendation})

        # Enhanced prompt for Gemini
        prompt = f"""
        You are an expert college academic advisor. Create comprehensive, personalized recommendations for this student:

        **Student Profile:**
        - Branch: {branch}
        - Year: {year}  
        - Interests: {interests}
        - Career Goals: {goals}

        **Available Options:**
        - Electives: {[e[0] for e in electives]}
        - Clubs: {[c[0] for c in clubs]}
        - Internships: {[i[0] for i in internships]}

        Create detailed recommendations in this exact markdown format:

        # 🎓 Personalized Academic & Career Recommendations

        ## 📋 Your Profile Summary
        [Brief analysis of student's profile and how interests align with career goals]

        ## 🎓 Recommended Electives (Top 3)

        ### 1. {electives[0][0]}
        **Why This Perfectly Fits You:** [Specific connection to their interests and goals]
        **Key Benefits:**
        • [Specific skill development]
        • [Career advantages]
        • [Industry relevance]
        **Prerequisites:** {electives[0][1]}
        **Career Impact:** [How this directly helps achieve their goals]

        ### 2. {electives[1][0] if len(electives) > 1 else '[Second Best Elective]'}
        **Why This Perfectly Fits You:** [Specific connection]
        **Key Benefits:**
        • [Benefits specific to their interests]
        • [Complementary skills]
        • [Future opportunities]
        **Prerequisites:** {electives[1][1] if len(electives) > 1 else '[Prerequisites]'}
        **Career Impact:** [Specific career benefits]

        ### 3. {electives[2][0] if len(electives) > 2 else '[Third Best Elective]'}
        **Why This Perfectly Fits You:** [Specific connection]
        **Key Benefits:**
        • [Advanced skill development]
        • [Industry exposure]
        • [Network building]
        **Prerequisites:** {electives[2][1] if len(electives) > 2 else '[Prerequisites]'}
        **Career Impact:** [Long-term career benefits]

        ## 🏛️ Recommended Club

        ### {clubs[0][0]}
        **Perfect Match Because:** [Why this club aligns with their profile]
        **What You'll Gain:**
        • [Specific networking opportunities]
        • [Skill development activities]
        • [Leadership experiences]
        • [Industry connections]

        ## 💼 Recommended Internship Path

        ### {internships[0][0]}
        **Ideal Match Because:** [Connection to interests and goals]
        **Experience You'll Gain:**
        • [Hands-on technical experience]
        • [Industry exposure]
        • [Professional skills]
        • [Network building]
        **Skills to Develop First:** {internships[0][1]}
        **Application Strategy:** [Specific advice for securing this internship]

        ## 🎯 Personalized Action Plan

        **Immediate Steps (Next 4 weeks):**
        1. [Specific first action]
        2. [Specific second action]
        3. [Specific third action]

        **Short-term Goals (3-6 months):**
        1. [Specific goal with timeline]
        2. [Specific goal with timeline]
        3. [Specific goal with timeline]

        **Long-term Vision (1-2 years):**
        1. [Major milestone]
        2. [Career positioning goal]
        3. [Expertise development target]

        ## 📈 Success Strategies

        **Skill Development Priority:**
        [Top 3 skills to focus on based on their interests and goals]

        **Networking Approach:**
        [Specific networking strategies for their field]

        **Portfolio Building:**
        [What they should include in their portfolio]

        Make every recommendation highly specific to their interests ({interests}) and career goals ({goals}). Be actionable and practical.
        """

        try:
            response = model.generate_content(prompt)
            recommendation = response.text
            logger.info(f"AI recommendation generated successfully for session {session['session_id']}")
            
            # Save to database if available
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO recommendations (session_id, branch, interests, goals, recommendation) VALUES (%s, %s, %s, %s, %s)",
                        (session['session_id'], branch, interests, goals, recommendation)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    logger.info("Recommendation saved to database")
            except Exception as db_error:
                logger.error(f"Failed to save recommendation to database: {db_error}")
            
            return jsonify({'recommendation': recommendation})
            
        except Exception as api_error:
            logger.error(f"Gemini API error: {api_error}")
            # Use the same fallback as when model is not available
            fallback_recommendation = f"""
# 🎓 Personalized Academic & Career Recommendations

## 📋 Your Profile
- **Branch:** {branch}
- **Year:** {year}
- **Interests:** {interests}
- **Career Goals:** {goals}

## 🎓 Recommended Electives

### 1. {electives[0][0]}
**Why This Fits:** This course aligns with your interests in {interests.split(',')[0].strip()} and supports your career aspirations.

**Key Benefits:**
- Develops critical technical skills
- Provides hands-on project experience  
- Opens specialized career pathways

**Prerequisites:** {electives[0][1]}

### 2. {electives[1][0] if len(electives) > 1 else 'Advanced Specialization'}
**Why This Fits:** Complements your interests while building analytical capabilities.

**Key Benefits:**
- Enhances problem-solving skills
- Provides theoretical foundation
- Builds relevant project portfolio

### 3. {electives[2][0] if len(electives) > 2 else 'Industry Applications'}
**Why This Fits:** Bridges academic knowledge with real-world applications.

**Key Benefits:**
- Exposure to cutting-edge technology
- Professional networking opportunities
- Practical project experience

## 🏛️ Recommended Club

### {clubs[0][0]}
**Why This Club:** Excellent match for your {branch} background and career interests.

**What You'll Gain:**
- Technical workshops and skill development
- Networking with industry professionals
- Leadership and teamwork experience
- Project collaboration opportunities

## 💼 Recommended Internship

### {internships[0][0]}
**Perfect Match:** Aligns with your interests and career goals in {branch}.

**Benefits:**
- Real-world application of your studies
- Industry tools and technology exposure
- Professional mentorship and networking
- Competitive resume building

**Required Skills:** {internships[0][1]}

## 🎯 Action Plan

**This Month:**
1. Research and apply to recommended club
2. Plan course selection for next semester  
3. Start building relevant technical skills

**Next 3-6 Months:**
1. Enroll in top recommended electives
2. Take active role in club activities
3. Begin internship preparation and applications

**Long-term (1-2 years):**
1. Secure internship in your field
2. Build strong professional network
3. Develop specialized expertise

## 📈 Additional Recommendations

**Focus Areas:**
- Technical skills: {interests.split(',')[0].strip()}
- Professional skills: Communication, teamwork, project management
- Industry knowledge: Stay updated with latest trends

**Success Tips:**
- Quality over quantity in activities
- Build meaningful professional relationships
- Document achievements and create portfolio
- Align all activities with career goals

*Note: This recommendation was generated with limited AI assistance. For more detailed guidance, ensure your system configuration is complete.*
            """
            return jsonify({'recommendation': fallback_recommendation})

    except Exception as e:
        logger.error(f"Error in get_recommendations: {e}")
        return jsonify({'error': 'An error occurred while generating recommendations. Please try again.'}), 500

# Route to get recommendation history
@app.route('/get_history', methods=['GET'])
def get_history():
    try:
        conn = get_db_connection()
        if not conn:
            logger.warning("Database not available for history")
            return jsonify({'history': []})

        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT branch, interests, goals, recommendation, created_at FROM recommendations WHERE session_id = %s ORDER BY created_at DESC LIMIT 5",
                (session.get('session_id', ''),)
            )
            history = []
            for row in cursor.fetchall():
                history.append({
                    'branch': row[0],
                    'interests': row[1],
                    'goals': row[2],
                    'recommendation': row[3],
                    'created_at': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else 'Unknown'
                })
            
            logger.info(f"History retrieved: {len(history)} items for session {session.get('session_id')}")
            return jsonify({'history': history})
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        logger.error(f"Error in get_history: {e}")
        return jsonify({'history': []})

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'gemini_api': 'available' if model else 'unavailable',
        'database': 'available' if db_pool else 'unavailable'
    })

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    logger.info(f"Gemini API: {'Configured' if model else 'Not configured'}")
    logger.info(f"Database: {'Available' if db_pool else 'Not available'}")
    app.run(debug=True, host='0.0.0.0', port=5000)