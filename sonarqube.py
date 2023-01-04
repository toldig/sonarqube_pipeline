#!/usr/bin/python3

import json
import os
import csv
from time import strptime
import argparse
import requests

USERNAME = 'admin'
PASSWORD = 'admin'
SONAR_URL = 'http://localhost:9000'
PROJECTS_URL = '{SONAR_URL}/api/projects/search'
PROJECT_ANALYSIS_URL = '{SONAR_URL}/api/project_analyses/search'
ISSUES_URL = '{SONAR_URL}/api/issues/search'
PROJECT_BRANCHES_URL = '{SONAR_URL}/api/project_branches/list'
DEBUG = False
START_CREATED_AFTER = '2000-01-01T00:00:00+0000'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'

CSV_FILE = 'sonarscan.csv'
CSV_HEADER = {0: 'project',
              1: 'severity',
              2: 'type',
              3: 'rule',
              4: 'component',
              5: 'line',
              6: 'message',
              7: 'author',
              8: 'status',
              9: 'effort',
              10: 'creation_date',
              11: 'key',
              12: 'tags'}

# pylint: disable= too-few-public-methods, too-many-instance-attributes
class Issue:
    '''
    Class to store issues
    '''
    def __init__(self, data: dict):
        self.self_initialized = True
        self.key = set_value(data, 'key')
        if self.key is None:
            self.self_initialized = False
        self.rule = set_value(data, 'rule')
        self.severity = set_value(data, 'severity')
        self.component = set_value(data, 'component')
        self.project = set_value(data, 'project')
        self.line = set_value(data, 'line')
        self.status = set_value(data, 'status')
        self.message = set_value(data, 'message')
        self.effort = set_value(data, 'effort')
        self.debt = set_value(data, 'debt')
        self.author = set_value(data, 'author')
        self.tags = set_value(data, 'tags')
        self.creation_date = set_value(data, 'creationDate')
        self.update_date = set_value(data, 'updateDate')
        self.close_date = set_value(data, 'closeDate')
        self.type = set_value(data, 'type')
        self.scope = set_value(data, 'scope')
        self.quick_fix_available = set_value(data, 'quickFixAvailable')
        if self.creation_date is not None:
            self.self_timestamp = strptime(self.creation_date, TIME_FORMAT)
        else:
            self.self_timestamp = None
            self.self_initialized = False

    def get_property(self, property_name: str) -> str:
        '''
        Returns the value of a given property if it exists
        Returns empty string if the property does not exist
        '''
        for attribute, value in self.__dict__.items():
            if attribute == property_name:
                return str(value)
        return ''


class SonarException(Exception):
    '''
    SonarException class to create custom exceptions
    '''
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        return self.message


def set_value(data: dict, key: str):
    '''
    Return the value of a given key from a given dictionary
    Returns None if the key does not exist in the dictionary
    '''
    if not isinstance(data, dict):
        return None
    if key in data.keys():
        return data[key]
    return None


def get_properties_of_class(obj):
    '''
    Returns the list of the properties of any object
    '''
    properties = []
    for name, _ in vars(obj).items():
        if not name.startswith('self'):
            properties.append(name)
    return properties


def serialize_issues(issues: dict):
    '''
    Builds a massive dictionary out of a list of issues
    so it can be dumped to a file
    '''
    serialized = {}
    properties = None
    for issue in issues:
        serialized[issue] = {}
        if properties is None:
            properties = get_properties_of_class(issues[issue])
        for name, value in vars(issues[issue]).items():
            if name in properties:
                serialized[issue][name] = value
    return serialized


def make_request(api_url: str, user: str, pwd: str, params=None) -> dict:
    '''
    Makes a request to Sonarqube API with parameters if they are given
    '''
    try:
        if params is None:
            response = requests.get(api_url, auth=(user, pwd))
        else:
            response = requests.get(api_url, auth=(user, pwd), params=params)
        if response.status_code == 200:
            return response.json()
        raise SonarException(f'GET {api_url} response status_code {response.status_code}')
    except Exception as exc:
        raise SonarException(f'make_request {type(exc)}: {exc}')


def get_item(data: dict, keys: list):
    '''
    Gets value from a nested dictionary
    '''
    current_data = data
    for key in keys:
        if not isinstance(current_data, dict):
            raise SonarException('get_item Exception: item is not dictionary')
        if key not in current_data.keys():
            raise SonarException(f'get_item Exception: {key} is not in {current_data.keys()}')
        current_data = current_data[key]
    return current_data


