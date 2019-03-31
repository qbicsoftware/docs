#!/usr/bin/env python

# Script to generate documentation javadocs using javasphinx
# This script assumes that javasphinx and git have been installed.

# Output of this script is to populate the "docs" folder. For each submodule
# in submodules.txt, a folder under docs will be created. The folder structure looks like:
# 
# .
# └── docs
#    ├── foo-lib
#    │    ├── com
#    │    │   └── foo
#    │    │       └── bar
#    │    │           ├── package-index.rst
#    │    │           ├── FooClass.rst
#    │    │           ├── BarClass.rst
#    │    │           └── FooBarClass.rst
#    │    └── packages.rst
#    └── bar-lib
#        ├── com
#        │   └── bar
#        │       └── foo
#        │           ├── package-index.rst
#        │           ├── FooClass.rst
#        │           ├── BarClass.rst
#        │           └── FooBarClass.rst
#        └── packages.rst

import argparse, os, subprocess
from datetime import date

# how many spaces should we write before writing each submodule name
SUBMODULE_INDENTATION_LEVEL = 3
# placeholder that will be substituted for the list of submodules
# if you change the value, make sure to also update the template file
# (.index.rst.template)
SUBMODULES_PLACEHOLDER = "$QBIC_DOCS_SUBMODULES$"
# version string placeholders
SHORT_VERSION_PLACEHOLDER = "$QBIC_DOCS_VERSION_SHORT$"
LONG_VERSION_PLACEHOLDER = "$QBIC_DOCS_VERSION_FULL$"
# current year placeholder
CURRENT_YEAR_PLACEHOLDER = "$QBIC_DOCS_CURRENT_YEAR$"
# name of the master document
INDEX_FILE = "index.rst"
# name of the configuration file
CONF_FILE = "conf.py"
# directory where all git submodules reside
SUBMODULE_FOLDER = "modules"
# folder that has the source code, relative to each submodule folder
SOURCE_DIR = 'src/main'
# name of branches
DEVELOPMENT_BRANCH = 'development'
RELEASE_BRANCH = 'master'

# parses arguments
def main():
    parser = argparse.ArgumentParser(description='QBiC Javadoc Generator.', prog='generate-javadocs.py', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-s', '--submodules-file', required=True, default='submodules.txt',
        help='File containing a list of submodules. For each submodule, javadocs will be generated.')
    parser.add_argument('-i', '--index-template-file', required=True, default='.index.rst.template',
        help='Template file to generate index.rst.')
    parser.add_argument('-c', '--conf-template-file', required=True, default='.conf.py',
        help='Template file to generate conf.py.')
    parser.add_argument('-o', '--output-dir', required=True, default='docs',
        help='Folder on which the javadocs will be generated.')
    parser.add_argument('-b', '--branch', required=True, 
        help='Branch from which javadocs will be generated for each submodule.')
    args = parser.parse_args()

    # read contents of the submodules file into a list
    submodules_list = parse_submodules_file(args.submodules_file)
    # for each repo, make sure that it has been added as a submodule, then
    # update each submodule and generate javadocs for it
    for submodule_name in submodules_list:
        update_submodule(submodule_name, args.branch)
        generate_javadocs(args.output_dir, submodule_name)
    # update index.rst and conf.py based on their templates   
    update_master_file('{}/{}'.format(args.output_dir, INDEX_FILE), args.index_template_file, submodules_list)
    update_conf('{}/{}'.format(args.output_dir, CONF_FILE), args.conf_template_file, args.branch)
    
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
            print('  Found submodule {}'.format(line))
    return submodule_names

# issues git commands to add/update a git submodule
# using the passed branch
def update_submodule(submodule_name, branch):
    # relative path to the submodule folder
    submodule_dir = get_submodule_dir(submodule_name)
    print('Updating {}'.format(submodule_dir))
    # force-add submodules
    print('  force-adding...')
    execute(
        ["git", "submodule", "add", "--force", "-b", branch, '../{}'.format(submodule_name), submodule_dir],
        'Could not add submodule {}.'.format(submodule_name))    
    # update submodule
    print('  updating...')
    execute(
        ["git", "submodule", "update", "--remote", submodule_dir], 
        'Could not update submodule {}.'.format(submodule_name))

