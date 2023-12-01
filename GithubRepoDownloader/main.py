import logging
import os
import shutil
from http import HTTPStatus
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_repo_zip(user, repo_name, download_path, session):
    """
    Download a GitHub repository as a ZIP archive.

    :param user: GitHub username of the repository owner.
    :param repo_name: Name of the repository.
    :param download_path: Local path where the ZIP file will be saved.
    :param session: Requests session with authentication.
    :return: The path to the downloaded ZIP file or None if download fails.
    """
    zip_url = f"https://github.com/{user}/{repo_name}/archive/master.zip"
    response = session.get(zip_url, stream=True)

    if response.status_code == requests.codes.ok:
        zip_filename = download_path / f"{repo_name}.zip"
        with open(zip_filename, 'wb') as zip_file:
            shutil.copyfileobj(response.raw, zip_file)
        return zip_filename
    else:
        logger.error(f"Failed to download {repo_name}. Status code: {response.status_code}")
        return None


def create_session(username, github_token):
    """
    Create a Requests session with GitHub authentication.

    This function takes a GitHub username and a personal access token
    (PAT) and returns a Requests session configured with HTTP basic
    authentication using the provided credentials.

    :param username: GitHub username for authentication.
    :type username: str
    :param github_token: Personal access token (PAT) for GitHub.
    :type github_token: str
    :return: A Requests session with GitHub authentication.
    :rtype: requests.Session
    """
    session = requests.Session()
    session.auth = HTTPBasicAuth(username, github_token)
    return session


def download_all_repos(username, download_path, github_token):
    """
    Download all repositories of a GitHub user as ZIP archives.

    This function takes a GitHub username, a local directory path for
    saving downloaded ZIP files, and a personal access token (PAT) for
    GitHub authentication. It creates a session, retrieves the user's
    repositories using the GitHub API, and downloads each repository
    as a ZIP archive.

    :param username: GitHub username of the target user.
    :type username: str
    :param download_path: Local path to save downloaded ZIP files.
    :type download_path: pathlib.Path
    :param github_token: Personal access token (PAT) for GitHub.
    :type github_token: str
    :return: None
    :rtype: None
    """
    os.makedirs(download_path, exist_ok=True)

    session = create_session(username, github_token)

    api_url = f"https://api.github.com/search/repositories?q=user:{username}"
    response = session.get(api_url)

    if response.status_code == HTTPStatus.OK:
        repos = response.json()['items']

        for repo in repos:
            repo_name = repo['name']
            zip_filename = download_repo_zip(username, repo_name, download_path, session)
            if zip_filename:
                logger.info(f"{repo_name} downloaded to {zip_filename}")
    else:
        logger.error(f"Failed to retrieve repositories. Status code: {response.status_code}")


if __name__ == "__main__":
    username = "raphvalleecem"
    download_path = Path.home() / 'Desktop' / f"{username}_repos"
    github_token = ""

    download_all_repos(username, download_path, github_token)
