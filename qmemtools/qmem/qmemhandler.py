#!/usr/bin/env python

import libxml2

#
# qhost_data[hostname]['num_proc']:str
#                     ['mem_total']:str
#                     ['jobs'][jobid]['jobcount']:int
#                                    ['master']:bool
#                                    ['taskid']:list
#                                    ['owner']:str
#                                    ['jobname']:str
#
def qhost_handler(xmldoc):
    qhost_data = {}
    try:
        rss=libxml2.parseDoc(xmldoc)
    except parserError:
        return qhost_data

    ctxt = rss.xpathNewContext()

    for host in ctxt.xpathEval("/qhost/host[@name!='global']"):
        ctxt.setContextNode(host)
        hostname = ctxt.xpathEval("@name")[0].content
        num_proc = ctxt.xpathEval("hostvalue[@name='num_proc']")[0].content
        mem_total = ctxt.xpathEval("hostvalue[@name='mem_total']")[0].content
        qhost_data.update({hostname: {'num_proc': num_proc, 'mem_total': mem_total, 'jobs': {}}})
        for job in ctxt.xpathEval("child::job"):
            ctxt.setContextNode(job)
            jobid = ctxt.xpathEval("attribute::name")[0].content
            if jobid not in qhost_data[hostname]['jobs']:
                qhost_data[hostname]['jobs'].update({jobid: {'jobcount':0, 'master': False, 'taskid': []}})

            for jobval in ctxt.xpathEval("child::jobvalue"):
                ctxt.setContextNode(jobval)
                for attr in ctxt.xpathEval("@name"):
                    if attr.content == 'job_owner':
                        qhost_data[hostname]['jobs'][jobid].update({'owner': jobval.content})
                    if attr.content == 'job_name':
                        qhost_data[hostname]['jobs'][jobid].update({'jobname': jobval.content})
                    if attr.content == 'pe_master':
                        if jobval.content == 'MASTER':
                            qhost_data[hostname]['jobs'][jobid].update({'master': True})
                    if attr.content == 'taskid':
                        qhost_data[hostname]['jobs'][jobid]['taskid'].append(jobval.content)

            if len(qhost_data[hostname]['jobs'][jobid]['taskid']) > 0:
                qhost_data[hostname]['jobs'][jobid]['jobcount'] = 1
            else:
                qhost_data[hostname]['jobs'][jobid]['jobcount'] += 1

    
    rss.freeDoc()
    ctxt.xpathFreeContext()
    return qhost_data

#
# array_task[jobid]['taskid']:list
#           [jobid.taskid]:hostname
#
def array_task_handler(qhost_data):
    array_task = {}

    for hostname, dictionary in qhost_data.items():
        for key in dictionary.keys():
            if key == 'jobs':
                for jobid in dictionary[key]:
                    length = len(dictionary[key][jobid]['taskid'])
                    if not array_task.has_key(jobid):
                        if length > 0:
                            array_task.update({jobid: {'taskid': dictionary[key][jobid]['taskid'][:]}})
                        else:
                            if dictionary[key][jobid]['master'] == True:
                                array_task.update({jobid: {'taskid': []}})
                    else:
                        if length > 0:
                            array_task[jobid]['taskid'].extend(dictionary[key][jobid]['taskid'][:])
                    if length > 0:
                        for taskid in dictionary[key][jobid]['taskid']:
                            hashkey = "%s.%s" % (jobid, taskid)
                            if not array_task.has_key(hashkey):
                                array_task.update({hashkey : hostname})
                    else:
                        hashkey = "%s.1" % jobid
                        if not array_task.has_key(hashkey):
                            if dictionary[key][jobid]['master'] == True:
                                array_task.update({hashkey: hostname})

    return array_task

