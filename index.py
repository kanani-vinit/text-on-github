import json
import os
import sys
import subprocess

import requests

from common import charMatrix
from dating import sunday_at_start
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

SKIP_WEEKS_FROM_FRONT = 2
SKIP_DAYS_FROM_ABOVE = 1
COMMIT_PER_DAY_FOR_HIGHLIGHTED = 5
COMMIT_PER_DAY_FOR_SHADOW = 1

OWNER = "kanani-vinit"
EMAIL = "kananivinitrocking@gmail.com"
REPO_NAME = "text-on-github"
CREATE_ENDPOINT = "https://api.github.com/user/repos"
DELETE_ENDPOINT = "https://api.github.com/repos/{owner}/{repo}"

TOKEN = os.getenv("GITHUB_TOKEN")


def get_text_input():
    if len(sys.argv) > 1:
        return sys.argv[1]
    else:
        return input("Enter the text string: ")


def construct_printing_matrix(text_input):
    m, n = len(charMatrix['a']), len(charMatrix['a'][0])

    spaceBetweenChars = 2

    printingMatrix = [[] for i in range(m)]

    for ch in text_input:
        charMatrixForCh = charMatrix.get(ch, charMatrix['?'])
        for i in range(m):
            printingMatrix[i].extend(charMatrixForCh[i])
        for i in range(spaceBetweenChars):
            for j in range(m):
                printingMatrix[j].append(' ')

    for i in range(m):
        print(''.join(printingMatrix[i]))

    return printingMatrix


def get_commit_dates(printingMatrix, start_date):
    commitDates = []

    for j in range(len(printingMatrix[0])):
        referenceDate = start_date + timedelta(days=SKIP_DAYS_FROM_ABOVE)
        for i in range(len(printingMatrix)):
            if printingMatrix[i][j] == '*':
                commitDates.append(referenceDate)
            referenceDate += timedelta(days=1)
        start_date += timedelta(weeks=1)
    return commitDates


def run_git_command(cmd):
    result = subprocess.run(cmd, shell=True, check=True, text=True)
    return result


def do_the_commits(commitDates, commitPerDay=1):
    for commitDate in commitDates:
        for i in range(commitPerDay):
            formatted_date = commitDate.strftime("%a %b %d %H:%M %Y %z")
            formatted_date_with_timezone = formatted_date + " +0700"
            cmd = f'GIT_COMMITTER_DATE="{formatted_date_with_timezone}" GIT_AUTHOR_DATE="{formatted_date_with_timezone}" git commit --allow-empty -m "committing on {formatted_date_with_timezone}"'
            run_git_command(cmd)

    cmd = 'git push origin main'
    run_git_command(cmd)


def run_command(command):
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with error: {e.output}")
        raise


def cleanup_repo(new_branch_name='temp-branch', commit_message='Initial commit', force_push=False):
    run_command(f'git checkout --orphan {new_branch_name}')
    run_command(f"git config --local user.name {OWNER}")
    run_command(f"git config --local user.email {EMAIL}")
    run_command('git add .')
    run_command(f'git commit -m "{commit_message}"')

    if force_push:
        main_branch = 'main'  # Change this if your main branch is named differently
        run_command(f'git branch -M {new_branch_name} {main_branch}')
        run_command(f'git push -f origin {main_branch}')


def get_contributions():
    query = """
            query($userName:String!) {
              user(login: $userName){
                contributionsCollection {
                  contributionCalendar {
                    totalContributions
                    weeks {
                      contributionDays {
                        contributionCount
                        date
                      }
                    }
                  }
                }
              }
            }
            """

    variables = {
        "userName": OWNER
    }

    body = {
        "query": query,
        "variables": variables
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }

    response = requests.post("https://api.github.com/graphql", headers=headers, json=body)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching commits: {response.text}")
        return None


def find_highest_contribution(contributions):
    highest_contributed_day = None
    highest_contributions = 0

    for week in contributions["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for day in week["contributionDays"]:
            if day["contributionCount"] > highest_contributions:
                highest_contributions = day["contributionCount"]
                highest_contributed_day = day["date"]

    return highest_contributed_day, highest_contributions


def create_local_repo():
    run_command('rm -rf .git')
    run_command('git init')
    run_command(f"git config --local user.name {OWNER}")
    run_command(f"git config --local user.email {EMAIL}")
    run_command('git add .')
    run_command('git commit -m "Initial commit"')
    run_command('git branch -M main')
    run_command(f'git remote add origin https://github.com/{OWNER}/{REPO_NAME}.git')
    run_command(f"git remote set-url origin https://{TOKEN}@github.com/{OWNER}/{REPO_NAME}.git")
    print("Git repo initialized successfully")


def create_remote_repo(delete_existing=False):
    exists = False
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    # check if repo already exists
    response = requests.get(f"https://api.github.com/repos/{OWNER}/{REPO_NAME}", headers=headers)
    if response.status_code == 200:
        exists = True
        print("Remote repo already exists")
        if not delete_existing:
            return

    else:
        print("Remote repo does not exist. Creating...")

    if delete_existing and exists:
        try:
            response = requests.delete(f"https://api.github.com/repos/{OWNER}/{REPO_NAME}", headers=headers)
            response.raise_for_status()
            print("Remote repo deleted successfully")
        except Exception as e:
            print(f"Error deleting remote repo: {e}")
            raise

    data = {
        "name": REPO_NAME,
        "description": "Text on GitHub HeatMap",
        "private": False
    }

    try:
        response = requests.post(CREATE_ENDPOINT, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        print("Remote repo created successfully")
    except requests.exceptions.HTTPError as e:
        print(f"Error creating remote repo: {e}")
        raise


def main():
    global COMMIT_PER_DAY_FOR_HIGHLIGHTED, COMMIT_PER_DAY_FOR_SHADOW

    create_local_repo()
    create_remote_repo(delete_existing=True)
    cleanup_repo(force_push=True)

    contributions = get_contributions()
    highest_contributed_day = find_highest_contribution(contributions)

    COMMIT_PER_DAY_FOR_HIGHLIGHTED = highest_contributed_day[1] * 3
    COMMIT_PER_DAY_FOR_SHADOW = highest_contributed_day[1]

    text_input = get_text_input().lower()

    printing_matrix = construct_printing_matrix(text_input)
    commit_dates_dark = get_commit_dates(printing_matrix, sunday_at_start + timedelta(weeks=SKIP_WEEKS_FROM_FRONT))
    commit_dates_shadow = get_commit_dates(printing_matrix,
                                           sunday_at_start + timedelta(weeks=SKIP_WEEKS_FROM_FRONT - 1))

    do_the_commits(commit_dates_dark, COMMIT_PER_DAY_FOR_HIGHLIGHTED)
    do_the_commits(commit_dates_shadow, COMMIT_PER_DAY_FOR_SHADOW)


if __name__ == '__main__':
    main()
