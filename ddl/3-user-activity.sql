create table user_activity (
	id serial not null primary key,
	"user" char(22) not null references "user" (id),
	action varchar(16) not null,
	date_actioned timestamp not null,
	object_type varchar(16) not null,
	object_id varchar(32) not null
);
