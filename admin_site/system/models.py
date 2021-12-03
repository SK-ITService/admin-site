import datetime
import random
import string
import re
import os.path
from distutils.version import LooseVersion

from dateutil.relativedelta import relativedelta

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings

from system.mixins import AuditModelMixin
from system.managers import SecurityEventQuerySet

"""The following variables define states of objects like jobs or PCs. It is
used for labeling in the GUI."""

# States
NEW = _("status:New")
FAIL = _("status:Fail")
UPDATE = _("status:Update")
OK = ''

# Priorities
INFO = 'info'
WARNING = 'warning'
IMPORTANT = 'important'
NONE = ''


class Configuration(models.Model):
    """This class contains/represents the configuration of a Site, a
    Distribution, a PC Group or a PC."""
    # Doesn't need any actual fields, it seems. Should not exist independently
    # of the classes to which it may be aggregated.
    name = models.CharField(max_length=255, unique=True)

    def update_from_request(self, req_params, submit_name):
        seen_set = set()

        existing_set = set(cnf.pk for cnf in self.entries.all())

        unique_names = set(req_params.getlist(submit_name, []))
        for pk in unique_names:
            key_param = "%s_%s_key" % (submit_name, pk)
            value_param = "%s_%s_value" % (submit_name, pk)

            key = req_params.getlist(key_param, '')
            value = req_params.getlist(value_param, '')

            if pk.startswith("new_"):
                # Create one or more new entries
                for k, v in zip(key, value):
                    cnf = ConfigurationEntry(
                        key=k,
                        value=v,
                        owner_configuration=self
                    )
                    cnf.save()
            else:
                # Update submitted entry
                cnf = ConfigurationEntry.objects.get(pk=pk)
                cnf.key = key[0]
                cnf.value = value[0]
                seen_set.add(cnf.pk)
                cnf.save()

        # Delete entries that were not in the submitted data
        for pk in existing_set - seen_set:
            cnf = ConfigurationEntry.objects.get(pk=pk)
            cnf.delete()

    def remove_entry(self, key):
        return self.entries.filter(key=key).delete()

    def update_entry(self, key, value):
        try:
            e = self.entries.get(key=key)
            e.value = value
        except ConfigurationEntry.DoesNotExist:
            e = ConfigurationEntry(
                owner_configuration=self,
                key=key,
                value=value
            )
        finally:
            e.save()

    def get(self, key, default=None):
        """Return value of the entry corresponding to key if it exists, None
        otherwise."""
        result = None
        try:
            e = self.entries.get(key=key)
            result = e.value
        except ConfigurationEntry.DoesNotExist:
            if default is not None:
                result = default
            else:
                raise

        return result

    def __str__(self):
        return self.name


class ConfigurationEntry(models.Model):
    """A single configuration entry - always part of an entire
    configuration."""
    key = models.CharField(max_length=32)
    value = models.CharField(max_length=4096)
    owner_configuration = models.ForeignKey(
        Configuration,
        related_name='entries',
        verbose_name=_('owner configuration'),
        on_delete=models.CASCADE,
    )


class Package(models.Model):
    """This class represents a single Debian package to be installed."""
    name = models.CharField(verbose_name=_('name'), max_length=255)
    version = models.CharField(verbose_name=_('version'), max_length=255)
    description = models.CharField(verbose_name=_('description'),
                                   max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'version'],
                name="unique_version_name"),
        ]


class CustomPackages(models.Model):
    """A list of packages to be installed on a PC or to be included in a
    distribution."""

    class Meta:
        verbose_name_plural = "Custom packages"

    name = models.CharField(verbose_name=_('name'), max_length=255)
    packages = models.ManyToManyField(Package,
                                      through='PackageInstallInfo',
                                      blank=True)

    def update_by_package_names(self, addlist, removelist):
        add_packages_old = set()
        remove_packages_old = set()

        for ii in self.install_infos.all():
            if ii.do_add:
                add_packages_old.add(ii.package.name)
            else:
                remove_packages_old.add(ii.package.name)

        for oldlist, newlist, addflag in [
            (add_packages_old, set(addlist), True),
            (remove_packages_old, set(removelist), False),
        ]:
            # Add new add-packages
            for name in newlist - oldlist:
                try:
                    package = Package.objects.filter(name=name)[0]
                except IndexError:
                    package = Package.objects.create(name=name)

                ii = PackageInstallInfo(
                    custom_packages=self,
                    package=package,
                    do_add=addflag
                )
                ii.save()
            # Remove unwanted add-packages
            qs = PackageInstallInfo.objects.filter(
                do_add=addflag,
                custom_packages=self,
                package__name__in=list(oldlist - newlist)
            )
            qs.delete()

    def update_package_status(self, name, do_add):
        # Delete any old reference
        self.install_infos.filter(
            package__name=name
        ).delete()

        # And create a new
        try:
            package = Package.objects.filter(name=name)[0]
        except IndexError:
            package = Package.objects.create(name=name)

        ii = PackageInstallInfo(
            custom_packages=self,
            package=package,
            do_add=do_add
        )

        ii.save()

    def __str__(self):
        return self.name


