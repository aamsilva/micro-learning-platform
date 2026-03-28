"""
AI Learning Assistant
ChatGPT-like assistant to help with learning
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models import User, Course, Lesson, Progress
import random
import re

ai_assistant_bp = Blueprint('ai_assistant', __name__, url_prefix='/ai-assistant')

# Simple AI responses (in production, use OpenAI API)
LEARNING_RESPONSES = {
    "explain": [
        "Let me break this down for you: {concept} is about understanding {detail}. Think of it like building blocks - each concept builds on the previous one.",
        "Great question! {concept} can be understood by looking at its key components: 1) The theory, 2) The practical application, 3) Common patterns.",
        "Here's a simple way to think about {concept}: Imagine you're teaching it to someone else. How would you explain it in 3 sentences?"
    ],
    "summary": [
        "Here's a summary of what we've covered: {summary}. The key takeaway is that understanding the fundamentals makes advanced topics easier.",
        "To recap: {summary}. This forms the foundation for more complex topics in this course."
    ],
    "quiz": [
        "Let me test your knowledge! What's the main concept behind {topic}? Think about the key principles we discussed.",
        "Here's a quick check: Can you explain {topic} in your own words? This will help reinforce your learning."
    ],
    "help": [
        "I'm here to help! What specific part of {topic} would you like me to clarify?",
        "Don't worry - learning takes time. Let's break this down together. What specifically would you like to understand better?"
    ],
    "motivate": [
        "You're doing great! Remember, every expert was once a beginner. Keep going!",
        "Consistency is key! Even 5 minutes a day adds up. You're on the right track!",
        "Learning is a journey, not a destination. Celebrate each small win!"
    ]
}

# Course content knowledge base (simplified)
CONCEPT_EXPLANATIONS = {
    "python": "Python is a high-level programming language known for its readability and versatility. It's great for beginners because the syntax is similar to English.",
    "programming": "Programming is the process of creating instructions for computers. It involves writing code in languages like Python, Java, or JavaScript.",
    "web development": "Web development involves creating websites and web applications. It includes HTML (structure), CSS (style), and JavaScript (interactivity).",
    "data science": "Data science combines statistics, programming, and domain expertise to extract insights from data. Key tools include Python, SQL, and machine learning.",
    "machine learning": "Machine learning is a type of AI that allows computers to learn from data without being explicitly programmed. It's used in recommendations, predictions, and more."
}

@ai_assistant_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    """
    Chat with AI Learning Assistant
    Request: {"message": "Explain Python", "context": {"course": "Python Basics", "lesson": "Introduction"}}
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    
    user_message = data.get('message', '').lower()
    context = data.get('context', {})
    
    # Determine intent
    intent = detect_intent(user_message)
    
    # Generate response
    response = generate_response(intent, user_message, context)
    
    return jsonify({
        "success": True,
        "data": {
            "response": response,
            "intent": intent,
            "suggestions": get_suggestions(intent, context),
            "timestamp": "2026-03-28T00:51:00Z"
        }
    })

@ai_assistant_bp.route('/explain-concept', methods=['POST'])
@jwt_required()
def explain_concept():
    """Explain a specific concept in the course"""
    data = request.get_json()
    concept = data.get('concept', '').lower()
    
    # Find explanation
    explanation = CONCEPT_EXPLANATIONS.get(concept, 
        f"Great question about {concept}! Let me help you understand this better. Think of it as building upon the fundamentals we've covered."
    )
    
    # Add examples
    examples = get_examples(concept)
    
    return jsonify({
        "success": True,
        "data": {
            "concept": concept,
            "explanation": explanation,
            "examples": examples,
            "related_topics": get_related_topics(concept)
        }
    })

