Version 5.2.1, January 3, 2022
--------------------------------

Hotfix:

- Added SERVER_EMAIL in settings to enable crash email.


Version 5.2.0, November 25, 2021
--------------------------------

New in this version:

- Added RPC endpoint for citizen/audience login for integration with a
  third-party authentication system like Cicero (e.g.).
- Added Citizen model to represent logged-in citizens.
- Site edit restored in frontend - this allows library users to change
  user login & quarantine durations.
- Site ID no longer displayed in configuration.
- Performance: Packages, package lists and distributions are removed.
- Upgraded to Django 3.2.9 - newer versions of a lot of other packages
  as well.

Version 5.1.1, October 20, 2021
-------------------------------

New in this version:

- Fix bug making it difficult to add policy scripts

Version 5.1.0, October 20, 2021
-------------------------------

New in this version:

- Fix bug not allowing script running on groups
- Fix bug not allowing job restart or copy-pasting the log
- Fix hover on pagination buttons, now indicating they're clickable
- Fix add new policy script, so clicking on the local/global badge adds the script as well.
- Wider, more readable job log window
- Scroll in job log and policy script search windows instead of the entire page
- Add information about online/offline, active/inactive computers on status page
  Related: For pcs that aren't activated, don't show the status instead of showing "Offline".
- /admin/ improments to AssociatedScripts and Configurations

Version 5.0.0, August 8, 2021
-----------------------------

New in this version:

- Overhaul user interface.
- Add pagination on Jobs and SecurityEvents.
- Add Script categories.
- Overhaul Script model (created by, updated by, maintained by magenta, author fields).
- Add Script search.
- Make local scripts deletable.
- Make groups deleteable.
- Add Django admin improvements (jobs run per script, number of computers per site etc.).
- Add generic Magenta login page.
- Remove create, update, delete capabilities for Sites.
- Overhaul documentation.
- Update translations
- Update jQuery to 3.5.1.
- Update Bootstrap to version 5.


Version 4.3.2, June 30, 2021
----------------------------

New in this version:

- Fixed bug allowing users to be deleted even if they've 
  run a script or have been assigned a security issue.
- Add reference in README to Read the Docs documentation 

Version 4.3.1, June 21, 2021
----------------------------

New in this version:

- Prevent users from seeing local scripts on other sites.
- Enable setting of Google Cloud Storage custom endpoint.
- Avoid crash (HTTP 500) on /sites/ URL when not logged in.


Version 4.3.0, May 11, 2021
---------------------------

New in this version:

- Allow users to be on multiple sites so they don't need to have more
  than one login.
- Fixed bug so that user type can now be changed in GUI.
- Fix failing documentation links.
- Update technical documentation and move it to Read The Docs.
- Improved site information in admin site.


Version 4.2.0, April 9, 2021
----------------------------

New in this version:

- "BibOS" renamed to "OS2borgerPC" everywhere.
- Packages functionality removed from front end.
- Navigation error when deleting PC fixed.
- django-extensions added for shell-plus capabilities.
- Avoid file clashes in Google Cloud Storage.
- Security fix: Django upgraded to version 3.1.8.


Version 4.1.6, January 28, 2021
-------------------------------

New in this version:

- Proper setup of logging - adjustable log level to stdout, ERROR and above
  always emailed to admins.
- A number of crashes (HTTP 500) on missing resources fixed (return 404 instead).


Version 4.1.5, January 27, 2021
-------------------------------

New in this version:

- Files from Google data buckets (MEDIA_ROOT) are served with
  signed-urls.


Version 4.1.4, January 25, 2021
-------------------------------

New in this version:

- Collectstatic is run at build time, not at startup.


Version 4.1.3, January 21, 2021
-------------------------------

New in this version:

- Don't crash (HTTP 500) if script code is not found - allow user to reupload.
- Fix handling of paths to MEDIA_ROOT in Docker image.
- Standardize handling of static media (CSS, Javascript, etc.).


Version 4.1.2, January 19, 2021
-------------------------------

New in this version:

- Application crashes if DB not correctly configured or mandatory
  settings are absent.
- Support for Google Cloud Storage.
- Ensure that ALLOWED_HOSTS is a list.
- Set 2s timeout for database connections.


Version 4.1.1, January 12, 2021
-------------------------------

New in this version:

- Fixed bug in CI script.


Version 4.1.0, January 12, 2021
-------------------------------

New in this version:

- Server now to be deployed with Docker.
- Gitlab CI added, including automatic build and push of new Docker images.
- Development environment with docker-compose.
- Documentation updated accordingly.
- Deprecated installation methods removed.


Version 4.0.0, December 10, 2020
--------------------------------

New in this version:

- Support for image versions in admin system.
- Upgraded to Python 3.8 and Django 3.1.4.
- Client: Replaced the lock file logic to better support failure
  recovery.


