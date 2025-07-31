from crontab import CronTab
from flask_socketio import emit
from flask import jsonify
import re
from crontab import CronSlices
import hashlib

class CronObserver():
    def __init__(self, app):
        self.app = app
    def notify(self, data):
        # emit cron jobs server
        with self.app.app_context():
            emit('cron_job_update', data, broadcast=True, namespace='/')
        
class CronTabHandler():
    def __init__(self, user):
        self.user = user
        self.observers = []
        self.cron_jobs = None
        self.get_cron_jobs()
        
    def parse_cron_command(self, command):
        duration = re.search('(?<=-t )\d\\.*\\d*', command)
        if duration is None:
            return 1
        else:
            return float(duration.group())

    def _hash_job(self, job):
        job_repr = f'{job.slices}_{self.parse_cron_command(job.command)}'.encode()
        return hashlib.md5(job_repr).hexdigest()
    
    def get_cron_jobs(self, silent=False):
        # load current cron jobs
        cron = CronTab(user=self.user)
        cron_slice_names = ['minute', 'hour', 'dom', 'mon', 'dow']
        jobs = {self._hash_job(job):
                {"active": job.enabled, 'command':job.command,
                'duration':float(self.parse_cron_command(job.command)),
                    **{cron_slice_names[i]:str(j)
                    for i, j in enumerate(job.slices)}}
                        for job in cron if "run_pump" in job.command}
        self.cron_jobs = jobs
        if not silent:
            self.notify()
        return jobs
        
    def get_valid_cron_slice(self, data):
        time_data = f"{data['minute']} {data['hour']} {data['dom']} {data['mon']} {data['dow']}"
        if CronSlices.is_valid(time_data) and 'duration' in data:
            return time_data
        else:
            return False
        
    def create_command(self, duration):
        return f'/home/ws/watersysenv/bin/python /home/ws/watersys_server/run_pump_remote.py -t {duration} >> /home/ws/out.txt  2>&1'
    
    
    def set_enable_job(self, idx, set_active):
        cron = CronTab(user=self.user)
        job = self.cron_jobs[idx]
        cron_slice = self.get_valid_cron_slice(job)
        duration = job['duration']
        iter = [job for job in cron.find_time(cron_slice) if self.parse_cron_command(job.command)==float(duration)]
        job = iter.pop()
        job.enable(set_active=='true')
        cron.write()
        self.get_cron_jobs()
        
    def remove_job():
        pass
    
    def _edit_cron_job(self, job, cron_slice, duration, active):
        job.set_comment('job added through server, do not change manually!')
        job.setall(cron_slice)
        job.command = self.create_command(duration)
        job.enable(active)
        return job
    
    def set_cron_job(self, data):
        cron = CronTab(user=self.user)
        cron_slice = self.get_valid_cron_slice(data)
        is_active = bool(data.get('active', False))
        duration = data.get('duration')
        try:
            float(duration)
        except ValueError:
            return 'unsuccesful', 'notvalid'

        if not cron_slice:
            return 'unsuccesful', 'notvalid'
        elif data.get('row_index') == 'new':
            job = cron.new(self.create_command(duration))
            job = self._edit_cron_job(job, cron_slice, duration, is_active)
            status = 'added'
            
        elif data.get('row_index') in self.cron_jobs:
            job = self.cron_jobs[data.get('row_index')]
            cron_slice_old = self.get_valid_cron_slice(job)
            iter = [job for job in cron.find_time(cron_slice_old) if self._hash_job(job)==data.get('row_index')]
            if (not iter) or (self._hash_job(iter[0]) != data.get('row_index')):
                return 'unsuccesful', 'jobnotfound'
            job = self._edit_cron_job(iter.pop(), cron_slice, duration, is_active)
            status = 'edited'
        else:
            return 'unsuccesful', 'jobnotfound'
        if job.is_valid():
            cron.write()
            self.get_cron_jobs()
            return 'succesfull', status
        else:
            return 'unsucessfull', 'unknown'        
    
    def register(self, observer):
        self.observers.append(observer)
    
    def notify(self):
        for observer in self.observers:
            observer.notify(self.cron_jobs)

if __name__ == '__main__':
    from werkzeug.datastructures import ImmutableMultiDict
    data = ImmutableMultiDict([('row_index','2b26235513f55b2e200d846461524f3d'), ('duration', '1'), ('active','active'),( 'minute', '1'), ('hour', '1'), ('dom', '*'), ('mon', '*'), ('dow', '1')])
    cronhandler = CronTabHandler('cedric')
    print(cronhandler.get_cron_jobs())
    cronhandler.get_valid_cron_slice(data)
    self = cronhandler
    cronhandler.register(CronObserver(app=None))
    
    for job in CronTab(user='cedric'):
        print(job)
    CronSlices.is_valid('0 * * * *')
    cron_ = CronTab('cedric')
    str(cron_[1].slices)
    #test
    import hashlib
    hashlib.md5(b'df').hexdigest()
