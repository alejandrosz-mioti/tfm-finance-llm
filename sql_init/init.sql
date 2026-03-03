-- 1. Tabla de Usuarios
CREATE TABLE usuarios (
user_id BIGINT PRIMARY KEY,
nombre VARCHAR(100),
fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabla de Cuentas CON SUBCUENTAS
CREATE TABLE cuentas (
id SERIAL PRIMARY KEY,
user_id BIGINT REFERENCES usuarios(user_id),
nombre_cuenta VARCHAR(50) NOT NULL,
parent_id INTEGER REFERENCES cuentas(id),
tipo VARCHAR(20), -- 'Principal' o 'Subcuenta'
saldo_actual DECIMAL(12, 2) DEFAULT 0.00,
UNIQUE(user_id, nombre_cuenta) -- Un usuario no puede repetir nombres de cuenta
);

-- 3. Tabla de Transacciones 
CREATE TABLE transacciones (
id SERIAL PRIMARY KEY,
user_id BIGINT REFERENCES usuarios(user_id),
cuenta_id INTEGER REFERENCES cuentas(id), -- Apunta a la cuenta/subcuenta exacta
tipo VARCHAR(50),
monto DECIMAL(12, 2) NOT NULL,
concepto TEXT,
categoria VARCHAR(50),
fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);