Version 3.1.3, October 18, 2019
-------------------------------

Bugfix release. Fixed in this version:

- #27486: Policy scripts are now executed when a borgerpc is added to a group through the computer-view.
- #30173: Scripts parameters are now being saved in the right order, to avoid integrityerror.
- #30520: All documentation pages are accessible again.
- #31066: Forward slashes in group names are now supported. 


Version 3.1.2.1, June 27, 2019
------------------------------

Infrastructural release. Fixed in this version:

- #27325: Deploying new versions should no longer result in migration conflicts


Version 3.1.1, March 25, 2019
-----------------------------

Minor bugfix release. Fixed in this version:

- #23873: The assignee list for security warnings is now a list of site users rather than system users
- #27408: The script list used when constructing a group policy is now in alphabetical order
- #27432: Policy script file parameter validation no longer demands that files be re-uploaded


Version 3.1.0, February 25, 2019
--------------------------------

- Support for associating scripts with groups (policies)
- Logging out of the admin system now works more reliably
- Users with staff access no longer have access to other sites' user information
- Bumped the bibos_client version to 0.0.5.0:
  - To support policies, clients now run scripts in a predictable order
  - Clients now send their bibos_client version to the administration system
- Bumped the bibos_utils version to 0.0.3.1:
  - A bug that could occasionally clear client configuration files has been fixed


Version 3.0.1, January 16, 2019
-------------------------------

- json data exposing existing computers on a given site can now be reached from %domain%/%site_id%/computers/json/ 


Version 3.0.0.3, Juli 02, 2018
------------------------------

Hotfix. New in this version:

 - Empty strings should only be used when checking input-fields


Version 3.0.0.2, Juni 28, 2018
------------------------------

Hotfix. New in this version:

 - Make the input-fields work again in script parameters


Version 3.0.0.1, Juni 13, 2018
------------------------------

Hotfix. New in this version:

 - Fix error in login
 - Correct the var path
 - Make bibos_client upgrade and remove netifaces requirement


Version 3.0.0, Juni 5, 2018
---------------------------

- Python 3 and Django 1.11 compatible code (admin-site)
- “Removal” of the upgrade management
- Jobs are now associated with a user
- UID is generated on the admin side
- settings.py uses an environment-file to differentiate dev/prod
- Post install script added for development

Version 2.3.3.1, February 23, 2017
----------------------------------

Hotfix. New in this version:

- Bumped bibos_client number to 0.3.2


Version 2.3.3, February 23, 2017
--------------------------------

- Ubuntu 16.04 is added as a closed distribution.


Version 2.3.2, October 24, 2016
-------------------------------

- If no network connection, lock for jobmanager is released.
- Documentation has been added, describing that the system is not 
  showing security events until after the computer package list 
  has been uploaded.
- Lokationsfeldt er blevet tilføjet til computerne, og dato format 
  ændret til dansk.


Version 2.3.1, September 22, 2016
---------------------------------

