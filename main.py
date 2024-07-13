#!/usr/bin/env python3
import os
import re
import subprocess
from typing import List, Optional

from github import Auth, Github, GitRelease, GitReleaseAsset
from pySmartDL import SmartDL
import requests
import yaml

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", None)
if GITHUB_TOKEN:
  github = Github(auth=Auth.Token(GITHUB_TOKEN))
else:
  github = Github()

def version_from_tag(tag: str) -> str:
  return tag[1:] if tag[0] == "v" else tag
  
def get_rpm_version(package_name: str) -> Optional[str]:
  try:
    return subprocess.check_output(["rpm", "-q", "--qf", "%{VERSION}", package_name]).decode('utf-8')
  except subprocess.CalledProcessError:
    return None  

def download_assets(release: GitRelease, outdir="downloads", content_types=None, regex_filter=None) -> List[str]:
  downloaded_assets = []
  asset: GitReleaseAsset
  if not content_types:
    content_types = ["application/x-rpm", "application/x-redhat-package-manager"]
  for asset in release.assets:
      if asset.content_type in content_types and (not regex_filter or re.match(regex_filter, asset.name)):
          url = asset.browser_download_url
          filename = os.path.basename(url)
          if not os.path.exists(outdir):
            os.mkdir(outdir)
          outfile = os.path.join(outdir, filename)
          
          print("Downloading", filename)
          obj = SmartDL(url, outfile)
          obj.start()
          downloaded_assets.append(obj.get_dest())
  return downloaded_assets

def get_latest_release(repo: str) -> GitRelease:
  return github.get_repo(repo).get_latest_release()


def read_config() -> dict:
  with open("config.yml", "r") as file:
    return yaml.load(file, Loader=yaml.FullLoader)

def is_current_version_installed(rpm_package: str, release_tag: str) -> bool:
  release_version = version_from_tag(release_tag)
  rpm_version = get_rpm_version(rpm_package)
  return release_version == rpm_version

if __name__ == "__main__":
  repos = read_config()["repositories"]
  packages_to_install = []
  for repo in repos:
    print(repo["repo"])
    release = get_latest_release(repo["repo"])
    package_name = repo.get("package", repo["repo"].split('/')[-1])
    if is_current_version_installed(package_name, release.tag_name):
      print(f"{package_name} is already installed at {release.tag_name}")
      continue
    regex_filter = repo.get("filter", None)
    content_types = repo.get("content_types", None)
    packages_to_install += download_assets(release, content_types=content_types, regex_filter=regex_filter)
  if len(packages_to_install) > 0:
    subprocess.run(["sudo", "dnf", "install"] + packages_to_install, check=True)