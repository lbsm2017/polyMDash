# Contributing to Polymarket Dashboard

Thank you for your interest in contributing to the Polymarket Dashboard! We welcome contributions from everyone. By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue on GitHub with the following information:
- A clear, descriptive title
- Steps to reproduce the issue
- Expected behavior
- Actual behavior
- Your environment (OS, Python version, etc.)
- Any relevant logs or error messages

### Suggesting Features

We welcome feature suggestions! Please create an issue with:
- A clear, descriptive title
- Detailed description of the proposed feature
- Why this feature would be useful
- Any relevant examples or mockups

### Contributing Code

1. **Fork the repository** and create your branch from `main`.
2. **Set up your development environment**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # if available
   ```
3. **Make your changes** following our coding standards.
4. **Write tests** for your changes.
5. **Run the tests** to ensure everything works:
   ```bash
   pytest tests/
   ```
6. **Update documentation** if necessary.
7. **Commit your changes** with a clear commit message.
8. **Push to your fork** and submit a pull request.

### Pull Request Process

1. Ensure your PR includes a clear description of the changes.
2. Reference any related issues.
3. Make sure all tests pass.
4. Update the README.md if your changes affect usage.
5. Your PR will be reviewed by maintainers, who may request changes.

## Development Setup

### Prerequisites
- Python 3.9+
- pip

### Installation
```bash
git clone https://github.com/your-username/polymarket-dashboard.git
cd polymarket-dashboard
pip install -r requirements.txt
```

### Running Tests
```bash
pytest tests/
```

### Code Style

We follow PEP 8 for Python code style. Please ensure your code:
- Uses 4 spaces for indentation
- Has proper docstrings
- Passes flake8 linting (if configured)

### Testing

- Write unit tests for new functionality
- Ensure all existing tests pass
- Aim for good test coverage

### Documentation

- Update docstrings for any modified functions/classes
- Update README.md for significant changes
- Add comments for complex logic

## Areas for Contribution

- Bug fixes
- Feature implementations
- Performance improvements
- Documentation improvements
- Test coverage enhancements
- UI/UX improvements

## Getting Help

If you need help, feel free to:
- Open an issue on GitHub
- Join our community discussions
- Contact the maintainers

Thank you for contributing to Polymarket Dashboard!