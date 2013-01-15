drop table if exists source;
create table source (
	id integer not null primary key,
	label varchar(16) not null,
	player_template text
);

insert into source (id, label) values
	(0, 'rockpack'),
	(1, 'youtube');
