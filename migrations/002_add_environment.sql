ALTER TABLE inventory ADD COLUMN environment TEXT NOT NULL DEFAULT 'lab';
CREATE INDEX inventory_environment ON inventory(environment);
