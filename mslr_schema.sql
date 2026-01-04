--- Database

CREATE DATABASE IF NOT EXISTS mslr_db;
USE mslr_db;

-- SCC Codes Table
CREATE TABLE scc_codes (
    scc_code VARCHAR(10) PRIMARY KEY,
    is_used BOOLEAN DEFAULT FALSE
);


-- Registered Voters Table

CREATE TABLE voters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    dob DATE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    scc_code VARCHAR(10) NOT NULL,
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scc_code) REFERENCES scc_codes(scc_code)
);

-- Insert  SCC Codes 

INSERT INTO scc_codes (scc_code) VALUES
('1AZN0FXJVM'),
('JOV50TOSYR'),
('SDUBJ5IOYB'),
('YFUVLYBQZR'),
('IGBQET8OOY'),
('R2ZHBUYO2V'),
('Z9HOC1LF4X'),
('9IJKHGHJK4'),
('N5J53QK9FO'),
('ZDN06T01V9'),
('4XRDN9O4AW'),
('921664ML8D'),
('A546AKU16A'),
('V0GB2G690L'),
('12EOU5RGVX'),
('0IXYCAH8UW'),
('GKJ3K1YBGE'),
('46HJV9KH1F'),
('S6K3AV3IVR'),
('IKKSZYJTSH');


select * from scc_codes;

select * from voters;