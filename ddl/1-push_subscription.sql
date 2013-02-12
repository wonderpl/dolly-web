create table push_subscription (
	id serial not null primary key,
	hub varchar(1024) not null,
	topic varchar(1024) not null,
	verify_token varchar(1024) not null,
	verified boolean not null default false,
	date_added timestamp not null,
	lease_expires timestamp not null,
	constraint hub_topic unique (hub, topic)
);
