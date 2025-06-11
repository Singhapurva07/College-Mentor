# College-Mentor
A Flask-based web application that helps college students choose electives, clubs, and internships based on their branch, interests, and career goals. Powered by the Gemini 2.0 Flash API for personalized recommendations and MySQL for data storage.
Features

Personalized Recommendations: Suggests 3 electives, 1 club, and 1 internship tailored to student inputs, with detailed explanations in bullet points.
Diverse Branches: Supports multiple branches (e.g., Computer Science, Mechanical Engineering, Civil Engineering, Business Administration).
Multi-Select Interests: Dropdown for selecting multiple interests relevant to engineering and business fields.
Autocomplete Goals: LLM-powered suggestions for career goals.
Recommendation History: Stores and displays past recommendations using session-based storage.
MySQL Backend: Stores electives, clubs, internships, and recommendations.
Modern UI: Built with Tailwind CSS and htmx for a responsive, dynamic interface.
Robust Error Handling: Includes logging and fallback recommendations for database or API failures.

Project Structure
college_mentor_chatbot/
├── app.py                  # Flask application
├── .env                    # Environment variables (API keys)
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html          # Frontend with embedded Tailwind CSS and htmx
└── logs/
    └── app.log             # Application logs (auto-created)

Prerequisites

Python 3.11+
MySQL 8.0+
Gemini 2.0 Flash API key
Node.js (optional, for Tailwind CSS development)

Setup Instructions

Clone the Repository
git clone <repository-url>
cd college_mentor_chatbot


Install DependenciesCreate a virtual environment and install Python packages:
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt


Configure Environment VariablesCreate a .env file in the root directory with the following:
GEMINI_API_KEY=your_gemini_flash_2_0_api_key


Replace your_gemini_flash_2_0_api_key with your Gemini API key.
Update MySQL credentials as per your setup.
Generate a random SECRET_KEY for Flask (e.g., python -c "import secrets; print(secrets.token_hex(16))").


Set Up MySQL Database

Ensure MySQL is running.
Run the schema script to create tables and insert sample data:mysql -u your_mysql_user -p < database/init_db.sql


Verify the college_mentor database and tables (electives, clubs, internships, recommendations) are created.


Run the ApplicationStart the Flask development server:
python app.py

Access the app at http://127.0.0.1:5000.


Usage

Select Branch: Choose your academic branch (e.g., Computer Science, Mechanical Engineering).
Choose Interests: Select multiple interests from the dropdown (e.g., AI, Robotics, Renewable Energy).
Enter Goals: Type career goals (e.g., "Become a data scientist") with autocomplete suggestions.
Get Recommendations: Submit the form to receive detailed recommendations in bullet points, including:
3 electives with prerequisites and career impact.
1 club with activities and networking benefits.
1 internship with required skills and application timeline.
Action plan for immediate, medium-term, and long-term steps.


View History: Click "Show Past Recommendations" to see up to 5 previous recommendations.

Troubleshooting

Gemini API Errors: Verify your API key in .env and ensure google-generativeai==0.8.3 is installed.
MySQL Connection Issues: Check .env credentials and ensure MySQL is running. Run mysql -u your_mysql_user -p to test.
Logs Not Created: Ensure write permissions in the project directory. The logs folder is auto-created.
Blank Recommendations: Check app.log for errors and ensure database tables are populated.
Htmx/Tailwind Issues: Verify internet connectivity for CDN links or host assets locally.

Future Enhancements

User Authentication: Add Flask-Login for personalized user profiles.
Advanced LLM Features: Summarize course syllabi or suggest skill-building resources.
Database Expansion: Include course schedules, club events, or internship deadlines.
Offline Mode: Cache recommendations for limited connectivity.
Analytics Dashboard: Track user interactions for admin insights.

Contributing

Fork the repository.
Create a feature branch (git checkout -b feature/your-feature).
Commit changes (git commit -m "Add your feature").
Push to the branch (git push origin feature/your-feature).
Open a pull request.

License
MIT License. See LICENSE for details.
Acknowledgments

Powered by Gemini 2.0 Flash for intelligent recommendations.
Built with Flask, Tailwind CSS, and htmx.
MySQL for robust data management.

