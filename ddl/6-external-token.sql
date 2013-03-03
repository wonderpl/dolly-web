create type external_system as enum ('facebook');
create table external_token (
	id serial not null primary key,
	"user" char(22) not null references "user" (id),
	external_system external_system not null,
	external_token varchar(1024) not null,
	external_uid varchar(1024) not null,
	expires timestamp not null,
	constraint user_system unique ("user", external_system),
	constraint system_uid unique (external_system, external_uid)
);
