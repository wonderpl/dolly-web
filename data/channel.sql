create table channel (
	id char(40) not null primary key,
	locale varchar(16) not null references locale (id),
	owner char(40) not null, -- references user
	title varchar(512) not null,
	thumbnail_url varchar(1024) not null
);
