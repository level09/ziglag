-- ZigLag on stk 16 at alembic revision 20261006_0002 (schema from the old chain), plus sample rows.
CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
CREATE TABLE role (
	id INTEGER NOT NULL, 
	name VARCHAR(80), 
	description VARCHAR(255), 
	PRIMARY KEY (id), 
	UNIQUE (name)
);
CREATE TABLE user (
	id INTEGER NOT NULL, 
	username VARCHAR(255), 
	fs_uniquifier VARCHAR(255) NOT NULL, 
	name VARCHAR(255), 
	created_at DATETIME NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password VARCHAR(255) NOT NULL, 
	password_set BOOLEAN NOT NULL, 
	active BOOLEAN, 
	failed_login_count INTEGER NOT NULL, 
	locked_until DATETIME, 
	confirmed_at DATETIME, 
	last_login_at DATETIME, 
	current_login_at DATETIME, 
	last_login_ip VARCHAR(255), 
	current_login_ip VARCHAR(255), 
	login_count INTEGER, 
	fs_webauthn_user_handle VARCHAR(64), 
	tf_phone_number VARCHAR(64), 
	tf_primary_method VARCHAR(140), 
	tf_totp_secret VARCHAR(255), 
	mf_recovery_codes JSON, 
	PRIMARY KEY (id), 
	UNIQUE (email), 
	UNIQUE (fs_uniquifier), 
	UNIQUE (fs_webauthn_user_handle), 
	UNIQUE (username)
);
CREATE TABLE oauth (
	id INTEGER NOT NULL, 
	provider VARCHAR(50) NOT NULL, 
	provider_user_id VARCHAR(256) NOT NULL, 
	token JSON, 
	created_at DATETIME NOT NULL, 
	user_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id), 
	CONSTRAINT uq_oauth_provider_user UNIQUE (provider, provider_user_id)
);
CREATE TABLE roles_users (
	user_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	PRIMARY KEY (user_id, role_id), 
	FOREIGN KEY(role_id) REFERENCES role (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE user_sessions (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	session_token VARCHAR(255) NOT NULL, 
	last_active DATETIME, 
	expires_at DATETIME, 
	ip_address VARCHAR(255), 
	meta JSON, 
	is_active BOOLEAN, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id), 
	UNIQUE (session_token)
);
CREATE TABLE web_authn (
	id INTEGER NOT NULL, 
	credential_id BLOB NOT NULL, 
	public_key BLOB NOT NULL, 
	sign_count INTEGER NOT NULL, 
	transports JSON, 
	extensions VARCHAR(255), 
	lastuse_datetime DATETIME NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	usage VARCHAR(64) NOT NULL, 
	backup_state BOOLEAN NOT NULL, 
	device_type VARCHAR(64) NOT NULL, 
	user_id VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (fs_webauthn_user_handle) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_web_authn_credential_id ON web_authn (credential_id);
CREATE TABLE business_settings (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	business_name VARCHAR(255), 
	business_number VARCHAR(100), 
	business_number_label VARCHAR(100), 
	owner_name VARCHAR(255), 
	address_line1 VARCHAR(255), 
	address_line2 VARCHAR(255), 
	address_line3 VARCHAR(255), 
	email VARCHAR(255), 
	phone VARCHAR(50), 
	mobile VARCHAR(50), 
	website VARCHAR(255), 
	logo_path VARCHAR(500), 
	tax_type VARCHAR(50), 
	tax_rate NUMERIC(5, 2), 
	tax_label VARCHAR(50), 
	tax_inclusive BOOLEAN, 
	invoice_prefix VARCHAR(20), 
	invoice_next_number INTEGER, 
	default_invoice_notes TEXT, 
	default_email_message TEXT, 
	send_copy_to_self BOOLEAN, 
	locale VARCHAR(10), 
	currency_code VARCHAR(3), 
	currency_symbol VARCHAR(5), 
	date_format VARCHAR(20), 
	tax_year_begins INTEGER, 
	invoice_title VARCHAR(100), 
	quantity_label VARCHAR(50), 
	unit_cost_label VARCHAR(50), 
	show_quantity_unit_cost BOOLEAN, 
	payment_instructions TEXT, 
	payment_paypal VARCHAR(255), 
	payment_other TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, tax_number VARCHAR(100), vat_id VARCHAR(100), default_tax_treatment VARCHAR(30) DEFAULT 'standard' NOT NULL, default_invoice_template VARCHAR(30) DEFAULT 'precision' NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id), 
	UNIQUE (user_id)
);
CREATE TABLE client (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	email VARCHAR(255), 
	address_line1 VARCHAR(255), 
	address_line2 VARCHAR(255), 
	address_line3 VARCHAR(255), 
	phone VARCHAR(50), 
	mobile VARCHAR(50), 
	fax VARCHAR(50), 
	notes TEXT, 
	created_at DATETIME, 
	updated_at DATETIME, vat_id VARCHAR(100), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE invoice (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	client_id INTEGER, 
	invoice_number VARCHAR(50) NOT NULL, 
	status VARCHAR(20), 
	date DATE, 
	due_date DATE, 
	terms VARCHAR(50), 
	subtotal NUMERIC(12, 2), 
	tax_amount NUMERIC(12, 2), 
	discount_type VARCHAR(20), 
	discount_value NUMERIC(12, 2), 
	discount_amount NUMERIC(12, 2), 
	total NUMERIC(12, 2), 
	amount_paid NUMERIC(12, 2), 
	balance_due NUMERIC(12, 2), 
	currency_code VARCHAR(3), 
	currency_symbol VARCHAR(5), 
	tax_type VARCHAR(50), 
	tax_rate NUMERIC(5, 2), 
	tax_label VARCHAR(50), 
	tax_inclusive BOOLEAN, 
	notes TEXT, 
	share_token VARCHAR(64), 
	from_name VARCHAR(255), 
	from_email VARCHAR(255), 
	from_address TEXT, 
	from_phone VARCHAR(50), 
	from_business_number VARCHAR(100), 
	created_at DATETIME, 
	updated_at DATETIME, 
	sent_at DATETIME, 
	viewed_at DATETIME, 
	paid_at DATETIME, service_date_from DATE, service_date_to DATE, tax_treatment VARCHAR(30) DEFAULT 'standard' NOT NULL, tax_exemption_reason TEXT, template_key VARCHAR(30) DEFAULT 'precision' NOT NULL, from_tax_number VARCHAR(100), from_vat_id VARCHAR(100), client_vat_id VARCHAR(100), client_name_snapshot VARCHAR(255), client_email_snapshot VARCHAR(255), client_address_snapshot TEXT, invoice_title_snapshot VARCHAR(100), payment_instructions_snapshot TEXT, archived_pdf_path VARCHAR(500), issued_at DATETIME, cancelled_at DATETIME, share_token_expires_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(client_id) REFERENCES client (id), 
	FOREIGN KEY(user_id) REFERENCES user (id), 
	UNIQUE (invoice_number), 
	UNIQUE (share_token)
);
CREATE TABLE invoice_item (
	id INTEGER NOT NULL, 
	invoice_id INTEGER NOT NULL, 
	description VARCHAR(500) NOT NULL, 
	detail TEXT, 
	quantity NUMERIC(10, 2), 
	unit_price NUMERIC(12, 2), 
	amount NUMERIC(12, 2), 
	taxable BOOLEAN, 
	sort_order INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoice (id) ON DELETE CASCADE
);
CREATE TABLE payment (
	id INTEGER NOT NULL, 
	invoice_id INTEGER NOT NULL, 
	amount NUMERIC(12, 2) NOT NULL, 
	method VARCHAR(50), 
	notes TEXT, 
	payment_date DATE, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoice (id) ON DELETE CASCADE
);
CREATE TABLE "activity" (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	action VARCHAR(255) NOT NULL, 
	data JSON, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_activity_user_id FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE INDEX ix_activity_created_at ON activity (created_at);
CREATE INDEX ix_activity_user_id ON activity (user_id);
CREATE INDEX ix_user_sessions_is_active ON user_sessions (is_active);
CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id);
CREATE TABLE quart_security_state (
	token VARCHAR(160) NOT NULL, 
	payload JSON NOT NULL, 
	expires_at BIGINT NOT NULL, 
	PRIMARY KEY (token)
);
CREATE INDEX ix_quart_security_state_expires_at ON quart_security_state (expires_at);
CREATE TABLE rate_limit_window (
	"key" VARCHAR(160) NOT NULL, 
	count INTEGER NOT NULL, 
	expires_at INTEGER NOT NULL, 
	PRIMARY KEY ("key")
);
CREATE INDEX ix_rate_limit_window_expires_at ON rate_limit_window (expires_at);
INSERT INTO alembic_version VALUES ('20261006_0002');
INSERT INTO user (id, fs_uniquifier, created_at, email, password, password_set, failed_login_count, confirmed_at)
  VALUES (1, 'u1', '2026-03-29 10:00:00', 'owner@example.com', 'hash', 1, 0, NULL);
INSERT INTO business_settings (id, user_id, business_name, vat_id) VALUES (1, 1, 'Example GmbH', 'DE123456789');
INSERT INTO client (id, user_id, name, vat_id) VALUES (1, 1, 'Acme AG', 'DE987654321');
INSERT INTO invoice (id, user_id, client_id, invoice_number, status, total, tax_treatment, template_key)
  VALUES (1, 1, 1, 'INV-0001', 'sent', 119.00, 'standard', 'precision');
INSERT INTO invoice_item (id, invoice_id, description, quantity, unit_price, amount, taxable)
  VALUES (1, 1, 'Consulting', 1, 100.00, 100.00, 1);
