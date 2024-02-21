

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