class PackageInstallInfo(models.Model):
    do_add = models.BooleanField(default=True)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    custom_packages = models.ForeignKey(CustomPackages,
                                        related_name='install_infos',
                                        on_delete=models.PROTECT)

    def __str__(self):
        return self.name


class PackageList(models.Model):
    """A list of packages to be installed on a PC or to be included in a
    distribution."""
    name = models.CharField(verbose_name=_('name'), max_length=255)
    packages = models.ManyToManyField(Package,
                                      through='PackageStatus',
                                      blank=True)

    @property
    def names_of_installed_package(self):
        return self.statuses.filter(
            Q(status__startswith='install') |
            Q(status=PackageStatus.NEEDS_UPGRADE) |
            Q(status=PackageStatus.UPGRADE_PENDING)
        ).values_list('package__name', flat=True)

    @property
    def needs_upgrade_packages(self):
        return [s.package for s in self.statuses.filter(
            status=PackageStatus.NEEDS_UPGRADE
        )]

    @property
    def pending_upgrade_packages(self):
        return [s.package for s in self.statuses.filter(
            status=PackageStatus.UPGRADE_PENDING
        )]

    def flag_for_upgrade(self, package_names):
        if len(package_names):
            qs = self.statuses.filter(
                package__name__in=package_names,
                status=PackageStatus.NEEDS_UPGRADE
            )
            num = len(qs)
            qs.update(
                status=PackageStatus.UPGRADE_PENDING
            )
            return num
        else:
            return 0

    def __str__(self):
        return self.name

    def flag_needs_upgrade(self, package_names):
        if len(package_names):
            qs = self.statuses.filter(
                package__name__in=package_names,
                status=PackageStatus.UPGRADE_PENDING
            )
            num = len(qs)
            qs.update(
                status=PackageStatus.NEEDS_UPGRADE
            )
            return num
        else:
            return 0


class PackageStatus(models.Model):
    NEEDS_UPGRADE = 'needs upgrade'
    UPGRADE_PENDING = 'upgrade pending'

    # Note that dpkg can output just about anything for the status-field,
    # but installed packages will all have a status that starts with
    # 'install'

    status = models.CharField(max_length=255)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    package_list = models.ForeignKey(PackageList,
                                     related_name='statuses',
                                     on_delete=models.PROTECT)

    def __str__(self):
        return self.name


