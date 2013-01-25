drop table if exists category;
create table category (
	id serial not null primary key,
	locale varchar(16) not null references locale (id),
	name varchar(32) not null,
	parent integer references category (id),
	priority integer not null default 0
);


-- ############################################################################
-- UK


insert into category (locale, priority, name) values ('en-gb', 11000, 'Music');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(130, 'Pop'),
		(120, 'Rock'),
		(110, 'Metal'),
		(100, 'Electronic'),
		(90,  'Dubstep'),
		(80,  'Hip Hop'),
		(70,  'Disco'),
		(60,  'RNB'),
		(50,  'Folk'),
		(40,  'World'),
		(30,  'Latin'),
		(20,  'Jazz'),
		(10,  'Classical')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'Music';


insert into category (locale, priority, name) values ('en-gb', 10000, 'Gaming');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(120, 'PS3'),
		(110, 'Xbox 360'),
		(100, 'Wii U'),
		(90,  '3DS '),
		(80,  'VITA'),
		(70,  'PC'),
		(60,  'IOS'),
		(50,  'Android'),
		(40,  'Retro'),
		(30,  'Walkthroughs'),
		(20,  'Esport'),
		(10,  'Interview')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'Gaming';

insert into category (locale, priority, name) values ('en-gb', 9000, 'Movies');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(110, 'Comedy'),
		(100, 'Thriller'),
		(90,  'Sci-fi'),
		(80,  'Action'),
		(70,  'Fantasy'),
		(60,  'Anime'),
		(50,  'Dramas'),
		(40,  'Horror'),
		(30,  'Romance'),
		(20,  'Musicals'),
		(10,  'World cinema')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'Movies';

insert into category (locale, priority, name) values ('en-gb', 8000, 'TV');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(50,  'Series'),
		(40,  'Shows'),
		(30,  'Reality show'),
		(20,  'Ads'),
		(10,  'Celebrities')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'TV';

insert into category (locale, priority, name) values ('en-gb', 7000, 'Animation');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(40,  'Cartoons'),
		(30,  'Anime'),
		(20,  'Short movies'),
		(10,  'Interview')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'Animation';

insert into category (locale, priority, name) values ('en-gb', 6000, 'Comedy');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(40,  'Animals & pets'),
		(30,  'Fails'),
		(20,  'Sketches'),
		(10,  'WTF')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'Comedy';

insert into category (locale, priority, name) values ('en-gb', 5000, 'Style');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(90,  'Designers'),
		(80,  'Runway'),
		(70,  'Shopping'),
		(60,  'Street style'),
		(50,  'Front row'),
		(40,  'Menswear'),
		(30,  'Interview'),
		(20,  'Accessories'),
		(10,  'Beauty')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'Style';

insert into category (locale, priority, name) values ('en-gb', 4000, 'Living');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(90,  'Design'),
		(80,  'Art'),
		(70,  'Interiors'),
		(60,  'Cars'),
		(50,  'Bikes'),
		(40,  'Family'),
		(30,  'Health'),
		(20,  'Travel'),
		(10,  'Craft')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'Living';

insert into category (locale, priority, name) values ('en-gb', 3000, 'Genius');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(80,  'Tech'),
		(70,  'History'),
		(60,  'Nature'),
		(50,  'Science'),
		(40,  'Talks'),
		(30,  'Hands-on'),
		(20,  'How to'),
		(10,  'News')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'Genius';

insert into category (locale, priority, name) values ('en-gb', 2000, 'Sports');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(130, 'Football'),
		(120, 'Cricket'),
		(110, 'Rugby'),
		(100, 'F1'),
		(90,  'Boxing'),
		(80,  'UFC'),
		(70,  'Tennis'),
		(60,  'WRC'),
		(50,  'Darts'),
		(40,  'NFL'),
		(30,  'MLB'),
		(20,  'NBA'),
		(10,  'NHL')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'Sports';

insert into category (locale, priority, name) values ('en-gb', 1000, 'Food');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(60,  'Chefs'),
		(50,  'Recipes'),
		(40,  'Healthy'),
		(30,  'Drinks'),
		(20,  'Cakes'),
		(10,  'Restaurants')
	) as c (name, priority) where locale = 'en-gb' and p.name = 'Food';


-- ############################################################################
-- US


insert into category (locale, priority, name) values ('en-us', 11000, 'Music');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(130, 'Pop'),
		(120, 'Rock'),
		(110, 'Metal'),
		(100, 'Electronic'),
		(90,  'Dubstep'),
		(80,  'Hip Hop'),
		(70,  'Disco'),
		(60,  'RNB'),
		(50,  'Folk'),
		(40,  'World'),
		(30,  'Latin'),
		(20,  'Jazz'),
		(10,  'Classical')
	) as c (name, priority) where locale = 'en-us' and p.name = 'Music';


