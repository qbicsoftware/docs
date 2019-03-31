#!/usr/bin/env bash

# Positional arguments:
#   1. docs folder: directory on which all javadocs were generated
#
# The following environment variables are required:
#   - GITHUB_USERNAME 
#   - GITHUB_ACCESS_TOKEN: 
# This script will commit/push changes to GitHub, so a username and a personal access token are required.
 
# This script commits changes done to the docs folder. When changes are committed,
# ReadTheDocs.org will start a build and will update the published documentation.

# we need to add a remote with credentials
git remote rm origin
git remote add origin https://$GITHUB_USERNAME:$GITHUB_ACCESS_TOKEN@github.com
git add $1
# instruct Travis to ignore this commit to avoid an infinite loop
git commit -m "[skip travis] Automatic javadoc generation" -m "Travis build ID: $TRAVIS_BUILD_ID" -m "Travis build number: $TRAVIS_BUILD_NUMBER"
git push -u origin master