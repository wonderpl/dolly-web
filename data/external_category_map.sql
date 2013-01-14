drop table if exists external_category_map;
drop table if exists external_category_map;
create table external_category_map (
	id integer not null primary key,
	locale varchar(16) not null references locale (id),
	source integer not null references source (id),
	term varchar(32) not null,
	label varchar(64),
	category integer references category (id)
);

-- from http://gdata.youtube.com/schemas/2007/categories.cat
insert into external_category_map (id, locale, source, term, label, category) values
	(0,  'en-gb', 1, 'Film', 'Film & Animation', 5),
	(1,  'en-gb', 1, 'Autos', 'Autos & Vehicles', NULL),
	(2,  'en-gb', 1, 'Music', 'Music', 1),
	(3,  'en-gb', 1, 'Animals', 'Pets & Animals', NULL),
	(4,  'en-gb', 1, 'Sports', 'Sports', 6),
	(5,  'en-gb', 1, 'Shortmov', 'Short Movies', NULL),
	(6,  'en-gb', 1, 'Travel', 'Travel & Events', NULL),
	(7,  'en-gb', 1, 'Games', 'Gaming', 2),
	(8,  'en-gb', 1, 'Videoblog', 'Videoblogging', 41),
	(9,  'en-gb', 1, 'People', 'People & Blogs', 41),
	(10, 'en-gb', 1, 'Comedy', 'Comedy', 8),
	(11, 'en-gb', 1, 'Entertainment', 'Entertainment', 5),
	(12, 'en-gb', 1, 'News', 'News & Politics', NULL),
	(13, 'en-gb', 1, 'Howto', 'Howto & Style', 91),
	(14, 'en-gb', 1, 'Education', 'Education', 9),
	(15, 'en-gb', 1, 'Tech', 'Science & Technology', 92),
	(16, 'en-gb', 1, 'Nonprofit', 'Nonprofits & Activism', NULL),
	(17, 'en-gb', 1, 'Movies', 'Movies', 51),
	(18, 'en-gb', 1, 'Movies_anime_animation', 'Anime/Animation', NULL),
	(19, 'en-gb', 1, 'Movies_action_adventure', 'Action/Adventure', NULL),
	(20, 'en-gb', 1, 'Movies_classics', 'Classics', NULL),
	(21, 'en-gb', 1, 'Movies_comedy', 'Comedy', NULL),
	(22, 'en-gb', 1, 'Movies_documentary', 'Documentary', NULL),
	(23, 'en-gb', 1, 'Movies_drama', 'Drama', 52),
	(24, 'en-gb', 1, 'Movies_family', 'Family', NULL),
	(25, 'en-gb', 1, 'Movies_foreign', 'Foreign', NULL),
	(26, 'en-gb', 1, 'Movies_horror', 'Horror', NULL),
	(27, 'en-gb', 1, 'Movies_sci_fi_fantasy', 'Sci-Fi/Fantasy', NULL),
	(28, 'en-gb', 1, 'Movies_thriller', 'Thriller', NULL),
	(29, 'en-gb', 1, 'Movies_shorts', 'Shorts', NULL),
	(30, 'en-gb', 1, 'Shows', 'Shows', NULL),
	(31, 'en-gb', 1, 'Trailers', 'Trailers', 51);
