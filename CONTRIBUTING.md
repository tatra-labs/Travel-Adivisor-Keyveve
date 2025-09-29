# Contributing to Travel Advisory Agent

Thank you for your interest in contributing to the Travel Advisory Agent! We welcome contributions from the community and appreciate your help in making this project better.

## 🤝 How to Contribute

### 1. Fork the Repository

1. Click the "Fork" button on the GitHub repository page
2. Clone your forked repository to your local machine:
   ```bash
   git clone https://github.com/yourusername/travel-advisory-agent.git
   cd travel-advisory-agent
   ```

### 2. Set Up Development Environment

1. **Install Dependencies**:

   ```bash
   # Run the setup script
   ./setup.sh  # Linux/Mac
   # or
   setup.bat   # Windows
   ```

2. **Create a Development Branch**:

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Install Development Dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```

### 3. Make Your Changes

- Write clean, readable code
- Follow the existing code style and conventions
- Add tests for new functionality
- Update documentation as needed

### 4. Test Your Changes

```bash
# Run backend tests
cd backend
python -m pytest tests/ -v

# Run integration tests
python test_complete_flow.py

# Check code formatting
black .
flake8 .

# Type checking
mypy .
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "feat: add new travel planning feature"
```

### 6. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with a clear description of your changes.

## 📋 Contribution Guidelines

### Code Style

- **Python**: Follow PEP 8 style guidelines
- **JavaScript/TypeScript**: Use ESLint and Prettier
- **Documentation**: Use clear, concise language
- **Comments**: Explain complex logic and business rules

### Commit Messages

Use conventional commit format:

```
type(scope): description

feat: add new travel destination support
fix: resolve cost parsing issue
docs: update API documentation
test: add unit tests for cost parser
refactor: improve error handling
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Pull Request Guidelines

1. **Clear Title**: Summarize the change in the title
2. **Detailed Description**: Explain what, why, and how
3. **Reference Issues**: Link to related issues
4. **Screenshots**: Include screenshots for UI changes
5. **Testing**: Ensure all tests pass

### Issue Reporting

When reporting bugs or requesting features:

1. **Check Existing Issues**: Search for similar issues first
2. **Use Templates**: Use the provided issue templates
3. **Provide Details**: Include steps to reproduce, expected vs actual behavior
4. **Environment Info**: Include OS, Python version, Docker version

## 🏗️ Development Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- OpenAI API Key (for testing)

### Local Development

1. **Clone and Setup**:

   ```bash
   git clone https://github.com/yourusername/travel-advisory-agent.git
   cd travel-advisory-agent
   ./setup.sh
   ```

2. **Environment Variables**:

   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Start Development Services**:
   ```bash
   docker-compose -f docker-compose.dev.yml up
   ```

### Project Structure

```
travel-advisory-agent/
├── frontend/          # Streamlit frontend
├── backend/           # FastAPI backend
├── tests/            # Test files
├── docs/             # Documentation
└── scripts/          # Utility scripts
```

## 🧪 Testing

### Running Tests

```bash
# Unit tests
pytest tests/ -v

# Integration tests
pytest tests/integration/ -v

# End-to-end tests
python test_complete_flow.py

# Coverage report
pytest --cov=app tests/
```

### Test Guidelines

- Write tests for new features
- Maintain >80% code coverage
- Use descriptive test names
- Mock external dependencies
- Test both success and error cases

## 📚 Documentation

### Code Documentation

- Use docstrings for functions and classes
- Follow Google docstring format
- Include type hints
- Document complex algorithms

### API Documentation

- Update OpenAPI schemas
- Include request/response examples
- Document error codes
- Add usage examples

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment**:

   - OS and version
   - Python version
   - Docker version
   - Browser (for frontend issues)

2. **Steps to Reproduce**:

   - Clear, numbered steps
   - Expected behavior
   - Actual behavior

3. **Additional Context**:
   - Screenshots or videos
   - Error messages
   - Log files

## ✨ Feature Requests

When requesting features:

1. **Problem Description**: What problem does this solve?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: What other solutions have you considered?
4. **Additional Context**: Any other relevant information

## 🏷️ Release Process

### Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped
- [ ] Release notes prepared
- [ ] Docker images built and tested

## 🤔 Questions?

- **GitHub Discussions**: For general questions and ideas
- **GitHub Issues**: For bugs and feature requests
- **Email**: dev@traveladvisoryagent.com

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Recognition

Contributors will be recognized in:

- README.md contributors section
- Release notes
- Project documentation

Thank you for contributing to the Travel Advisory Agent! 🎉
