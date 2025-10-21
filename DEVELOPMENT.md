# Development Guide

This document outlines best practices for developing and maintaining the Tempest Weather Station Waggle Plugin.

## Development Workflow

### 1. Documentation Requirements

#### Update README.md
- **Always** update README.md when adding new features or changing existing ones
- Include usage examples for new functionality
- Update configuration tables and examples
- Ensure all command-line arguments and environment variables are documented
- Add troubleshooting sections for new features

#### Update CHANGES.md (Changelog)
- **Every change** must be documented in CHANGES.md
- Use consistent date format: `YYYY-MM-DD`
- Include section headers for major changes vs bugfixes vs enhancements
- Document:
  - What was changed
  - Why it was changed  
  - Code locations affected (file paths and line numbers when relevant)
  - Breaking changes or migration notes
- Use clear, descriptive commit-style messages

#### Maintain TODO.md
- Keep a **running TODO.md** with current work in progress
- Mark completed tasks with ✅
- Add new tasks as they're identified
- Include future enhancement ideas
- Update project status regularly

### 2. Git Workflow - Pull Request Based Development

#### Branch Strategy
- **Always create feature branches** for new work instead of committing directly to `main`
- Use descriptive branch names:
  - `feature/description` (e.g., `feature/tcp-protocol-support`)
  - `fix/description` (e.g., `fix/timestamp-metadata-error`)
  - `docs/description` (e.g., `docs/update-readme-examples`)

#### Pull Request Workflow
1. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** following all documentation requirements below

3. **Test and validate** using syntax checks and manual testing

4. **Commit with conventional messages**:
   ```bash
   git add .
   git commit -m "feat: add your feature description
   
   Detailed explanation of changes:
   - What was modified and why
   - Technical details and implementation notes
   
   Files changed:
   - main.py: specific functions/lines modified
   - README.md: documentation updates
   - CHANGES.md: changelog entry
   
   Testing:
   - Manual testing performed
   - Syntax checks passing"
   ```

5. **Push branch and create Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create PR on GitHub with descriptive title and body

6. **Pull Request Requirements**:
   - Clear, descriptive title
   - Detailed description of changes and rationale
   - Checklist of completed requirements
   - Reference any related issues

#### Commit Message Format
Use conventional commit-style messages for all commits:
```bash
# Feature additions
feat: brief description of new feature

# Bug fixes  
fix: brief description of bug fix

# Documentation updates
docs: brief description of documentation changes

# Code refactoring
refactor: brief description of refactoring

# Dependencies or build changes
chore: brief description of maintenance tasks
```

#### Example Good Branch and PR Workflow
```bash
# Create feature branch
git checkout -b feature/environment-variable-support

# Make changes following documentation requirements
# ... code changes ...
# ... update README.md ...
# ... update CHANGES.md ...
# ... update TODO.md ...

# Run syntax checks
./check-syntax.sh

# Commit with conventional message
git add .
git commit -m "feat: add environment variable support for all config options

Added TEMPEST_* environment variables for every command-line argument:
- TEMPEST_UDP_PORT, TEMPEST_PUBLISH_INTERVAL, TEMPEST_DEBUG, TEMPEST_NO_FIREWALL
- Configuration priority: CLI args > ENV vars > Defaults
- Added startup indicators showing active env vars

Files changed:
- main.py: parse_args() function enhanced with env var support
- README.md: comprehensive configuration tables added  
- CHANGES.md: detailed changelog entry
- TODO.md: updated task status

Testing:
- Syntax checks passing
- Manual testing with various env var combinations
- Verified CLI args override env vars as expected

Benefits:
- Better Docker/Kubernetes integration
- Easier CI/CD configuration"

# Push and create PR
git push origin feature/environment-variable-support
```

#### Pull Request Template
When creating PRs, include this information:

**Title**: `[Type] Brief description`

**Description**:
```markdown
## Overview
Brief description of what this PR does and why.

## Changes Made
- [ ] Code changes in main.py (list specific functions/features)
- [ ] Documentation updates (README.md, CHANGES.md, TODO.md)
- [ ] Testing completed

## Technical Details
- What was implemented
- Key technical decisions and rationale
- Any breaking changes or migration notes

## Testing
- [ ] Syntax checks passing (`./check-syntax.sh`)
- [ ] Manual testing performed
- [ ] Environment variable testing (if applicable)

## Documentation
- [ ] README.md updated with new features/examples
- [ ] CHANGES.md includes detailed changelog entry
- [ ] TODO.md reflects current status

## Checklist
- [ ] Follows development workflow from DEVELOPMENT.md
- [ ] All documentation requirements met
- [ ] Ready for review and merge
```

### 3. Code Quality Standards

#### Python Best Practices
- Use context managers (`with Plugin() as plugin:`)
- Avoid global mutable state
- Use type hints where appropriate
- Follow PEP 8 style guidelines
- Use descriptive variable and function names

