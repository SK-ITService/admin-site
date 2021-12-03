# This module contains the implementation of the XML-RPC API used by the
# client.

import system.proxyconf
import system.utils
import hashlib
import requests
import logging

from datetime import datetime, timedelta
from django.conf import settings

from .models import PC, Site, Distribution, Configuration, ConfigurationEntry
from .models import PackageList, Package, PackageStatus, CustomPackages
from .models import Job, Script, SecurityProblem, SecurityEvent
from .models import CiceroPatron


def register_new_computer(mac, name, distribution, site, configuration):
    """Register a new computer with the admin system - after registration, the
    computer will be submitted for approval."""

    # Hash our uid
    uid = hashlib.md5(mac.encode("utf-8")).hexdigest()

    try:
        new_pc = PC.objects.get(uid=uid)
        package_list = new_pc.package_list
        custom_packages = new_pc.custom_packages
    except PC.DoesNotExist:
        new_pc = PC(name=name, uid=uid)
        new_pc.site = Site.objects.get(uid=site)
        # TODO: Better to enforce existence of package list in AfterSave
        # signal.
        package_list = PackageList(name=name)
        custom_packages = CustomPackages(name=name)

    new_pc.distribution = Distribution.objects.get(uid=distribution)
    new_pc.is_activated = False
    new_pc.mac = mac
    # Create new configuration, populate with data from computer's config.
    # If a configuration with the same ID is hanging, reuse.
    config_name = "_".join([site, name, uid])
    try:
        my_config = Configuration.objects.get(name=config_name)
    except Configuration.DoesNotExist:
        my_config = Configuration()
        my_config.name = config_name
    finally:
        # Delete pre-existing entries
        entries = ConfigurationEntry.objects.filter(owner_configuration=my_config)
        for e in entries:
            e.delete()
    my_config.save()
    # And load configuration

    # Update configuration with uid
    configuration.update({"uid": uid})

    # Update configuration with os2 product
    # New image versions set it themselves, old don't so for those
    # we detect and set it this way
    if "os2_product" not in configuration:
        if "os2borgerpc_version" in configuration:
            product = "os2borgerpc"
        else:
            product = "os2displaypc"
        configuration.update({"os2_product": product})

    for k, v in list(configuration.items()):
        entry = ConfigurationEntry(key=k, value=v, owner_configuration=my_config)
        entry.save()
    # Tell us about yourself
    new_pc.do_send_package_info = True
    # Set and save PmC
    new_pc.configuration = my_config
    package_list.save()
    new_pc.package_list = package_list
    custom_packages.save()
    new_pc.custom_packages = custom_packages
    new_pc.save()
    return uid


def upload_dist_packages(distribution_uid, package_data):
    """This will upload the packages and package versions for a given
    BibOS distribution. A BibOS distribution is here defined as a completely
    fresh install of a standardized Debian-like system which is to be supported
    by the BibOS admin."""

    if distribution_uid in settings.CLOSED_DISTRIBUTIONS:
        # Ignore
        return 0

    distribution = Distribution.objects.get(uid=distribution_uid)

    if package_data is not None:
        distribution.package_list.packages.clear()

        for pd in package_data:
            # First, assume package & version already exists.
            try:
                p = Package.objects.get(name=pd["name"], version=pd["version"])
            except Package.DoesNotExist:
                p = Package.objects.create(
                    name=pd["name"],
                    version=pd["version"],
                    description=pd["description"],
                )
            finally:
                PackageStatus.objects.create(
                    package=p,
                    package_list=distribution.package_list,
                    status=pd["status"],
                )
    return 0


def send_status_info(pc_uid, package_data, job_data, update_required):
    """Update package lists as well as the status of outstanding jobs.
    If no updates of package or job data, these will be None. In that
    case, this function really works as an "I'm alive" signal."""

    # TODO: Code this

    # 1. Lookup PC, update "last_seen" field
    pc = PC.objects.get(uid=pc_uid)

    if not pc.is_activated:
        # Fail silently
        return 0

    pc.last_seen = datetime.now()
    pc.save()

    # 2. Update package lists with package data
    if package_data and pc.do_send_package_info:
        # Ignore if we didn't ask for this

        # Clear existing packages
        pc.package_list.packages.clear()

        # Insert new ones
        # package_data is a list of dicts with the correct field names.
        for pd in package_data:
            # First, assume package & version already exists.
            try:
                p = Package.objects.get(name=pd["name"], version=pd["version"])
            except Package.DoesNotExist:
                p = Package.objects.create(
                    name=pd["name"],
                    version=pd["version"],
                    description=pd["description"],
                )
            finally:
                PackageStatus.objects.create(
                    package=p, package_list=pc.package_list, status=pd["status"]
                )
        # Assume no packages are any longer "pending".
        pc.custom_packages.update_by_package_names(
            pc.pending_packages_remove, pc.pending_packages_add
        )
        # We just got the package info update we requested, so clear the flag
        # until we need a new update.
        pc.do_send_package_info = False

    # 3. Update jobs with job data
    if job_data is not None:
        for jd in job_data:
            job = Job.objects.filter(pk=jd["id"]).first()
            if not job:
                continue
            job.status = jd["status"]
            job.started = jd["started"]
            job.finished = jd["finished"]
            job.log_output = jd["log_output"]
            job.save()

    # 4. Check if update is required.
    if update_required is not None:
        updates, security_updates = list(map(int, update_required))
        if security_updates > 0:
            pc.is_update_required = True
            # See if things have changed and we need to update the package
            # lists.
            old_updates = int(pc.configuration.get("updates", 0))
            old_security = int(pc.configuration.get("security_updates", 0))
            if (security_updates > old_security) or (updates > old_updates):
                pc.do_send_package_info = True
            else:
                pc.do_send_package_info = False
        elif pc.is_update_required:
            pc.is_update_required = False
        # Save update info in configuration
        pc.configuration.update_entry("updates", updates)
        pc.configuration.update_entry("security_updates", security_updates)

    pc.save()

    return 0


