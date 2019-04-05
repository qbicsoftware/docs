#!/usr/bin/env python

# Script to automatically generate a README.md file containing links to all GitHub pages
# containing documentation. It is assummed that cookiecutter has been installed and is
# available as a Python module.
#
# This script injects extra context using cookiecutter's API to provide the most recent
# links to generated reports.

import cookiecutter, tempfile, argparse, os, subprocess, sys, re
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
# folder where submodules reside
SUBMODULES_DIR = 'submodules'
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
    parser.add_argument('-m', '--submodules-dir', default=SUBMODULES_DIR,
        help='Directory containing all submodules.')
    parser.add_argument('-u', '--username-var-name', default=USERNAME_ENV_VARIABLE_NAME,
        help='Name of the environment variable holding the GitHub username used to push changes in reports.')
    parser.add_argument('-a', '--access-token-var-name', default=TOKEN_ENV_VARIABLE_NAME,
        help='Name of the environment variable holding the GitHub personal access token used to push changes in reports.')
    parser.add_argument('--danger-debug', action='store_true',
        help='Prints out potentially sensitive debug information, such as credentials. Never use in remote environments.')
    parser.add_argument('-p', '--pages-branch', default='gh-pages',
        help='Branch holding the documentation. This applies both for the individual projects and for the summary (this repo).')
    parser.add_argument('-b', '--base-report-dir', default=BASE_REPORT_DIR,
        help='Base directory where reports reside on each of the submodules.')
    parser.add_argument('repo_slug', 
        help='Slug of this repository, e.g., qbicsoftware/docs.')
    parser.add_argument('branch', 
        help='Branch where changes done on the submodules will be performed.')
    parser.add_argument('commit_message', nargs='+', 
        help='Message(s) to use when committing changes.')
    args = parser.parse_args()

    # just in case
    if args.danger_debug:
        if 'CI' in os.environ or 'TRAVIS' in os.environ or 'CONTINUOUS_INTEGRATION' in os.environ:
            print('WARNING: it seems that you are executing this script on Travis CI. Running with --danger-debug is recommended against. Stopping.')
            exit(1)

    # read contents of the submodules (repos) file into a list
    submodules = parse_submodules_file(args.repos_file)

    # since this will run on Travis, we cannot assume that we can change the current local repo without breaking anything
    # the safest way would be to clone this same repository on a temporary folder and leave the current local repo alone
    working_dir = tempfile.mkdtemp()
    custom_remote = build_remote(args)
    clone_repo(args.repo_slug, working_dir, custom_remote)

    # we have to update modules and commit to development, NOT to gh-pages!
    # for each repo, make sure that it has been added as a submodule
    checkout_branch(working_dir, args.branch)
    for submodule in submodules:
        update_submodule(working_dir, submodule, args)
    # push changes
    push_upstream(working_dir, args.branch, args)

    # reports are available only in a specific branch
    checkout_branch(working_dir, args.pages_branch)
    # make sure to start with an empty repo
    remove_unneeded_files(working_dir, args)

    # prepare to use cookiecutter
    # all modules are present, we have to build a dictionary with a structure similar to cookiecutter.json
    extra_context = build_extra_context(working_dir, args)
    extra_content['folder_name'] = GENERATED_DIR
    # apply the template and generate output in a temp folder
    cookiecutter_output_dir = tempfile.mkdtemp()
    cookiecutter(COOKIECUTTER_TEMPLATE, no_input=True, overwrite_if_exists=True, extra_context=extra_context, output_dir=cookiecutter_output_dir)
    # move the files from the output dir to the cloned repository's root folder
    for f in os.listdir(os.path.join(cookiecutter_output_dir, GENERATED_DIR)):
        os.shutil.move(os.path.join(cookiecutter_output_dir, GENERATED_DIR, f), working_dir)

    # push changes upstream to gh-pages
    push_upstream(working_dir, args.pages_branch, args)

    # clean up
    if not args.skip_cleanup:
        print('Removing working folders {}, {}'.format(working_dir, cookiecutter_output_dir))
        os.shutil.rmtree(working_dir)
        os.shutil.rmtree(cookiecutter_output_dir)
    else:
        print('Working folders {}, {} were not removed (skipping cleanup)'.format(working_dir, cookiecutter_output_dir))


# Parses the file found at the given path, returns
# a list where each element is a line in the file.
# Lines starting with '#' are ignored
def parse_submodules_file(submodules_file):
    print('Reading submodule names from {}'.format(submodules_file))
    submodule_names = []
    with open(submodules_file, "r") as f: 
        for line in f:
            line = line.strip()
            # ignore comments and empty lines
            if not line or line.startswith('#'):
                continue
            submodule_names.append(line)
            print('    Found submodule {}'.format(line))
    return submodule_names