#### Error Handling
- Always handle exceptions gracefully
- Log errors with appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Publish error status to Waggle when applicable
- Continue operation when possible (don't crash on single message errors)

#### Testing Approach
- Test error conditions (network failures, malformed data)
- Verify environment variable parsing
- Test throttling behavior
- Validate metadata structure

### 4. File Organization

#### Required Files
- `main.py` - Core application logic
- `README.md` - User documentation
- `CHANGES.md` - Detailed changelog
- `TODO.md` - Task tracking
- `DEVELOPMENT.md` - This file
- `requirements.txt` - Dependencies
- `Dockerfile` - Container configuration

#### Update Priority
When making changes in a feature branch, update files in this order:
1. **Code changes** (main.py)
2. **README.md** (user-facing documentation)
3. **CHANGES.md** (changelog)
4. **TODO.md** (task tracking)
5. **Git commit** (in feature branch)
6. **Pull Request** (for review and merge)

### 5. Development Checklist

Before creating a Pull Request, verify:

- [ ] **Feature branch created** (not working directly on main)
- [ ] Code changes are working and tested
- [ ] **Syntax checks pass** (see Syntax Checking section below)
- [ ] README.md is updated with new features/examples
- [ ] CHANGES.md includes detailed changelog entry
- [ ] TODO.md reflects current status
- [ ] Commit message follows conventional format
- [ ] All changes committed to feature branch
- [ ] Branch pushed to remote repository
- [ ] Pull Request created with comprehensive description

#### Syntax Checking

**Required checks before every feature branch commit and Pull Request**:

1. **Python Syntax Check**:
   ```bash
   python3 -m py_compile main.py
   ```

2. **Python Linting** (if flake8 is available):
   ```bash
   python3 -m flake8 main.py --max-line-length=100
   ```

3. **Basic Import Test**:
   ```bash
   python3 -c "import main" 2>/dev/null || echo "Import test failed"
   ```

**Automated syntax check script**:
Use the included `check-syntax.sh` script for comprehensive checking:
```bash
./check-syntax.sh
```

This script performs:
- Python syntax validation (`py_compile`)
- Import testing (handles development environments)
- Code quality checks (long lines, print statements)
- Optional flake8 linting (if available)
- File permission verification
- Required file presence checks

**Check requirements**:
- No syntax errors (py_compile must succeed)
- Standard library imports work correctly
- Waggle imports are optional in development environments
- Basic code quality issues are flagged (warnings only)
- Required files (main.py, README.md, requirements.txt) are present

### 6. Documentation Standards

#### README.md Structure
```markdown
# Title
Brief description

## Overview
What it does

## Features
- Bullet list of capabilities

## Installation
Step-by-step instructions

## Usage
- Basic examples
- Configuration options
- Advanced usage

## Configuration
Tables of all options (CLI args + ENV vars)

## Troubleshooting
Common issues and solutions
```

#### CHANGES.md Structure
```markdown
# Change Log

## YYYY-MM-DD - Feature Title

### Type: Description ✅

**What was changed**:
- Bullet points of changes

**Code Changes**:
- Specific file:line references

**Benefits**:
- Why this was needed

**Example Usage**:
```code
examples if relevant
```
```

#### TODO.md Structure
```markdown
# Project TODO

## Current Status: [STATUS]

## Completed Tasks
- ✅ Completed items

## In Progress
- 🔄 Current work

## Future Enhancements
- [ ] Future ideas
```

### 7. Waggle Integration Standards

#### Plugin Publishing
- Always use `scope="beehive"` for environmental data
- Include complete metadata with sensor name, units, descriptions
- Use standardized missing values (-9999.0 for numeric, "unknown" for strings)
- Add explicit UTC timestamps

#### Error Handling
- Publish plugin status for monitoring
- Handle UDP listener failures gracefully
- Log all errors with context
- Continue operation when possible

### 8. Environment and Deployment

#### Docker Compatibility
- Ensure all configuration can be set via environment variables
- Document Docker usage examples
- Test container startup scenarios

#### Configuration Management
- Support both CLI args and environment variables
- Document precedence order (CLI > ENV > Defaults)
- Validate configuration values
- Show active configuration at startup

### 9. Maintenance Guidelines

#### Regular Tasks
- Update dependencies in requirements.txt
- Review and update TODO.md monthly
- Keep CHANGES.md current with each release
- Test with actual Tempest hardware when possible

#### Breaking Changes
- Document all breaking changes prominently in CHANGES.md
- Provide migration instructions
- Update README.md examples
- Consider version compatibility

### 10. Troubleshooting Development Issues

#### Common Problems
- Plugin initialization errors: Check Plugin() constructor requirements
- Port binding issues: Verify firewall and network configuration
- Missing dependencies: Update requirements.txt and test installation
- Environment variable issues: Test parsing and precedence

#### Debug Mode
Always test with `--debug` flag enabled:
```bash
python3 main.py --debug
```

This shows detailed logging for development and troubleshooting.

---

## Quick Reference

### Pull Request Workflow:
1. Create feature branch ✅
2. Make changes following documentation requirements ✅
3. Run syntax checks ✅
4. Update README.md ✅
5. Update CHANGES.md ✅  
6. Update TODO.md ✅
7. Commit to feature branch with conventional message ✅
8. Push branch to remote ✅
9. Create Pull Request with comprehensive description ✅

### File Update Order:
1. Code changes (main.py)
2. Documentation updates (README.md, CHANGES.md, TODO.md)
3. Git commit in feature branch
4. Push branch and create Pull Request

### Branch Naming:
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Documentation Standards:
- README.md: User-facing documentation
- CHANGES.md: Detailed technical changelog
- TODO.md: Task and status tracking
- DEVELOPMENT.md: This development guide

### Key Principles:
- **Never commit directly to main** - always use feature branches and Pull Requests
- **All changes require documentation updates** - README.md, CHANGES.md, TODO.md
- **Comprehensive testing** - syntax checks and manual validation required
- **Clear commit messages** - conventional format with detailed descriptions

Following these practices ensures the project remains maintainable, well-documented, and collaborative through proper code review processes.