def get_instructions(pc_uid, update_data):
    """This function will ask for new instructions in the form of a list of
    jobs, which will be scheduled for execution and executed upon receipt.
    These jobs will generally take the form of bash scripts."""

    pc = PC.objects.get(uid=pc_uid)

    pc.last_seen = datetime.now()
    pc.save()

    if not pc.is_activated:
        # Fail silently
        return ([], False)

    update_pkgs = update_data.get("updated_packages", [])
    if len(update_pkgs) > 0:
        for pdata in update_pkgs:
            # Find or create the package in the global collection of packages
            try:
                p = Package.objects.get(name=pdata["name"], version=pdata["version"])
            except Package.DoesNotExist:
                p = Package(
                    name=pdata["name"],
                    version=pdata["version"],
                    description=pdata["description"],
                )
                p.save()
            # Change or create the package status for the package/PC
            p_status = pc.package_list.statuses.filter(
                package__name=pdata["name"],
            ).delete()
            p_status = PackageStatus(
                status="install", package=p, package_list=pc.package_list
            )
            p_status.save()

            pc.package_list.statuses.filter(
                package__name=pdata["name"],
                package__version=pdata["version"],
            ).update(status="installed ok")

    remove_pkgs = update_data.get("removed_packages", [])
    if len(remove_pkgs) > 0:
        pc.package_list.statuses.filter(package__name__in=remove_pkgs).delete()

    # Get list of packages to install and remove.
    to_install, to_remove = pc.pending_package_updates

    # Add packages that are pending update to the list of packages we want
    # installed, as apt-get will upgrade any package in the package list
    # for apt-get install.
    for p in pc.package_list.pending_upgrade_packages:
        to_install.add(p.name)

    # Make sure packages added to be upgraded now are no longer pending.
    pc.package_list.flag_needs_upgrade(
        [p.name for p in pc.package_list.pending_upgrade_packages]
    )

    # Make sure packages we just installed are not flagged for removal
    for name in [p["name"] for p in update_pkgs]:
        if name in to_remove:
            pc.custom_packages.update_package_status(name, True)
            to_remove.remove(name)

    # Make sure packages we just removed are not flagged for installation
    for name in remove_pkgs:
        if name in to_install:
            pc.custom_packages.update_package_status(name, False)
            to_install.remove(name)

    jobs = []
    for job in pc.jobs.filter(status=Job.NEW).order_by("pk"):
        job.status = Job.SUBMITTED
        job.save()
        jobs.append(job.as_instruction)

    security_objects = []
    # First check for security scripts covering the site
    site_security_problems = SecurityProblem.objects.filter(site_id=pc.site).exclude(
        alert_groups__isnull=False
    )

    for security_problem in site_security_problems:
        security_objects.append(insert_security_problem_uid(security_problem))

    # Then check for security scripts covering groups the pc is a member of.
    pc_groups = pc.pc_groups.all()
    if len(pc_groups) > 0:

        for group in pc_groups:
            security_problems = SecurityProblem.objects.filter(alert_groups=group.id)
            if len(security_problems) > 0:
                for problem in security_problems:
                    security_objects.append(insert_security_problem_uid(problem))

    scripts = []

    for script in security_objects:
        if script["is_security_script"] == 1:
            s = {"name": script["name"], "executable_code": script["executable_code"]}
            scripts.append(s)

    result = {
        "security_scripts": scripts,
        "jobs": jobs,
        "configuration": pc.get_full_config(),
    }

    if pc.do_send_package_info:
        result["do_send_package_info"] = True

    return result


def insert_security_problem_uid(securityproblem):
    script = Script.objects.get(security_problems=securityproblem)
    code = script.executable_code.read().decode("utf8")
    code = str(code).replace("%SECURITY_PROBLEM_UID%", securityproblem.uid)
    s = {
        "name": securityproblem.uid,
        "executable_code": code,
        "is_security_script": script.is_security_script,
    }
    return s


def get_proxy_setup(pc_uid):
    pc = PC.objects.get(uid=pc_uid)
    if not pc.is_activated:
        return 0
    return system.proxyconf.get_proxy_setup(pc_uid)