# Builds a git remote using environment variables for credentials and the repo slug
def build_remote(args):
    return 'https://{}:{}@github.com/{}'.format(os.environ[args.username_var_name], os.environ[args.access_token_var_name], args.repo_slug)


# Clones the given remote repository into the working directory
def clone_repo(repo_slug, working_dir, custom_remote):
    print('Cloning {} into temporary folder {}'.format(repo_slug, working_dir))    
    execute(['git', 'clone', custom_remote, working_dir], 'Could not clone {} in directory {}'.format(repo_slug, working_dir))


# Checks out a git the given git branch using working_dir as a local repo
def checkout_branch(working_dir, branch):
    # we need to add the branch if it doesn't exist (git checkout -b branch),
    # but if the branch already exists, we need to checkout (git checkout branch), luckily, 
    # "git checkout -b branch" fails if branch already exists!
    print('Changing to branch {}'.format(branch))
    try:
        execute(['git', '-C', working_dir, 'checkout', branch])
    except:
        execute(['git', '-C', working_dir, 'checkout', '-b', branch], 'Could not create branch {}'.format(branch))


# Goes through the all files/folders (non-recursively) and deletes them using 'git rm'.
# Files that should not be deleted are ignored
def remove_unneeded_files(working_dir, args):
    print('Cleaning local repository ({}) of non-reports files'.format(working_dir))
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


# issues git commands to add/update a git submodule
# using the passed branch
def update_submodule(working_dir, submodule_name, args):
    # relative path to the submodule folder
    submodule_dir = get_submodule_dir(submodule_name, args)
    print('Updating submodule {}'.format(submodule_dir))
    # force-add submodules
    print('    force-adding...')    
    execute(
        ['git', '-C', working_dir, 'submodule', 'add', '--force', '../{}'.format(submodule_name), submodule_dir],
        'Could not add submodule {}.'.format(submodule_name))
    # we are interested in a particular branch (args.pages_branch); if this branch doesn't exist on the submodule,
    # we cannot simply use "-b <branch>" because the command will fail, so we will need to first check if the 
    # submodule has said branch and take it from there
    try:
        print('    checking out branch {}...'.format(args.pages_branch))
        execute(
            ['git', '-C', os.path.join(working_dir, submodule_name), 'checkout', args.pages_branch])
    except:
        print('    WARNING: submodule {} does not yet have a branch named {}'.format(submodule_name, args.pages_branch))


# given a submodule, returns the path of the folder, relative to root
def get_submodule_dir(submodule, args):
    return '{}/{}'.format(args.submodules_dir, submodule)


# builds a dictionary similar to cookiecutter.json containing the latest values
# this is just some advanced trickery, no more, no less... we are assumming that each of the submodules points to the gh-pages branch,
# and that this branch contains a folder under which all versions of all reports are found
def build_extra_context(working_dir, submodules, args):
    extra_context = {}
    reports = {}    
    for submodule in submodules:
        submodule_reports = {}
        for f in os.listdir(os.path.join(working_dir, args.submodules_dir, submodule, args.base_report_dir)):
            # treat all directories as reports, just make sure to check for snapshot reports
            if os.path.isdir(os.path.join(working_dir, args.submodules_dir, submodule, args.base_report_dir, f)):
                if f == args.snapshot_reports_dir:
                    submodule_reports['development'] = build_report_url(submodule, args.snapshot_reports_dir, args)
                else:
                    submodule_reports[f] = build_report_url(submodule, f, args)
        if len(submodule_reports):
            reports[submodule] = submodule_reports
        else:
            print('WARNING: no reports were found for repository {}', submodule, file=sys.stderr)            
    extra_context['reports'] = reports


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


# Executes an external command, raises an exception if the return code is not 0
# stderr/stdout are hidden by default to avoid leaking credentials into log files in Travis
# Important: do not commit code that might print sensitive information, this might end up in a log somewhere outside our control
def execute(command, error_message='Error encountered while executing command', danger_debug=False):
    # do not print the command! this might expose usernames/passwords/tokens!
    completed_process = subprocess.run(command, capture_output=True)
    if (completed_process.returncode != 0):
        raise Exception('{}\n  Exit code={}\n  stderr={}\n  stdout{}'.format(
            error_message, completed_process.returncode, 
            '***hidden***' if not danger_debug else completed_process.stderr, 
            '***hidden***' if not danger_debug else completed_process.stdout))

if __name__ == "__main__":
    main()
