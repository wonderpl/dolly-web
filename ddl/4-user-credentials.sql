alter table "user"
	add password_hash varchar(60) not null default '',
	add refresh_token char(32) not null default '';

create index refresh_token on
	"user" (refresh_token);
