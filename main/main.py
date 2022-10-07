import _init
import sys
import os
import time
import subprocess
from datetime import datetime, timedelta
import alt_proc.cfg
import alt_proc.file
import alt_proc.pg
import alt_proc.time

class Launcher:

    def __init__(self):

        print('Init')
        self.main_dir = os.path.abspath(os.path.dirname(__file__)) + '/'
        self.cfg = alt_proc.cfg.read(self.main_dir + '_cfg/_main.cfg')
        self.projects_dir = os.path.abspath(alt_proc.cfg.main_dir() + '../..') + '/'
        wd = os.getcwd() + '/'
        if wd.split('/')[-2] != 'launcher':
            raise Exception('Wrong working directory. Should be "launcher/"')
        self.alt_proc_wd = os.path.abspath(wd + '../')
        alt_proc_cfg = alt_proc.cfg.read(f'{self.main_dir}../../_cfg/alt_proc.cfg')
        self.db = alt_proc.pg.DB(**alt_proc_cfg.db)
        self.launcher_mtime = datetime.now()
        sql = """
            insert into values (key, value) values ('launcher_mtime', now())
            on conflict (key) do update set value = excluded.value
        """
        self.db.sql(sql)
        sql = """
            insert into values (key, value) values ('launcher_status', 'RUN')
            on conflict (key) do update set value = excluded.value
        """
        self.db.sql(sql)

    def reinit(self):

        self.emit_periodic_events()

    def emit_periodic_events(self):

        sql = '''
            select task_id from tasks t
            where status='ACTIVE' and type='PERIODIC' and last_proc_id is null
            '''
        tasks = self.db.sql(sql)
        for task in tasks:
            sql = '''
                insert into events (task_id) values (%s)
                '''
            event_id = self.db.sql(sql, task.task_id, return_id='event_id')
            sql = '''
                select event_id, e.task_id from events e where event_id=%s
                '''
            event = self.db.sql(sql, event_id, return_one=True)
            proc_id = self.add_new_proc(event)
            sql = '''
                update tasks set last_proc_id = %s where task_id=%s
                '''
            event = self.db.sql(sql, (proc_id, task.task_id))

    def fix_db(self):
        pass

    def add_new_event_procs(self):

        sql = '''
            select task_id from tasks t
            where status='ACTIVE' and  
                exists(
                    select event_id from events e 
                    where e.task_id=t.task_id and e.status='WAIT'
                    )
            '''
        waiting_task_ids = [task.task_id for task in self.db.sql(sql)]
        if not waiting_task_ids:
            return

        sql = '''
            select t.task_id, sum(p.status is not null::int) as n_procs, t.n_runs
            from tasks t 
            left join events e on t.task_id = e.task_id
            left join procs p on e.event_id = p.event_id
            where (p.status is null or p.status not in ('DONE', 'DELETED')) and 
                t.task_id in %s
            group by t.task_id
            '''
        add_tasks = self.db.sql(sql, (tuple(waiting_task_ids),))

        for task in add_tasks:
            n_events = task.n_runs - task.n_procs
            if n_events <= 0:
                continue
            sql = '''
                select event_id, e.task_id from events e 
                left join tasks t on t.task_id = e.task_id
                where t.task_id=%s and e.status='WAIT'
                limit %s
                '''
            events = self.db.sql(sql, (task.task_id, n_events))
            for event in events:
                self.add_new_proc(event)

    def add_new_proc(self, event):

        error = None
        task = self.db.sql("select * from tasks where task_id=%s", event.task_id, return_one=True)
        if task.status != 'ACTIVE':
            return
        task_file = f'{self.projects_dir}{task.project}/main/_cfg/{task.name}.task'
        if not os.path.exists(task_file):
            error = f'Task file not exists: {task_file}'
        if not error:
            try:
                task_cfg = alt_proc.cfg.read(task_file)
            except KeyboardInterrupt:
                sys.exit()
            except Exception as ex:
                print(ex)
                error = f'Error reading task file: {task_file}'
        if not error:
            try:
                if len(task_cfg.scripts) < 1:
                    raise Exception('Task scripts empty')
                for script in task_cfg.scripts:
                    script_file = f'{self.projects_dir}{task.project}/main/{script.script}'
                    if not os.path.exists(script_file):
                        error = f'Script file not exists: {script_file}'
            except KeyboardInterrupt:
                sys.exit()
            except Exception as ex:
                print(ex)
                error = 'Wrong task file format'
        if error:
            self.message('ERROR', error)
            sql = "update tasks set status='FATAL' where task_id=%s"
            self.db.sql(sql, event.task_id)
            return
        sql = '''
            insert into procs (event_id) values (%s)
            '''
        proc_id = self.db.sql(sql, event.event_id, return_id='proc_id')
        for iscript, script in enumerate(task_cfg.scripts):
            sql = '''
                insert into scripts (proc_id, iscript, script, name, resources, status) 
                values (%s, %s, %s, %s, %s, %s)
                '''
            self.db.sql(sql, (proc_id, iscript, script.script, alt_proc.file.name(script.script),
                              script.get('resources'), 'WAIT' if iscript == 0 else 'NEXT'))
        sql = '''
            update events set status='USED' where event_id=%s
            '''
        self.db.sql(sql, event.event_id)
        print('Proc created', proc_id)

        return proc_id

    def message(self, type, msg):
        print(type, msg)

    def choose_script_to_start(self):
        sql = '''
            select s.script_id, s.iscript, s.script, s.name, t.project, p.proc_id, t.task_id 
            from scripts s
            left join procs p on s.proc_id = p.proc_id
            left join events e on e.event_id = p.event_id
            left join tasks t on t.task_id = e.task_id
            where s.status='WAIT' and p.status='WAIT' and t.status='ACTIVE' and 
                (p.run_at<now() or p.run_at is null)
            order by t.priority desc
        '''
        scripts = self.db.sql(sql)
        if not scripts:
            return

        script = scripts[0]

        return script

    def run_script(self, script):
        proc_wd = f'{self.alt_proc_wd}/procs/{script.proc_id}/'
        script_wd = f'{proc_wd}_{script.iscript:02d}_{script.name}/'
        alt_proc.file.mkdir(script_wd)
        script_path = f'{self.projects_dir}{script.project}/main/{script.script}'
        alt_proc.file.write(script_wd + 'run.cfg', script_path)
        alt_proc.file.write(script_wd + 'run.bash', 'ipython /alt_proc/projects/_cfg/run.py')
        print('Starting script', script_path)
        subprocess.check_call('chmod u+x ' + script_wd + 'run.bash', shell=True)

        sql = """
            update scripts set status='RUN', stime=now(), etime=null where script_id=%s
        """
        self.db.sql(sql, (script.script_id))

        cmd = f'{sys.executable} {script_path} >>log.txt 2>&1'
        os_pid = subprocess.Popen(cmd, cwd=script_wd, shell=True).pid

        sql = """
            update procs set status='RUN', os_pid = %s, mtime=now() where proc_id=%s
        """
        self.db.sql(sql, (os_pid, script.proc_id))
        sql = """
            update tasks set last_proc_id = %s where task_id=%s
        """
        self.db.sql(sql, (script.proc_id, script.task_id))

    def update_running_procs_status(self):
        # running procs with no running scripts
        sql = """
            select p.proc_id, t.type, t.period 
            from procs p
            left join events e on e.event_id = p.event_id
            left join tasks t on e.task_id = t.task_id
            where p.status='RUN' and not exists(
                select script_id from scripts s where s.proc_id=p.proc_id and s.status='RUN'  
                ) 
        """
        procs = self.db.sql(sql)
        for proc in procs:
            sql = """
                select script_id, status, result from scripts where proc_id=%s order by iscript
            """
            scripts = self.db.sql(sql, proc.proc_id)
            proc_done, result = False, 'SUCCESS'
            for script in scripts:
                if script.result == 'FATAL':
                    result = 'FATAL'
                    proc_done = True
                    break
                if script.result == 'ERRORS':
                    result = 'ERRORS'
                if script.status != 'DONE':
                    sql = """
                        update scripts set status='WAIT' where script_id=%s
                    """
                    self.db.sql(sql, script.script_id)
                    sql = """
                        update procs set status='WAIT' where proc_id=%s
                    """
                    self.db.sql(sql, proc.proc_id)
                    break
            else:
                proc_done = True

            if proc_done:
                if proc.type == 'EVENT':
                    sql = """
                        update procs set status='DONE', result = %s where proc_id=%s
                    """
                    self.db.sql(sql, (result, proc.proc_id))
                else:
                    sql = """
                        update procs 
                        set status='WAIT', result = %s, run_at=now() + interval '%s MINUTES' 
                        where proc_id=%s
                    """
                    self.db.sql(sql, (result, proc.period, proc.proc_id))
                    sql = """
                        update scripts set status='NEXT' where proc_id=%s
                    """
                    self.db.sql(sql, proc.proc_id)
                    sql = """
                        update scripts set status='WAIT' where proc_id=%s and iscript=0
                    """
                    self.db.sql(sql, proc.proc_id)

    def update_host_mtime(self):

        if datetime.now() - self.launcher_mtime < timedelta(minutes=1):
             return

        sql = """
            update values set value = now() where key='launcher_mtime' 
        """
        self.db.sql(sql)

    def get_launcher_status(self):

        sql = """
            select value from values where key='launcher_status' 
        """
        return self.db.sql(sql, return_one=True).value

    def loop(self):

        self.reinit()

        print('Loop')
        while True:
            self.update_host_mtime()

            self.update_running_procs_status()

            status = self.get_launcher_status()
            if status == 'EXIT':
                sys.exit()
            if status == 'RUN':
                self.add_new_event_procs()

                script = self.choose_script_to_start()
                if script:
                    self.run_script(script)

            time.sleep(1)


if __name__ == '__main__':
    launcher = Launcher()

    launcher.loop()
