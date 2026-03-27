# Micro Learning Platform

A comprehensive Learning Management System (LMS) built with Flask and vanilla JavaScript. This platform enables users to create, enroll in, and complete courses with interactive quizzes, progress tracking, and certificates of completion.

## Features

### User Management
- User registration and authentication with JWT tokens
- Role-based access (Student, Instructor, Admin)
- Profile management with avatar support

### Course Management
- Course creation with rich content (video, text, code blocks)
- Course categories and tagging system
- Course enrollment and waitlist
- Course reviews and ratings (1-5 stars)
- Search and filtering by category, difficulty, rating

### Learning Experience
- Interactive video and text lessons
- Lesson progress tracking
- Embedded code snippets with syntax highlighting
- Quiz/Assessment system with multiple question types
- Certificate generation upon course completion

### Analytics Dashboard
- Personal learning statistics
- Course completion rates
- Time spent learning
- Performance trends
- Achievement badges

## Tech Stack

- **Backend:** Python 3.11+, Flask 3.0
- **Database:** SQLite with SQLAlchemy ORM
- **Authentication:** JWT (JSON Web Tokens)
- **Frontend:** Vanilla HTML, CSS, JavaScript
- **Testing:** Pytest

## Project Structure

```
micro-learning-platform/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .gitignore             # Git ignore rules
├── src/
│   ├── models.py          # Database models
│   ├── auth.py            # Authentication logic
│   ├── courses.py         # Course management
│   ├── api.py             # REST API endpoints
│   └── analytics.py       # Learning analytics
├── templates/
│   ├── base.html          # Base template
│   ├── index.html         # Landing page
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── dashboard.html     # User dashboard
│   ├── courses.html       # Course listing
│   ├── course_detail.html # Course details
│   ├── lesson.html        # Lesson viewer
│   ├── quiz.html          # Quiz interface
│   ├── profile.html       # User profile
│   └── analytics.html     # Analytics dashboard
├── static/
│   ├── css/
│   │   ├── main.css       # Main styles
│   │   ├── dashboard.css  # Dashboard styles
│   │   ├── course.css     # Course styles
│   │   └── quiz.css       # Quiz styles
│   └── js/
│       ├── main.js        # Main application logic
│       ├── auth.js        # Authentication
│       ├── courses.js     # Course management
│       ├── lessons.js     # Lesson handling
│       ├── quiz.js        # Quiz functionality
│       └── analytics.js   # Analytics charts
└── tests/
    ├── test_models.py     # Model tests
    ├── test_auth.py       # Auth tests
    ├── test_courses.py    # Course tests
    ├── test_api.py        # API tests
    └── test_analytics.py  # Analytics tests
```

## Installation

### Prerequisites
- Python 3.11 or higher
- pip package manager

### Setup

1. Clone the repository and navigate to the project:
```bash
cd micro-learning-platform
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set environment variables:
```bash
export SECRET_KEY="your-secret-key-here"
export JWT_SECRET_KEY="your-jwt-secret-key"
export FLASK_ENV="development"
```

5. Initialize the database:
```bash
python main.py init-db
```

6. Run the application:
```bash
python main.py run
```

The application will be available at `http://localhost:5000`

## Default Admin User

After running `init-db`, a default admin user is created:
- Email: admin@lms.com
- Password: admin123

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Register new user |
| `/api/auth/login` | POST | Login user |
| `/api/auth/logout` | POST | Logout user |
| `/api/auth/profile` | GET | Get current user profile |

### Courses
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/courses` | GET | List all courses |
| `/api/courses` | POST | Create new course |
| `/api/courses/<id>` | GET | Get course details |
| `/api/courses/<id>` | PUT | Update course |
| `/api/courses/<id>` | DELETE | Delete course |
| `/api/courses/<id>/enroll` | POST | Enroll in course |
| `/api/courses/<id>/reviews` | GET | Get course reviews |
| `/api/courses/<id>/reviews` | POST | Add course review |

### Lessons
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/courses/<id>/lessons` | GET | List course lessons |
| `/api/lessons/<id>` | GET | Get lesson content |
| `/api/lessons/<id>/complete` | POST | Mark lesson complete |

### Quizzes
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/lessons/<id>/quiz` | GET | Get lesson quiz |
| `/api/quizzes/<id>/submit` | POST | Submit quiz answers |
| `/api/quizzes/<id>/results` | GET | Get quiz results |

### Analytics
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/overview` | GET | Get learning overview |
| `/api/analytics/progress` | GET | Get progress data |
| `/api/analytics/performance` | GET | Get performance data |

### Search
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | GET | Search courses |

## Database Models

### User
- id: Integer (Primary Key)
- email: String (Unique)
- password_hash: String
- username: String (Unique)
- full_name: String
- role: String (student/instructor/admin)
- avatar_url: String
- created_at: DateTime
- updated_at: DateTime

### Course
- id: Integer (Primary Key)
- title: String
- description: Text
- thumbnail_url: String
- instructor_id: Integer (Foreign Key)
- category_id: Integer (Foreign Key)
- difficulty: String (beginner/intermediate/advanced)
- price: Float
- is_published: Boolean
- created_at: DateTime
- updated_at: DateTime

### Lesson
- id: Integer (Primary Key)
- course_id: Integer (Foreign Key)
- title: String
- content: Text
- content_type: String (video/text/code)
- video_url: String
- order: Integer
- created_at: DateTime
- updated_at: DateTime

### Quiz
- id: Integer (Primary Key)
- lesson_id: Integer (Foreign Key)
- title: String
- passing_score: Integer
- questions: JSON

### Progress
- id: Integer (Primary Key)
- user_id: Integer (Foreign Key)
- course_id: Integer (Foreign Key)
- lesson_id: Integer (Foreign Key)
- completed: Boolean
- completed_at: DateTime

### Certificate
- id: Integer (Primary Key)
- user_id: Integer (Foreign Key)
- course_id: Integer (Foreign Key)
- certificate_number: String (Unique)
- issued_at: DateTime

### Review
- id: Integer (Primary Key)
- user_id: Integer (Foreign Key)
- course_id: Integer (Foreign Key)
- rating: Integer (1-5)
- comment: Text
- created_at: DateTime

### Category
- id: Integer (Primary Key)
- name: String
- description: String
- icon: String

## Running Tests

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_auth.py -v
```

## Development Commands

```bash
# Initialize database
python main.py init-db

# Create admin user
python main.py create-admin

# Run in development mode
python main.py run --debug

# Run with reloader
python main.py run --reload
```

## Security Features

- JWT token authentication with expiration
- Password hashing with bcrypt
- CSRF protection
- Rate limiting on API endpoints
- Input validation and sanitization
- SQL injection prevention via ORM
- XSS protection

## Learning Analytics Metrics

The platform tracks the following metrics:
- Total learning time
- Courses enrolled and completed
- Quiz scores and attempts
- Daily/weekly/monthly activity
- Streak tracking
- Popular courses
- Average completion rate

## Future Enhancements

- [ ] Email notifications
- [ ] Discussion forums
- [ ] Course completion badges
- [ ] Mobile responsive design
- [ ] Video streaming
- [ ] Payment integration
- [ ] Social features
- [ ] Learning paths
- [ ] Gamification elements

## License

MIT License - See LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## Support

For issues and questions, please open an issue on the project repository.