class Site(models.Model):
    """A site which we wish to admin"""
    name = models.CharField(verbose_name=_('name'), max_length=255)
    uid = models.CharField(verbose_name=_('UID'), max_length=255, unique=True)
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    paid_for_access_until = models.DateField(
        verbose_name=_("Paid for access until this date"),
        null=True,
        blank=True)
    # Official library number
    # https://slks.dk/omraader/kulturinstitutioner/biblioteker/biblioteksstandardisering/biblioteksnumre

    # Necessary for customers who wish to integrate with standard library login.
    isil = models.CharField(
        verbose_name="ISIL", max_length=10, blank=True,
        help_text=_("Necessary for customers who wish to" +
                    " integrate with standard library login")
        )

    class Meta:
        ordering = ["name"]

    @staticmethod
    def get_system_site():
        try:
            site = Site.objects.get(uid='system').first()
        except Site.DoesNotExist:
            site = Site.objects.create(
                name='system',
                uid='system',
                configuration=Configuration.objects.create(
                    name='system_site_configuration'
                )
            )
        return site

    @property
    def users(self):
        users = User.objects.filter(
            bibos_profile__sites=self
        ).extra(
            select={'lower_name': 'lower(username)'}
        ).order_by('lower_name')

        return users

    @property
    def url(self):
        return self.uid

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Customize behaviour when saving a site object."""
        # Before actual save
        # 1. uid should consist of lowercase letters.
        self.uid = self.uid.lower()
        # 2. Create related configuration object if necessary.
        is_new = self.id is None

        try:
            conf = self.configuration
        except Configuration.DoesNotExist:
            conf = None

        if is_new and conf is None:
            try:
                self.configuration = Configuration.objects.get(
                    name=self.uid
                )
            except Configuration.DoesNotExist:
                self.configuration = Configuration.objects.create(
                    name=self.uid
                )

        # Perform save
        super(Site, self).save(*args, **kwargs)

        # After save
        pass

    def get_absolute_url(self):
        return '/site/{0}'.format(self.url)


class Distribution(models.Model):
    """This represents a GNU/Linux distribution managed by us."""
    name = models.CharField(verbose_name=_('name'), max_length=255)
    uid = models.CharField(verbose_name=_('UID'), max_length=255)
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    # CustomPackages is preferrable here.
    # Maybe we'd like one distribution to inherit from another.
    package_list = models.ForeignKey(PackageList, on_delete=models.PROTECT)

    def __str__(self):
        return self.name


class Error(Exception):
    pass


class MandatoryParameterMissingError(Error):
    pass


class PCGroup(models.Model):
    """Groups of PCs. Each PC may be in zero or many groups."""
    name = models.CharField(verbose_name=_('name'), max_length=255)
    uid = models.CharField(verbose_name=_('id'), max_length=255)
    description = models.TextField(verbose_name=_('description'),
                                   max_length=1024, null=True, blank=True)
    site = models.ForeignKey(
        Site, related_name='groups', on_delete=models.CASCADE
    )
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    custom_packages = models.ForeignKey(
        CustomPackages, on_delete=models.PROTECT
    )

    def __str__(self):
        return self.name

    @property
    def url(self):
        return self.uid

    def save(self, *args, **kwargs):
        """Customize behaviour when saving a group object."""
        # Before actual save
        is_new = self.id is None
        if is_new and self.name:
            self.uid = self.uid.lower()
            related_name = 'Group: ' + self.name
            self.configuration, new = Configuration.objects.get_or_create(
                name=related_name
            )
            self.custom_packages, new = CustomPackages.objects.get_or_create(
                name=related_name
            )
        # Perform save
        super(PCGroup, self).save(*args, **kwargs)

        # After save
        pass

    def update_associated_script_positions(self):
        existing_set = (
            set(asc for asc in self.policy.all().order_by('position')))
        for count, asc in enumerate(existing_set):
            asc.position = count
            self.save()

    def update_policy_from_request(self, request, submit_name):
        req_params = request.POST
        req_files = request.FILES

        seen_set = set()
        existing_set = set(asc.pk for asc in self.policy.all())

        position = 0
        for pk in req_params.getlist(submit_name, []):
            script_param = "%s_%s" % (submit_name, pk)

            script_pk = int(req_params.get(script_param, None))
            script = Script.objects.get(pk=script_pk)

            if pk.startswith("new_"):
                # If the model already has a script at this position in the
                # list, then the user must have deleted it in the UI; remove it
                # from the database as well
                try:
                    existing = AssociatedScript.objects.get(
                            group=self, position=position)
                    # (... although we shouldn't try to remove it twice!)
                    existing_set.remove(existing.pk)
                    existing.delete()
                except AssociatedScript.DoesNotExist:
                    pass

                asc = AssociatedScript(
                        group=self, script=script, position=position)
                asc.save()
                pk = asc.pk
                position += 1
            else:
                pk = int(pk)
                asc = AssociatedScript.objects.get(
                        pk=pk, group=self, script=script)
                position = asc.position + 1

            for inp in script.ordered_inputs:
                try:
                    par = AssociatedScriptParameter.objects.get(
                            script=asc, input=inp)
                except AssociatedScriptParameter.DoesNotExist:
                    par = AssociatedScriptParameter(script=asc, input=inp)
                param_name = "{0}_param_{1}".format(script_param, inp.position)
                if inp.value_type == Input.FILE:
                    if param_name not in req_files \
                            or not req_files[param_name]:
                        if par.pk is not None:
                            # Don't blank existing values
                            continue
                        elif inp.mandatory:
                            raise MandatoryParameterMissingError(inp)
                        else:
                            pass
                    else:
                        par.file_value = req_files[param_name]
                else:
                    if param_name not in req_params \
                            or not req_params[param_name]:
                        if par.pk is not None:
                            # Don't blank existing values
                            continue
                        elif inp.mandatory:
                            raise MandatoryParameterMissingError(inp)
                        else:
                            pass
                    else:
                        par.string_value = req_params[param_name]
                par.save()
            seen_set.add(pk)

        # Delete entries that were not in the submitted data
        for pk in existing_set - seen_set:
            asc = AssociatedScript.objects.get(pk=pk)
            asc.delete()

    @property
    def ordered_policy(self):
        return self.policy.all().order_by('position')

    def get_absolute_url(self):
        site_url = self.site.get_absolute_url()
        return '{0}/groups/{1}'.format(site_url, self.url)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['uid', 'site'],
                name="unique_uid_per_group"
            ),
        ]


class PC(models.Model):
    """This class represents one PC, i.e. one client of the admin system."""
    mac = models.CharField(verbose_name=_('MAC'), max_length=255, blank=True)
    name = models.CharField(verbose_name=_('name'), max_length=255)
    uid = models.CharField(verbose_name=_('UID'), max_length=255)
    description = models.CharField(verbose_name=_('description'),
                                   max_length=1024, blank=True)
    distribution = models.ForeignKey(Distribution, on_delete=models.PROTECT)
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    pc_groups = models.ManyToManyField(PCGroup, related_name='pcs', blank=True)
    package_list = models.ForeignKey(
        PackageList, null=True, blank=True, on_delete=models.PROTECT
    )
    custom_packages = models.ForeignKey(
        CustomPackages, null=True, blank=True, on_delete=models.PROTECT
    )
    site = models.ForeignKey(
        Site, related_name='pcs', on_delete=models.CASCADE
    )
    is_activated = models.BooleanField(
        verbose_name=_('activated'),
        default=False
    )
    is_update_required = models.BooleanField(verbose_name=_('update required'),
                                             default=False)
    # This field is used to communicate to the JobManager on each PC that it
    # should send an update of installed packages next time it contacts us.
    do_send_package_info = (
        models.BooleanField(verbose_name=_('send package info'),
                            default=True))
    creation_time = models.DateTimeField(verbose_name=_('creation time'),
                                         auto_now_add=True)
    last_seen = models.DateTimeField(verbose_name=_('last seen'),
                                     null=True, blank=True)
    location = models.CharField(verbose_name=_('location'),
                                max_length=1024, blank=True, default='')

    @property
    def current_packages(self):
        return set(self.package_list.names_of_installed_package)

    @property
    def wanted_packages(self):
        """Wanted packages are all packages present on the system (including
        manually installed) PLUS all packages *explicitly* added through the
        admin system, MINUS all packages *explicitly* removed through the admin
        system.

        That is, the point of departure is NOT the packages present in the
        distribution, but the packages present on the PC itself.
        """
        wanted_packages = self.current_packages

        for group in self.pc_groups.all():
            iis = group.custom_packages.install_infos
            for do_add, name in iis.values_list('do_add', 'package__name'):
                if do_add:
                    wanted_packages.add(name)
                else:
                    wanted_packages.discard(name)

        iis = self.custom_packages.install_infos
        for do_add, name in iis.values_list('do_add', 'package__name'):
            if do_add:
                wanted_packages.add(name)
            else:
                wanted_packages.discard(name)

        return wanted_packages

    @property
    def online(self):
        """A PC being online is defined as last seen less than 5 minutes ago."""
        if not self.last_seen:
            return False
        now = timezone.now()
        return self.last_seen >= now - relativedelta(minutes=5)

    @property
    def pending_package_updates(self):
        wanted = self.wanted_packages
        current = self.current_packages
        return (wanted - current, current - wanted)

    @property
    def pending_packages_add(self):
        return self.wanted_packages - self.current_packages

    @property
    def pending_packages_remove(self):
        return self.current_packages - self.wanted_packages

    class Status:
        """This class represents the status of af PC. We may want to do
        something similar for jobs."""

        def __init__(self, state, priority):
            self.state = state
            self.priority = priority

    @property
    def status(self):
        if not self.is_activated:
            return self.Status(NEW, INFO)
        elif self.is_update_required:
            # If packages require update
            return self.Status(UPDATE, WARNING)
        else:
            # Get a list of all jobs associated with this PC and see if any of
            # them failed.
            failed_jobs = self.jobs.filter(status=Job.FAILED)
            if len(failed_jobs) > 0:
                # Only UNHANDLED failed jobs, please.
                return self.Status(FAIL, IMPORTANT)
            else:
                return self.Status(OK, None)

    def get_list_of_configurations(self):
        configs = [self.site.configuration]
        configs.extend([g.configuration for g in self.pc_groups.all()])
        configs.append(self.configuration)
        return configs

    def get_config_value(self, key, default=None):
        value = default
        configs = self.get_list_of_configurations()
        for conf in configs:
            try:
                entry = conf.entries.get(key=key)
                value = entry.value
            except ConfigurationEntry.DoesNotExist:
                pass
        return value

    def get_full_config(self):
        result = {}
        configs = self.get_list_of_configurations()
        for conf in configs:
            for entry in conf.entries.all():
                result[entry.key] = entry.value
        return result

    def get_merged_config_list(self, key, default=None):
        result = default[:] if default is not None else []

        configs = [self.site.configuration]
        configs.extend([g.configuration for g in self.pc_groups.all()])
        configs.append(self.configuration)

        for conf in configs:
            try:
                entry = conf.entries.get(key=key)
                for v in entry.value.split(","):
                    v = v.strip()
                    if v != '' and v not in result:
                        result.append(v)
            except ConfigurationEntry.DoesNotExist:
                pass

        return result

    def get_absolute_url(self):
        return reverse('computer', args=(self.site.uid, self.uid))

    def supports_ordered_job_execution(self):
        v = self.get_config_value("_os2borgerpc.client_version")
        if v:
            return LooseVersion("0.0.5.0") <= LooseVersion(v)
        else:
            return False

    def os2_product(self):
        """Return whether a PC is running os2borgerpc or os2displaypc."""
        return self.get_config_value("os2_product")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class ScriptTag(models.Model):
    """A tag model for scripts."""
    name = models.CharField(verbose_name=_('name'), max_length=255)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Script(AuditModelMixin):
    """A script to be performed on a registered client computer."""
    name = models.CharField(verbose_name=_('name'), max_length=255)
    description = models.TextField(verbose_name=_('description'),
                                   max_length=4096)
    site = models.ForeignKey(Site, related_name='scripts',
                             null=True, blank=True, on_delete=models.CASCADE)
    # The executable_code field should contain a single executable (e.g. a Bash
    # script OR a single extractable .zip or .tar.gz file with all necessary
    # data.
    executable_code = models.FileField(verbose_name=_('executable code'),
                                       upload_to='script_uploads')
    is_security_script = models.BooleanField(verbose_name=_('security script'),
                                             default=False, null=False)

    maintained_by_magenta = models.BooleanField(
        verbose_name=_("maintained by Magenta"),
        default=False,
        null=False,
    )
    author = models.CharField(verbose_name=_("author"), max_length=255,
                              null=False, blank=True)
    author_email = models.EmailField(verbose_name=_("author email"),
                                     null=False, blank=True)
    tags = models.ManyToManyField(ScriptTag,
                                  related_name='scripts', blank=True)

    @property
    def is_global(self):
        return self.site is None

    def __str__(self):
        return self.name

    @staticmethod
    def get_system_script(name):
        try:
            script = Script.objects.get(description=name)
        except Script.DoesNotExist:
            system_site = Site.get_system_site()

            full_script_path = os.path.join(
                settings.MEDIA_ROOT,
                'system_scripts/',
                name
            )

            if(os.path.isfile(full_script_path)):
                args = []
                title = name
                title_matcher = re.compile(r'BIBOS_SCRIPT_TITLE:\s*([^\n]+)')
                arg_matcher = re.compile(
                    'BIBOS_SCRIPT_ARG:(' +
                    '|'.join([v for v, n in Input.VALUE_CHOICES]) +
                    ')',
                    flags=re.IGNORECASE
                )

                fh = open(full_script_path, 'r')
                for line in fh.readlines():
                    m = arg_matcher.search(line)
                    if m is not None:
                        args.append(m.group(1).upper())
                    else:
                        m = title_matcher.search(line)
                        if m is not None:
                            title = m.group(1)
                fh.close()

                script = Script.objects.create(
                    name=title,
                    description=name,
                    executable_code='system_scripts/' + name,
                    site=system_site
                )
                script.save()

                for position, vtype in enumerate(args):
                    Input.objects.create(
                        name=script.name + " arg " + str(position + 1),
                        position=position,
                        value_type=vtype,
                        mandatory=True,
                        script=script
                    )
            else:
                script = None
        return script

    def run_on(self, site, pc_list, *args, user):
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        batch = Batch(site=site, script=self,
                      name=' '.join([self.name, now_str]))
        batch.save()

        # Add parameters
        for i, inp in enumerate(self.ordered_inputs):
            if i < len(args):
                value = args[i]
                if(inp.value_type == Input.FILE):
                    p = BatchParameter(
                        input=inp, batch=batch, file_value=value)
                else:
                    p = BatchParameter(
                        input=inp, batch=batch, string_value=value)
                p.save()

        for pc in pc_list:
            job = Job(batch=batch, pc=pc, user=user)
            job.save()

        return batch

    @property
    def ordered_inputs(self):
        return self.inputs.all().order_by('position')

    def get_absolute_url(self, **kwargs):
        if 'site_uid' in kwargs:
            site_uid = kwargs['site_uid']
        else:
            site_uid = self.site.uid
        if self.is_security_script:
            return reverse('security_script', args=(site_uid, self.pk))
        else:
            return reverse('script', args=(site_uid, self.pk))

    class Meta:
        ordering = ['name']


class Batch(models.Model):
    """A batch of jobs to be performed on a number of computers."""

    class Meta:
        verbose_name_plural = "Batches"

    # TODO: The name should probably be generated automatically from ID and
    # script and date, etc.
    name = models.CharField(verbose_name=_('name'), max_length=255)
    script = models.ForeignKey(Script, on_delete=models.CASCADE)
    site = models.ForeignKey(
        Site, related_name='batches', on_delete=models.CASCADE
    )

    def __str__(self):
        return self.name


class AssociatedScript(models.Model):
    """A script associated with a group. Adding a script to a group causes it
    to be run on all computers in the group; adding a computer to a group with
    scripts will cause all of those scripts to be run on the new member."""

    group = models.ForeignKey(
        PCGroup, related_name='policy', on_delete=models.CASCADE
    )
    script = models.ForeignKey(
        Script, related_name='associations', on_delete=models.CASCADE
    )
    position = models.IntegerField(verbose_name=_('position'))

    def make_batch(self):
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return Batch(site=self.group.site, script=self.script,
                     name=', '.join([self.group.name,
                                    self.script.name,
                                    now_str]
                                    ))

    def make_parameters(self, batch):
        params = []
        for i in self.script.inputs.all():
            try:
                asp = self.parameters.get(input=i)
                params.append(asp.make_batch_parameter(batch))
            except AssociatedScriptParameter.DoesNotExist:
                # XXX
                raise
        return params

    @property
    def ordered_parameters(self):
        return self.parameters.all().order_by('input__position')

    def run_on(self, user, pcs):
        """\
