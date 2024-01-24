`Changelog <https://github.com/feenes/timon/releases>`__
========================================================

`v0.4.0 <https://github.com/feenes/mytb/compare/v0.3.2...v0.4.0>`__
-------------------------------------------------------------------
Bump to Python 3.11+ (drop support for olders)

Features
- #77 Better messages for HttpJsonProbes
- #78 #80 Web interface have the worst status color in the column header
- #83 Web interface: Add a worst status counter in column headers
- #87 Add HttpJsonTimeoutProbe that permits checking the timestamp in a json
- #91 Add paranoia-loop (-p) to the run command
- #92 Add Timon Plugins
- #92 #97 #101 Add an Http Server Plugin
- #98 #100 Add a Db store for probe results and probe status changes
- #104 Add an extra field in probe config for all extra data unused by probes

Bugs
- #81 Set probe status to ERROR instead of UNKNOWN for http response statuses differents of 200 and 404
- #86 Fix Web Interface Notifications
- #88 Fix ClientCACheck with TLS 1.3
- #89 Fix don't fail if hprobes is None
- #102 Fix notifiers that crash timon

Coding style / CI
- #83 Web interface refactorisation of table population
- #95 Cleanup: change from print to logs
- #103 Remove trio framework and use asyncio only

`v0.3.2 <https://github.com/feenes/mytb/compare/v0.3.1...v0.3.2>`__
-------------------------------------------------------------------
Features
- #43 + #53 now there's a --pdb and a --pdb-hook switch
- #70 + #72 add flap detection
- #64 add timeout for subprocess probes to avoid too long freezes
- #44 notifiers no more compulsory
- #66 add retry for isup probe
- #65 + #67 add timeout detection for webif
- change isup timeout
- allow sub second delays for shell loop

Bugs
- #71 fix rsrc limits (introduced during refactoring)
- #72 fix http probe bugs (url_params, ...) + tests
- #68 fix scheduler bug
- fix cert bug for async requests
- #61 fix increasing timeout
- #52 fail interal was not dumped properly

Testing
- #51 attempts for debugging / testing the scheduler

Coding style / CI
- #47 refactor probe initialisation 
- #49 old coroutine / yield syntax has been removed
- #58 coding style check now for isort
- #57 use github actions for CI
- #59 add isort check for CI. no flake for pypy
- #46 refactor resources and modernize some code
`v0.3.1 <https://github.com/feenes/mytb/compare/v0.3.0...v0.3.1>`__
-------------------------------------------------------------------

-  Probe: OneUrlHttpJsonIntervalProbe (a value has to be in a certain
   range)
-  Probe: ClientCA Probe. to whether servers accept client certs
-  Webif: Notification permission requested when loading page (and not
   at first notif)
-  Notifier: Posting request to external url
-  fixing some package meta data
-  fixed setup for gitlab-ci runners
-  fix CI runners (enter and leave subdirs)
-  flake fixes
-  cleanup. rename var (double reversed logic)

`v0.3.0 <https://github.com/feenes/mytb/compare/v0.2.0...v0.3.0>`__
-------------------------------------------------------------------
-  web-if: servers in table view can be grouped
-  a prebuilt version of the web interface is now part of the repository
-  resource limits can be set via env vars
-  robustify web-if: server notification
-  robostify web-if: handling of missing hosts
-  add helper to build webif
-  update some node dependencis for web-if
-  some code cleanup for python and js

`v0.2.0 <https://github.com/feenes/mytb/compare/0.1.0...v0.2.0>`__
-------------------------------------------------------------------
-  first version with front end browser notifications on state changes
