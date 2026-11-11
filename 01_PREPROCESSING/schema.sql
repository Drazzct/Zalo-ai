-- Source preserving SQLite stage for biz_101. Convert thousands-separated VND to INTEGER and 'D thg M YYYY' to ISO date.
-- sales_lines_raw stores ALL rows; sales_lines view excludes only identical export repeats within the same order (rulebook §8).
CREATE TABLE sales_lines_raw (
 source_csv_line INTEGER PRIMARY KEY,
 sale_price_vnd INTEGER NOT NULL,
 order_status TEXT NOT NULL,
 product_name TEXT NOT NULL,
 order_date TEXT NOT NULL,
 unit TEXT NOT NULL,
 quantity INTEGER NOT NULL,
 line_amount_vnd INTEGER NOT NULL,
 base_quantity INTEGER NOT NULL,
 order_id TEXT NOT NULL,
 customer_name TEXT NOT NULL,
 is_duplicate_export INTEGER NOT NULL CHECK (is_duplicate_export IN (0,1))
);
CREATE INDEX idx_order_date ON sales_lines_raw(order_date);
CREATE INDEX idx_order_id ON sales_lines_raw(order_id);
CREATE INDEX idx_product_name ON sales_lines_raw(product_name);
CREATE VIEW sales_lines AS SELECT source_csv_line,sale_price_vnd,order_status,product_name,order_date,unit,quantity,line_amount_vnd,base_quantity,order_id,customer_name FROM sales_lines_raw WHERE is_duplicate_export=0;
CREATE TABLE calendar (date TEXT PRIMARY KEY,weekday INTEGER,lunar_day INTEGER,lunar_month INTEGER,lunar_year INTEGER,lunar_leap INTEGER,holiday TEXT);