Runs this script on several PCs, returning a batch representing this task."""
        batch = self.make_batch()
        batch.save()
        params = self.make_parameters(batch)

        for p in params:
            p.save()
        for pc in pcs:
            job = Job(batch=batch, pc=pc, user=user)
            job.save()

        return batch

    def __str__(self):
        return "{0}, {1}: {2}".format(self.group, self.position, self.script)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['position', 'group'],
                name="unique_group_position"
            ),
        ]


class Job(models.Model):
    """A Job or task to be performed on a single computer."""

    # Job status choices
    NEW = 'NEW'
    SUBMITTED = 'SUBMITTED'
    RUNNING = 'RUNNING'
    DONE = 'DONE'
    FAILED = 'FAILED'
    RESOLVED = 'RESOLVED'

    STATUS_TRANSLATIONS = {
        NEW: _('jobstatus:New'),
        SUBMITTED: _('jobstatus:Submitted'),
        RUNNING: _('jobstatus:Running'),
        FAILED: _('jobstatus:Failed'),
        DONE: _('jobstatus:Done'),
        RESOLVED: _('jobstatus:Resolved')
    }

    STATUS_CHOICES = (
        (NEW, STATUS_TRANSLATIONS[NEW]),
        (SUBMITTED, STATUS_TRANSLATIONS[SUBMITTED]),
        (RUNNING, STATUS_TRANSLATIONS[RUNNING]),
        (FAILED, STATUS_TRANSLATIONS[FAILED]),
        (DONE, STATUS_TRANSLATIONS[DONE]),
        (RESOLVED, STATUS_TRANSLATIONS[RESOLVED])
    )

    # Is it ideal to hardcode CSS class names in here? Better in template tag?
    STATUS_TO_LABEL = {
        NEW: 'bg-secondary',
        SUBMITTED: 'bg-info',
        RUNNING: 'bg-warning',
        DONE: 'bg-success',
        FAILED: 'bg-danger',
        RESOLVED: 'bg-primary'
    }

    # Fields
    # Use built-in ID field for ID.
    status = models.CharField(max_length=10, choices=STATUS_CHOICES,
                              default=NEW)
    log_output = models.TextField(verbose_name=_('log output'),
                                  max_length=128000,
                                  blank=True)
    started = models.DateTimeField(verbose_name=_('started'), null=True)
    finished = models.DateTimeField(verbose_name=_('finished'), null=True)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    batch = models.ForeignKey(
        Batch, related_name='jobs', on_delete=models.CASCADE
    )
    pc = models.ForeignKey(PC, related_name='jobs', on_delete=models.CASCADE)

    def __str__(self):
        return '_'.join(map(str, [self.batch, self.id]))

    @property
    def has_info(self):
        return self.status == Job.FAILED or len(self.log_output) > 1

    @property
    def status_label(self):
        if self.status is None:
            return ''
        else:
            return Job.STATUS_TO_LABEL[self.status]

    @property
    def status_translated(self):
        if self.status is None:
            return ''
        else:
            return Job.STATUS_TRANSLATIONS[self.status]

    @property
    def failed(self):
        return self.status == Job.FAILED

    @property
    def as_instruction(self):
        parameters = []

        for param in self.batch.parameters.order_by("input__position"):
            parameters.append({
                'type': param.input.value_type,
                'value': param.transfer_value
            })

        return {
            'id': self.pk,
            'status': self.status,
            'parameters': parameters,
            'executable_code':
                self.batch.script.executable_code.read().decode('utf8')
        }

    def resolve(self):
        if self.failed:
            self.status = Job.RESOLVED
            self.save()
        else:
            raise Exception(_('Cannot change status from {0} to {1}').format(
                self.status,
                Job.RESOLVED
            ))

    def restart(self, user=user):
        if not self.failed:
            raise Exception(_('Can only restart jobs with status %s') % (
                Job.FAILED
            ))
        # Create a new batch
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        script = self.batch.script
        new_batch = Batch(site=self.batch.site, script=script,
                          name=' '.join([script.name, now_str]))
        new_batch.save()
        for p in self.batch.parameters.all():
            new_p = BatchParameter(
                input=p.input,
                batch=new_batch,
                file_value=p.file_value,
                string_value=p.string_value
            )
            new_p.save()

        new_job = Job(batch=new_batch, pc=self.pc, user=user)
        new_job.save()
        self.resolve()

        return new_job


class Input(models.Model):
    """Input for a script"""

    # Value types
    STRING = 'STRING'
    INT = 'INT'
    DATE = 'DATE'
    FILE = 'FILE'

    VALUE_CHOICES = (
        (STRING, _('String')),
        (INT, _('Integer')),
        (DATE, _('Date')),
        (FILE, _('File'))
    )

    name = models.CharField(verbose_name=_('name'), max_length=255)
    value_type = models.CharField(verbose_name=_('value type'),
                                  choices=VALUE_CHOICES, max_length=10)
    position = models.IntegerField(verbose_name=_('position'))
    mandatory = models.BooleanField(verbose_name=_('mandatory'), default=True)
    script = models.ForeignKey(
        Script, related_name='inputs', on_delete=models.CASCADE
    )

    def __str__(self):
        return self.script.name + "/" + self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['position', 'script'],
                name="unique_script_position"
            ),
        ]


def upload_file_name(instance, filename):
    size = 32
    random_dirname = ''.join(
        random.choice(
            string.ascii_lowercase + string.digits
        ) for x in range(size)
    )
    return '/'.join(['parameter_uploads', random_dirname, filename])


class Parameter(models.Model):
    """A concrete value for the Input of a Script."""

    string_value = models.CharField(max_length=4096, null=True, blank=True)
    file_value = models.FileField(upload_to=upload_file_name,
                                  null=True,
                                  blank=True)
    # which input does this belong to?
    input = models.ForeignKey(Input, on_delete=models.CASCADE)

    @property
    def transfer_value(self):
        input_type = self.input.value_type
        if input_type == Input.FILE:
            return self.file_value.url
        else:
            return self.string_value

    class Meta:
        abstract = True


class BatchParameter(Parameter):
    # Which batch is this parameter associated with?
    batch = models.ForeignKey(
        Batch, related_name='parameters', on_delete=models.CASCADE
    )

    def __str__(self):
        return "{0}: {1}".format(self.input, self.transfer_value)


class AssociatedScriptParameter(Parameter):
    # Which associated script is this parameter, er, associated with?
    script = models.ForeignKey(
        AssociatedScript, related_name='parameters', on_delete=models.CASCADE
    )

    def make_batch_parameter(self, batch):
        if self.input.value_type == Input.FILE:
            return BatchParameter(
                batch=batch, input=self.input, file_value=self.file_value)
        else:
            return BatchParameter(
                batch=batch, input=self.input, string_value=self.string_value)

    def __str__(self):
        return "{0} - {1}: {2}".format(
            self.script, self.input, self.transfer_value)


class SecurityProblem(models.Model):
    """A security problem and the method (script) to handle it."""

    # Problem levels.

    NORMAL = 'Normal'
    HIGH = 'High'
    CRITICAL = 'Critical'

    LEVEL_TRANSLATIONS = {
        NORMAL: _('securitylevel:Normal'),
        HIGH: _('securitylevel:High'),
        CRITICAL: _('securitylevel:Critical'),
    }

    LEVEL_CHOICES = (
        (CRITICAL, LEVEL_TRANSLATIONS[CRITICAL]),
        (HIGH, LEVEL_TRANSLATIONS[HIGH]),
        (NORMAL, LEVEL_TRANSLATIONS[NORMAL]),
    )

    LEVEL_TO_LABEL = {
        NORMAL: 'label-gentle-warning',
        HIGH: 'label-warning',
        CRITICAL: 'label-important',
    }

    name = models.CharField(verbose_name=_('name'), max_length=255)
    uid = models.SlugField(verbose_name=_('UID'))
    description = models.TextField(verbose_name=_('description'), blank=True)
    level = models.CharField(verbose_name=_('level'), max_length=10,
                             choices=LEVEL_CHOICES, default=HIGH)
    site = models.ForeignKey(
        Site, related_name='security_problems', on_delete=models.CASCADE
    )
    security_script = models.ForeignKey(
        Script, verbose_name=_('security script'),
        related_name='security_problems',
        on_delete=models.CASCADE
    )
    alert_groups = models.ManyToManyField(PCGroup,
                                          related_name='security_problems',
                                          verbose_name=_('alert groups'),
                                          blank=True)
    alert_users = models.ManyToManyField(User,
                                         related_name='security_problems',
                                         verbose_name=_('alert users'),
                                         blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

        constraints = [
            models.UniqueConstraint(
                fields=['uid', 'site'],
                name="unique_uid_per_site"
            ),
        ]


class SecurityEvent(models.Model):

    """A security event is an instance of a security problem."""

    # Event status choices

    objects = SecurityEventQuerySet.as_manager()

    NEW = 'NEW'
    ASSIGNED = 'ASSIGNED'
    RESOLVED = 'RESOLVED'

    STATUS_TRANSLATIONS = {
        NEW: _('eventstatus:New'),
        ASSIGNED: _('eventstatus:Assigned'),
        RESOLVED: _('eventstatus:Resolved')
    }

    STATUS_CHOICES = (
        (NEW, STATUS_TRANSLATIONS[NEW]),
        (ASSIGNED, STATUS_TRANSLATIONS[ASSIGNED]),
        (RESOLVED, STATUS_TRANSLATIONS[RESOLVED])
    )

    STATUS_TO_LABEL = {
        NEW: 'bg-primary',
        ASSIGNED: 'bg-secondary',
        RESOLVED: 'bg-success'
    }
    problem = models.ForeignKey(
        SecurityProblem, null=False, on_delete=models.CASCADE
    )
    # The time the problem was reported in the log file
    ocurred_time = models.DateTimeField(verbose_name=_('occurred'))
    # The time the problem was submitted to the system
    reported_time = models.DateTimeField(verbose_name=_('reported'))
    pc = models.ForeignKey(PC, on_delete=models.CASCADE, related_name="security_events")
    summary = models.CharField(max_length=4096, null=False, blank=False)
    complete_log = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES,
                              default=NEW)
    assigned_user = models.ForeignKey(
        User, verbose_name=_('assigned user'),
        null=True, blank=True, on_delete=models.SET_NULL
    )
    note = models.TextField(null=True, blank=True)

    def __str__(self):
        return "{0}: {1}".format(self.problem.name, self.id)


class ImageVersion(models.Model):
    BORGERPC = "BORGERPC"
    DISPLAYPC = "DISPLAYPC"

    platform_choices = (
        (BORGERPC, _("BorgerPC")),
        (DISPLAYPC, _("DisplayPC")),
    )

    platform = models.CharField(max_length=128, choices=platform_choices)
    image_version = models.CharField(unique=True, max_length=7)
    release_date = models.DateField()
    os = models.CharField(verbose_name="OS", max_length=30)
    release_notes = models.TextField(max_length=350)
    image_upload = models.FileField(upload_to="images", default='#')

    def __str__(self):
        return "| {0} | {1} | {2} | {3} | {4} |".format(
            self.image_version,
            self.release_date,
            self.os,
            self.release_notes,
            self.image_upload
        )

    class Meta:
        ordering = ['platform', '-image_version']


# Last_successful_login is only updated whenever the citizen user:
# 1. Successfully authenticates with their backend (exists in their db, not locked out)
# 2. Successfully logs into a borgerPC because they either still have time left or it's
# after the quarantine period
class Citizen(models.Model):
    citizen_id = models.CharField(unique=True, max_length=128)
    last_successful_login = models.DateTimeField()
    site = models.ForeignKey(Site, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.site} - {self.citizen_id}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['citizen_id', 'site'],
                name="unique_citizen_per_site"
            ),
        ]
