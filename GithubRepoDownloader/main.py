import os
import shutil
from os.path import expanduser

import requests


def download_repo_zip(user, repo_name, download_path, token):
    zip_url = f"https://github.com/{user}/{repo_name}/archive/master.zip"
    headers = {'Authorization': f'token {token}'}
    response = requests.get(zip_url, headers=headers, stream=True)

    if response.status_code == 200:
        zip_filename = f"{download_path}/{repo_name}.zip"
        with open(zip_filename, 'wb') as zip_file:
            shutil.copyfileobj(response.raw, zip_file)
        return zip_filename
    else:
        print(f"Failed to download {repo_name}. Status code: {response.status_code}")
        return None


def download_all_repos(username, download_path, github_token):
    # Create the download directory if it doesn't exist
    os.makedirs(download_path, exist_ok=True)

    # Get the list of repositories for the given user
    api_url = f"https://api.github.com/user/repos"
    headers = {'Authorization': f'token {github_token}'}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        repos = response.json()

        # Download each repository as a zip file
        for repo in repos:
            repo_name = repo['name']
            print(f"Downloading {repo_name}...")
            zip_filename = download_repo_zip(username, repo_name, download_path, github_token)
            if zip_filename:
                print(f"{repo_name} downloaded to {zip_filename}")
            else:
                print(f"Failed to download {repo_name}.")
    else:
        print(f"Failed to retrieve repositories. Status code: {response.status_code}")


if __name__ == "__main__":
    username = "Tranzitron"
    home = expanduser("~")
    download_path = fr"{home}\Desktop\{username}_repos"
    github_token = "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"

    download_all_repos(username, download_path, github_token)
