/**
 * 登录页面 JavaScript
 * 支持密码登录 + 手机验证码登录双 Tab
 */

// ==================== Tab 切换 ====================
function switchTab(tab) {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector(`.auth-tab[data-tab="${tab}"]`).classList.add('active');
    document.getElementById(`tab${tab.charAt(0).toUpperCase() + tab.slice(1)}`).classList.add('active');
    hideAlert();
}

// ==================== 消息提示 ====================
function showAlert(message, type) {
    const el = document.getElementById('messageAlert');
    el.textContent = message;
    el.className = `alert alert-${type}`;
    el.style.display = 'block';
    if (type === 'success') setTimeout(() => { el.style.display = 'none'; }, 3000);
}

function hideAlert() {
    document.getElementById('messageAlert').style.display = 'none';
}

function showFieldError(fieldId, msg) {
    const input = document.getElementById(fieldId);
    const err = document.getElementById(fieldId + 'Error');
    if (input) input.classList.add('error');
    if (err) { err.textContent = msg; err.style.display = 'block'; }
}

function clearFieldErrors() {
    document.querySelectorAll('.error-message').forEach(e => e.style.display = 'none');
    document.querySelectorAll('input.error').forEach(e => e.classList.remove('error'));
}

function clearInputError(el) {
    el.classList.remove('error');
    const errId = el.id + 'Error';
    const err = document.getElementById(errId);
    if (err) err.style.display = 'none';
}

// ==================== 发送验证码 ====================
let countdownTimer = null;

function sendCode() {
    const phone = document.getElementById('phoneInput').value.trim();
    if (!validatePhone(phone)) return;

    const btn = document.getElementById('sendCodeBtn');
    btn.disabled = true;
    btn.classList.add('sending');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 发送中...';

    fetch('/api/send-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: phone })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showAlert('验证码已发送（开发环境请查看终端控制台）', 'info');
            startCountdown(60);
        } else {
            showAlert(data.message || '发送失败', 'error');
            btn.disabled = false;
            btn.classList.remove('sending');
            btn.innerHTML = '获取验证码';
        }
    })
    .catch(err => {
        showAlert('网络错误，请稍后重试', 'error');
        btn.disabled = false;
        btn.classList.remove('sending');
        btn.innerHTML = '获取验证码';
    });
}

function startCountdown(seconds) {
    const btn = document.getElementById('sendCodeBtn');
    if (countdownTimer) clearInterval(countdownTimer);
    btn.innerHTML = `${seconds}s 后重试`;
    countdownTimer = setInterval(() => {
        seconds--;
        if (seconds <= 0) {
            clearInterval(countdownTimer);
            countdownTimer = null;
            btn.disabled = false;
            btn.classList.remove('sending');
            btn.innerHTML = '重新获取';
        } else {
            btn.innerHTML = `${seconds}s 后重试`;
        }
    }, 1000);
}

function validatePhone(phone) {
    clearFieldErrors();
    if (!phone) { showFieldError('phoneInput', '请输入手机号'); return false; }
    if (!/^1[3-9]\d{9}$/.test(phone)) { showFieldError('phoneInput', '请输入正确的手机号'); return false; }
    return true;
}

// ==================== 密码登录 ====================
document.addEventListener('DOMContentLoaded', function() {
    const pwForm = document.getElementById('passwordForm');
    if (pwForm) {
        pwForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            clearFieldErrors();

            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;

            if (!username) { showFieldError('username', '请输入用户名'); return; }
            if (!password) { showFieldError('password', '请输入密码'); return; }

            const btn = this.querySelector('button[type="submit"]');
            const origText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 登录中...';
            btn.disabled = true;

            try {
                const r = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const data = await r.json();
                if (data.success) {
                    showAlert('登录成功！正在跳转...', 'success');
                    localStorage.setItem('user', JSON.stringify(data.user));
                    localStorage.setItem('session_id', data.session_id);
                    setTimeout(() => { window.location.href = '/home'; }, 1000);
                } else {
                    showAlert(data.message || '登录失败', 'error');
                }
            } catch(err) {
                showAlert('网络错误，请稍后重试', 'error');
            } finally {
                btn.innerHTML = origText;
                btn.disabled = false;
            }
        });
    }

    // ==================== 手机验证码登录 ====================
    const phoneForm = document.getElementById('phoneForm');
    if (phoneForm) {
        phoneForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            clearFieldErrors();

            const phone = document.getElementById('phoneInput').value.trim();
            const code = document.getElementById('codeInput').value.trim();

            if (!validatePhone(phone)) return;
            if (!code) { showFieldError('codeInput', '请输入验证码'); return; }
            if (code.length !== 6) { showFieldError('codeInput', '验证码为6位数字'); return; }

            const btn = this.querySelector('button[type="submit"]');
            const origText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 登录中...';
            btn.disabled = true;

            try {
                const r = await fetch('/api/phone-login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone, code })
                });
                const data = await r.json();
                if (data.success) {
                    showAlert('登录成功！正在跳转...', 'success');
                    localStorage.setItem('user', JSON.stringify(data.user));
                    localStorage.setItem('session_id', data.session_id);
                    setTimeout(() => { window.location.href = '/home'; }, 1000);
                } else {
                    showAlert(data.message || '登录失败', 'error');
                }
            } catch(err) {
                showAlert('网络错误，请稍后重试', 'error');
            } finally {
                btn.innerHTML = origText;
                btn.disabled = false;
            }
        });
    }

    // 输入时清除错误
    document.querySelectorAll('input').forEach(el => {
        el.addEventListener('input', function() { clearInputError(this); });
    });

    // 开发环境自动填充测试用户
    if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
        const u = document.getElementById('username');
        const p = document.getElementById('password');
        if (u) u.value = 'testuser';
        if (p) p.value = 'test123';
    }
});
