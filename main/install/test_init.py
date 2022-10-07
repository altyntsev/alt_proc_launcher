import alt_path
from _header import *
import db_lib

print('Test Init')

db = db_lib.connect()

alt_proc_wd = os.path.abspath(os.getcwd() + '/..').replace('\\','/') + '/'
alt.file.delete(alt_proc_wd + 'jobs/')

for table in ['runs','events','cmds','msgs','scripts','jobs','tasks']:
    db.sql("DELETE from %s" % table)

sql = "insert into cmds (name, params) values (%s,%s)"
db.sql(sql, ('NEW_TASK', json.dumps(dict(
    name='test-scan', project='2018-10-23-alt_proc_tests', type='PERIODIC', period=1))))
db.sql(sql, ('NEW_TASK', json.dumps(dict(
    name='test-simple', project='2018-10-23-alt_proc_tests', type='EVENT'))))

values = db_lib.Values(db)
values['host_status'] = 'RUN'
values['cfg_msgs'] = ''

print('Done')