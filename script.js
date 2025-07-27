// DOM Elements
const loginForm = document.getElementById('loginForm');
const passwordInput = document.getElementById('password');
const passwordToggle = document.getElementById('passwordToggle');
const loginBtn = document.getElementById('loginBtn');
const loading = document.getElementById('loading');
const roleSelect = document.getElementById('role');
const emailInput = document.getElementById('email');

// Mock user database for demonstration
const mockUsers = {
    admin: {
        email: 'admin@eduguard.com',
        password: 'admin123',
        name: 'System Administrator'
    },
    faculty: {
        email: 'faculty@eduguard.com',
        password: 'faculty123',
        name: 'Dr. John Smith'
    },
    student: {
        email: 'student@eduguard.com',
        password: 'student123',
        name: 'Jane Doe'
    }
};

// Password visibility toggle
passwordToggle.addEventListener('click', function() {
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);
    
    const icon = this.querySelector('i');
    if (type === 'text') {
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
        this.classList.add('active');
    } else {
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
        this.classList.remove('active');
    }
});

// Role selection handler
roleSelect.addEventListener('change', function() {
    const selectedRole = this.value;
    
    // Update email placeholder based on role
    if (selectedRole) {
        emailInput.placeholder = `${selectedRole}@eduguard.com`;
        
        // Add subtle visual feedback
        this.style.borderColor = '#2D9CDB';
        setTimeout(() => {
            this.style.borderColor = '#e5e7eb';
        }, 1000);
    } else {
        emailInput.placeholder = 'example@domain.com';
    }
});

// Form validation
function validateForm() {
    const role = roleSelect.value;
    const email = emailInput.value.trim();
    const password = passwordInput.value;
    
    const errors = [];
    
    if (!role) {
        errors.push('Please select your role');
        highlightError(roleSelect);
    }
    
    if (!email) {
        errors.push('Email is required');
        highlightError(emailInput);
    } else if (!isValidEmail(email)) {
        errors.push('Please enter a valid email address');
        highlightError(emailInput);
    }
    
    if (!password) {
        errors.push('Password is required');
        highlightError(passwordInput);
    } else if (password.length < 6) {
        errors.push('Password must be at least 6 characters');
        highlightError(passwordInput);
    }
    
    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

// Email validation
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Highlight error fields
function highlightError(element) {
    element.style.borderColor = '#ef4444';
    element.style.boxShadow = '0 0 0 3px rgba(239, 68, 68, 0.1)';
    
    setTimeout(() => {
        element.style.borderColor = '#e5e7eb';
        element.style.boxShadow = 'none';
    }, 3000);
}

// Show error message
function showError(message) {
    // Remove existing error messages
    const existingError = document.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.style.cssText = `
        background: #fee2e2;
        color: #dc2626;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        border: 1px solid #fecaca;
        font-size: 14px;
        animation: slideDown 0.3s ease-out;
    `;
    errorDiv.textContent = message;
    
    loginForm.insertBefore(errorDiv, loginForm.firstChild);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 5000);
}

// Show success message
function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.style.cssText = `
        background: #d1fae5;
        color: #065f46;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        border: 1px solid #a7f3d0;
        font-size: 14px;
        animation: slideDown 0.3s ease-out;
    `;
    successDiv.textContent = message;
    
    loginForm.insertBefore(successDiv, loginForm.firstChild);
}

// Simulate login authentication
function authenticateUser(role, email, password) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            const user = mockUsers[role];
            
            if (user && user.email === email && user.password === password) {
                resolve({
                    success: true,
                    user: {
                        role: role,
                        email: email,
                        name: user.name
                    }
                });
            } else {
                reject({
                    success: false,
                    message: 'Invalid credentials. Please check your email and password.'
                });
            }
        }, 2000); // Simulate network delay
    });
}

// Show loading state
function showLoading() {
    loading.classList.add('show');
    loginBtn.disabled = true;
}

// Hide loading state
function hideLoading() {
    loading.classList.remove('show');
    loginBtn.disabled = false;
}

