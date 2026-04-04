# Security Policy

**Last Updated:** April 4, 2026

## 1. Reporting Security Vulnerabilities

If you discover a security vulnerability in ARIA, please **do not** post it on public forums, GitHub issues, or social media.

### Responsible Disclosure

Please report security vulnerabilities to:

**Email**: security@aria.local

**Include in your report:**
- Description of the vulnerability
- Steps to reproduce
- Impact assessment
- Suggested fix (if available)

We will acknowledge receipt within 24 hours and work toward a fix.

## 2. Security Practices

### 2.1 Authentication
- Passwords are hashed using bcrypt (never stored in plain text)
- JWT tokens for API authentication
- HTTPS/TLS for all data in transit
- Refresh token rotation

### 2.2 Data Protection
- SQLite encryption for local development
- PostgreSQL encryption at rest for production
- SSL/TLS encryption in transit
- Regular backups with encryption

### 2.3 Access Control
- Role-based access control (RBAC)
- API rate limiting (100 req/min per user)
- IP rate limiting (500 req/min per IP)
- Session timeouts (30 minutes)

### 2.4 Code Security
- Regular dependency updates
- No hardcoded secrets
- Input validation and sanitization
- CSRF protection for forms
- XSS prevention via React escaping

## 3. Third-Party Dependencies

We use the following third-party services with security in mind:

- **Tavily API**: Web search (see https://tavily.com/security)
- **Ollama**: Local AI models (runs on your machine, no external data)
- **PostgreSQL**: Industry-standard RDBMS
- **Node.js / Python**: Regularly updated runtimes

All dependencies are monitored using:
- npm audit
- pip audit
- Dependabot alerts

## 4. Incident Response

In case of a security incident:
1. We will investigate and contain the issue
2. Affected users will be notified within 72 hours
3. A postmortem will be published
4. Remediation measures will be implemented

## 5. Compliance

### SDLC Security
- Code review before merging
- No direct commits to main branch
- Automated testing for security issues
- Static analysis (ESLint, Pylint)

### Data Privacy
- GDPR compliance (data export, deletion, portability)
- No third-party tracking
- No selling of user data
- Privacy Policy: See `/src/docs/PRIVACY_POLICY.md`

### Encryption Standards
- TLS 1.2+ for transit (1.3 preferred for production)
- bcrypt for password hashing
- AES-256 for data at rest (production)

## 6. Security Updates

We recommend:
- Keep your browser updated
- Keep your OS and dependencies updated
- Use a password manager
- Enable 2FA when available (coming Phase 4)

## 7. Security Contact

For security concerns, responsible disclosure inquiries, or security research:

**Email**: jit.paul.jit2008@gmail.com 
**Response Time**: Within 48 hours

## 8. Future Security Enhancements

Planned for future phases:
- **Phase 4**: Two-factor authentication (2FA/TOTP)
- **Phase 4**: Email verification with DKIM/SPF
- **Phase 5**: Advanced threat detection
- **Phase 5**: Audit logging and compliance reporting
- **Phase 5**: WAF (Web Application Firewall) integration

## 9. Disclaimer

While we take security very seriously, no system is 100% secure. We make no guarantees and are not liable for unauthorized access, data loss, or misuse of the Service.

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- CWE Top 25: https://cwe.mitre.org/top25/
- NIST Cybersecurity Framework: https://www.nist.gov/cyberframework

---

**Version**: 1.0 MVP  
**Status**: Active  
**Next Review**: July 4, 2026