@ai_assistant_bp.route('/study-help', methods=['POST'])
@jwt_required()
def study_help():
    """Get study help for current lesson"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    course_id = data.get('course_id')
    lesson_id = data.get('lesson_id')
    
    if not course_id or not lesson_id:
        return jsonify({"error": "course_id and lesson_id required"}), 400
    
    lesson = Lesson.query.get(lesson_id)
    course = Course.query.get(course_id)
    
    # Get user's progress
    completed = Progress.query.filter_by(
        user_id=user_id,
        course_id=course_id,
        completed=True
    ).count()
    
    # Generate study help
    help_content = {
        "current_lesson": lesson.title if lesson else "Unknown",
        "course": course.title if course else "Unknown",
        "progress": completed,
        "study_tips": get_study_tips(lesson.title if lesson else ""),
        "key_points": extract_key_points(lesson.content if lesson else ""),
        "practice_suggestions": get_practice_suggestions(lesson.title if lesson else "")
    }
    
    return jsonify({
        "success": True,
        "data": help_content
    })

@ai_assistant_bp.route('/recommend-next', methods=['GET'])
@jwt_required()
def recommend_next():
    """AI recommends next learning step"""
    user_id = get_jwt_identity()
    
    # Get current progress
    in_progress = Progress.query.filter_by(user_id=user_id, completed=False).first()
    
    if in_progress:
        return jsonify({
            "success": True,
            "data": {
                "recommendation": "Continue your current lesson",
                "reason": "You have an unfinished lesson. Complete it to maintain momentum!",
                "lesson_id": in_progress.lesson_id
            }
        })
    
    # Get enrolled courses
    enrollments = Enrollment.query.filter_by(user_id=user_id).all()
    
    if not enrollments:
        return jsonify({
            "success": True,
            "data": {
                "recommendation": "Start a new course",
                "reason": "You haven't enrolled in any courses yet!"
            }
        })
    
    # Recommend based on popular courses
    popular = Course.query.order_by(Course.enrollment_count.desc()).first()
    
    return jsonify({
        "success": True,
        "data": {
            "recommendation": f"Try {popular.title}",
            "reason": f"This is popular among your colleagues!",
            "course_id": popular.id
        }
    })

def detect_intent(message):
    """Detect user's intent from message"""
    if any(word in message for word in ['explain', 'what is', 'how does', 'define', 'understand']):
        return "explain"
    elif any(word in message for word in ['summarize', 'recap', 'review', 'summary']):
        return "summary"
    elif any(word in message for word in ['quiz', 'test', 'question', 'check']):
        return "quiz"
    elif any(word in message for word in ['help', 'confused', 'stuck', 'hard']):
        return "help"
    elif any(word in message for word in ['motivate', 'encourage', 'why', 'giving up']):
        return "motivate"
    else:
        return "general"

def generate_response(intent, message, context):
    """Generate AI response based on intent"""
    responses = LEARNING_RESPONSES.get(intent, LEARNING_RESPONSES["help"])
    response = random.choice(responses)
    
    # Extract key concept from message
    concept = extract_concept(message)
    
    # Fill in template
    response = response.replace("{concept}", concept or "this topic")
    response = response.replace("{detail}", "the fundamentals")
    response = response.replace("{topic}", concept or "this subject")
    response = response.replace("{summary}", "the key concepts we've covered")
    
    return response

def extract_concept(message):
    """Extract the main concept from user's message"""
    words = message.split()
    for word in words:
        if word.lower() in CONCEPT_EXPLANATIONS:
            return word.lower()
    return "this concept"

def get_examples(concept):
    """Get examples for a concept"""
    examples = {
        "python": ["print('Hello World')", "Creating a simple calculator", "Building a web scraper"],
        "programming": ["Writing a function", "Creating a loop", "Building an app"],
        "web development": ["Building a form", "Creating a responsive layout", "Adding interactivity"],
        "data science": ["Analyzing sales data", "Creating visualizations", "Building a prediction model"]
    }
    return examples.get(concept, ["Practice with real examples", "Build a small project", "Try coding exercises"])

def get_related_topics(concept):
    """Get related topics"""
    related = {
        "python": ["JavaScript", "Data Structures", "Web Scraping"],
        "programming": ["Algorithms", "Problem Solving", "Debugging"],
        "web development": ["HTML", "CSS", "React"],
        "data science": ["Statistics", "Machine Learning", "Visualization"]
    }
    return related.get(concept, ["Practice more", "Review basics", "Ask questions"])

def get_study_tips(lesson_title):
    """Get study tips for a lesson"""
    tips = [
        "Take notes while watching - it helps retention!",
        "Try explaining the concept to someone else - teaching is learning!",
        "Break the content into smaller chunks - microlearning works!",
        "Practice with real examples - hands-on is key!",
        "Review within 24 hours - spacing repetition helps memory!"
    ]
    return random.sample(tips, 3)

def extract_key_points(content):
    """Extract key points from lesson content"""
    if not content:
        return ["Focus on understanding the main concepts", "Practice the examples"]
    
    # Simple extraction - split by sentences
    sentences = content.split('.')
    key_points = [s.strip() for s in sentences[:3] if s.strip()]
    
    return key_points if key_points else ["Understand the core concepts", "Practice regularly"]

def get_practice_suggestions(lesson_title):
    """Get practice suggestions"""
    return [
        "Try coding the examples yourself",
        "Modify the code and experiment",
        "Create a small project using what you learned",
        "Teach someone else what you learned",
        "Take a short quiz to test your knowledge"
    ]