#
# qstat_data[owner]['uid']:str
#                  ['jobs'][jobid]['requested_h_vmem_strval']:str
#                                 ['requested_h_vmem_dblval']:float
#                                 ['hostname'][hostname]['master']:str
#                                                       ['slave']:str
#                                                       [taskid]:str
def qstat_handler(xmldoc, qhost_data, array_task):
    qstat_data = {}
    try:
        rss=libxml2.parseDoc(xmldoc)
    except parserError:
        return qstat_data

    ctxt = rss.xpathNewContext()

    for stat in ctxt.xpathEval("/detailed_job_info/djob_info/element"):
        ctxt.setContextNode(stat)
        jobid = ctxt.xpathEval("JB_job_number")[0].content
        uid = ctxt.xpathEval("JB_uid")[0].content
        owner = ctxt.xpathEval("JB_owner")[0].content
        for hard_resources in ctxt.xpathEval("JB_hard_resource_list/*"):
            ctxt.setContextNode(hard_resources)
            if ctxt.xpathEval("CE_name")[0].content == "h_vmem":
                requested_h_vmem_strval = ctxt.xpathEval("CE_stringval")[0].content
                requested_h_vmem_dblval = float(ctxt.xpathEval("CE_doubleval")[0].content)
                if qstat_data.has_key(owner):
                    qstat_data[owner]['jobs'].update({jobid: {'requested_h_vmem_strval': requested_h_vmem_strval, 'requested_h_vmem_dblval': requested_h_vmem_dblval, 'hostname': {}}})
                else:
                    qstat_data.update({owner: {'uid': uid, 'jobs': {jobid: {'requested_h_vmem_strval': requested_h_vmem_strval, 'requested_h_vmem_dblval': requested_h_vmem_dblval, 'hostname': {}}}}})

        ctxt.setContextNode(stat)

        # minimum slots
        slots = 1

        if jobid in array_task:
            # task array or not ?
            if len(array_task[jobid]['taskid']) > 0:
                for tasks in ctxt.xpathEval("JB_ja_tasks/ulong_sublist"):
                    ctxt.setContextNode(tasks)
                    taskid = ctxt.xpathEval("JAT_task_number")[0].content
                    for scaled in ctxt.xpathEval("JAT_scaled_usage_list/scaled"):
                        ctxt.setContextNode(scaled)
                        if ctxt.xpathEval("UA_name")[0].content == "maxvmem":
                            maxvmem = ctxt.xpathEval("UA_value")[0].content
                            if array_task.has_key('%s.%s'%(jobid,taskid)):
                                if qstat_data[owner]['jobs'][jobid]['hostname'].has_key(array_task['%s.%s'%(jobid,taskid)]):
                                    qstat_data[owner]['jobs'][jobid]['hostname'][array_task['%s.%s'%(jobid,taskid)]].update({taskid:maxvmem})
                                else:
                                    qstat_data[owner]['jobs'][jobid]['hostname'].update({array_task['%s.%s'%(jobid,taskid)]: {taskid:maxvmem}})
            else:
                # number of slots used for openmp and PE
                rn_max = ctxt.xpathEval("JB_pe_range/ranges/RN_max")
                if type(rn_max) is list and len(rn_max):
                    slots = int(rn_max[0].content)
    
                for tasks in ctxt.xpathEval("JB_ja_tasks"):
                    ctxt.setContextNode(tasks)
                    # take the master
                    for scaled in ctxt.xpathEval("*/JAT_scaled_usage_list/scaled"):
                        ctxt.setContextNode(scaled)
                        if ctxt.xpathEval("UA_name")[0].content == "maxvmem":
                            maxvmem = ctxt.xpathEval("UA_value")[0].content
                            data = qhost_data[array_task["%s.1"%jobid]]['jobs'][jobid]
                            if data['jobcount'] != slots:
                                data['jobcount'] -= 1
                            qstat_data[owner]['jobs'][jobid]['hostname'].update({array_task["%s.1"%jobid]: {'master': maxvmem}})
    
                    ctxt.setContextNode(tasks)

                    for tasklist in ctxt.xpathEval("*/JAT_task_list"):
                        ctxt.setContextNode(tasklist)
                        hostname = []
                        for host in ctxt.xpathEval("*/PET_granted_destin_identifier_list/*/JG_qhostname"):
                            hostname.append(host.content)
    
                        index = 0
                        for pet_scaled in ctxt.xpathEval("*/PET_scaled_usage/scaled"):
                            ctxt.setContextNode(pet_scaled)
                            if ctxt.xpathEval("UA_name")[0].content == "maxvmem":
                                maxvmem = ctxt.xpathEval("UA_value")[0].content
                                if qstat_data[owner]['jobs'][jobid]['hostname'].has_key(hostname[index]):
                                    qstat_data[owner]['jobs'][jobid]['hostname'][hostname[index]].update({'slave': maxvmem})
                                else:
                                    qstat_data[owner]['jobs'][jobid]['hostname'].update({hostname[index]: {'slave': maxvmem}})
                                index += 1

    rss.freeDoc()
    ctxt.xpathFreeContext()
    return qstat_data
