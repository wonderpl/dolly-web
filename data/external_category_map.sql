-- from http://gdata.youtube.com/schemas/2007/categories.cat
insert into external_category_map (locale, source, term, label)
	select id, 1, term, label from (values
		('Film', 'Film & Animation'),
		('Autos', 'Autos & Vehicles'),
		('Music', 'Music'),
		('Animals', 'Pets & Animals'),
		('Sports', 'Sports'),
		('Shortmov', 'Short Movies'),
		('Travel', 'Travel & Events'),
		('Games', 'Gaming'),
		('Videoblog', 'Videoblogging'),
		('People', 'People & Blogs'),
		('Comedy', 'Comedy'),
		('Entertainment', 'Entertainment'),
		('News', 'News & Politics'),
		('Howto', 'Howto & Style'),
		('Education', 'Education'),
		('Tech', 'Science & Technology'),
		('Nonprofit', 'Nonprofits & Activism'),
		('Movies', 'Movies'),
		('Movies_anime_animation', 'Anime/Animation'),
		('Movies_action_adventure', 'Action/Adventure'),
		('Movies_classics', 'Classics'),
		('Movies_comedy', 'Comedy'),
		('Movies_documentary', 'Documentary'),
		('Movies_drama', 'Drama'),
		('Movies_family', 'Family'),
		('Movies_foreign', 'Foreign'),
		('Movies_horror', 'Horror'),
		('Movies_sci_fi_fantasy', 'Sci-Fi/Fantasy'),
		('Movies_thriller', 'Thriller'),
		('Movies_shorts', 'Shorts'),
		('Shows', 'Shows'),
		('Trailers', 'Trailers')
	) as youtube (term, label), locale;


update external_category_map
	set category = category.id from category, (values
		('Film', 'Movies'),
		('Autos', 'Cars'),
		('Music', 'Music'),
		('Sports', 'Sports'),
		('Travel', 'Travel'),
		('Games', 'Gaming'),
		('Comedy', 'Comedy'),
		('News', 'News'),
		('Howto', 'How to'),
		('Tech', 'Tech'),
		('Shows', 'Shows'),
		('Trailers', 'Movies')
	) as map (term, cat)
	where category.locale = external_category_map.locale and
		category.name = map.cat and
		external_category_map.term = map.term;