# generates javadocs for the given submodule
def generate_javadocs(output_dir, submodule_name):
    # each submodule gets a directory under output_dir (e.g., docs/foo-lib, docs/bar-service)
    # make sure that the folder exists    
    javadoc_output_dir = get_javadoc_output_dir(output_dir, submodule_name)
    submodule_src_dir = '{}/{}'.format(get_submodule_dir(submodule_name), SOURCE_DIR)
    print('Generating javadocs from {} into {}'.format(submodule_src_dir, javadoc_output_dir))
    if not (os.path.exists(javadoc_output_dir)):
        os.makedirs(javadoc_output_dir)
    execute(
        ['javasphinx-apidoc', '-o', javadoc_output_dir, '-t', submodule_name, submodule_src_dir],
        'Could not generate javadocs for {}'.format(submodule_name))

# updates index.rst based on a template, substituting placeholders
def update_master_file(index_file, template_file, submodules_list):    
    # convert the list of modules to a string with indented lines    
    indented_submodules = ''
    # be nice and list repos alphabetically in index.rst
    for submodule_name in submodules_list.sorted():
        # this works in python lol
        indented_submodules = indented_submodules + \
            '{}{}\n'.format(' ' * SUBMODULE_INDENTATION_LEVEL, submodule_name)
    variables = {}
    variables[SUBMODULES_PLACEHOLDER] = indented_submodules
    resolve_placeholders(index_file, template_file, **variables)

# updates conf.py based on a template, substituting placeholders
def update_conf(conf_file, template_file, branch):
    variables = {}    
    if branch == DEVELOPMENT_BRANCH:
        variables[LONG_VERSION_PLACEHOLDER] = 'Development (SNAPSHOT)'
    elif branch == RELEASE_BRANCH:
        variables[LONG_VERSION_PLACEHOLDER] = 'Stable release'
    else:
        raise Exception('Unrecognized branch {}. Only {} and {} are recognized'.format(branch, DEVELOPMENT_BRANCH, RELEASE_BRANCH))
    variables[SHORT_VERSION_PLACEHOLDER] = branch
    variables[CURRENT_YEAR_PLACEHOLDER] = str(date.today().year)
    resolve_placeholders(conf_file, template_file, **variables)

# reads a template file, substitutes placeholders (**kwargs), and writes
# the resolved template to dest_file
def resolve_placeholders(dest_file_path, template_file_path, **kwargs):
    print('Resolving placeholders using {} as template'.format(template_file_path))
    # read the full contents of the file
    with open(template_file_path, 'r') as f:
        content = f.read()
    # resolve all placeholders
    for placeholder_name, placeholder_value in kwargs.items():
        print('  replacing {} with {}'.format(placeholder_name, placeholder_value))
        content.replace(placeholder_name, placeholder_value)
    # write content to the destination file
    print('  writing to {}'.format(dest_file_path))
    with open(dest_file_path, 'w') as f:
        f.write(content)

# given a submodule, returns the path of the folder, relative to the master repo
def get_submodule_dir(submodule_name):
    return '{}/{}'.format(SUBMODULE_FOLDER, submodule_name)

# given a submodule, returns the path of the corresponding javadoc output folder
def get_javadoc_output_dir(base_dir, submodule_name):
    return '{}/{}'.format(base_dir, submodule_name)

# executes an external command, raises an exception if the return code is not 0
def execute(command, error_message):
    print('    executing {}'.format(' '.join(str(x) for x in command)))
    completed_process = subprocess.run(command, capture_output=True)
    if (completed_process.returncode != 0):
        raise Exception('{}\n  Exit code={}\n  stderr={}\n  stdout{}'.format(
            error_message, completed_process.returncode, completed_process.stderr, completed_process.stdout))

if __name__ == "__main__":
    main()
