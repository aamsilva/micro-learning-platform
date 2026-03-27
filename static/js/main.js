/* ============================================
   Micro Learning Platform - Main JavaScript
   ============================================ */

// Utility Functions
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-circle',
        info: 'fa-info-circle'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Add slideOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Auth helpers
function getAuthToken() {
    return localStorage.getItem('lms_access_token');
}

function getCurrentUser() {
    const userStr = localStorage.getItem('lms_user');
    return userStr ? JSON.parse(userStr) : null;
}

function isAuthenticated() {
    return !!getAuthToken();
}

function logout() {
    localStorage.removeItem('lms_access_token');
    localStorage.removeItem('lms_refresh_token');
    localStorage.removeItem('lms_user');
    window.location.href = '/login';
}

// API helper
async function apiCall(url, options = {}) {
    const token = getAuthToken();
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        }
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    if (mergedOptions.body && typeof mergedOptions.body === 'object') {
        mergedOptions.body = JSON.stringify(mergedOptions.body);
    }
    
    const response = await fetch(url, mergedOptions);
    const data = await response.json();
    
    if (!response.ok) {
        throw new Error(data.error || 'API call failed');
    }
    
    return data;
}

// Format date
function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Format relative time
function formatRelativeTime(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (seconds < 60) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    
    return formatDate(dateStr);
}

// Truncate text
function truncate(text, length = 100) {
    if (!text) return '';
    return text.length > length ? text.substring(0, length) + '...' : text;
}

// Debounce
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Throttle
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Navigation toggle
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
    
    // Logout button
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            logout();
        });
    }
    
    // Add fade-in animation to main content
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.style.opacity = '0';
        mainContent.style.transition = 'opacity 0.3s ease';
        setTimeout(() => {
            mainContent.style.opacity = '1';
        }, 100);
    }
});

// Handle unauthorized responses
document.addEventListener('apiError', function(e) {
    if (e.detail.status === 401) {
        showToast('Your session has expired. Please login again.', 'warning');
        logout();
    }
});

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

// Export utilities for use in other scripts
window.LMS = {
    showToast,
    getAuthToken,
    getCurrentUser,
    isAuthenticated,
    logout,
    apiCall,
    formatDate,
    formatRelativeTime,
    truncate,
    debounce,
    throttle
};