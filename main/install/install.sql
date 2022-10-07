create table cmds
(
	cmd_id serial not null
		constraint cmds_pk
			primary key,
	name varchar not null,
	params json,
	status varchar default 'WAIT'::character varying not null,
	error varchar,
	ctime timestamp default now() not null
);

alter table cmds owner to alt_proc;

create index cmds_status_index
	on cmds (status);

create table tasks
(
	task_id serial not null
		constraint tasks_pk
			primary key,
	type varchar not null,
	name varchar not null,
	status varchar default 'PAUSE'::character varying not null,
	project varchar not null,
	period integer,
	priority integer default 0 not null,
	n_fatals integer default 1 not null,
	n_runs integer default 1 not null
);

alter table tasks owner to alt_proc;

create index tasks_status_index
	on tasks (status);

create table events
(
	event_id serial not null
		constraint events_pk
			primary key,
	task_id integer not null
		constraint events_tasks_fk
			references tasks
				on update cascade on delete cascade,
	param varchar,
	ctime timestamp default now() not null,
	status varchar default 'WAIT'::character varying not null,
	params json
);

alter table events owner to alt_proc;

create index events_status_index
	on events (status);

create table jobs
(
	job_id serial not null
		constraint jobs_pk
			primary key,
	status varchar default 'WAIT'::character varying not null,
	result varchar,
	todo boolean default false not null,
	event_id integer
		constraint jobs_events_fk
			references events
				on update cascade on delete cascade,
	ctime timestamp default now() not null,
	stime timestamp,
	etime timestamp,
	mtime timestamp not null,
	run_at timestamp,
	os_pid integer
);

alter table jobs owner to alt_proc;

create index jobs_status_index
	on jobs (status);

create table scripts
(
	script_id serial not null
		constraint scripts_pk
			primary key,
	job_id integer not null
		constraint scripts_jobs_fk
			references jobs
				on update cascade on delete cascade,
	iscript integer,
	cmd varchar not null,
	name varchar not null,
	status varchar default 'WAIT'::character varying not null,
	result varchar,
	todo boolean default false not null,
	last_run_id integer,
	resources json
);

alter table scripts owner to alt_proc;

create table msgs
(
	msg_id serial not null
		constraint msgs_pk
			primary key,
	msg varchar not null,
	type varchar not null,
	active boolean default true not null,
	script_id integer not null
		constraint msgs_scripts_fk
			references scripts
				on update cascade on delete cascade,
	stime timestamp not null,
	etime timestamp not null,
	n_runs integer default 1 not null,
	todo boolean default false not null,
	read boolean default false not null,
	send boolean default false not null
);

alter table msgs owner to alt_proc;

create table runs
(
	run_id serial not null
		constraint runs_pk
			primary key,
	script_id integer not null
		constraint runs_scripts_fk
			references scripts
				on update cascade on delete cascade,
	result varchar,
	stime timestamp default now(),
	etime timestamp,
	restart_after integer,
	msgs varchar,
	debug boolean default false
);

alter table runs owner to alt_proc;

create table values
(
	name varchar not null
		constraint values_pk
			primary key,
	value varchar
);

alter table values owner to alt_proc;

create table monitor
(
	date date not null
		constraint monitor_pk
			primary key,
	data json not null
);

alter table monitor owner to alt_proc;

