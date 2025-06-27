# Security Guidelines for Motor Data Dashboard

## 🔐 Authentication Security

### Current Setup
The dashboard uses password-based authentication with the following security measures:

1. **Password Hashing**: All passwords are stored as SHA-256 hashes
2. **External Configuration**: Credentials are stored in `config.py` (excluded from version control)
3. **Environment Variable Support**: Production deployments can use environment variables
4. **Session Management**: Secure session handling via Streamlit's session state

### 🚨 Important Security Notes

#### 1. The `config.py` file is NOT committed to Git
- This file contains password hashes and should never be shared publicly
- It's listed in `.gitignore` to prevent accidental commits
- Each deployment needs its own `config.py` file

### 🔧 How to Change Passwords

#### Method 1: Update config.py directly
1. Open `config.py`
2. Use the `hash_new_password()` function to generate new hashes:
```python
from config import hash_new_password
print(hash_new_password("your_new_password"))
```
3. Replace the hash in the `AUTH_USERS` dictionary

#### Method 2: Use Environment Variables (Recommended for Production)
```bash
export ADMIN_PASSWORD_HASH="your_new_hash_here"
export WILL_PASSWORD_HASH="your_new_hash_here"
export DEMO_PASSWORD_HASH="your_new_hash_here"
```

### 🏢 Production Deployment

For production environments:

1. **Remove demo credentials**
2. **Use strong passwords** (12+ characters, mixed case, numbers, symbols)
3. **Set environment variables** instead of hardcoded values
4. **Restrict file permissions** on `config.py` (chmod 600)
5. **Use HTTPS** in production
6. **Consider additional security layers** (IP restrictions, VPN, etc.)

### 🛠️ Adding New Users

1. Generate password hash:
```python
python3 -c "from config import hash_new_password; print(hash_new_password('new_password'))"
```

2. Add to `config.py`:
```python
AUTH_USERS = {
    "existing_user": "existing_hash...",
    "new_username": "new_hash_here...",
}
```

### 🔍 Security Checklist

- [ ] Changed default passwords
- [ ] `config.py` is in `.gitignore`
- [ ] Using environment variables in production
- [ ] Strong passwords (12+ characters)
- [ ] Limited user accounts (remove unused ones)
- [ ] Regular password rotation schedule
- [ ] HTTPS enabled in production
- [ ] Server access logs monitored

### ⚠️ Limitations

This is a **basic authentication system** suitable for:
- ✅ Internal tools and dashboards
- ✅ Small team access control
- ✅ Development/demo environments

For enterprise use, consider:
- OAuth/SSO integration
- Database-backed user management
- Role-based access control (RBAC)
- Multi-factor authentication (MFA)
- Password complexity requirements
- Account lockout policies

### 📞 Support

If you need help with authentication setup or have security concerns, please contact the development team. 