import os
import shutil
from os.path import expanduser

import requests


def download_repo_zip(user, repo_name, downloadpath):
    zip_url = f"https://github.com/{user}/{repo_name}/archive/master.zip"
    response = requests.get(zip_url, stream=True)
    zip_filename = f"{downloadpath}/{repo_name}.zip"

    with open(zip_filename, 'wb') as zip_file:
        shutil.copyfileobj(response.raw, zip_file)

    return zip_filename


def download_all_repos(username, download_path):
    # Create the download directory if it doesn't exist
    os.makedirs(download_path, exist_ok=True)

    # Get the list of repositories for the given user
    api_url = f"https://api.github.com/users/{username}/repos"
    response = requests.get(api_url)
    repos = response.json()

    # Download each repository as a zip file
    for repo in repos:
        repo_name = repo['name']
        print(f"Downloading {repo_name}...")
        zip_filename = download_repo_zip(username, repo_name, download_path)
        print(f"{repo_name} downloaded to {zip_filename}")


if __name__ == "__main__":
    username = "Tranzitron"
    home = expanduser("~")
    download_path = fr"{home}\Desktop\{username}_repos"

    download_all_repos(username, download_path)
