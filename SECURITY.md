# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please follow our responsible disclosure process.

### DO NOT

- ❌ Open a public GitHub issue for security vulnerabilities
- ❌ Disclose the vulnerability publicly before it's fixed
- ❌ Exploit the vulnerability beyond what's necessary to demonstrate it

### DO

- ✅ Report privately using the process below
- ✅ Provide sufficient detail to reproduce the issue
- ✅ Allow reasonable time for us to respond and fix

## Vulnerability Disclosure Policy (VDP)

### Scope

This policy applies to:
- AgentSRE core SRE engines (`agent-sre`)
- Alert channel integrations (PagerDuty, Slack, Opsgenie)
- Cost guard engine
- Chaos engine
- Kubernetes operator (`operator/`)
- AgentSRE MCP Server
- AgentSRE REST API
- Official documentation and examples

### Out of Scope

- Third-party dependencies (report to upstream)
- Social engineering attacks
- Denial of service attacks
- Issues in forks or unofficial distributions

### How to Report

**Email:** security@agentmesh.dev (or imran.siddique@microsoft.com)

**GitHub Security Advisories:** [Report a vulnerability](https://github.com/imran-siddique/agent-sre/security/advisories/new)

### What to Include

1. **Description:** Clear explanation of the vulnerability
2. **Impact:** What an attacker could achieve
3. **Steps to Reproduce:** Detailed reproduction steps
4. **Affected Versions:** Which versions are impacted
5. **Suggested Fix:** (Optional) If you have a proposed solution
6. **Your Contact:** Email for follow-up questions

## Response Timeline

| Phase | Target Time |
|-------|-------------|
| Initial acknowledgment | 24 hours |
| Severity assessment | 72 hours |
| Fix development | 7-90 days (severity dependent) |
| Public disclosure | After fix is released |

### Severity Levels

| Level | Description | Target Fix Time |
|-------|-------------|-----------------|
| **Critical** | Remote code execution, auth bypass, uncontrolled fault injection | 7 days |
| **High** | Alert channel credential exposure, cost guard bypass | 14 days |
| **Medium** | Limited impact vulnerabilities | 30 days |
| **Low** | Minor issues, hardening | 90 days |

## Security Considerations

### Alert Channel Credentials

AgentSRE integrates with external alerting services. Credential handling requires special attention:

- **PagerDuty tokens**, **Slack webhook URLs**, and **Opsgenie API keys** must be stored using secrets management (e.g., Kubernetes Secrets, HashiCorp Vault)
- Never log or expose credentials in alert payloads or audit trails
- Rotate alert channel credentials regularly
- Use scoped tokens with minimal permissions

### Cost Guard Thresholds

Cost guard thresholds and budget configurations are security-sensitive:

- Unauthorized manipulation of budget thresholds can lead to unchecked resource spend or denial of legitimate scaling
- Treat threshold configuration as a privileged operation requiring RBAC enforcement
- Audit all changes to cost guard parameters

### Chaos Engine Safety

Fault injection carries inherent risk and must be tightly controlled:

- **Blast radius limits** must be enforced — never allow unrestricted fault scope
- Chaos experiments must require explicit approval and scoping before execution
- Safety interlocks (kill switches) must remain functional at all times
- Audit all chaos experiment invocations and their outcomes

### MCP Server Trust Boundary

- The MCP server exposes SRE capabilities to external agents — treat it as an untrusted boundary
- Validate and sanitize all inputs from MCP clients
- Apply capability scoping and rate limiting to MCP endpoints
- Authenticate all MCP connections

### REST API Authentication

- All REST API endpoints must require authentication
- Use short-lived tokens with appropriate scopes
- Enforce rate limiting to prevent abuse
- Log all API access for audit purposes

## Coordinated Disclosure

We follow coordinated disclosure practices:

1. **Private Report:** You report to us privately
2. **Acknowledgment:** We confirm receipt within 24 hours
3. **Investigation:** We assess severity and develop fix
4. **Notification:** We notify you when fix is ready
5. **Release:** We release the fix
6. **Disclosure:** We publish a security advisory (crediting you)
7. **Embargo Lift:** You may publish your findings

### Embargo Period

- Default embargo: 90 days from report
- May be extended for complex issues
- May be shortened if actively exploited

## Security Advisories

Published advisories are available at:
- [GitHub Security Advisories](https://github.com/imran-siddique/agent-sre/security/advisories)

## Credits

We recognize security researchers who responsibly disclose vulnerabilities:

- Security advisory credits
- Hall of Fame in CONTRIBUTORS.md
- Social media acknowledgment (with permission)

## Contact

- **Security Reports:** security@agentmesh.dev / imran.siddique@microsoft.com
- **General Questions:** hello@agentmesh.dev
- **GitHub:** [@imran-siddique](https://github.com/imran-siddique)

---

*This security policy follows the [disclose.io](https://disclose.io/) safe harbor guidelines.*

*Last updated: July 2025*
