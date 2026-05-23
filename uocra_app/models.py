import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "uocra.db"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
        nombre TEXT NOT NULL, rol TEXT NOT NULL DEFAULT 'cliente',
        activo INTEGER NOT NULL DEFAULT 1, creado_en TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL,
        cuit TEXT, domicilio TEXT, actividad TEXT,
        mail TEXT, cbu TEXT, activa INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS config_mail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        smtp_host TEXT DEFAULT 'smtp.gmail.com', smtp_port INTEGER DEFAULT 587,
        smtp_user TEXT, smtp_password TEXT,
        mail_estudio_1 TEXT DEFAULT 'clgest@gmail.com',
        mail_estudio_2 TEXT DEFAULT 'clgestad@gmail.com'
    );
    CREATE TABLE IF NOT EXISTS usuario_empresa (
        usuario_id INTEGER REFERENCES usuarios(id),
        empresa_id INTEGER REFERENCES empresas(id),
        PRIMARY KEY (usuario_id, empresa_id)
    );
    CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresas(id),
        legajo TEXT NOT NULL, nombre TEXT NOT NULL, cuil TEXT,
        categoria TEXT DEFAULT 'AYUDANTE',
        jornada TEXT DEFAULT 'JORNADA COMPLETA',
        fecha_ingreso TEXT, estado TEXT DEFAULT 'A',
        convenio TEXT DEFAULT 'OBREROS DE LA CONSTRUCCION',
        cp TEXT DEFAULT '4000', activo INTEGER DEFAULT 1,
        UNIQUE(empresa_id, legajo)
    );
    CREATE TABLE IF NOT EXISTS novedades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresas(id),
        empleado_id INTEGER NOT NULL REFERENCES empleados(id),
        periodo_mes TEXT NOT NULL, periodo_anio TEXT NOT NULL,
        estado TEXT DEFAULT 'A', fecha_ini TEXT, fecha_fin TEXT,
        hs1 REAL DEFAULT 0, inas1 REAL DEFAULT 0, enf1 REAL DEFAULT 0,
        fer1 REAL DEFAULT 0, vac1 REAL DEFAULT 0, ext1 REAL DEFAULT 0,
        hs2 REAL DEFAULT 0, inas2 REAL DEFAULT 0, enf2 REAL DEFAULT 0,
        fer2 REAL DEFAULT 0, vac2 REAL DEFAULT 0, ext2 REAL DEFAULT 0,
        obs TEXT, confirmado INTEGER DEFAULT 0, confirmado_en TEXT,
        creado_por INTEGER REFERENCES usuarios(id),
        creado_en TEXT DEFAULT (datetime('now')),
        UNIQUE(empresa_id, empleado_id, periodo_mes, periodo_anio)
    );
    CREATE TABLE IF NOT EXISTS documentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL REFERENCES empresas(id),
        empleado_id INTEGER NOT NULL REFERENCES empleados(id),
        tipo_doc TEXT NOT NULL, estado_empl TEXT NOT NULL,
        nombre_arch TEXT NOT NULL, datos BLOB NOT NULL,
        mime_type TEXT DEFAULT 'application/octet-stream',
        origen TEXT DEFAULT 'cliente',
        estado_doc TEXT DEFAULT 'subido',
        comentario TEXT,
        subido_por INTEGER REFERENCES usuarios(id),
        subido_en TEXT DEFAULT (datetime('now')),
        revisado_por INTEGER REFERENCES usuarios(id),
        revisado_en TEXT
    );
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER REFERENCES usuarios(id),
        accion TEXT NOT NULL, detalle TEXT, ip TEXT,
        ts TEXT DEFAULT (datetime('now'))
    );
    """)
    db.commit()
    cur = db.execute("SELECT id FROM config_mail LIMIT 1")
    if not cur.fetchone():
        db.execute("INSERT INTO config_mail (smtp_host,smtp_port,mail_estudio_1,mail_estudio_2) VALUES ('smtp.gmail.com',587,'clgest@gmail.com','clgestad@gmail.com')")
    cur = db.execute("SELECT id FROM usuarios WHERE email='clgest@gmail.com'")
    if not cur.fetchone():
        db.execute("INSERT INTO usuarios (email,password,nombre,rol) VALUES (?,?,?,?)",
            ("clgest@gmail.com", generate_password_hash("lescgo1"), "Estudio CL Gestion", "estudio"))
        db.execute("INSERT INTO usuarios (email,password,nombre,rol) VALUES (?,?,?,?)",
            ("clgestad@gmail.com", generate_password_hash("lescgo2"), "Estudio CL Admin", "estudio"))
        db.execute("INSERT INTO empresas (nombre,cuit) VALUES (?,?)", ("NASTIQUE OSCAR","30-12345678-9"))
    db.commit()
    db.close()

# ── Auth ─────────────────────────────────────────────────────────
def verificar_login(email, password):
    db = get_db()
    u = db.execute("SELECT * FROM usuarios WHERE email=? AND activo=1",(email,)).fetchone()
    db.close()
    if u and check_password_hash(u["password"], password): return u
    return None

# ── Empresas ─────────────────────────────────────────────────────
def get_empresas_usuario(user_id, rol):
    db = get_db()
    if rol == "estudio":
        rows = db.execute("SELECT * FROM empresas WHERE activa=1 ORDER BY nombre").fetchall()
    else:
        rows = db.execute("SELECT e.* FROM empresas e JOIN usuario_empresa ue ON ue.empresa_id=e.id WHERE ue.usuario_id=? AND e.activa=1",(user_id,)).fetchall()
    db.close()
    return rows

def save_config_empresa(empresa_id, d):
    db = get_db()
    db.execute("UPDATE empresas SET nombre=?,cuit=?,domicilio=?,actividad=?,mail=?,cbu=? WHERE id=?",
        (d["nombre"],d["cuit"],d["domicilio"],d["actividad"],d["mail"],d["cbu"],empresa_id))
    db.commit(); db.close()

# ── Config mail ──────────────────────────────────────────────────
def get_config_mail():
    db = get_db()
    row = db.execute("SELECT * FROM config_mail LIMIT 1").fetchone()
    db.close(); return row

def save_config_mail(d):
    db = get_db()
    db.execute("UPDATE config_mail SET smtp_host=?,smtp_port=?,smtp_user=?,smtp_password=?,mail_estudio_1=?,mail_estudio_2=?",
        (d["smtp_host"],d["smtp_port"],d["smtp_user"],d["smtp_password"],d["mail_estudio_1"],d["mail_estudio_2"]))
    db.commit(); db.close()

# ── Empleados ────────────────────────────────────────────────────
def get_empleados(empresa_id, solo_activos=True):
    db = get_db()
    q = "SELECT * FROM empleados WHERE empresa_id=?"
    if solo_activos: q += " AND activo=1"
    q += " ORDER BY CAST(legajo AS INTEGER)"
    rows = db.execute(q,(empresa_id,)).fetchall()
    db.close(); return rows

def alta_empleado(empresa_id, datos):
    db = get_db()
    cur = db.execute("SELECT MAX(CAST(legajo AS INTEGER)) as m FROM empleados WHERE empresa_id=?",(empresa_id,))
    sig = (cur.fetchone()["m"] or 0) + 1
    db.execute("INSERT INTO empleados (empresa_id,legajo,nombre,cuil,categoria,jornada,fecha_ingreso,estado,convenio,cp) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (empresa_id,str(sig),datos["nombre"],datos["cuil"],datos["categoria"],datos["jornada"],datos.get("fecha_ingreso"),"I",datos.get("convenio","OBREROS DE LA CONSTRUCCION"),datos.get("cp","4000")))
    db.commit(); db.close(); return str(sig)

# ── Novedades ────────────────────────────────────────────────────
def get_novedades_periodo(empresa_id, mes, anio):
    db = get_db()
    rows = db.execute("SELECT n.*,e.nombre as emp_nombre,e.legajo,e.jornada,e.categoria FROM novedades n JOIN empleados e ON e.id=n.empleado_id WHERE n.empresa_id=? AND n.periodo_mes=? AND n.periodo_anio=? ORDER BY CAST(e.legajo AS INTEGER)",(empresa_id,mes,anio)).fetchall()
    db.close(); return rows

def guardar_novedad(empresa_id, empleado_id, mes, anio, d, usuario_id):
    db = get_db()
    db.execute("""INSERT INTO novedades (empresa_id,empleado_id,periodo_mes,periodo_anio,estado,fecha_ini,fecha_fin,hs1,inas1,enf1,fer1,vac1,ext1,hs2,inas2,enf2,fer2,vac2,ext2,obs,creado_por) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(empresa_id,empleado_id,periodo_mes,periodo_anio) DO UPDATE SET estado=excluded.estado,fecha_ini=excluded.fecha_ini,fecha_fin=excluded.fecha_fin,hs1=excluded.hs1,inas1=excluded.inas1,enf1=excluded.enf1,fer1=excluded.fer1,vac1=excluded.vac1,ext1=excluded.ext1,hs2=excluded.hs2,inas2=excluded.inas2,enf2=excluded.enf2,fer2=excluded.fer2,vac2=excluded.vac2,ext2=excluded.ext2,obs=excluded.obs,creado_por=excluded.creado_por""",
        (empresa_id,empleado_id,mes,anio,d.get("estado","A"),d.get("fecha_ini"),d.get("fecha_fin"),d.get("hs1",0),d.get("inas1",0),d.get("enf1",0),d.get("fer1",0),d.get("vac1",0),d.get("ext1",0),d.get("hs2",0),d.get("inas2",0),d.get("enf2",0),d.get("fer2",0),d.get("vac2",0),d.get("ext2",0),d.get("obs",""),usuario_id))
    db.commit(); db.close()

def confirmar_periodo(empresa_id, mes, anio):
    db = get_db()
    db.execute("UPDATE novedades SET confirmado=1,confirmado_en=datetime('now') WHERE empresa_id=? AND periodo_mes=? AND periodo_anio=?",(empresa_id,mes,anio))
    db.commit(); db.close()

def periodo_ya_confirmado(empresa_id, mes, anio):
    db = get_db()
    row = db.execute("SELECT SUM(confirmado) as c, COUNT(*) as t FROM novedades WHERE empresa_id=? AND periodo_mes=? AND periodo_anio=?",(empresa_id,mes,anio)).fetchone()
    db.close()
    return row and row["t"] > 0 and row["c"] == row["t"]

# ── Documentos ───────────────────────────────────────────────────
DOCS_POR_ESTADO = {
    "I":   ["PREOCUPACIONAL","SOLICITUD_INGRESO","DNI","ALTA_TEMPRANA","EDET"],
    "E":   ["CERTIF_MEDICO"],
    "V":   ["NOTIF_VACACIONES"],
    "ART": ["INFORME_ART","PARTE_MEDICO","RECIBO_FIRMADO"],
    "B":   ["TELEGRAMA","LIQ_FINAL","ULT_RECIBO","CERTIF_ART80","ANSES_PS62","ARDA","CERTIF_BANCARIA","ACUSE_RECIBO"],
}
DOC_LABELS = {
    "PREOCUPACIONAL":"Examen preocupacional","SOLICITUD_INGRESO":"Solicitud de ingreso",
    "DNI":"DNI frente y dorso","ALTA_TEMPRANA":"Alta temprana AFIP","EDET":"EDET con domicilio",
    "CERTIF_MEDICO":"Certificado médico","NOTIF_VACACIONES":"Notif. vacaciones firmada",
    "INFORME_ART":"Informe ART","PARTE_MEDICO":"Parte médico","RECIBO_FIRMADO":"Recibo firmado",
    "TELEGRAMA":"Telegrama","LIQ_FINAL":"Liquidación final","ULT_RECIBO":"Último recibo",
    "CERTIF_ART80":"Certif. Art.80 LCT","ANSES_PS62":"ANSES PS6.2","ARDA":"Constancia ARDA",
    "CERTIF_BANCARIA":"Certif. bancaria","ACUSE_RECIBO":"Acuse recibo firmado",
}
ESTADO_EMPL_LABEL = {"I":"Incorporación","E":"Enfermedad","V":"Vacaciones","ART":"ART","B":"Baja"}

def subir_documento(empresa_id,empleado_id,tipo_doc,estado_empl,nombre_arch,datos_bin,mime_type,origen,usuario_id):
    db = get_db()
    cur = db.execute("INSERT INTO documentos (empresa_id,empleado_id,tipo_doc,estado_empl,nombre_arch,datos,mime_type,origen,estado_doc,subido_por) VALUES (?,?,?,?,?,?,?,?,'subido',?)",
        (empresa_id,empleado_id,tipo_doc,estado_empl,nombre_arch,datos_bin,mime_type,origen,usuario_id))
    doc_id = cur.lastrowid; db.commit(); db.close(); return doc_id

def get_documentos_empleado(empresa_id,empleado_id):
    db = get_db()
    rows = db.execute("SELECT d.*,u.nombre as subido_nombre,u.rol as subido_rol FROM documentos d LEFT JOIN usuarios u ON u.id=d.subido_por WHERE d.empresa_id=? AND d.empleado_id=? ORDER BY d.subido_en DESC",(empresa_id,empleado_id)).fetchall()
    db.close(); return rows

def get_documento(doc_id):
    db = get_db()
    row = db.execute("SELECT * FROM documentos WHERE id=?",(doc_id,)).fetchone()
    db.close(); return row

def revisar_documento(doc_id,estado,comentario,usuario_id):
    db = get_db()
    db.execute("UPDATE documentos SET estado_doc=?,comentario=?,revisado_por=?,revisado_en=datetime('now') WHERE id=?",(estado,comentario,usuario_id,doc_id))
    db.commit(); db.close()

def get_documentos_pendientes_empresa(empresa_id):
    db = get_db()
    rows = db.execute("SELECT d.*,e.nombre as emp_nombre,e.legajo,u.nombre as subido_nombre,u.rol as subido_rol FROM documentos d JOIN empleados e ON e.id=d.empleado_id LEFT JOIN usuarios u ON u.id=d.subido_por WHERE d.empresa_id=? AND d.estado_doc='subido' ORDER BY d.subido_en DESC",(empresa_id,)).fetchall()
    db.close(); return rows

def get_resumen_docs_empleado(empresa_id,empleado_id,estado_empl):
    requeridos = DOCS_POR_ESTADO.get(estado_empl,[])
    if not requeridos: return [],[]
    db = get_db()
    subidos = db.execute("SELECT tipo_doc,estado_doc,nombre_arch,subido_en FROM documentos WHERE empresa_id=? AND empleado_id=? AND estado_empl=? AND estado_doc!='rechazado' ORDER BY subido_en DESC",(empresa_id,empleado_id,estado_empl)).fetchall()
    db.close()
    tipos_ok = {r["tipo_doc"] for r in subidos}
    pendientes = [t for t in requeridos if t not in tipos_ok]
    return list(subidos), pendientes

# ── Audit log ────────────────────────────────────────────────────
def registrar_log(usuario_id,accion,detalle,ip):
    db = get_db()
    db.execute("INSERT INTO audit_log (usuario_id,accion,detalle,ip) VALUES (?,?,?,?)",(usuario_id,accion,detalle,ip))
    db.commit(); db.close()

def get_audit_log(limite=200):
    db = get_db()
    rows = db.execute("SELECT l.*,u.email,u.nombre as u_nombre FROM audit_log l LEFT JOIN usuarios u ON u.id=l.usuario_id ORDER BY l.ts DESC LIMIT ?",(limite,)).fetchall()
    db.close(); return rows

def get_usuarios_todos():
    db = get_db()
    rows = db.execute("SELECT * FROM usuarios ORDER BY rol,nombre").fetchall()
    db.close(); return rows

def crear_usuario(email,password,nombre,rol,empresas_ids):
    db = get_db()
    cur = db.execute("INSERT INTO usuarios (email,password,nombre,rol) VALUES (?,?,?,?)",(email,generate_password_hash(password),nombre,rol))
    uid = cur.lastrowid
    for eid in empresas_ids: db.execute("INSERT OR IGNORE INTO usuario_empresa VALUES (?,?)",(uid,eid))
    db.commit(); db.close(); return uid
