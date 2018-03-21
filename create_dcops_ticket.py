#!/usr/bin/env python
"""Create a DCOPS tickets to check why machine is not pingable
"""


import click
import csv
import getpass
import socket
import yaml
import urllib
from urllib import urlopen
import json
from jira import JIRA
from string import Template
import pprint
import fileinput


def GetJira(username, password_handler):
    """Create a JIRA object."""
    while True:
        try:
            options = {'agile_rest_path': 'agile', 'verify': False}
            password = password_handler()

            jira = JIRA(server='https://jiraip',
                        options=options, basic_auth=(username, password))
            break
        except KeyboardInterrupt:
            print("Ctrl-C pressed, exiting...\n")
            exit(-1)
        except:
            print('Failed to log into JIRA.')
    return jira


def GetPosInfo(hostname):
    """Fetches host information from POS database"""


def GetCsv():
    list_of_lists = []

    spamreader = csv.reader(fileinput.input('-'), quoting=csv.QUOTE_ALL)
    for row in spamreader:
        list_of_lists.append(row)
        print ', '.join(row)

    return list_of_lists


def GetDcopsFields(username, hostname, f5_ok, live_cfg_ok, dcops_reboot_ok, summary):
    """Create a dictionary with all the DCOPS fields needed to create the DCOPS not pingable issue."""
    def question(q): return raw_input(
        q).lower().strip()[0] == "y" or question(q)
    # Get user input
    print 'You will be prompted for DCOPS Not Pingable info.'
    if not hostname:
        hostname = raw_input("Hostname: ")
    correct_input = False
    while not correct_input:
        try:
            socket.gethostbyname(hostname)
            break
        except socket.gaierror:
            print "Invalid Hostname please try again"
            hostname = raw_input("Hostname: ")
        else:
            correct_input = True
    if not summary:

        summary = raw_input("Summary of issue: ")
    try:
        pos_f = urlopen("http://database/enc.php?host=" + hostname)
        pos_json = json.loads(pos_f.read().decode('utf-8'))
        pos_f.close()
        pos_data = ''
        for key in pos_json:
            pos_data += "| *{:20s}* | {:40s} |\n".format(key, pos_json[key])
        print pos_data
    except IOError as err:
        print("Can't read from database.com: %s" % (err))
        exit(-2)

    d = {'hostname': hostname, 'f5_ok': f5_ok, 'live_cfg_ok': live_cfg_ok,
         'dcops_reboot_ok': dcops_reboot_ok, 'pos_data': pos_data, 'summary': summary}

    description = Template("""
*As an MZ Employee I would like to request DCOPS to investigate the host bellow.*

1. Provide Hostname
{code}$hostname{code}

2. Provide summary of issue with host
{code}$summary{code}

3. Has the host been removed from the F5 Load balancer pool?
{code}$f5_ok{code}

4. Has the host been removed from the live.cfg config?
{code}$live_cfg_ok{code}

5. May DCOPS reboot the server?
{code}$dcops_reboot_ok{code}

6. Provide all host info from POS (http://database).
{code}$pos_data{code}
                           """).substitute(d)

    # Build dictionary
    fields = {
        'project': {'key': 'DCOPS'},
        'issuetype': {'name': 'Story'},
        'summary': 'Please check %s' % (hostname),
        'customfield_12001': {'value': 'LAS1'},  # Location Field
        'customfield_12000': [{'value': 'Troubleshooting'}],  # Request Type
        'description': description,
    }

    return fields


def CallJira(username, password_handler, hostname, f5_ok, live_cfg_ok, dcops_reboot_ok, summary):
    fields = GetDcopsFields(username, hostname, f5_ok,
                            live_cfg_ok, dcops_reboot_ok, summary)
    pprint.pprint(fields)
    jira = GetJira(username, password_handler)
    issue = jira.create_issue(fields)
    print json.dumps(fields, indent=2, sort_keys=True)
    print 'Ping DCOPS PM if you need to expedite ticket %s ' % issue.permalink()


@click.command()
@click.option('--hostname', help='Hostname having issues')
@click.option('--username', default=getpass.getuser(), help='Your jira username')
@click.option('--summary', default='', help='Summary of issue with server')
@click.option('--f5_ok', default=True, type=click.BOOL, help='was hostname removed from F5 pool')
@click.option('--live_cfg_ok', default=True, type=click.BOOL, help='was hostname removed from live cfg')
@click.option('--dcops_reboot_ok', default=True, type=click.BOOL, help='can dcops reboot server')
@click.option('--csv_read', default=False, type=click.BOOL, help='input is csv - first field is hostname, the entire line is summary')
def main(hostname, username, f5_ok, live_cfg_ok, dcops_reboot_ok, summary, csv_read):

    password_handler = PasswordHandler()

    if csv_read:

        rows = GetCsv()
        pprint.pprint(rows)

        for row in rows:
            hostname = row[0]
            summary = "\n".join(row)
            CallJira(username, password_handler, hostname, f5_ok,
                     live_cfg_ok, dcops_reboot_ok, summary)
    else:
        CallJira(username, password_handler, hostname, f5_ok,
                 live_cfg_ok, dcops_reboot_ok, summary)


class PasswordHandler(object):

    def __init__(self):
        self._cache = None

    def __call__(self):

        if not self._cache:
            self._cache = self.reallyGetPassword()

        return self._cache

    def reallyGetPassword(self):

        return getpass.getpass('JIRA password: ')


if __name__ == "__main__":
    main()

# vim:expandtab:ts=4:sw=4
