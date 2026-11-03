# Contributing to craft-packages

Welcome to craft-packages! We welcome community contributions, bug reports, and suggestions.

Before contributing code, please review and sign the [Canonical Contributor License Agreement](https://ubuntu.com/legal/contributors).
All participants must abide by the [Ubuntu Code of Conduct](https://ubuntu.com/community/docs/ethos/code-of-conduct).

## Setting up development environment

1. Fork and clone the repository:

    ```bash
    git clone https://github.com/<username>/craft-packages.git
    cd craft-packages
    git remote add upstream https://github.com/canonical/craft-packages.git
    ```

2. Set up the development environment using `uv`:
    ```bash
    make setup
    ```

## Development workflow

- **Format code**:
    ```bash
    make format
    ```
- **Run linters**:
    ```bash
    make lint
    ```
- **Run fast tests**:
    ```bash
    make test-fast
    ```
- **Run full tests**:
    ```bash
    make test
    ```
- **Build documentation**:
    ```bash
    make docs
    ```

## Submitting changes

- Branch names should be descriptive (e.g. `work/<description>` or `work/<ticket>-<description>`).
- Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
- Open a pull request against `main` at https://github.com/canonical/craft-packages/pulls.
