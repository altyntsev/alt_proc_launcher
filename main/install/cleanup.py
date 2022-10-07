import alt_path
from _header import *
import db_lib

print('Cleanup')

stop

db = db_lib.connect()

alt_proc_wd = os.path.abspath(os.getcwd() + '/..').replace('\\','/') + '/'
alt.file.delete(alt_proc_wd + 'jobs/')

for table in ['cmds','msgs','runs','scripts','jobs','events']: # 'tasks'
    print(table)
    db.sql("truncate table %s cascade" % table)
    db.sql("alter sequence %s_%s_id_seq restart with 1" % (table, table[:-1]))

tasks = db.sql("select * from tasks where status='ACTIVE' and type='PERIODIC'")
for task in tasks:
    sql = "insert into events (task_id) values (%s)"
    db.sql(sql, task.task_id)

print('Done')