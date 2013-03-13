alter type external_system add value 'twitter';
alter type external_system add value 'google';

create table reserved_username (
	username varchar(52) not null primary key,
	external_system external_system not null,
	external_uid varchar(1024) not null,
	external_data text
);
