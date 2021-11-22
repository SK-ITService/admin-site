# Generated by Django 3.1.9 on 2021-11-22 13:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0038_auto_20211118_1431'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='packageinstallinfo',
            name='custom_packages',
        ),
        migrations.RemoveField(
            model_name='packageinstallinfo',
            name='package',
        ),
        migrations.RemoveField(
            model_name='packagelist',
            name='packages',
        ),
        migrations.RemoveField(
            model_name='packagestatus',
            name='package',
        ),
        migrations.RemoveField(
            model_name='packagestatus',
            name='package_list',
        ),
        migrations.RemoveField(
            model_name='distribution',
            name='package_list',
        ),
        migrations.RemoveField(
            model_name='pc',
            name='custom_packages',
        ),
        migrations.RemoveField(
            model_name='pc',
            name='do_send_package_info',
        ),
        migrations.RemoveField(
            model_name='pc',
            name='package_list',
        ),
        migrations.RemoveField(
            model_name='pcgroup',
            name='custom_packages',
        ),
        migrations.DeleteModel(
            name='CustomPackages',
        ),
        migrations.DeleteModel(
            name='Package',
        ),
        migrations.DeleteModel(
            name='PackageInstallInfo',
        ),
        migrations.DeleteModel(
            name='PackageList',
        ),
        migrations.DeleteModel(
            name='PackageStatus',
        ),
    ]
