#!/usr/bin/env python

# Script to automatically generate a README.md file containing links to all GitHub pages
# containing documentation. The following assumptions are made:
# 
#  * cookiecutter has been installed and is available as a Python module.
#  * this repo has a branch matching the --pages-branch command-line option.
#
# This script injects extra context using cookiecutter's API to provide the most recent
# links to generated reports.

import tempfile, argparse, os, subprocess, sys, re, traceback, shutil
from cookiecutter.main import cookiecutter
from datetime import date

# location of the template that cookiecutter will use
COOKIECUTTER_TEMPLATE = 'template'
# only the most recent SNAPSHOT version will be shown,
# this is the name of the folder containing the snapshot reports
SNAPSHOT_REPORTS_DIR = 'development'
# file containing the names of the repos for which reports will be shown
REPOSITORIES_FILE = 'repos.txt'
# credentials are given via environment variables
USERNAME_ENV_VARIABLE_NAME = 'REPORTS_GITHUB_USERNAME'
TOKEN_ENV_VARIABLE_NAME = 'REPORTS_GITHUB_ACCESS_TOKEN'
# base directory where reports reside on gh-pages of each of the submodules
BASE_REPORT_DIR = 'reports'
# value for cookiecutter.folder_name
GENERATED_DIR = 'generated'
# compiled regex to match files that should not be deleted when cleaning the working folder (in gh-pages)
UNTOUCHABLE_FILES_MATCHER = re.compile('^\.git.*')

# parses arguments
def main():
    parser = argparse.ArgumentParser(description='QBiC Javadoc Generator.', prog='generate-javadocs.py', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-r', '--repos-file', default=REPOSITORIES_FILE,
        help='File containing a list of GitHub repositories containing reports.')
    parser.add_argument('-t', '--template', default=COOKIECUTTER_TEMPLATE,
        help='Cookiecutter template directory.')
    parser.add_argument('-s', '--snapshots-reports-dir', default=SNAPSHOT_REPORTS_DIR,
        help='Name of the directory containing development (SNAPSHOT) reports.')
    parser.add_argument('-d', '--dry-run', action='store_true',
        help='Execute in dry run mode. No changes to this repo will be done in dry run mode.')
    parser.add_argument('--skip-cleanup', action='store_true',
        help='If used, temporary folders used as working directories will not be removed.')
    parser.add_argument('-u', '--username-var-name', default=USERNAME_ENV_VARIABLE_NAME,
        help='Name of the environment variable holding the GitHub username used to push changes in reports.')
    parser.add_argument('-a', '--access-token-var-name', default=TOKEN_ENV_VARIABLE_NAME,
        help='Name of the environment variable holding the GitHub personal access token used to push changes in reports.')
    parser.add_argument('-p', '--pages-branch', default='gh-pages',
        help='Branch holding the documentation. This applies both for the individual projects and for the summary (this repo).')
    parser.add_argument('-o', '--organization', default='qbicsoftware',
        help='Name of the organization (or username) for which documentation will be built. All repos should be part of this organization (or username).')
    parser.add_argument('-b', '--base-report-dir', default=BASE_REPORT_DIR,
        help='Base directory where reports reside on each of the submodules.')
    parser.add_argument('repo_slug', 
        help='Slug of this repository, e.g., qbicsoftware/docs.')
    parser.add_argument('commit_message', nargs='+', 
        help='Message(s) to use when committing changes.')
    args = parser.parse_args()

    # read contents of the repos file into a list
    repos = parse_repos_file(args)

    # we have to clone each of the repos (we use a temp folder) and checkout their gh-pages branch
    # keep track of which repo will be cloned in which directory
    repo_dirs = {}
    for repo in repos:
        try:
            repo_dirs[repo] = tempfile.mkdtemp()
            clone_single_branch('{}/{}'.format(args.organization, repo), repo_dirs[repo], args.pages_branch)
        except:
            # we could parse the stdout to make sure that this failed because the pages branch does not exit...
            # or we could just assume that this failed because the pages branch does not exist...
            print('WARNING: could not clone a single branch, {}, from repo {}. Are you sure that the branch exists?'.format(args.pages_branch, repo))

    # prepare to use cookiecutter
    # build a dictionary with a structure similar to cookiecutter.json
    extra_context = build_extra_context(repo_dirs, args)
    extra_context['folder_name'] = GENERATED_DIR
    # apply the template and generate output in a temp folder
    cookiecutter_output_dir = tempfile.mkdtemp()
    cookiecutter(COOKIECUTTER_TEMPLATE, no_input=True, overwrite_if_exists=True, extra_context=extra_context, output_dir=cookiecutter_output_dir)

    # since this will run on Travis, we cannot assume that we can change the current local repo without breaking anything
    # the safest way would be to clone this same repository on a temporary folder and leave the current local repo alone
    working_dir = tempfile.mkdtemp()
    # we need a remote with credentials because we will be pushing changes upstream
    custom_remote = build_remote(args)
    # we assume that the pages branch exists in this repo, if not, this will fail
    print('Cloning this repo, {}, on directory {}'.format(args.repo_slug, working_dir))
    clone_single_branch(args.repo_slug, working_dir, custom_remote, args.pages_branch)
    # make sure to remove everything we see
    print('Cleaning local repository ({})'.format(working_dir))
    remove_unneeded_files(working_dir, args)
    # move the files from the output dir to the cloned repository's root folder
    print('Moving cookiecutter output from {} to {}'.format(cookiecutter_output_dir, working_dir))
    for f in os.listdir(os.path.join(cookiecutter_output_dir, GENERATED_DIR)):
        shutil.move(os.path.join(cookiecutter_output_dir, GENERATED_DIR, f), working_dir)

    # push changes upstream to gh-pages
    push_upstream(working_dir, args.pages_branch, args)

    # clean up
    if not args.skip_cleanup:
        print('Removing cookiecutter working folder, {}'.format(cookiecutter_output_dir))
        print('Removing folder where this repo was cloned, {}'.format(working_dir))
        shutil.rmtree(working_dir)
        shutil.rmtree(cookiecutter_output_dir)
        print('Removing repo directories')
        for repo, repo_dir in repo_dirs.items():
            print('    Removing folder where repo {} was cloned, {}'.format(repo, repo_dir))
    else:
        print('Working folders and repo folders were not removed (skipping cleanup)')


