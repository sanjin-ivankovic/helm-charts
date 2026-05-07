# Contributing to Homelab Helm Charts

Thank you for your interest in contributing! This project is a portfolio
demonstration of Helm chart development best practices. While it's primarily a
personal project, I welcome contributions that improve documentation, fix bugs,
or enhance the overall quality.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Contribution Workflow](#contribution-workflow)
- [Style Guidelines](#style-guidelines)
- [Commit Message Conventions](#commit-message-conventions)

## Code of Conduct

This project follows a simple principle: **Be respectful and constructive**.
We're all here to learn and improve.

## How Can I Contribute?

### Reporting Issues

If you find a bug, documentation error, or have a suggestion:

1. **Check existing issues** to avoid duplicates
2. **Create a new issue** with:
   - Clear, descriptive title
   - Detailed description of the problem or suggestion
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Environment details (if applicable)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- **Use case**: Why this enhancement would be useful
- **Proposed solution**: How you envision it working
- **Alternatives**: Any alternative approaches you've considered

### Pull Requests

I welcome pull requests for:

- Documentation improvements
- Bug fixes
- Chart enhancements
- New chart additions
- CI/CD improvements

## Development Setup

### Prerequisites

- `helm` v4.x
- `kubectl` (for template validation)
- `yamllint`
- `markdownlint-cli2`
- `pre-commit`

### Local Environment

```bash
# Clone the repository
git clone <repo-url>
cd helm-charts

# Install pre-commit hooks
make setup

# Lint a chart
make lint CHART=searxng

# Test chart templates
make test CHART=searxng

# Validate (lint + test)
make validate CHART=searxng

# Validate all charts
make validate-all
```

## Contribution Workflow

1. **Fork the repository**

2. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow existing patterns and conventions
   - Update documentation if needed
   - Test your changes locally

4. **Validate your changes**

   ```bash
   # Lint and test the chart
   make validate CHART=<chart-name>

   # Run all linters
   make lint-all
   ```

5. **Commit with meaningful messages** (see [Commit
   Conventions](#commit-message-conventions))

6. **Push to your fork**

   ```bash
   git push origin feature/your-feature-name
   ```

7. **Open a Pull Request**
   - Reference any related issues
   - Describe what changed and why
   - Include before/after template diffs if applicable

## Style Guidelines

### Chart Structure

Every chart must follow this structure:

```text
charts/<chart-name>/
├── Chart.yaml          # Chart metadata (apiVersion: v2)
├── values.yaml         # Default values with @section/@param annotations
├── templates/          # Kubernetes manifest templates
│   ├── _helpers.tpl    # Template helpers
│   ├── deployment.yaml
│   ├── service.yaml
│   └── ...
└── README.md           # Chart documentation
```

### Chart.yaml Standards

- `apiVersion: v2` (Helm 3)
- `type: application`
- `kubeVersion` constraint required
- Semantic versioning for `version` and `appVersion`
- `maintainers`, `keywords`, `home`, and `sources` populated

### Values.yaml Standards

- Follow the standardized section order documented in
  [docs/values_yaml_standard_order.md](docs/values_yaml_standard_order.md)
- Use `@section` and `@param` annotations for documentation
- See [docs/charts.md](docs/charts.md) for format standards

### Documentation

- Use Markdown for all documentation
- Include code examples where helpful
- Update the main README if adding significant features
- Keep line length reasonable (~80 characters max)
- Use proper headings hierarchy

## Commit Message Conventions

Follow conventional commit format:

```text
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature or chart
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `chore`: Maintenance tasks
- `test`: Testing improvements
- `ci`: CI/CD changes
- `build`: Build system changes

### Examples

```text
feat(searxng): add persistence volume support

- Add PVC template for search history
- Add configurable storageClass in values.yaml
- Update README with persistence section
```

```text
fix(cloudflared): correct service port mapping

The target port did not match the container port,
causing connection timeouts.
```

## Testing Requirements

Before submitting a PR:

1. **Lint the chart**

   ```bash
   make lint CHART=<chart-name>
   ```

2. **Test template rendering**

   ```bash
   make test CHART=<chart-name>
   ```

3. **Update documentation** if you changed:
   - Chart values
   - Chart structure
   - Prerequisites

## License

By contributing, you agree that your contributions will be licensed under the
MIT License.