insert into category (locale, priority, name) values ('en-us', 10000, 'Gaming');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(120, 'PS3'),
		(110, 'Xbox 360'),
		(100, 'Wii U'),
		(90,  '3DS '),
		(80,  'VITA'),
		(70,  'PC'),
		(60,  'IOS'),
		(50,  'Android'),
		(40,  'Retro'),
		(30,  'Walkthroughs'),
		(20,  'Esport'),
		(10,  'Interview')
	) as c (name, priority) where locale = 'en-us' and p.name = 'Gaming';

insert into category (locale, priority, name) values ('en-us', 9000, 'Movies');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(110, 'Comedy'),
		(100, 'Thriller'),
		(90,  'Sci-fi'),
		(80,  'Action'),
		(70,  'Fantasy'),
		(60,  'Anime'),
		(50,  'Dramas'),
		(40,  'Horror'),
		(30,  'Romance'),
		(20,  'Musicals'),
		(10,  'World cinema')
	) as c (name, priority) where locale = 'en-us' and p.name = 'Movies';

insert into category (locale, priority, name) values ('en-us', 8000, 'TV');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(50,  'Series'),
		(40,  'Shows'),
		(30,  'Reality show'),
		(20,  'Ads'),
		(10,  'Celebrities')
	) as c (name, priority) where locale = 'en-us' and p.name = 'TV';

insert into category (locale, priority, name) values ('en-us', 7000, 'Animation');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(40,  'Cartoons'),
		(30,  'Anime'),
		(20,  'Short movies'),
		(10,  'Interview')
	) as c (name, priority) where locale = 'en-us' and p.name = 'Animation';

insert into category (locale, priority, name) values ('en-us', 6000, 'Comedy');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(40,  'Animals & pets'),
		(30,  'Fails'),
		(20,  'Sketches'),
		(10,  'WTF'),
		(5,   'Geeky')
	) as c (name, priority) where locale = 'en-us' and p.name = 'Comedy';

insert into category (locale, priority, name) values ('en-us', 5000, 'Style');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(90,  'Designers'),
		(80,  'Runway'),
		(70,  'Shopping'),
		(60,  'Street style'),
		(50,  'Front row'),
		(40,  'Menswear'),
		(30,  'Interview'),
		(20,  'Accessories'),
		(10,  'Beauty')
	) as c (name, priority) where locale = 'en-us' and p.name = 'Style';

insert into category (locale, priority, name) values ('en-us', 4000, 'Living');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(90,  'Design'),
		(80,  'Art'),
		(70,  'Interiors'),
		(60,  'Cars'),
		(50,  'Bikes'),
		(40,  'Family'),
		(30,  'Health'),
		(20,  'Travel'),
		(10,  'Craft')
	) as c (name, priority) where locale = 'en-us' and p.name = 'Living';

insert into category (locale, priority, name) values ('en-us', 3000, 'Genius');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(80,  'Tech'),
		(70,  'History'),
		(60,  'Nature'),
		(50,  'Science'),
		(40,  'Talks'),
		(30,  'Hands-on'),
		(20,  'How to'),
		(10,  'News')
	) as c (name, priority) where locale = 'en-us' and p.name = 'Genius';

insert into category (locale, priority, name) values ('en-us', 2000, 'Sports');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(110, 'NFL'),
		(100, 'MLB'),
		(90,  'NBA'),
		(80,  'NHL'),
		(70,  'NCAAF'),
		(60,  'NCAAM'),
		(50,  'Nascar'),
		(40,  'Golf'),
		(30,  'Soccer'),
		(20,  'Tennis'),
		(10,  'Boxing')
	) as c (name, priority) where locale = 'en-us' and p.name = 'Sports';

insert into category (locale, priority, name) values ('en-us', 1000, 'Food');
insert into category (locale, priority, name, parent)
	select locale, c.name, c.priority, p.id from category p, (values 
		(60,  'Chefs'),
		(50,  'Recipes'),
		(40,  'Healthy'),
		(30,  'Drinks'),
		(20,  'Cakes'),
		(10,  'Restaurants')
	) as c (name, priority) where locale = 'en-us' and p.name = 'Food';


-- ############################################################################
-- mapping

insert into category_locale (here, there)
	select a.id, b.id
		from category a join category b on
		a.locale = 'en-gb' and
		b.locale = 'en-us' and
		a.name = replace(b.name, 'Soccer', 'Football');

