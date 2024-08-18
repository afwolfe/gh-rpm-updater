#!/usr/bin/env python3
import os
import logging
import re
import subprocess
from typing import List, Optional

from github import Auth, Github
from github.GitRelease import GitRelease
import yaml

logging.getLogger().setLevel(logging.INFO)


def version_from_tag(tag: str, version_tag_prefix: str = "v") -> str:
    return (
        tag[len(version_tag_prefix) :]
        if tag[0 : len(version_tag_prefix)] == version_tag_prefix
        else tag
    )


def get_rpm_version(package_name: str) -> Optional[str]:
    try:
        return subprocess.check_output(
            ["rpm", "-q", "--qf", "%{VERSION}", package_name]
        ).decode("utf-8")
    except subprocess.CalledProcessError:
        return None


def get_asset_urls(release: GitRelease, content_types, regex_filter=None) -> List[str]:
    downloaded_assets = []
    for asset in release.assets:
        if asset.content_type in content_types and (
            not regex_filter or re.match(regex_filter, asset.name)
        ):
            url = asset.browser_download_url
            downloaded_assets.append(url)
    return downloaded_assets


def get_latest_release(github: Github, repo: str) -> GitRelease:
    return github.get_repo(repo).get_latest_release()


def read_config() -> dict:
    xdg_config_home = os.path.expanduser(os.environ.get("XDG_CONFIG_HOME", "~/.config"))
    config_dir = os.path.join(xdg_config_home, "gh-rpm")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "config.yml")
    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            yaml.dump({"repositories": []}, f)
    return yaml.safe_load(open(config_path, "r"))


def get_github_token(config: dict) -> Optional[str]:
    return os.environ.get("GITHUB_TOKEN", config.get("github_token", None))


def get_github(config: dict) -> Github:
    github_token = get_github_token(config)
    if github_token:
        logging.debug("Creating Github instnace with GitHub token")
        return Github(auth=Auth.Token(github_token)) if github_token else Github()
    else:
        logging.warn(
            "Creating Github instance without GitHub token, you may encounter rate-limiting errors."
        )
        return Github()


def is_current_version_installed(
    rpm_package: str, release_tag: str, version_tag_prefix: str
) -> bool:
    release_version = version_from_tag(release_tag, version_tag_prefix)
    rpm_version = get_rpm_version(rpm_package)
    return release_version == rpm_version


def install_packages(install_cmd: List[str], packages_to_install: List[str]):
    if len(packages_to_install) > 0:
        try:
            subprocess.run(install_cmd + packages_to_install, check=True)
        except subprocess.CalledProcessError as e:
            raise Exception("Error while installing packages", e)


def main():
    config = read_config()
    repos = config["repositories"]
    install_cmd = config.get("install_cmd", ["sudo", "dnf", "install"])
    github = get_github(config)
    packages_to_install = []
    if len(repos) == 0:
        logging.info("No repositories configured, exiting.")
        exit(0)
    for repo in repos:
        logging.info(f"Checking {repo['repo']}")
        release = get_latest_release(github, repo["repo"])
        package_name = repo.get("package", repo["repo"].split("/")[-1])
        version_tag_prefix = repo.get("version_tag_prefix", "v")
        if is_current_version_installed(
            package_name, release.tag_name, version_tag_prefix
        ):
            logging.info(f"{package_name} is already up-to-date at {release.tag_name}")
            continue
        regex_filter = repo.get("filter", None)
        content_types = repo.get(
            "content_types",
            ["application/x-rpm", "application/x-redhat-package-manager"],
        )

        packages_to_install += get_asset_urls(
            release, content_types=content_types, regex_filter=regex_filter
        )
    install_packages(install_cmd, packages_to_install=packages_to_install)


if __name__ == "__main__":
    main()
