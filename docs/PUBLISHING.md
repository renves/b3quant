# Publishing Guide - PyBovespa

## Prerequisites

### 1. Create a PyPI Account

1. Go to https://pypi.org/account/register/
2. Complete the registration
3. Verify your email

### 2. Configure 2FA (Required)

1. PyPI → Account Settings → Two factor authentication
2. Use an app like Google Authenticator
3. Save the recovery codes

### 3. Generate a PyPI API Token

1. PyPI → Account Settings → API tokens
2. Click "Add API token"
3. Name: `pybovespa-github-actions`
4. Scope: `Entire account` (or specific to pybovespa after the first upload)
5. Copy the token (starts with `pypi-`)

### 4. Add the Token to GitHub

1. GitHub repo → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `PYPI_API_TOKEN`
4. Value: Paste the PyPI token
5. Click "Add secret"

## Release Process with Release-Please

### How It Works

Release-please automates the entire process:
- Automatically creates release PRs
- Updates the CHANGELOG.md
- Increments the version in `__init__.py`
- Creates Git tags
- Publishes to PyPI

### Conventional Commits

Use commits in the following format:
```
feat: add new feature
fix: fix bug
docs: update documentation
chore: maintenance tasks
refactor: code refactoring
test: add or update tests
```

Examples:
```bash
git commit -m "feat: add daily download support"
git commit -m "fix: memory leak in parser"
git commit -m "docs: update README examples"
```

### Release Workflow

1. **Develop normally**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin main
   ```

2. **Release-Please automatically creates a PR**
   - After the push, release-please analyzes the commits
   - Creates/updates a PR named "chore: release X.Y.Z"
   - The PR contains:
     - Updated CHANGELOG
     - Updated version in `__init__.py`
     - Release tag

3. **Review and Merge the PR**
   - Review the generated CHANGELOG
   - Make adjustments if necessary
   - Merge the PR when ready

4. **Automatic Publishing**
   - When the PR is merged, GitHub Actions:
     - Creates the Git tag
     - Builds the package
     - Publishes it to PyPI automatically

## Manual Publishing (Alternative)

### 1. Prepare the Environment

```bash
cd pybovespa
python -m pip install --upgrade pip build twine
```

### 2. Update the Version

Edit `pybovespa/__init__.py`:
```python
__version__ = "0.2.0"  # or the new version
```

### 3. Update the CHANGELOG

Add the changes to `CHANGELOG.md`:
```markdown
## [0.2.0] - 2024-12-21

### Added
- New feature X

### Fixed
- Bug Y
```

### 4. Build the Package

```bash
python -m build
```

This creates:
- `dist/pybovespa-0.2.0.tar.gz`
- `dist/pybovespa-0.2.0-py3-none-any.whl`

### 5. Upload to TestPyPI (Optional)

Test first:
```bash
python -m twine upload --repository testpypi dist/*
```

Install from TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ pybovespa
```

### 6. Upload to PyPI

```bash
python -m twine upload dist/*
```

When prompted:
- Username: `__token__`
- Password: Your PyPI token (starts with `pypi-`)

### 7. Create a GitHub Release

```bash
git tag v0.2.0
git push origin v0.2.0
```

On GitHub:
1. Releases → Draft a new release
2. Choose tag: v0.2.0
3. Title: Release 0.2.0
4. Description: Copy from CHANGELOG
5. Publish release

## Post-Publication Verification

1. **Check on PyPI**
   - https://pypi.org/project/pybovespa/

2. **Test Installation**
   ```bash
   pip install pybovespa
   python -c "import pybovespa; print(pybovespa.__version__)"
   ```

3. **Test Functionality**
   ```python
   from pybovespa import PyBovespa
   pyb = PyBovespa()
   # Basic test...
   ```

## Troubleshooting

### Error: "File already exists"
- A version with this number already exists on PyPI
- Increment the version and try again

### Error: "Invalid credentials"
- Incorrect or expired token
- Generate a new token on PyPI

### Error: "Package name already taken"
- The name `pybovespa` is already in use
- Choose another name (e.g. `pybovespa-data`)

### Release-Please did not create a PR
- Check if commits follow conventional commits
- Commits must be on the `main` branch
- Check GitHub Actions logs

## Best Practices

1. **Always test before publishing**
   - Run `uv run pytest`
   - Test in a clean environment

2. **Semantic Versioning**
   - MAJOR: breaking API changes
   - MINOR: backward-compatible new features
   - PATCH: bug fixes

3. **Detailed CHANGELOG**
   - Document all changes
   - Use categories: Added, Changed, Deprecated, Removed, Fixed, Security

4. **Up-to-date Documentation**
   - Update README when needed
   - Keep examples working

## Recommended Workflow

For continuous development:

```bash
# 1. Create a feature branch
git checkout -b feature/new-feature

# 2. Develop and commit using conventional commits
git add .
git commit -m "feat: add feature X"

# 3. Push and create a PR
git push origin feature/new-feature

# 4. After merging into main, release-please handles the rest!
```

## Useful Links

- [PyPI](https://pypi.org/)
- [TestPyPI](https://test.pypi.org/)
- [Release-Please Docs](https://github.com/googleapis/release-please)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
