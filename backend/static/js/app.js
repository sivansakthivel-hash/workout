// Utility functions for API calls and common operations

// API Base URL
const API_BASE = '';

// Helper function for API calls
async function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    };

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...defaultOptions,
        ...options
    });

    return response;
}

// Format date helper
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

// Show notification helper
function showNotification(message, type = 'info') {
    // This can be enhanced with a toast notification library
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Validate PIN
function validatePIN(pin) {
    return /^\d{4}$/.test(pin);
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        apiCall,
        formatDate,
        showNotification,
        validatePIN
    };
}
