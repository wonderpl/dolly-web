alter table "user"
	add date_of_birth date,
	add date_joined timestamp,
	add date_updated timestamp,
	alter username type varchar(52),	-- facebook limit + 2
	alter first_name type varchar(32),
	alter last_name type varchar(32);

update "user" set
	date_joined = now(),
	date_updated = now();

alter table "user"
	alter date_joined set not null,
	alter date_updated set not null;

create table user_account_event (
	id serial not null primary key,
	username varchar(52) not null,
	event_date timestamp not null,
	event_type varchar(32) not null,
	event_value varchar(1024) not null,
	ip_address inet not null,
	user_agent varchar(1024) not null,
	clientid char(22) not null
);