def push_config_keys(pc_uid, config_dict):
    pc = PC.objects.get(uid=pc_uid)
    if not pc.is_activated:
        return 0

    # We need two config dicts: one from the PC itself and one from groups
    # and global configuration
    config_lists = pc.get_list_of_configurations()

    pc_config_list = config_lists.pop()

    pc_config = {}
    for entry in pc_config_list.entries.all():
        pc_config[entry.key] = entry.value

    others_config = {}
    for conf in config_lists:
        for entry in conf.entries.all():
            others_config[entry.key] = entry.value

    for key, value in list(config_dict.items()):
        # Special case: If the value we want is in others_config, we just have
        # to remove any pc-specific config:
        if key in others_config and others_config[key] == value:
            if key in pc_config:
                pc.configuration.remove_entry(key)
        else:
            pc.configuration.update_entry(key, value)

    return True


def push_security_events(pc_uid, csv_data):
    pc = PC.objects.get(uid=pc_uid)

    for data in csv_data:
        csv_split = data.split(",")
        try:
            security_problem = SecurityProblem.objects.get(uid=csv_split[1])

            new_security_event = SecurityEvent(problem=security_problem, pc=pc)
            new_security_event.ocurred_time = datetime.strptime(
                csv_split[0], "%Y%m%d%H%M"
            )
            new_security_event.reported_time = datetime.now()
            new_security_event.summary = csv_split[2]
            new_security_event.complete_log = csv_split[3]
            new_security_event.save()
        except IndexError:
            return False

        # Notify subscribed users
        system.utils.notify_users(csv_split, security_problem, pc)

    return 0


def cicero_login(username, password, site):
    """Check if user is allowed to log in and give the go-ahead if so.

    Return values:
        -1: Unable to authenticate.
         0: No time remaining, i.e. user is quarantined.
        >0: The number of minutes the user is allowed.
    """

    logger = logging.getLogger(__name__)
    time_allowed = -1
    try:
        site = Site.objects.get(uid=site)
    except Site.DoesNotExist:
        logger.error(f"Site {site} does not exist - unable to proceed.")
        return time_allowed
    patron_id = cicero_validate(username, password, site.isil)

    if patron_id:
        patron_hash = hashlib.sha512(str(patron_id).encode()).hexdigest()
        now = datetime.now()
        time_allowed = int(
            site.configuration.get(settings.USER_LOGIN_DURATION_CONF, 30)
        )
        # Get previous login, if any.
        try:
            patron = CiceroPatron.objects.get(patron_id=patron_hash)
        except CiceroPatron.DoesNotExist:
            patron = None

        if patron:
            quarantine_time = site.configuration.get(
                settings.USER_QUARANTINE_DURATION_CONF, 2
            )
            quarantine_time = int(quarantine_time)
            if (now - patron.last_successful_login) > timedelta(hours=quarantine_time):
                patron.last_successful_login = now
                patron.save()
            elif now - patron.last_successful_login < timedelta(minutes=time_allowed):
                time_allowed = (
                    time_allowed - (now - patron.last_successful_login).seconds // 60
                )
            else:
                time_allowed = 0
        else:
            # First-time login, all good.
            patron = CiceroPatron(
                patron_id=patron_hash, last_successful_login=now, site=site
            )
        patron.save()

    return time_allowed


def cicero_validate(loaner_number, pincode, agency_id):
    """Do the actual validation against the Cicero service.

    If successful, this function will return the Cicero Patron ID, otherwise it
    will return something falsey like None, 0 or ''.
    """
    logger = logging.getLogger(__name__)
    try:
        pincode = int(pincode)
    except ValueError:
        logger.error(f"Pincode must be a number - {pincode} is not  number.")
        return 0
    if not agency_id:
        logger.error("Agency ID / ISIL MUST be specified.")
        return 0
    # First, get sessionKey.
    session_key_url = (
        f"{settings.CICERO_URL}/rest/external/v1/{agency_id}/authentication/login/"
    )
    response = requests.post(
        session_key_url,
        json={"username": settings.CICERO_USER, "password": settings.CICERO_PASSWORD},
    )
    if response.ok:
        session_key = response.json()["sessionKey"]
        # Just debugging for the moment.
    else:
        # TODO: Unable to authenticate with system user - log this.
        message = response.json()["message"]
        logger.error(
            f"Unable to log in with configured user name and password: {message}"
        )
        return 0
    # We now have a valid session key.
    loaner_auth_url = (
        f"{settings.CICERO_URL}/rest/external/{agency_id}/patrons/authenticate/v6"
    )
    response = requests.post(
        loaner_auth_url,
        headers={"X-session": session_key},
        json={"libraryCardNumber": loaner_number, "pincode": pincode},
    )
    if response.ok:
        result = response.json()
        authenticate_status = result["authenticateStatus"]
        print(authenticate_status)
        if authenticate_status != "VALID":
            logger.error(
                f"Unable to authenticate with loaner ID and pin: {authenticate_status}"
            )
            return 0
        # Loaner has been successfully authenticated.
        patron_id = result["patron"]["patronId"]
        return patron_id

    print(response)
