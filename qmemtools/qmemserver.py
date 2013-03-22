#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# web related modules
#
import web
import simplejson as json

#
# system related modules
#
from sys import argv, exit, stdout, stderr, modules
from os import popen
from time import sleep
from threading import Thread, Lock

#
# qmem related modules
#
from qmem.qmemdaemon import Daemon
from qmem.qmemhandler import qhost_handler, qstat_handler, array_task_handler

shared = modules['__main__']

#
# thread to update shared data in background
# Its cpu time consuming due to xml parsing
# Be careful with check_timer value
#
def update_data():
    while(1):
        if file_generation == False:
            try:
                fd = open(qhost_xml_file, 'r')
                qhost_xmldoc = fd.read().decode(xml_encoding).encode("utf-8")
            except IOError:
                print >> stderr, "Failed to open: %s" % qhost_xml_file
            else:
                fd.close()
            try:
                fd = open(qstat_xml_file, 'r')
                qstat_xmldoc = fd.read().decode(xml_encoding).encode("utf-8")
            except IOError:
                print >> stderr, "Failed to open: %s" % qstat_xml_file
            else:
                fd.close()
        else:
            qhost_xmldoc = popen("qhost -j -xml").read().decode(xml_encoding).encode("utf-8")
            qstat_xmldoc = popen("qstat -j '*' -xml").read().decode(xml_encoding).encode("utf-8")

        #
        # ensure shared data between web.py thread and this one
        # are accessed by one thread at time
        #
        shared.lock.acquire(True)

        del shared.qhost_data
        del shared.array_task_data
        del shared.qstat_data

        shared.qhost_data = qhost_handler(qhost_xmldoc)
        shared.array_task_data = array_task_handler(shared.qhost_data)
        shared.qstat_data = qstat_handler(qstat_xmldoc, shared.qhost_data, shared.array_task_data)

        shared.lock.release()

        del qhost_xmldoc
        del qstat_xmldoc

        sleep(loop_timer)

#
# Daemon class for qmem
#
class QmemDaemon(Daemon):
    def run(self):
        web.config.debug = webdebug
        app = web.application(urls, globals())
        t = Thread(target=update_data)
        t.start()
        app.run()

#
# Class object to handle request by urls
#

#
# return non filtered qhost_data
#
class Qhost(object):
    def GET(self):
        shared.lock.acquire(True)
        if len(shared.qhost_data) > 0:
            success = True
            message = ""
        else:
            success = False
            message = "No data for qhost"
        result = {"success": success, "message": message, "data": shared.qhost_data}
        data = json.dumps(result)
        shared.lock.release()
        return data

#
# return non filtered qstat_data
#
class Qstat(object):
    def GET(self):
        shared.lock.acquire(True)
        if len(shared.qstat_data) > 0:
            success = True
            message = ""
        else:
            success = False
            message = "No data for qstat"
        result = {"success": success, "message": message, "data": shared.qstat_data}
        data = json.dumps(result)
        shared.lock.release()
        return data

#
# mapping urls/object
#
urls = (
    '/qhost', 'Qhost',
    '/qstat', 'Qstat',
)

#
# need help ?
#
def usage(progname):
    print "usage: %s [start|stop|restart]" % progname

if __name__ == "__main__":
    import os
    import pwd
    import grp
    import ConfigParser

    #
    # shared data and lock
    #
    lock = Lock()
    qhost_data = None
    array_task_data = None
    qstat_data = None

    #
    # read configuration file
    #
    config = ConfigParser.ConfigParser()
    config.read('/etc/qmem/qmemserver.conf')

    port = config.get('system', 'port')
    xml_encoding = config.get('files', 'xml_encoding')
    xml_directory = config.get('files', 'xml_directory')
    loop_timer = config.getint('system', 'loop_timer')
    file_generation = config.getboolean('files', 'xml_generation')
    webdebug = config.getboolean('system', 'debug')
    log_directory = config.get('system', 'log_directory')
    pid_directory = config.get('system', 'pid_directory')
    user = config.get('system', 'user')
    group = config.get('system', 'group')

    qhost_xml_file = config.get('files', 'qhost_xml')
    qstat_xml_file = config.get('files', 'qstat_xml')

    if len(argv) == 2:
        #
        # trick to handle argument from command line and to pass port argument to web.py server
        #
        argument = argv[1]
        argv[1] = port
        try:
            uid = pwd.getpwnam(user).pw_uid
        except KeyError:
            print "User %s not found on system" % user
            exit(1)
        try:
            gid = grp.getgrnam(group).gr_gid
        except KeyError:
            print "Group %s not found on system" % group
            exit(1)
        pidfile = os.path.join(pid_directory, 'qmemserver.pid')
        logfile = os.path.join(log_directory, 'qmemserver.log')
        qmemdaemon = QmemDaemon(pidfile=pidfile, logfile=logfile, uid=uid, gid=gid, debug=webdebug)
        if argument == 'start':
            qmemdaemon.start()
        elif argument == 'stop':
            qmemdaemon.stop()
        elif argument == 'restart':
            qmemdaemon.restart()
        else:
            usage(argv[0])
            exit(2)
    else:
        usage(argv[0])
        exit(2)

    exit(0)
