CREATE TABLE inventory (id INTEGER PRIMARY KEY, hostname TEXT NOT NULL UNIQUE);
INSERT INTO inventory(hostname) VALUES ('lab-node-1');