// Handle successful login
function handleLoginSuccess(userData) {
    hideLoading();
    showSuccess(`Welcome back, ${userData.user.name}!`);
    
    // Store user data (in real app, use secure storage)
    sessionStorage.setItem('currentUser', JSON.stringify(userData.user));
    
    // Simulate redirect to dashboard
    setTimeout(() => {
        alert(`Login successful!\n\nRole: ${userData.user.role}\nEmail: ${userData.user.email}\nName: ${userData.user.name}\n\nIn a real application, you would be redirected to the ${userData.user.role} dashboard.`);
        
        // Reset form
        loginForm.reset();
        const successMessage = document.querySelector('.success-message');
        if (successMessage) {
            successMessage.remove();
        }
    }, 1500);
}

// Handle login error
function handleLoginError(error) {
    hideLoading();
    showError(error.message);
    
    // Add shake animation to form
    const loginCard = document.querySelector('.login-card');
    loginCard.style.animation = 'shake 0.5s ease-in-out';
    setTimeout(() => {
        loginCard.style.animation = 'slideUp 0.6s ease-out';
    }, 500);
}

// Form submission handler
loginForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Remove existing messages
    const existingMessages = document.querySelectorAll('.error-message, .success-message');
    existingMessages.forEach(msg => msg.remove());
    
    // Validate form
    const validation = validateForm();
    
    if (!validation.isValid) {
        showError(validation.errors[0]);
        return;
    }
    
    // Get form data
    const formData = {
        role: roleSelect.value,
        email: emailInput.value.trim(),
        password: passwordInput.value
    };
    
    // Show loading
    showLoading();
    
    try {
        const result = await authenticateUser(formData.role, formData.email, formData.password);
        handleLoginSuccess(result);
    } catch (error) {
        handleLoginError(error);
    }
});

// Input event listeners for real-time validation feedback
[roleSelect, emailInput, passwordInput].forEach(input => {
    input.addEventListener('input', function() {
        // Reset error styling on input
        this.style.borderColor = '#e5e7eb';
        this.style.boxShadow = 'none';
        
        // Remove error messages when user starts typing
        const errorMessage = document.querySelector('.error-message');
        if (errorMessage) {
            errorMessage.remove();
        }
    });
});

// Add CSS for shake animation
const style = document.createElement('style');
style.textContent = `
    @keyframes shake {
        0%, 100% { transform: translateX(0); }
        10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
        20%, 40%, 60%, 80% { transform: translateX(5px); }
    }
    
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);

// Initialize demo credentials display
document.addEventListener('DOMContentLoaded', function() {
    // Add demo credentials info (remove in production)
    const demoInfo = document.createElement('div');
    demoInfo.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 16px;
        border-radius: 8px;
        font-size: 12px;
        font-family: monospace;
        z-index: 1000;
        max-width: 250px;
    `;
    demoInfo.innerHTML = `
        <strong>Demo Credentials:</strong><br>
        <strong>Admin:</strong> admin@eduguard.com / admin123<br>
        <strong>Faculty:</strong> faculty@eduguard.com / faculty123<br>
        <strong>Student:</strong> student@eduguard.com / student123
    `;
    document.body.appendChild(demoInfo);
    
    // Auto-hide demo info after 10 seconds
    setTimeout(() => {
        demoInfo.style.opacity = '0.5';
    }, 10000);
});

// Keyboard navigation enhancement
document.addEventListener('keydown', function(e) {
    // Enter key on role select should focus email input
    if (e.key === 'Enter' && document.activeElement === roleSelect) {
        e.preventDefault();
        emailInput.focus();
    }
    
    // Enter key on email should focus password input
    if (e.key === 'Enter' && document.activeElement === emailInput) {
        e.preventDefault();
        passwordInput.focus();
    }
    
    // Escape key to clear form
    if (e.key === 'Escape') {
        const confirmation = confirm('Clear form?');
        if (confirmation) {
            loginForm.reset();
            roleSelect.focus();
        }
    }
});

// Auto-focus first input on page load
window.addEventListener('load', function() {
    roleSelect.focus();
});