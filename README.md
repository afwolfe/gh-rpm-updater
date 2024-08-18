# GitHub RPM Updater

A Python script to update RPM packages from GitHub that do not have a corresponding RPM repo.

## Usage

Create a config file at `${XDG_CONFIG_HOME}/.config/gh-rpm/config.yml` with the following structure:

```yaml
repositories:
  - repo: rclone/rclone # The name of the GitHub repo to search releases for.
    package:  rclone # The name of the installed RPM package - defaults to the repo name if not specified
    filter: '.*amd64.*' # An optional RegEx filter, useful for ensuring you only download and install the version for your distro/architecture.
    content_types: # An optional list of content types to filter on, will default to "application/x-rpm" and "application/x-redhat-package-manager" if not specified.
github_token: # Am optional GitHub personal access token with read permissions for the repo(s) specified above. It can also be set via the "GITHUB_TOKEN" environment variable.
```

Install Python dependencies and run, optionally passing in a GitHub token from the environment:

```shell
poetry install
export GITHUB_TOKEN="..."
poetry run gh-rpm
```