# Parses the file found at the given path, returns
# a list where each element is a line in the file.
# Lines starting with '#' are ignored
def parse_repos_file(args):
    print('Reading GitHub repository names from {}'.format(args.repos_file))
    repo_names = []
    with open(args.repos_file, "r") as f: 
        for line in f:
            line = line.strip()
            # ignore comments and empty lines
            if not line or line.startswith('#'):
                continue
            if '{}/{}'.format(args.organization, line) == '{}'.format(args.repo_slug):
                print('    WARNING: Ignoring this repository, {}.'.format(line))
            repo_names.append(line)
            print('    Found repo {}'.format(line))
    return repo_names


# Builds a git remote using environment variables for credentials and the repo slug
def build_remote(args):
    return 'https://{}:{}@github.com/{}'.format(os.environ[args.username_var_name], os.environ[args.access_token_var_name], args.repo_slug)


# Clones a single branch from the remote repository into the working directory
def clone_single_branch(repo_slug, working_dir, custom_remote, branch):
    print('Cloning {}, branch {}, into temporary folder {}'.format(repo_slug, branch, working_dir))    
    execute(['git', 'clone', '--single-branch', '--branch', branch, custom_remote, working_dir], 
                'Could not clone {} in directory {}'.format(repo_slug, working_dir))


