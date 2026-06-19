// ─────────────────────────────────────────────────────────────────────────────
// Initialization
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    checkLoginStatus();
});

// ─────────────────────────────────────────────────────────────────────────────
// Toast
// ─────────────────────────────────────────────────────────────────────────────
let toastTimeout = null;
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastIcon = document.getElementById('toastIcon');
    const toastMsg = document.getElementById('toastMessage');
    if (!toast) return;
    if (toastTimeout) clearTimeout(toastTimeout);

    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    toastIcon.textContent = icons[type] || 'ℹ️';
    toastMsg.textContent = message;
    toast.className = 'toast ' + type;
    toast.classList.remove('hidden');
    toastTimeout = setTimeout(() => toast.classList.add('hidden'), 5000);
}

// ─────────────────────────────────────────────────────────────────────────────
// Login Status
// ─────────────────────────────────────────────────────────────────────────────
async function checkLoginStatus() {
    const cardLoader = document.getElementById('cardLoader');
    try {
        const response = await fetch('/api/alerts/status');
        const user = await response.json();
        if (user.logged_in) {
            renderLoggedInView(user);
        } else {
            renderLoggedOutView();
        }
    } catch (error) {
        console.error('Error checking auth:', error);
        showToast('Connection error. Please reload.', 'error');
        renderLoggedOutView();
    } finally {
        if (cardLoader) cardLoader.classList.add('hidden');
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Render Views
// ─────────────────────────────────────────────────────────────────────────────
async function renderLoggedInView(user) {
    document.getElementById('loggedOutView').classList.add('hidden');
    const loggedInView = document.getElementById('loggedInView');
    loggedInView.classList.remove('hidden');

    document.getElementById('displayName').textContent = user.name;
    document.getElementById('displayEmail').textContent = user.email;
    document.getElementById('alertToggle').checked = user.notifications_enabled === 1;
    updateBadgeState(user.notifications_enabled === 1);

    // Check SMTP configuration
    await checkSmtpStatus();
}

function renderLoggedOutView() {
    document.getElementById('loggedInView').classList.add('hidden');
    document.getElementById('loggedOutView').classList.remove('hidden');
}

function updateBadgeState(enabled) {
    const activeBadge = document.getElementById('activeBadge');
    const mutedBadge = document.getElementById('mutedBadge');
    if (enabled) {
        activeBadge.style.display = 'inline-block';
        mutedBadge.style.display = 'none';
    } else {
        activeBadge.style.display = 'none';
        mutedBadge.style.display = 'inline-block';
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// SMTP Configuration
// ─────────────────────────────────────────────────────────────────────────────
async function checkSmtpStatus() {
    try {
        const res = await fetch('/api/alerts/smtp-status');
        const data = await res.json();
        renderSmtpStatus(data.configured);
    } catch (e) {
        console.error('SMTP status check failed:', e);
    }
}

function renderSmtpStatus(configured) {
    const warningBanner  = document.getElementById('smtpWarningBanner');
    const setupCard      = document.getElementById('smtpSetupCard');
    const configuredBadge = document.getElementById('smtpConfiguredBadge');

    if (configured) {
        warningBanner.classList.add('hidden');
        setupCard.classList.add('hidden');
        configuredBadge.classList.remove('hidden');
    } else {
        warningBanner.classList.remove('hidden');
        setupCard.classList.remove('hidden');
        configuredBadge.classList.add('hidden');
    }
}

function toggleSmtpPasswordVisibility() {
    const input = document.getElementById('smtpPasswordInput');
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
}

async function saveSmtpPassword() {
    const input = document.getElementById('smtpPasswordInput');
    const saveBtn = document.getElementById('smtpSaveBtn');
    const spinner = document.getElementById('smtpSaveSpinner');
    const password = input.value.trim();

    if (!password) {
        showToast('Please enter your Gmail App Password first.', 'error');
        return;
    }
    if (password.length < 16) {
        showToast('App Password should be 16 characters. Check and try again.', 'error');
        return;
    }

    saveBtn.disabled = true;
    spinner.classList.remove('hidden');

    try {
        const res = await fetch('/api/alerts/configure-smtp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ smtp_password: password })
        });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message, 'success');
            input.value = '';
            renderSmtpStatus(true);
        } else {
            showToast(data.error || 'Failed to save password.', 'error');
        }
    } catch (e) {
        console.error('Save SMTP error:', e);
        showToast('Network error saving password.', 'error');
    } finally {
        saveBtn.disabled = false;
        spinner.classList.add('hidden');
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Login / Logout
// ─────────────────────────────────────────────────────────────────────────────
async function handleLogin(event) {
    event.preventDefault();
    const name  = document.getElementById('userName').value.trim();
    const email = document.getElementById('userEmail').value.trim();
    const btn   = document.getElementById('loginSubmitBtn');
    const spinner = document.getElementById('loginSpinner');

    if (!name || !email) { showToast('Please fill out all fields.', 'error'); return; }

    btn.disabled = true;
    spinner.classList.remove('hidden');

    try {
        const res = await fetch('/api/alerts/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email })
        });
        const data = await res.json();
        if (res.ok) {
            showToast('Welcome, ' + data.name + '!', 'success');
            renderLoggedInView(data);
        } else {
            showToast(data.error || 'Login failed.', 'error');
        }
    } catch (e) {
        showToast('Network error during login.', 'error');
    } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
    }
}

async function handleLogout() {
    if (!confirm('Are you sure you want to log out?')) return;
    try {
        await fetch('/api/alerts/logout', { method: 'POST' });
        document.getElementById('userName').value = '';
        document.getElementById('userEmail').value = '';
        showToast('Logged out.', 'info');
        renderLoggedOutView();
    } catch (e) {
        showToast('Logout failed.', 'error');
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Toggle
// ─────────────────────────────────────────────────────────────────────────────
async function handleToggleChange(checkbox) {
    const enabled = checkbox.checked;
    checkbox.disabled = true;
    try {
        const res = await fetch('/api/alerts/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ notifications_enabled: enabled })
        });
        const data = await res.json();
        if (res.ok) {
            updateBadgeState(enabled);
            showToast(enabled ? 'Notifications enabled!' : 'Notifications muted.', enabled ? 'success' : 'info');
        } else {
            checkbox.checked = !enabled;
            updateBadgeState(!enabled);
            showToast(data.error || 'Update failed.', 'error');
        }
    } catch (e) {
        checkbox.checked = !enabled;
        updateBadgeState(!enabled);
        showToast('Network error.', 'error');
    } finally {
        checkbox.disabled = false;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Test Email
// ─────────────────────────────────────────────────────────────────────────────
async function triggerTestEmail() {
    const btn     = document.getElementById('testEmailBtn');
    const spinner = document.getElementById('testSpinner');

    btn.disabled = true;
    spinner.classList.remove('hidden');
    showToast('Compiling alert report and sending...', 'info');

    try {
        const res = await fetch('/api/alerts/test-email', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (res.ok) {
            if (data.simulated) {
                showToast('SMTP not configured yet — email saved to sent_emails_log.txt. Set up your App Password above to receive real emails.', 'info');
            } else {
                showToast('Test email sent to your inbox! Check it now.', 'success');
            }
        } else {
            showToast(data.error || 'Failed to send.', 'error');
        }
    } catch (e) {
        showToast('Network error.', 'error');
    } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
    }
}
