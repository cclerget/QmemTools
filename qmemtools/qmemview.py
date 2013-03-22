#!/usr/bin/env python
# -*- coding: utf-8 -*-

if __name__ == "__main__":
    import os
    import re
    import sys
    import getopt
    import httplib
    import simplejson

    def usage():
        progname = os.path.basename(sys.argv[0])
        print 'usage: %s <url:port> : display all hosts' % progname
        print '       %s <url:port> -h : display this help' % progname
        print '       %s <url:port> -u : display all job details / host' % progname
        print '       %s <url:port> -j <jobid>: display details for one job (set -u automatically)' % progname
        print '       %s <url:port> -o <owner>: display owner\'s job details (set -u automatically)' % progname
        print '       %s <url:port> -h <hostname> : display only selected host' % progname
        print '       %s <url:port> -u -h <hostname> : display only selected host with job details for this host' % progname
        print '       %s <url:port> -h <hostname> -j <jobid> : display only selected host with job details for jobid only' % progname
        print '       <url:port> argument should be set to point on qmemserver address and port. ie: %s localhost:8080' % progname

    try:
        opts, args = getopt.getopt(sys.argv[2:], "h:j:o:u",["hostname=","jobid=","owner="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    user_switch = False
    filter_host = False
    filter_job = False
    filter_owner = False
    selected_jobid = ""
    selected_host = ""
    selected_owner = ""

    if len(sys.argv) < 2:
        print "Error: <url:port> argument is missing"
        usage()
        sys.exit(2)

    param = sys.argv[1].split(":")
    if len(param) != 2:
        print "Url argument should be in format url:port"
        sys.exit(1)

    for opt, arg in opts:
        if opt in ("-h", "--hostname"):
            if arg != "":
                filter_host = True
                selected_host = arg
            else:
                usage()
                sys.exit()
        elif opt in ("-j", "--jobid"):
            if arg != "":
                filter_job = True
                selected_jobid = arg
                user_switch = True
        elif opt in ("-o", "--owner"):
            if arg != "":
                filter_owner = True
                selected_owner = arg
                user_switch = True
        elif opt == '-u':
            user_switch = True

    try:
        conn = httplib.HTTPConnection(param[0], param[1])
    except Exception as e:
        print "Unable to connect to %s:%s: %s" % (param[0], param[1], e.strerror)
        sys.exit(1)

    try:
        conn.request("GET", "/qhost")
        r = conn.getresponse()
    except Exception as e:
        print "Request have failed:", e.strerror
        print "qmemserver is running ? url argument is wrong ?"
        sys.exit(1)

    data = simplejson.loads(r.read())
    qhost_data = data['data']

    try:
        conn.request("GET", "/qstat")
        r = conn.getresponse()
    except Exception as e:
        print "Request have failed:", e.strerror
        print "qmemserver is running ? url argument is wrong ?"
        sys.exit(1)

    data = simplejson.loads(r.read())
    qstat_data = data['data']

    conn.close()

    p = re.compile('([0-9]+\.[0-9]+)([GgKkMmTt])')

    header = "\033[1mHOSTNAME\tUSAGE\t\t\t\t\t\tPERCENTAGE\tMEMORY NEEDED\tMEMORY RESERVED\tTOTAL MEMORY\tAVAILABLE MEM\tSLOTS\033(B\033[m"
    separator = "\t\t-------------------------------------------------------------------------------------------------------------------------------------\n"

    if user_switch == False:
        print header

    for hostname in sorted(qhost_data.iterkeys()):
        if filter_host == False or selected_host == hostname:
            mem_needed = 0.0
            mem_reserved = 0.0
            slots_used = 0
            user_detail = ""

            num_proc = qhost_data[hostname]['num_proc']
            mem_total = qhost_data[hostname]['mem_total']

            joblist = [key for key in qhost_data[hostname]['jobs'].iterkeys()]
            if filter_job == True and selected_jobid not in joblist:
                continue

            ownerlist = [jobid for jobid in joblist if qhost_data[hostname]['jobs'][jobid]['owner'] == selected_owner]
            if filter_owner == True and len(ownerlist) == 0:
                continue

            if user_switch == True:
                print header

            for key, data in qhost_data[hostname]['jobs'].items():

                jobid = key

                if filter_job == True and selected_jobid != jobid:
                    continue

                owner = data['owner']
                jobcount = data['jobcount']
                jobname = data['jobname']
                taskid = data['taskid']
                master = data['master']

                if filter_owner == True and owner != selected_owner:
                    continue

                if not qstat_data[owner]['jobs'][jobid]['hostname'].has_key(hostname):
                    continue

                for h, v in qstat_data[owner]['jobs'][jobid]['hostname'][hostname].items():
                    slots_used += jobcount
                    reserved_memory = (qstat_data[owner]['jobs'][jobid]['requested_h_vmem_dblval'] * jobcount)/(1024*1024*1024)
                    mem_reserved += reserved_memory

                    if h not in ('master','slave'):
                        jobnumber = "%s.%s" % (jobid, h)
                    else:
                        jobnumber = jobid
                    if v != "":
                        needed_memory = float(v)/(1024*1024*1024)
                    else:
                        needed_memory = 0.0/(1024*1024*1024)

                    mem_needed += needed_memory

                    if reserved_memory > 0.0:
                        job_percent = needed_memory*100/reserved_memory
                    else:
                        job_percent = 0.0

                    job_p = "%.1f %%" % (job_percent)
                    needed_p = "%.2f G" % (needed_memory)
                    reserved_p = "%.2f G" % (reserved_memory)

                    if user_detail == "":
                        user_detail += separator

                    if master == True:
                        master_str = "Master"
                    else:
                        master_str = ""

                    user_detail += "\033[1m\t%-8s%-15s\033(B\033[m%-15s%-15s\t%-8s\t%-10s\t%-10s\t\t\t\t\t%d/%s\n" % (master_str, jobnumber, owner, jobname[0:15], job_p, needed_p, reserved_p, jobcount, num_proc)
                    user_detail += separator

            usage = ""

            mem_cap_regex = p.match(mem_total)
            if mem_cap_regex != None:
                mem_capacity = (int(float(mem_cap_regex.group(1)) / 2) + 1) * 2

            prog_needed = int(round((float(mem_needed)*40)/mem_capacity))
            usage += "\033[31m\033[1m"
            if prog_needed > 0:
                for i in xrange(0, prog_needed):
                    usage += "#"
            usage += "\033[34m"

            prog_reserved = int(round((float(mem_reserved)*40)/mem_capacity))
            for i in xrange(prog_needed, prog_reserved):
                usage += "#"

            usage += "\033[32m\033[1m"
            for i in xrange(prog_reserved, 40):
                usage += "#"
            usage += "\033[0m"

            if float(mem_reserved) > 0.0:
                percent = float(mem_needed)*100/float(mem_reserved)
            else:
                percent = 0.0

            color_percent = ""
            if percent >= 50.0:
                color_percent = "\033[34m\033[1m"

            if percent < 50.0 and float(mem_needed) > 0.0:
                color_percent = "\033[31m\033[1m"

            end_color = "\033(B\033[m\033[0m"
    
            job_p = "%.1f %%" % (percent)
            needed_p = "%.2f G" % (float(mem_needed))
            reserved_p = "%.2f G" % (float(mem_reserved))
            mem_capacity_p = "%d G" % (mem_capacity)
            warning_host = ""
            available_p = "%.2f G" % (float(mem_capacity) - float(mem_reserved))

            if float(mem_reserved) > 0.0:
                if float(mem_capacity)/float(mem_reserved) < 4.0 and slots_used != num_proc:
                    warning_host = "\033[31m\033[1m"

            end_host = "\033(B\033[m"

            print "%s%-15s%s\t%-40s\t%s%-8s%s\t%-10s\t%-10s\t%-10s\t%-10s\t%d/%s" % (warning_host,
                                                                              hostname,
                                                                              end_host,
                                                                              usage,
                                                                              color_percent,
                                                                              job_p,
                                                                              end_color,
                                                                              needed_p,
                                                                              reserved_p,
                                                                              mem_capacity_p,
                                                                              available_p,
                                                                              slots_used,
                                                                              num_proc)

            color_percent = "\033[0m"

            if user_switch == True:
                print user_detail

    print ""
    print "  \033[31m\033[1m#\033(B\033[m\033[0m Needed"
    print "  \033[34m\033[1m#\033(B\033[m\033[0m Reserved"
    print "  \033[32m\033[1m#\033(B\033[m\033[0m Available"
    print ""

