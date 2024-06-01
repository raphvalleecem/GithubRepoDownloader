import logging
import os
import pathlib
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import requests
import toml
from colorlog import ColoredFormatter
from requests import RequestException, Session, Response
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)

# Define the colored formatter
formatter = ColoredFormatter(
    '%(log_color)s%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'black,bg_red',
    }
)

# Create a console handler and set the formatter
ch = logging.StreamHandler()
ch.setFormatter(formatter)

# Add the console handler to the logger
logger.addHandler(ch)

CONFIG_FILE_PATH: Path = Path("config.toml")
# Regex's for validating GitHub token
GITHUB_TOKEN_REGEX = re.compile(r'^(gh[ps]_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})$')


def download_repo_zip(user: str, repo_name: str, download_path: Path, session: Session):
    """
    Download a GitHub repository as a ZIP archive.

    :param user: GitHub username of the repository owner.
    :param repo_name: Name of the repository.
    :param download_path: Local path where the ZIP file will be saved.
    :param session: Requests session with authentication.
    :return: The path to the downloaded ZIP file or None if download fails.
    """
    zip_url: str = f"https://github.com/{user}/{repo_name}/archive/master.zip"
    try:
        response: Response = session.get(zip_url, stream=True)
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_error:
        logger.error(f"HTTP Error while downloading {repo_name}. Status code: {http_error.response.status_code}")
        return None
    except requests.exceptions.ConnectionError as connection_error:
        logger.error(f"Connection Error while downloading {repo_name}. Error: {connection_error}")
        return None
    except requests.exceptions.Timeout as timeout_error:
        logger.error(f"Timeout Error while downloading {repo_name}. Error: {timeout_error}")
        return None
    except requests.exceptions.RequestException as exception:
        logger.error(f"Failed to download {repo_name}. Error: {exception}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while downloading {repo_name}. Error: {e}")
        return None

    zip_filename: Path = download_path / f"{repo_name}.zip"
    with open(zip_filename, 'wb') as zip_file:
        shutil.copyfileobj(response.raw, zip_file)
    return zip_filename


def create_session(username: str, github_token: str):
    """
    Create a Requests session with GitHub authentication.

    :param username: GitHub username for authentication.
    :type username: str
    :param github_token: Personal access token (PAT) for GitHub.
    :type github_token: str
    :return: A Requests session with GitHub authentication.
    :rtype: requests.Session
    """
    session: Session = requests.Session()
    session.auth = HTTPBasicAuth(username, github_token)
    return session


def current_milli_time():
    return round(time.time() * 1000)


def download_all_repos(username: str, download_path: Path, github_token: str):
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
    """
    os.makedirs(download_path, exist_ok=True)

    session: Session = create_session(username, github_token)

    api_url: str = f"https://api.github.com/search/repositories?q=user:{username}"
    try:
        response = session.get(api_url)
        response.raise_for_status()
    except RequestException as e:
        logger.error(f"Failed to retrieve repositories. Error: {e}")
        return

    repos = response.json()['items']

    if not github_token:
        logger.warning("No GitHub Token was provided. Falling back to PUBLIC repository only.")
        logger.warning("For PRIVATE repositories, add your GitHub Token.")

    current_time = current_milli_time()
    min_delay = 500
    for repo in repos:
        repo_name = repo.get('name')
        if not repo_name:
            logger.warning(f"Invalid name for repo: {repo}")
            continue
        delta_time = current_milli_time() - current_time
        if delta_time < min_delay:
            sleep_time = (min_delay - delta_time) / 1000
            logger.warning(f"Sleeping for: {sleep_time}")
            time.sleep(sleep_time)
        current_time = current_milli_time()
        zip_filename = download_repo_zip(username, repo_name, download_path, session)
        if zip_filename:
            logger.info(f"{repo_name} downloaded to {zip_filename}")


def config_write(config):
    """
    Write the configuration to a file.

    :param config: Configuration object.
    :type config: dict
    """
    with open(CONFIG_FILE_PATH, "w") as config_file:
        toml.dump(config, config_file)
    logger.info(f"Configuration updated at {CONFIG_FILE_PATH}")


def config_read() -> dict[str, Any]:
    """
    Read configuration from a file. If the file doesn't exist, create it with default values.

    :return: Configuration object.
    :rtype: dict
    """
    default_config = {
        "github_username": "",
        "github_token": "",
        "download_path": str(Path.home() / 'Desktop' / 'GithubRepoDownloader_repos'),
    }

    if not CONFIG_FILE_PATH.is_file():
        with open(CONFIG_FILE_PATH, "w") as config_file:
            toml.dump(default_config, config_file)
            logger.info(f"Default configuration created at {CONFIG_FILE_PATH}")

    with open(CONFIG_FILE_PATH, "r") as config_file:
        config: dict[str, Any] = toml.load(config_file)

    # Validate GitHub username
    if not config["github_username"] or not re.match(r'^[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*$', config["github_username"]):
        logger.error("GitHub username is invalid. Please provide a valid GitHub username.")
        sys.exit(1)

    # Validate GitHub token
    if not validate_github_token(config["github_token"]):
        logger.error("GitHub token is invalid. Please provide a valid GitHub token.")
        sys.exit(1)

    # Validate download path
    download_path = Path(config["download_path"])
    if not download_path.is_absolute():
        logger.error("Download path is invalid. Please provide a valid absolute path.")
        sys.exit(1)

    return config


def validate_github_token(github_token: str) -> bool:
    """
    Validate the GitHub token using the provided regex.

    GitHub token validation regular expressions
    https://gist.github.com/magnetikonline/073afe7909ffdd6f10ef06a00bc3bc88

    :param github_token: GitHub personal access token.
    :type github_token: str
    :return: True if the token is valid, False otherwise.
    :rtype: bool
    """
    return bool(GITHUB_TOKEN_REGEX.match(github_token))


if __name__ == "__main__":
    config: dict[str, Any] = config_read()

    username: str = config["github_username"]
    download_path: Path = Path(config["download_path"])
    github_token: str = config["github_token"]

    isError: bool = False

    if not username:
        logger.error("GitHub username is empty. Please provide a valid GitHub username.")
        isError = True

    if not download_path or not download_path.is_absolute():
        logger.error("Download path is invalid. Please provide a valid absolute path.")
        isError = True

    if not validate_github_token(github_token):
        logger.error("GitHub token is invalid. Please provide a valid GitHub token.")
        isError = True

    if isError:
        sys.exit(1)

    logger.info("Download Started")
    download_all_repos(username, download_path, github_token)
    logger.info("Download Ended")