def get_issues(args: dict, project: str):
    '''
    Download all the issues from Sonarqube for a given project
    Runs until new issues are found
    Returns a dictionary with all the issues
    '''
    all_issues = {}
    created_after = START_CREATED_AFTER
    created_after_timestamp = strptime(START_CREATED_AFTER, TIME_FORMAT)
    new_found = True
    all_issues = {}
    # for _ in range(10):
    while new_found:
        new_found = False
        issues = make_request(args['issues_url'],
                              args['user'],
                              args['password'],
                              {'componentKeys': project,
                               'createdAfter': created_after,
                               's': 'CREATION_DATE',
                               'ps': 500})

        if issues is None:
            raise SonarException(f'Could not get the list of issues for {project} project')

        print(f"  Issues found {len(issues['issues'])}")
        for index in range(len(issues['issues'])):
            current_issue = Issue(issues['issues'][index])
            if current_issue.self_initialized:
                if current_issue.key not in all_issues:
                    all_issues[current_issue.key] = current_issue
                    new_found = True
                    if current_issue.self_timestamp > created_after_timestamp:
                        created_after_timestamp = current_issue.self_timestamp
                        created_after = current_issue.creation_date

    print(f'  {len(all_issues)} unique issues found')
    # pylint: disable= broad-except
    if args['debug']:
        try:
            file_name = f'{project}.json'
            if os.path.exists(file_name):
                os.remove(file_name)
            with open(file_name, 'w') as tmp_file:
                serialized = serialize_issues(all_issues)
                tmp_file.write(json.dumps(serialized, indent=2))
            print(f'  {file_name} saved with {len(all_issues)} unique issues')
        except Exception as exc:
            print(f'  get_issues save file {type(exc)}: {exc}')
    return all_issues


def save_issues_to_csv(projects_issues: dict, filename: str):
    '''
    Generates a csv file with all the projects and their issues
    '''
    header = [CSV_HEADER[index] for index in sorted(CSV_HEADER.keys())]
    with open(filename, 'w', encoding='UTF-8', newline='') as out:
        writer = csv.writer(out)
        writer.writerow(header)
        for project in projects_issues.keys():
            for issue in projects_issues[project]:
                row = []
                for property_name in header:
                    row.append(projects_issues[project][issue].get_property(property_name))
                writer.writerow(row)


def parse_arguments():
    '''
    Parse command line arguments.
    Get input from user for: username, password, url, filename, is_debug
    All are optional
    '''
    parser = argparse.ArgumentParser(description='Download all project issues from Sonarqube ')
    parser.add_argument('--debug', '-d', action='count', default=0,
                        help='Save results as .json files for each project')
    parser.add_argument('--sonarqube-url', '-s', type=str, default=SONAR_URL,
                        help=f'Url of Sonarqube, default {SONAR_URL}')
    parser.add_argument('--user', '-u', type=str, default=USERNAME,
                        help=f'Sonarqube username, default {USERNAME}')
    parser.add_argument('--password', '-p', type=str, default=PASSWORD,
                        help=f'Sonarqube password, default {PASSWORD}')
    parser.add_argument('--file', '-f', type=str, default=CSV_FILE,
                        help=f'Path of csv output file, default {CSV_FILE}')
    return vars(parser.parse_args())


def main():
    '''
    Get a list of projects from sonarqube.
    Get all the issues for all projects.
    Save them all to a csv file
    '''
    try:
        args = parse_arguments()
        args['project_url'] = PROJECTS_URL.format(SONAR_URL=args['sonarqube_url'])
        args['project_analysis_url'] = PROJECT_ANALYSIS_URL.format(SONAR_URL=args['sonarqube_url'])
        args['issues_url'] = ISSUES_URL.format(SONAR_URL=args['sonarqube_url'])
        args['project_branches_url'] = PROJECT_BRANCHES_URL.format(SONAR_URL=args['sonarqube_url'])
        projects = make_request(args['project_url'], args['user'], args['password'])
        print(f"Found {get_item(projects, ['paging', 'total'])} projects")
        projects_issues = {}
        for component in get_item(projects, ['components']):
            project_name = get_item(component, ['key'])
            print(f"Getting issues for project: {project_name}")
            issues = get_issues(args, project_name)
            projects_issues[project_name] = issues
        save_issues_to_csv(projects_issues, args['file'])
    except SonarException as exc:
        print(f'ERROR: {exc}')


if __name__ == "__main__":
    main()
