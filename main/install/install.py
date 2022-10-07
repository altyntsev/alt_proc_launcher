import alt_path
from _header import *
import db_lib

print('Install')

db = db_lib.connect()

# db.sql( alt.file.read(main_dir + 'install/host.sql') )

values = db_lib.Values(db)

db.sql("delete from values")
db.sql("insert into values values ('launcher_mtime', %s)", alt.time.now())
db.sql("insert into values values ('host_status', 'PAUSE')")
db.sql("insert into values values ('cfg_msgs', '')")
db.sql("insert into values values ('cfg_resources', '{}')")

print('Done')