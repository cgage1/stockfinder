

CREATE TABLE dbo.symbols (
	symbol varchar PRIMARY key,
	"type" varchar NULL,
	"subtype" varchar NULL,
	exchange varchar null,
	category varchar NULL,
	description varchar NULL,
	"comment" varchar NULL
);
COMMENT ON TABLE dbo.symbols IS 'symbols lookup table';


select * from dbo.symbols


-- drop table dbo.symbol_quotes
CREATE TABLE dbo.symbol_quotes (
	id bigserial,
	symbol varchar not null,
	date date not null, 
	open float NULL,
	high varchar NULL,
	low varchar null,
	close varchar not null,
	adj_close varchar NULL,
	volume varchar null,
	primary key (symbol,date)
	
);

-- drop table dbo.symbol_quotes_staging
CREATE TABLE dbo.symbol_quotes_staging (
	symbol varchar not null,
	date varchar not null,
	open float NULL,
	high varchar NULL,
	low varchar null,
	close varchar not null,
	adj_close varchar NULL,
	volume varchar null
);
COMMENT ON TABLE dbo.symbol_quotes_staging IS 'staging table for dbo.symbol_quotes, volatile data.';


/* upsert from staging into main table */ 
INSERT INTO dbo.symbol_quotes (symbol, "date", "open", high, low, "close", adj_close, volume)
	select symbol, cast("date" as date) date , "open", high, low, "close", adj_close, volume
	from dbo.symbol_quotes_staging 
	on conflict 
	do nothing 
; 


-- get symbol dates for 
with maxdates as (
	select symbol, max(date) maxdate 
	from dbo.symbol_quotes
	group by symbol 
	)
select s.symbol, cast(coalesce(maxdates.maxdate, '1980-01-01') as varchar) maxdate 
from dbo.symbols s
LEFT JOIN maxdates ON s.symbol = maxdates.symbol 



SELECT sq.symbol, sq."date", sq."open", sq.high, sq.low, sq."close", sq.adj_close, sq.volume
FROM dbo.symbol_quotes sq
join dbo.symbols s on s.symbol = sq.symbol 
	and s.active = '1'
	
	
SELECT * FROM dbo.symbols 




	
	SELECT symbol, "type", subtype, exchange, category, description, "comment", active
	FROM dbo.symbols where symbol = 'MDT'

-- delete from dbo.symbols where symbol = 'MDT'

-- update dbo.symbols set type = 'STOCK' where symbol in ('ILMN','BABA')
	
SELECT * FROM dbo.watchlists 


-- drop table dbo.watchlists 
create table dbo.watchlists (
	id serial not null primary key,
	shortname varchar unique not null, 
	longname varchar
	)

insert into dbo.watchlists (shortname, longname) select 'Algo','Trading algorithm potentials'


select * from dbo.watchlists 


-- drop table dbo.watchlistsymbols
create table dbo.watchlistsymbols (
	id serial not null, 
	watchlist_id int REFERENCES dbo.watchlists(id), 
	symbol varchar REFERENCES dbo.symbols(symbol),
	primary key (watchlist_id,symbol)
	)


-- create default watchlist 
insert into dbo.watchlistsymbols (watchlist_id, symbol)
	select (select id from dbo.watchlists where shortname = 'Algo'), symbol 
	from dbo.symbols 
	where symbol in ('OMIC','ALGN')


	
	
	
	
