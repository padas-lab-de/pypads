Changelog
=========


0.5.4 (2020-12-08)
------------------

Fix
~~~
- Syntax errors in the docs. [Mehdi Ben Amor]

Other
~~~~~
- Bump version: 0.5.3 → 0.5.4. [Thomas Weißgerber]
- Bump version: 0.5.2 → 0.5.3. [Thomas Weißgerber]
- Bump version: 0.5.1 → 0.5.2. [Thomas Weißgerber]


0.5.3 (2020-12-08)
------------------
- Bump version: 0.5.2 → 0.5.3. [Thomas Weißgerber]


0.5.2 (2020-12-08)
------------------
- Bump version: 0.5.1 → 0.5.2. [Thomas Weißgerber]


0.5.1 (2020-12-08)
------------------
- Bump version: 0.5.0 → 0.5.1. [Thomas Weißgerber]


0.5.0 (2020-12-07)
------------------

New
~~~
- Reduced performance impact of pypads by about 50% by reducing the
  number of needed rest calls to the tracking server. [Thomas
  Weißgerber]

Changes
~~~~~~~
- Added function to retrieve subset of row ids based on logical
  operators. [christofer]
- Added result summary / search. [Thomas Weißgerber]
- Added result summary / search. [Thomas Weißgerber]
- Added classification metrics to the sklearn mapping file. [Thomas
  Weißgerber]
- Fix in call_tracke.has_call_identity, recursive tracking unit tests.
  [Mehdi Ben Amor]

Other
~~~~~
- Bump version: 0.4.0 → 0.5.0. [Mehdi Ben Amor]


0.4.0 (2020-10-20)
------------------

New
~~~
- Reduced intrusiveness of git change preserving. [Thomas Weißgerber]
- Run loggers unit test. wip! [Mehdi Ben Amor]
- Tests for injection loggers. [Mehdi Ben Amor]
- Updated pipeline tracker, removed unneeded PoC loggers. [Thomas
  Weißgerber]
- Added references between tracked objects, logger outputs and logger
  calls as well as parameters etc. [Thomas Weißgerber]
- Added mongoDB support! [Thomas Weißgerber]
- Added register_setup/teardown_utility. This allows for registering
  functions before/after executing a run which are themselves not stored
  as a logger. [Thomas Weißgerber]

Changes
~~~~~~~
- Reworked storage of Hardware details. [Thomas Weißgerber]
- Removed branching for now. We now just store the current changes as a
  patch. [Thomas Weißgerber]

Fix
~~~
- Fixed tests. [christofer]
- Updated tests for current API. [christofer]
- Updated tests for new api. [christofer]

Other
~~~~~
- Bump version: 0.3.2 → 0.4.0. [Thomas Weißgerber]


0.3.2 (2020-09-14)
------------------
- Bump version: 0.3.1 → 0.3.2. [Mehdi Ben Amor]


0.3.1 (2020-09-04)
------------------

Fix
~~~
- Chg: broken import in the new mlflow release. [Mehdi Ben Amor]
- Class reference fix. [Mehdi Ben Amor]
- Fixed multiple executions of the same hooks / anchors when defined by
  multiple matching mappings. [Thomas Weißgerber]

Other
~~~~~
- Bump version: 0.3.0 → 0.3.1. [Mehdi Ben Amor]


0.3.0 (2020-08-31)
------------------

New
~~~
- Added a new TrackingObjectModel class. [Thomas Weißgerber]
- Added logger schemata. [Thomas Weißgerber]

Changes
~~~~~~~
- Fix: parametersILF fix and MetricILF rework. [Mehdi Ben Amor]

Other
~~~~~
- Bump version: 0.2.3 → 0.3.0. [Mehdi Ben Amor]


0.2.3 (2020-06-23)
------------------
- Bump version: 0.2.2 → 0.2.3. [mehdi]


0.2.2 (2020-06-23)
------------------
- Bump version: 0.2.1 → 0.2.2. [mehdi]


0.2.1 (2020-06-22)
------------------

New
~~~
- Added changelog to documentation. [Thomas Weißgerber]
- Plugin system support New: usr: Yaml format for mapping files New:
  usr: Importlib performance rebuild. [Thomas Weißgerber]
- Added mapping file yaml support. [Thomas Weißgerber]

  # Conflicts:
  #	.bumpversion.cfg
  #	CHANGELOG.rst
  #	README.DEV.md
  #	docs/conf.py
  #	docs/projects/pypadre.rst
  #	docs/related_projects.rst
  #	poetry.lock
  #	pyproject.toml

Changes
~~~~~~~
- Updated Readme's. [Thomas Weißgerber]

Fix
~~~
- Managing git repository for Ipython notebooks. [mehdi]
- Removed comment. [Thomas Weißgerber]
- Updated the doc to include references to other projects. [Thomas
  Weißgerber]

Other
~~~~~
- Bump version: 0.2.0 → 0.2.1. [Thomas Weißgerber]


0.2.0 (2020-06-22)
------------------
- Bump version: 0.1.20 → 0.2.0. [Thomas Weißgerber]


0.1.20 (2020-05-19)
-------------------
- Bump version: 0.1.19 → 0.1.20. [Thomas Weißgerber]


0.1.19 (2020-05-19)
-------------------
- Bump version: 0.1.18 → 0.1.19. [Thomas Weißgerber]


0.1.18 (2020-05-19)
-------------------
