create table admin_log (
	id serial not null primary key,
	username varchar(254) not null,
	"timestamp" timestamp not null,
	action varchar(254) not null,
	model varchar(254) not null,
	instance_id varchar(254) not null,
	value varchar(1024) not null default ''
);