- Backwards compatibility: If security dir is missing, security is ignored.
- Migrations committed, WSGI script is fixed.
- Performance improvements (don't load all jobs and batches)
- Technical documentation was broken after upgrade to Django 1.8.
- Allow one security script to work with several rules.
- The version number for the bibos_client is bumped to 0.0.3.1.


Version 2.3.0, June 30, 2016
----------------------------

- Security warnings are added - a whole new subsystem which can generate
  warnings about suspicious activity on the client computers. It is
  possible to create security scripts, which will run on the clients,
  detect events and create corresponding security warnings. It is
  possible to see a list of active computers & thus to detect if the
  admin system has lost contact to certain computers, which my be used
  to wrong purposes.
- Bug in date format is fixed.
- System is upgraded to Django 1.8.
- The version number for the bibos_client is bumped to 0.0.3.0. It now 
  supports the security warning subsystem.


Version 2.2.5.1,  April 6, 2016
-------------------------------

Hotfix. New in this version:

- Add LoginRequired mixin to the PC Update view.


Version 2.2.5.1,  March 21, 2016
--------------------------------

Hotfix. New in this version:

- The version number for the bibos_client is bumped to 0.0.2.6.


Version 2.2.5,  March 21, 2016
------------------------------

New in this version:

- Upon registration to the admin system, the bibos client tries to auto
  detect the operating system so the correct distribution will be chosen.


Version 2.2.4,  June 13, 2014
-----------------------------

Rollback of model changes in hotfix 2.2.3.2, retain failed upgrade management.

- The model changes, i.e. the bookkeeping with added and removed packages,
  caused serious performance problems. These have been rolled back.
- The changes that set "pending upgrade" packages back to "upgrade possible",
  i.e. to avoid automatic generation of new job upon failure, has been
  retained. This solves the problem the libraries were having in practise.

This version should be considered stable. At the time of writing, we're not
aware of any serious issues.


Version 2.2.3.1,  June 3, 2014
------------------------------

Hotfix. New in this version:

- During update of package info, clear lists of submitted packages instead of
  cycling through them. Note, this is an optimistic strategy. The goal is to
  avoid the catastrophic performance problems which were presumably due to the
  recalculation of these lists against all installed packages.


Version 2.2.3,  May 28, 2014
----------------------------

New in this version:

- Prevent package upgrades from looping upon failure. This is done by removing
  submitted package upgrades from the "to upgrade" list, so they're not picked
  up next time the job manager runs.


Version 2.2.2, February 4, 2014
-------------------------------

New in this version:

- Fixed type bug (comparison between integers and strings) which caused the
  performance issue to regress (ticket #9611).


Version 2.2.1, February 3, 2014
-------------------------------
New in this version:

- Package lists are only synchronized between client and server if number of
  updates changes (solves performance issue cf. ticket #9611).
- Design bug when adding to long list of groups fixed, cf. ticket #9097.
- Crash when trying to sort job list under PC fixed (ticket #9548).
- Developer documentation updated and improved.


Version 2.2.0, December 27, 2013
--------------------------------
New in this version:

- Stale locks are avoided by introducing Unix-style file locking instead.
  Previously, a crashed job would leave a dangling log on the client computers,
  which in turn would cause the job manager to terminate immediately, because
  it thought that another instance was running. This meant that the admin
  system would lose all contact with the machine and the lock had to be removed
  manually for the admin system's control with it to resume - yielding bugs
  such as #9320. With the new locking style, a lock set by a process will always
  disappear when the process terminates. This means that crashing jobs can no
  longer cause a client computer to lose contact with the admin server.

This is the first "final release" following the critical bug fixes in the 2.1.*
series, and this version concludes the first phase of the BibOS Admin project.


Version 2.1.2, December 23, 2013
--------------------------------

New in this version:

- Performance problem in jobs list is solved by allowing user to choose between
  different lengths (cf. ticket #9301).
- Status label to be shown translated on PC job lists (ticket #9339).
- Stay on selected PC even if it's in the bottom of a very long list of
  computers (ticket #9342).


Version 2.1.1.3, December 17, 2013 (hotfix)
-------------------------------------------

New in this version:

- bibos-client fixed so that it always sends status info - not only when jobs
  are executed, cf. ticket #9634.
- Server fixed so that packages pending for installation are always installed,
  even if we ask the client to upgrade its package info - also cf. #9634.


Version 2.1.1.1, December 4, 2013
---------------------------------

New in this version:

- The system defined "wanted packages" as packages in the *distribution*
  plus/minus the packages that were explicitly added or removed through the
  admin interface. This means that packages that were installed manually or
  through a script on the individual computer would be removed because they
  were neither in the distribution nor in the add list, and packages in the
  distribution that were removed on the individual computer would be added.

  Since the gateway needs a number of packages that were not added through the
  admin interface, this means it was basically nuked as soon as the
  synchronization started working, as we've seen with ticket #9383.

  From now on, the system will define "wanted packages" as *all packages
  currently present on the machine* plus all packages explicitly added in the
  admin system, minus all packages explicitly removed through the admin system.

  This creates a new problem, namely that packages which were added (or removed)
  through a group will no longer be automatically removed (or added,
  respectively) when a computer is removed from the group. That should probably
  be dealt with by a special field which specifies whether a package was added
  through group membership and should be removed if it's no longer demanded by
  any group. This is a task for a future version of the system.


Version 2.1.1, November 25, 2013
--------------------------------

New in this version: 

- File parameters were renamed when running scripts more than once, #9100.
- User interface bug would hide group list if a group had many computers in it,
  #9097.
- Major overhaul of user interface.
- Update synchronization improved (not fixed).


Version 2.1.0, October 11, 2013
-------------------------------

New in this version:

A lot of bugs have been fixed, and the design has been thoroughly
polished. 

A brief summary:

- Spaces and other special characters are now allowed (though discouraged, 
  in the case of spaces *strongly* discouraged) in URLs.
- JQuery is hosted locally and not loaded from another host.
- "System" site is added to host system scripts.
- Scripts to install LibreOffice 4 and Oracle's Java are added.
- The documentation has been finished.
- Technical documentation in source code is included on the admin site as
  well.
- Localization infrastructure is introduced to permit translation (currently
  Danish is only supported locale).
- Creative Commons Attribution-ShareAlike license has been added for
  the documentation.
- bibos-client has been changed to support wireless networks.
- System now supports fixed gateway/proxy configured by IP address, not just
  auto-detection.
- Computers may be deleted from the admin system.
- Only superadmins may edit global scripts.

Executive summary:

- Status moves from "beta" to "production".


Version 2.0.2, July 12, 2013
----------------------------

New in this version:

- Everything is functional now
- Status moves from "mockup" to beta

