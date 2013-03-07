create table subscription (
	"user" char(22) not null references "user" (id),
	channel char(24) not null references channel (id),
	date_created timestamp not null,
	primary key ("user", channel)
);
