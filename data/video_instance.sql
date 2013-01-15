drop table if exists video_instance;
create table video_instance (
	id char(40) not null primary key,
	title varchar(512),	-- XXX: Needed?
	date_added timestamp not null default CURRENT_TIMESTAMP,
	video char(40) not null references video (id),
	channel char(40) not null references channel (id)
);

