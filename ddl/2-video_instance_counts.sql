alter table video_instance
	add view_count integer not null default 0,
	add star_count integer not null default 0;
