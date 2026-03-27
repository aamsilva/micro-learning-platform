"""
Tests for authentication module
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, db
from src.models import User
from src.auth import (
    create_user, authenticate_user, hash_password, verify_password,
    validate_email, validate_password, generate_tokens, change_password
)


@pytest.fixture
def test_app():
    """Create test app"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    
    with app.app_context():
        db.create_all()
    
    yield app


def test_validate_email():
    """Test email validation"""
    assert validate_email('test@example.com') is True
    assert validate_email('invalid-email') is False
    assert validate_email('') is False
    assert validate_email('test@') is False


def test_validate_password():
    """Test password validation"""
    # Valid password
    is_valid, error = validate_password('Password1')
    assert is_valid is True
    assert error is None
    
    # Too short
    is_valid, error = validate_password('Pass1')
    assert is_valid is False
    assert '8 characters' in error
    
    # No uppercase
    is_valid, error = validate_password('password1')
    assert is_valid is False
    assert 'uppercase' in error
    
    # No lowercase
    is_valid, error = validate_password('PASSWORD1')
    assert is_valid is False
    assert 'lowercase' in error
    
    # No number
    is_valid, error = validate_password('Password')
    assert is_valid is False
    assert 'number' in error


def test_hash_password():
    """Test password hashing"""
    password = 'TestPassword123'
    hashed = hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password('wrongpassword', hashed) is False


def test_create_user(test_app):
    """Test user creation"""
    with test_app.app_context():
        user = create_user(
            email='newuser@test.com',
            username='newuser',
            password='Password123',
            full_name='New User'
        )
        
        assert user is not None
        assert user.email == 'newuser@test.com'
        assert user.username == 'newuser'
        assert user.full_name == 'New User'
        assert user.role == 'student'
        
        # Try to create duplicate
        try:
            create_user(
                email='newuser@test.com',
                username='newuser',
                password='Password123',
                full_name='New User'
            )
        except Exception as e:
            assert 'already' in str(e).lower()


def test_authenticate_user(test_app):
    """Test user authentication"""
    with test_app.app_context():
        # Create user
        create_user(
            email='authtest@test.com',
            username='authtest',
            password='Password123',
            full_name='Auth Test'
        )
        
        # Authenticate
        user, tokens = authenticate_user('authtest@test.com', 'Password123')
        
        assert user is not None
        assert user.email == 'authtest@test.com'
        assert 'access_token' in tokens
        assert 'refresh_token' in tokens
        
        # Wrong password
        try:
            authenticate_user('authtest@test.com', 'wrongpassword')
        except Exception as e:
            assert 'invalid' in str(e).lower()


def test_change_password(test_app):
    """Test password change"""
    with test_app.app_context():
        # Create user
        user = create_user(
            email='password@test.com',
            username='passworduser',
            password='OldPassword123',
            full_name='Password User'
        )
        
        # Change password
        result = change_password(user.id, 'OldPassword123', 'NewPassword456')
        assert result is True
        
        # Old password should not work
        try:
            change_password(user.id, 'OldPassword123', 'Another123')
        except Exception as e:
            assert 'current password' in str(e).lower()


def test_generate_tokens(test_app):
    """Test token generation"""
    with test_app.app_context():
        user = create_user(
            email='token@test.com',
            username='tokentest',
            password='Password123',
            full_name='Token Test'
        )
        
        tokens = generate_tokens(user)
        
        assert 'access_token' in tokens
        assert 'refresh_token' in tokens
        assert tokens['token_type'] == 'Bearer'


def test_login_endpoint(test_app):
    """Test login endpoint"""
    client = test_app.test_client()
    
    with test_app.app_context():
        create_user(
            email='endpoint@test.com',
            username='endpointuser',
            password='Password123',
            full_name='Endpoint Test'
        )
    
    # Login
    response = client.post('/api/auth/login', json={
        'email': 'endpoint@test.com',
        'password': 'Password123'
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert 'tokens' in data['data']


def test_register_endpoint(test_app):
    """Test registration endpoint"""
    client = test_app.test_client()
    
    response = client.post('/api/auth/register', json={
        'email': 'register@test.com',
        'username': 'registertest',
        'password': 'Password123',
        'full_name': 'Register Test'
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert 'user' in data['data']


def test_protected_endpoint(test_app):
    """Test protected endpoint access"""
    client = test_app.test_client()
    
    # Without token
    response = client.get('/api/auth/profile')
    assert response.status_code == 401
    
    # Get token and try again
    with test_app.app_context():
        user = create_user(
            email='protected@test.com',
            username='protecteduser',
            password='Password123',
            full_name='Protected Test'
        )
        tokens = generate_tokens(user)
    
    response = client.get('/api/auth/profile', headers={
        'Authorization': f'Bearer {tokens["access_token"]}'
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])