# Goes through the all files/folders (non-recursively) and deletes them using 'git rm'.
# Files that should not be deleted are ignored
def remove_unneeded_files(working_dir, args):    
    for f in os.listdir(working_dir):
        if should_delete(f, args):
            # instead of using OS calls to delete files/folders, use git rm to stage deletions
            print('    Deleting {} from {} branch'.format(f, args.pages_branch))
            execute(['git', '-C', working_dir, 'rm', '-r', '--ignore-unmatch', f], 'Could not remove {}.'.format(f))
            # files that are not part of the repository aren't removed by git and the --ignore-unmatch flag makes
            # git be nice so it doesn't exit with errors, so we need to force-remove them
            force_delete(os.path.join(working_dir, f))
        else:
            print('    Ignoring file/folder {}'.format(f))


# builds a dictionary similar to cookiecutter.json containing the latest values
# this is just some advanced trickery, no more, no less... we are assumming that each of the cloned repos points to the
# pages branch and that the repository has a given directory structure (see comment on .generate-reports.py on the cookiecutter-templates-cli repo)
def build_extra_context(repo_dirs, args):
    extra_context = {}
    reports = {}    
    for repo, repo_dir in repo_dirs.items():
        # alliteration FTW
        repo_reports = {}
        repo_reports_dir = os.path.join(repo_dir, args.base_report_dir)
        if os.path.exists(repo_reports_dir) and os.path.isdir(repo_reports_dir):
            for f in os.listdir(repo_reports_dir):
                # treat all directories as reports, just make sure to check for snapshot reports
                if os.path.isdir(os.join(repo_reports_dir, f)):
                    if f == args.snapshot_reports_dir:
                        repo_reports['development'] = build_report_url(repo, args.snapshot_reports_dir, args)
                    else:
                        repo_reports[f] = build_report_url(repo, f, args)
        if len(repo_reports):
            reports[repo] = repo_reports
        else:
            print('WARNING: no reports were found for repository {}'.format(repo), file=sys.stderr)
    extra_context['reports'] = reports
    return extra_context


# Adds, commits and pushes changes
def push_upstream(working_dir, branch, args):
    if args.dry_run:
        print('(running in dry run mode) Local/remote repository will not be modified')
    else:
        # add changes to the index
        print('Staging changes for commit')
        execute(['git', '-C', working_dir, 'add', '.'], 'Could not stage reports for commit.')

        # build the git-commit command and commit changes
        print('Pushing changes upstream')
        git_commit_command = ['git', '-C', working_dir, 'commit']
        for commit_message in args.commit_message:
            git_commit_command.extend(['-m', commit_message])
        execute(git_commit_command, 'Could not commit changes')

        # https://www.youtube.com/watch?v=vCadcBR95oU
        execute(['git', '-C', working_dir, 'push', '-u', 'origin', branch], 'Could not push changes using provided credentials.')


# Whether it is safe to delete the given path, we won't delete important files/folders (such as .git)
def should_delete(path, args):
    return not UNTOUCHABLE_FILES_MATCHER.match(path)


# builds a report URL
def build_report_url(submodule, report_dir, args):
    return 'https://qbicsoftware.github.com/{}/{}/{}/index.html'.format(submodule, args.base_report_dir, report_dir)


# Forcefully deletes recursively the passed file/folder using OS calls
def force_delete(file):
    if os.path.exists(file):
        if os.path.isdir(file):
            shutil.rmtree(file)
        else:
            os.remove(file)


# Executes an external command
# stderr/stdout are hidden to avoid leaking credentials into log files in Travis, so it might be a pain in the butt to debug, sorry, but safety first!
# if exit_if_fail is set to True, this method will print minimal stacktrace information and exit if a failure is encountered, otherwise, an exception 
# will be thrown (this is useful if an error will be handled by the invoking method)
def execute(command, error_message='Error encountered while executing command', exit_if_fail=True):
    # do not print the command, stderr or stdout! this might expose usernames/passwords/tokens!
    try:
        subprocess.run(command, check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except:
        if exit_if_fail:
            stack = traceback.extract_stack()
            try:
                print('{}\n  Error originated at file {}, line {}'.format(error_message, stack[-2].filename, stack[-2].lineno), file=sys.stderr)            
            except:
                print('{}\n  No information about the originating call is available.'.format(error_message), file=sys.stderr)
            exit(1)
        else:
            raise Exception()
    

if __name__ == "__main__":
    main()