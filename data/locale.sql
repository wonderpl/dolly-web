drop table if exists locale;
create table locale (
	id varchar(16) not null primary key,
	name varchar(32) not null
);

insert into locale (id, name) values
	('en-gb', 'UK'),
	('en-us', 'US');
