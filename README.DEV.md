# Building and installing local version

To build the package you can just run:

``
poetry build
``

A wheel is created which can be used to install the package into the local python env.

``
pip install ./dist/pypads-0.1.4.tar.gz
``

# Publishing a new version

To publish a new version of the library it's version number has to be increased.
A task is defined on taskipy for this purpose.

``
task publish patch/minor/major
``

You can use [bump2version](https://pypi.org/project/bump2version/) instead to increment version numbers where needed and manually publish the changes.
Using one of the following commands bumps the version and pushes it tagged to git.

``
bump2version patch
``
``
bump2version minor
``
``
bump2version major
``

# Generating a changelog

A changelog can be generated from the git log manually with 

``
gitchangelog > CHANGELOG.rst
``

Following config includes information on how to structure your git commit messages.

Use following format: ``ACTION: [AUDIENCE:] COMMIT_MSG [!TAG ...]``

Examples:

````
new: usr: support of git implemented
chg: re-indentend some lines !cosmetic
fix: pkg: updated year of licence coverage.
new: test: added a bunch of test around user usability of feature X.
fix: typo in spelling my name in comment. !minor
````

````
# -*- coding: utf-8; mode: python -*-
##
## Format
##
##   ACTION: [AUDIENCE:] COMMIT_MSG [!TAG ...]
##
## Description
##
##   ACTION is one of 'chg', 'fix', 'new'
##
##       Is WHAT the change is about.
##
##       'chg' is for refactor, small improvement, cosmetic changes...
##       'fix' is for bug fixes
##       'new' is for new features, big improvement
##
##   AUDIENCE is optional and one of 'dev', 'usr', 'pkg', 'test', 'doc'
##
##       Is WHO is concerned by the change.
##
##       'dev'  is for developpers (API changes, refactors...)
##       'usr'  is for final users (UI changes)
##       'pkg'  is for packagers   (packaging changes)
##       'test' is for testers     (test only related changes)
##       'doc'  is for doc guys    (doc only changes)
##
##   COMMIT_MSG is ... well ... the commit message itself.
##
##   TAGs are additionnal adjective as 'refactor' 'minor' 'cosmetic'
##
##       They are preceded with a '!' or a '@' (prefer the former, as the
##       latter is wrongly interpreted in github.) Commonly used tags are:
##
##       'refactor' is obviously for refactoring code only
##       'minor' is for a very meaningless change (a typo, adding a comment)
##       'cosmetic' is for cosmetic driven change (re-indentation, 80-col...)
##       'wip' is for partial functionality but complete subfunctionality.
##
## Example:
##
##   new: usr: support of bazaar implemented
##   chg: re-indentend some lines !cosmetic
##   new: dev: updated code to be compatible with last version of killer lib.
##   fix: pkg: updated year of licence coverage.
##   new: test: added a bunch of test around user usability of feature X.
##   fix: typo in spelling my name in comment. !minor
##
##   Please note that multi-line commit message are supported, and only the
##   first line will be considered as the "summary" of the commit message. So
##   tags, and other rules only applies to the summary.  The body of the commit
##   message will be displayed in the changelog without reformatting.


##
## ``ignore_regexps`` is a line of regexps
##
## Any commit having its full commit message matching any regexp listed here
## will be ignored and won't be reported in the changelog.
##
ignore_regexps = [
    r'@minor', r'!minor',
    r'@cosmetic', r'!cosmetic',
    r'@refactor', r'!refactor',
    r'@wip', r'!wip',
    r'^([cC]hg|[fF]ix|[nN]ew)\s*:\s*[p|P]kg:',
    r'^([cC]hg|[fF]ix|[nN]ew)\s*:\s*[d|D]ev:',
    r'^(.{3,3}\s*:)?\s*[fF]irst commit.?\s*$',
    r'^$',  ## ignore commits with empty messages
]
````

Changelogs are automatically generated on deployment.

# Generating the documentation

The documentation is generated via sphinx. You can generate it manually by calling:

``
make -C ./docs html
``

The documentation should be updated automatically when a push is registered on github master due to webhook settings on readthedocs.

# Deploying to PyPi

Deployment is done by poetry.

``
poetry publish
``